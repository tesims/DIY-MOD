from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import json
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any, Union
import logging
from pydantic import BaseModel, validator, field_validator

# Import existing modules
from processors import RedditProcessor, TwitterProcessor
from database import (
    get_user_filters, add_filter, remove_filter, update_filter,
)
from ServerCache import image_cache
from llm import ContentFilter
from llm.chat import FilterCreationChat
from llm.vision import VisionFilterCreator
from utils import setup_logging, ConfigManager

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path, override=True)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize configuration and shared resources
config = ConfigManager()
chat_processor = FilterCreationChat()
vision_processor = VisionFilterCreator()

# WebSocket processing handler
async def handle_websocket_processing(websocket: WebSocket, user_id: str, message: dict):
    """Handle feed processing requests over WebSocket"""
    try:
        request_id = message.get("requestId")
        feed_data = message.get("data", {})
        
        if not request_id:
            await websocket.send_json({
                "type": "error",
                "error": "Missing requestId",
                "timestamp": datetime.now().isoformat()
            })
            return
            
        logger.info(f"Processing WebSocket feed request {request_id} for user {user_id}")
        
        # Extract processing parameters
        url = feed_data.get("url", "")
        platform = feed_data.get("platform", "unknown")
        response_data = feed_data.get("response", "")
        
        if not response_data:
            await websocket.send_json({
                "type": "error",
                "requestId": request_id,
                "error": "Missing response data",
                "timestamp": datetime.now().isoformat()
            })
            return
        
        # Create feed_info structure expected by processors
        feed_info = {
            "response": response_data
        }
        
        # Process based on platform
        start_time = datetime.now()
        
        if 'reddit' in platform.lower() or 'reddit' in url.lower():
            processor = RedditProcessor(user_id, feed_info, url)
            processed_response = await processor.work_on_feed()
        elif 'twitter' in platform.lower() or 'x.com' in url.lower():
            processor = TwitterProcessor(user_id, feed_info, url)
            processed_response = await processor.work_on_feed()
        else:
            # Default to Reddit processor
            processor = RedditProcessor(user_id, feed_info, url)
            processed_response = await processor.work_on_feed()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Send response back through WebSocket
        await websocket.send_json({
            "type": "processing_response",
            "requestId": request_id,
            "data": {
                "feed": {
                    "response": processed_response
                },
                "processingTime": f"{processing_time:.2f}s"
            },
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"WebSocket processing completed for {request_id} in {processing_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Error in WebSocket processing: {e}")
        await websocket.send_json({
            "type": "error",
            "requestId": message.get("requestId"),
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")
        
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")
        
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections for a specific user"""
        if user_id in self.active_connections:
            disconnected_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected_connections.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected_connections:
                self.disconnect(conn, user_id)
                
    async def send_image_result(self, user_id: str, image_url: str, processed_value: str):
        """Send processed image result to user"""
        message = {
            "type": "image_processed",
            "image_url": image_url,
            "processed_value": processed_value,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_to_user(user_id, message)
        logger.info(f"Sent image result to user {user_id}: {image_url}")

# Global connection manager
manager = ConnectionManager()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("FastAPI application starting up...")
    
    # Create temp directory
    upload_folder = os.path.join(os.path.dirname(__file__), "temp", "uploads")
    os.makedirs(upload_folder, exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("FastAPI application shutting down...")

# Create FastAPI app
app = FastAPI(
    title="DIY Content Moderation API",
    description="AI-powered content moderation with real-time WebSocket updates",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
origins = [
    "https://reddit.com",
    "https://*.reddit.com",
    "https://www.reddit.com",
    "https://x.com", 
    "https://*.x.com",
    "https://twitter.com",
    "https://*.twitter.com",
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:5001",
    "https://api.rayhan.io"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class FeedRequest(BaseModel):
    user_id: str
    url: str
    data: Union[str, dict]  # Accept both string and dict to handle different client formats
    tab_id: Optional[str] = None
    extension_version: Optional[str] = None
    useBatching: Optional[bool] = False

class FilterRequest(BaseModel):
    user_id: str
    filter_text: str
    content_type: str = "all"
    intensity: int = 5  # Default to maximum intensity - intensity levels removed
    duration: str = "permanent"
    is_temporary: Optional[bool] = None
    expires_at: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    history: List[Dict] = []
    user_id: str = "default_user"

class FilterUpdateRequest(BaseModel):
    user_id: str
    filter_text: Optional[str] = None
    content_type: Optional[str] = None
    intensity: Optional[int] = 5  # Default to maximum intensity - intensity levels removed
    duration: Optional[str] = None

# Utility functions
PLATFORM_PROCESSORS = {
    'reddit': RedditProcessor,
    'twitter': TwitterProcessor
}

PLATFORM_RESPONSE_FORMAT = {
    'reddit': ".html",
    'twitter': ".json"
}

def get_platform_from_url(url: str) -> Optional[str]:
    if 'reddit.com' in url:
        return 'reddit'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    else:
        return None

# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and listen for messages
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message from {user_id}: {data}")
            
            try:
                message = json.loads(data)
                
                # Handle processing requests
                if message.get("type") == "process_feed":
                    await handle_websocket_processing(websocket, user_id, message)
                
                # Handle other message types
                elif message.get("type") == "connection":
                    await websocket.send_json({
                        "type": "connection_ack",
                        "message": "WebSocket connection established",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Default echo response for other messages
                else:
                    await websocket.send_json({
                        "type": "echo",
                        "message": f"Received: {data}",
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# HTTP endpoints
@app.get("/ping")
async def ping():
    """Health check endpoint"""
    logger.info("Received ping from extension")
    return {
        "status": "success",
        "message": "DIY-MOD FastAPI server is running",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/get_feed")
async def process_feed(request: FeedRequest):
    """Process a social media feed"""
    try:
        # Create data directory for request logging
        data_dir = Path(__file__).parent / "data" / "requests"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Log request metadata
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        req_id = f"{str(request.user_id)[:4]}_{timestamp}"
        request_dir = data_dir / req_id
        request_dir.mkdir(exist_ok=True)
        
        # Log the incoming request for debugging
        logger.info(f"Processing feed request for user {request.user_id} from {request.url}")
        logger.debug(f"Request data type: {type(request.data)}")
        logger.debug(f"Request data preview: {str(request.data)[:200]}...")
        
        # Parse the JSON data string or handle dict
        try:
            # Handle empty string case
            if not request.data:
                raise HTTPException(status_code=400, detail="Data field cannot be empty")
            
            # If data is already a dict, use it directly
            if isinstance(request.data, dict):
                data = request.data
            else:
                # If data is a string, try to parse it as JSON
                if request.data.strip() == '':
                    raise HTTPException(status_code=400, detail="Data field cannot be empty")
                data = json.loads(request.data)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for data: {request.data[:100] if isinstance(request.data, str) else str(request.data)[:100]}...")
            raise HTTPException(status_code=400, detail=f"Invalid JSON in data field: {e}")
        
        # Ensure data is a dictionary
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Data field must be a JSON object")
            
        feed_info = data.get('feed_info')
        if not feed_info:
            raise HTTPException(status_code=400, detail="No feed_info in data")

        # Get platform
        platform = get_platform_from_url(request.url)
        if not platform:
            raise HTTPException(status_code=400, detail="Unsupported platform in URL")
        
        # Save the feed data
        in_file = "in_feed" + PLATFORM_RESPONSE_FORMAT.get(platform, ".html")
        with open(request_dir / in_file, 'w', encoding='utf-8') as f:
            f.write(feed_info.get('response', ''))

        # Get appropriate processor
        processor_class = PLATFORM_PROCESSORS.get(platform)
        if not processor_class:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
            
        # Process feed
        processor = processor_class(user_id=request.user_id, feed_info=feed_info, url=request.url)
        modified_feed = await processor.work_on_feed()
        
        # Log response
        out_file = "out_feed" + PLATFORM_RESPONSE_FORMAT.get(platform, ".html")
        with open(request_dir / out_file, 'w', encoding='utf-8') as f:
            f.write(modified_feed)
            
        logger.info(f"Successfully processed feed for user {request.user_id}")
        return {
            'status': 'success',
            'feed': {'response': modified_feed}
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error processing feed for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/filters")
async def get_filters(user_id: str):
    """Get user's content filters"""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
        
    filters = get_user_filters(user_id)
    logger.info(f"Loaded {len(filters)} filters for user {user_id}")
    return {
        "status": "success",
        "message": f"Found {len(filters)} filters",
        "filters": filters
    }

@app.post("/filters")
async def create_filter(request: FilterRequest):
    """Create a new content filter"""
    # Set is_temporary explicitly based on duration
    is_temporary = request.duration != 'permanent'
    
    # Calculate expiration for temporary filters
    filter_data = request.dict()
    filter_data['is_temporary'] = is_temporary
    
    # Always set intensity to maximum level (5) - intensity levels removed
    filter_data['intensity'] = 5
    
    if is_temporary:
        from datetime import timedelta
        duration = request.duration
        
        if duration == 'day':
            filter_data['expires_at'] = datetime.now() + timedelta(days=1)
        elif duration == 'week':
            filter_data['expires_at'] = datetime.now() + timedelta(weeks=1)
        elif duration == 'month':
            filter_data['expires_at'] = datetime.now() + timedelta(days=30)
        
        logger.debug(f"Creating temporary filter with duration {duration}, expires_at: {filter_data['expires_at']}")
    else:
        filter_data['expires_at'] = None
        
    content_filter = ContentFilter(**filter_data)
    filter_id = add_filter(request.user_id, content_filter.model_dump())
    
    return {
        "status": "success",
        "message": "Filter created successfully",
        "filter_id": filter_id
    }

@app.put("/filters/{filter_id}")
async def update_filter_endpoint(filter_id: int, request: FilterUpdateRequest):
    """Update an existing content filter"""
    filter_data = {k: v for k, v in request.dict().items() if v is not None}
    
    # Always set intensity to maximum level (5) - intensity levels removed
    filter_data['intensity'] = 5
    
    content_filter = ContentFilter(**filter_data)
    
    if update_filter(request.user_id, filter_id, content_filter.model_dump()):
        return {
            "status": "success",
            "message": "Filter updated successfully"
        }
    raise HTTPException(status_code=404, detail="Filter not found")

@app.delete("/filters/{filter_id}")
async def delete_filter_endpoint(filter_id: int, user_id: str):
    """Delete a content filter"""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
        
    if remove_filter(user_id, filter_id):
        return {
            "status": "success",
            "message": "Filter deleted successfully"
        }
    raise HTTPException(status_code=404, detail="Filter not found")

@app.post("/chat")
async def chat(request: ChatRequest):
    """Process chat messages and return LLM response"""
    try:
        # Add user_id to history if not present in latest message
        if request.history and isinstance(request.history[-1], dict) and 'user_id' not in request.history[-1]:
            request.history[-1]['user_id'] = request.user_id
            
        response = chat_processor.process_chat(request.message, request.history, request.user_id)
        return {
            'status': 'success',
            'user_id': request.user_id,
            **response
        }
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/image")
async def chat_with_image(
    image: UploadFile = File(...),
    message: str = Form(""),
    history: str = Form("[]"),
    user_id: str = Form("default_user")
):
    """Process image uploads for filter creation"""
    try:
        # Parse history
        try:
            history_data = json.loads(history)
        except json.JSONDecodeError:
            history_data = []
            
        # Generate unique filename
        file_ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        upload_folder = os.path.join(os.path.dirname(__file__), "temp", "uploads")
        file_path = os.path.join(upload_folder, unique_filename)
        
        # Save the file temporarily
        with open(file_path, "wb") as buffer:
            content = await image.read()
            buffer.write(content)
        
        logger.info(f"Saved uploaded image to {file_path}")
        
        try:
            # Process the image with GPT-4V
            response = vision_processor.process_image(
                image_path=file_path,
                message=message,
                history=history_data,
                user_id=user_id
            )
            
            return {
                'status': 'success',
                'user_id': user_id,
                **response
            }
        finally:
            # Clean up - remove the temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        logger.error(f"Image chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_img_result")
async def get_img_result(img_url: str, filters: str):
    """Get processed image result (legacy endpoint for backward compatibility)"""
    if not img_url or not filters:
        raise HTTPException(status_code=400, detail="img_url and filters parameters are required")
    
    try:
        # Parse the filters parameter - it comes as a JSON string from the browser
        try:
            parsed_filters = json.loads(filters)
            # If it's a list with one item, use that item directly for cache lookup
            if isinstance(parsed_filters, list) and len(parsed_filters) == 1:
                filter_for_cache = parsed_filters[0]
            else:
                # Fallback to the original filters string
                filter_for_cache = filters
        except json.JSONDecodeError:
            # If parsing fails, use the original string
            filter_for_cache = filters
        
        result = image_cache.get_processed_value_from_cache(image_url=img_url, filters=filter_for_cache)
        logger.debug(f"Image Polling Result: \nImage URL: {img_url}\nFilters (original): {filters}\nFilters (parsed): {filter_for_cache}\nResult: {result}")
        
        if result:
            return {
                "status": "COMPLETED",
                "processed_value": result
            }

        return {
            "status": "NOT FOUND"
        }
    except Exception as e:
        logger.error(f"Error in get_img_result for {img_url}: {str(e)}")
        # Return a proper JSON response even on error
        return {
            "status": "ERROR",
            "error": str(e)
        }

# Function to send image results via WebSocket
async def notify_image_processed(user_id: str, image_url: str, processed_value: str):
    """Function to be called by Celery workers when image processing is complete"""
    await manager.send_image_result(user_id, image_url, processed_value)

# Make the connection manager available for Celery workers
def get_connection_manager():
    return manager

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=5000, reload=True) 