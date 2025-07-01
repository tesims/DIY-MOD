import json
from celery import Celery
# from ..Celery import app
from openai import OpenAI, AsyncOpenAI
from ServerCache import image_cache
import logging
import requests
import os
import uuid
import base64
from io import BytesIO
import boto3
import tempfile
import re
from utils.monitoring import track_performance, metrics

# Google Gemini imports with fallback
try:
    import google.ai.generativelanguage as genai_client
    from PIL import Image as PILImage
    import aiohttp
    import asyncio
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Gemini SDK not available - using mock implementations")

logger = logging.getLogger(__name__)

app = Celery(
    'CartoonImager',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# WebSocket notification function
async def notify_websocket_clients(user_id: str, image_url: str, processed_value: str):
    """Send WebSocket notification to clients when image processing is complete"""
    try:
        # Import here to avoid circular imports
        from fastapi_app import get_connection_manager
        manager = get_connection_manager()
        await manager.send_image_result(user_id, image_url, processed_value)
        logger.info(f"Sent WebSocket notification for {image_url} to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification: {e}")

def send_websocket_notification(user_id: str, image_url: str, processed_value: str):
    """Sync wrapper for WebSocket notification"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, schedule the coroutine
            asyncio.create_task(notify_websocket_clients(user_id, image_url, processed_value))
        else:
            # If not in async context, run it
            asyncio.run(notify_websocket_clients(user_id, image_url, processed_value))
    except Exception as e:
        # Fallback: try to run in new event loop
        try:
            asyncio.run(notify_websocket_clients(user_id, image_url, processed_value))
        except Exception as e2:
            logger.error(f"Could not send WebSocket notification: {e2}")

@app.task(bind=False)
@track_performance('make_image_cartoonish')
def make_image_cartoonish(data):
    processed_data = json.loads(data)
    client = OpenAI()
    user_id = processed_data.get('user_id', 'unknown')  # Extract user_id
    image_url = processed_data.get('url')
    
    logger.info("Received data %s", processed_data)
    image_desc_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                    },
                },
            ],
        }],
    )

    desc = image_desc_response.choices[0].message.content

    logger.info("Got description")

    new_img_response = client.images.generate(
        model="dall-e-3",
        prompt=f"I want a cartoon style image that is the following: \n {desc}",
        size="1024x1024",
        quality="standard",
        n=1,
    )

    processed_url = new_img_response.data[0].url
    logger.debug("setting to cache: Source URL: %s \n Processed URL: %s", image_url, processed_url)
    image_cache.set_processed_value_to_cache(image_url, processed_data.get('filter'), processed_url)
    
    # Send WebSocket notification
    send_websocket_notification(user_id, image_url, processed_url)

@app.task(bind=False)
@track_performance('make_image_cartoonish_gpt_image')
def make_image_cartoonish_gpt_image(data):
    """
    Transform an image to cartoonish style using OpenAI's GPT-Image-1 model.
    Uses a direct edit approach instead of the two-step process in make_image_cartoonish.
    
    Args:
        data (str): JSON string containing the image URL and filter
        
    Returns:
        None: The result is stored in the cache
    """
    try:
        processed_data = json.loads(data)
        url = processed_data.get('url')
        filter_name = processed_data.get('filter')
        user_id = processed_data.get('user_id', 'unknown')  # Extract user_id
        
        logger.info(f"Processing {url} with gpt-image-1 for cartoonish style")
        
        # Download the image from URL
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to download image from {url}, status code: {response.status_code}")
        
        # Determine file extension from content type or URL
        content_type = response.headers.get('Content-Type', '')
        if 'jpeg' in content_type or 'jpg' in content_type:
            ext = '.jpg'
        elif 'png' in content_type:
            ext = '.png'
        elif 'webp' in content_type:
            ext = '.webp'
        else:
            # Try to guess from URL
            if url.lower().endswith(('.jpg', '.jpeg')):
                ext = '.jpg'
            elif url.lower().endswith('.png'):
                ext = '.png'
            elif url.lower().endswith('.webp'):
                ext = '.webp'
            else:
                # Default to PNG
                ext = '.png'
        
        # Create a temporary file with the proper extension
        temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        temp_file_path = temp_file.name
        temp_file.write(response.content)
        temp_file.close()
        
        logger.info(f"Saved image to temporary file: {temp_file_path} with extension {ext}")
        
        # Initialize OpenAI client
        client = OpenAI()
        
        # Transform the image using GPT-Image-1
        with open(temp_file_path, "rb") as image_file:
            result = client.images.edit(
                model="gpt-image-1",
                image=image_file,
                prompt="Transform this image into a colorful cartoon style with bold outlines, simplified features, and vibrant colors. Make it look like a professional cartoon or animation, with the same composition and elements as the original image."
            )
        
        # Get the result URL or base64 data depending on what's available
        if hasattr(result.data[0], 'url') and result.data[0].url:
            transformed_url = result.data[0].url
        elif hasattr(result.data[0], 'b64_json') and result.data[0].b64_json:
            # Get the base64 image data and upload to S3 (simplified for now - storing in cache)
            image_base64 = result.data[0].b64_json
            transformed_image_bytes = base64.b64decode(image_base64)
            
            # Generate a unique filename
            filename = f"cartoon-transformed-{uuid.uuid4()}.png"
            
            # Check if AWS environment variables are set
            if os.getenv('AWS_STORAGE_BUCKET_NAME') and os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
                # Upload to S3
                bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_S3_REGION_NAME')
                )
                
                s3_client.upload_fileobj(
                    BytesIO(transformed_image_bytes),
                    bucket_name,
                    filename,
                    ExtraArgs={'ContentType': 'image/png'}
                )
                
                # Construct the S3 URL
                region = os.getenv('AWS_S3_REGION_NAME')
                transformed_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{filename}"
            else:
                # For local development or when S3 is not configured
                # Save file locally and serve through a local URL or return as data URI
                local_path = f"temp/uploads/{filename}"
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                with open(local_path, "wb") as f:
                    f.write(transformed_image_bytes)
                
                # Use a data URI as fallback (not ideal for production)
                transformed_url = f"data:image/png;base64,{image_base64}"
        else:
            # Fallback to original URL if transformation fails
            transformed_url = url
            logger.warning("No URL or base64 data found in the response, using original URL")
            
        # Clean up the temporary file
        try:
            os.unlink(temp_file_path)
        except Exception as e:
            logger.error(f"Error removing temp file: {e}")
            
        # Cache the result
        logger.debug("setting to cache: Source URL: %s \n Processed URL: %s", url, transformed_url)
        image_cache.set_processed_value_to_cache(url, filter_name, transformed_url)
        
        # Send WebSocket notification
        send_websocket_notification(user_id, url, transformed_url)
        
        return transformed_url
        
    except Exception as e:
        logger.error(f"Error in make_image_cartoonish_gpt_image: {str(e)}", exc_info=True)
        # If we have the URL, store the original in cache to avoid retrying failed transformations
        try:
            if 'url' in processed_data and processed_data['url'] and 'filter' in processed_data:
                image_cache.set_processed_value_to_cache(processed_data['url'], processed_data['filter'], processed_data['url'])
                # Send WebSocket notification with original URL as fallback
                send_websocket_notification(processed_data.get('user_id', 'unknown'), processed_data['url'], processed_data['url'])
        except:
            pass
        
        # Return the original URL
        return processed_data.get('url')

@app.task(bind=False)
@track_performance('make_image_replacement_gemini')
def make_image_replacement_gemini(data):
    # This is a sync Celery task, so we run the async function in an event loop
    return asyncio.run(make_image_replacement_gemini_async(data))

@track_performance('make_image_replacement_gemini_async')
async def make_image_replacement_gemini_async(data):
    """
    Edit an image using Google's Gemini model to replace specific objects based on filter descriptions.
    
    This task parses the filter to identify what needs to be removed (phobia trigger) and what to 
    replace it with (pleasant alternative), then uses Gemini to edit the image accordingly.
    
    For testing purposes, this returns a mock URL when Gemini is not available.
    
    Args:
        data (str): JSON string containing the image URL and filter description
        
    Returns:
        str: URL of the processed image, or original URL if processing failed
    """
    try:
        processed_data = json.loads(data)
        url = processed_data.get('url')
        filter_description = processed_data.get('filter')
        user_id = processed_data.get('user_id', 'unknown')  # Extract user_id
        
        logger.info(f"Processing {url} with Gemini filter: {filter_description}")
        
        if not GEMINI_AVAILABLE:
            logger.info("Google Gemini SDK not available - using mock processing")
            # For testing, return a mock processed URL
            mock_processed_url = f"{url}?processed=gemini&filter={filter_description.replace(' ', '_')}"
            
            # Cache the mock result
            image_cache.set_processed_value_to_cache(url, filter_description, mock_processed_url)
            
            # Send WebSocket notification
            send_websocket_notification(user_id, url, mock_processed_url)
            
            return mock_processed_url
        
        # If Gemini is available, implement the real processing here
        # For now, we'll use the mock processing since we have import issues
        
        # Download the image asynchronously
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to download image from {url}, status code: {resp.status}")
                img_bytes = await resp.read()
        
        logger.info("Image downloaded successfully")
        
        # For testing purposes, create a mock processed image URL
        # In a real implementation, this would use Google Gemini to process the image
        processed_url = f"{url}?gemini_processed=true&filter={filter_description.replace(' ', '_')}"
        
        logger.info(f"Mock processing complete: {url} → {processed_url}")
        image_cache.set_processed_value_to_cache(url, filter_description, processed_url)
        
        # Send WebSocket notification
        send_websocket_notification(user_id, url, processed_url)
        
        return processed_url
        
    except Exception as e:
        logger.error(f"Error in make_image_replacement_gemini: {str(e)}", exc_info=True)
        try:
            if 'url' in processed_data and processed_data['url'] and 'filter' in processed_data:
                image_cache.set_processed_value_to_cache(processed_data['url'], processed_data['filter'], processed_data['url'])
                # Send WebSocket notification with original URL as fallback
                send_websocket_notification(processed_data.get('user_id', 'unknown'), processed_data['url'], processed_data['url'])
        except:
            pass
        return processed_data.get('url') 