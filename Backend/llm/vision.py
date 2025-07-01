import os
import base64
import logging
import json
from typing import Dict, List, Any, Optional
# Google GenAI imports
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    
from utils.errors import LLMError, handle_processing_errors
from utils.config import ConfigManager

logger = logging.getLogger(__name__)

class MockGeminiVisionClient:
    """Mock Gemini Vision client for testing purposes"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        logger.info("Using mock Gemini Vision client for testing")
        
    def models_generate_content(self, model: str, contents: List[Dict], config: Dict = None) -> Dict:
        """Mock content generation to simulate vision analysis"""
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "text": "Based on the image, I've identified potential content to filter.",
                            "filter_data": {
                                "filter_text": "Mocked filter from image",
                                "content_type": "image"
                            },
                            "options": ["Create filter", "Refine filter", "Cancel"]
                        })
                    }]
                }
            }]
        }

class VisionFilterCreator:
    """
    Process images using Google Gemini to understand content for filter creation.
    This class handles converting images to base64 and preparing them
    for processing with the vision model.
    """
    def __init__(self):
        """Initialize the vision processor with API key and configuration"""
        config = ConfigManager()
        llm_config = config.get_llm_config()
        
        # Validate API key or use mock
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('TESTING_MODE', '')
        if not api_key:
            if os.getenv('TESTING_MODE'):
                api_key = 'test_key_mock'
            else:
                raise LLMError("GOOGLE_API_KEY not found in environment")
        
        # Initialize client
        if GEMINI_AVAILABLE and not os.getenv('TESTING_MODE'):
            self.client = genai.Client(api_key=api_key)
            logger.info("Using real Gemini client")
        else:
            self.client = MockGeminiVisionClient(api_key=api_key)
            logger.info("Using mock VisionFilterCreator client")
        
        # Get model and parameters from config
        self.vision_model = llm_config.filter_model
        self.max_tokens = llm_config.max_tokens
        self.temperature = llm_config.temperature
        
        logger.info(f"Initialized VisionFilterCreator using {self.vision_model}")
        
    def _encode_image(self, image_path: str) -> str:
        """Convert an image file to base64 encoding"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            raise LLMError(f"Failed to encode image: {e}")
    
    @handle_processing_errors
    def process_image(self, image_path: str, message: str = "", history: List[Dict] = None, user_id: str = None) -> Dict[str, Any]:
        """
        Process an image to understand what content should be filtered
        
        Args:
            image_path: Path to the image file
            message: Optional text message from the user
            history: Optional conversation history
            user_id: Optional user ID for tracking
            
        Returns:
            Dict containing filter information extracted from the image
        """
        try:
            # Encode the image to base64
            base64_image = self._encode_image(image_path)
            
            # Construct system prompt
            system_prompt = "Analyze image for filter creation"
            
            # Prepare prompt with image
            prompt = system_prompt
            if message:
                prompt += f"\n\nUser message: {message}"
            
            # Log the request
            logger.info(f"Sending vision request for user {user_id}")
            
            # Call the vision model
            response = self.client.models_generate_content(
                model=self.vision_model,
                contents=[
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": base64_image
                                }
                            }
                        ]
                    }
                ]
            )
            
            # Process response
            response_text = response["candidates"][0]["content"]["parts"][0]["text"]
            logger.debug(f"Vision model response: {response_text[:100]}...")
            
            try:
                # Try to parse as JSON
                json_data = json.loads(response_text)
                return json_data
            except json.JSONDecodeError:
                # If not valid JSON, wrap it in our format
                logger.warning("Vision response was not valid JSON, wrapping it")
                return {
                    "text": response_text,
                    "filter_data": {
                        "filter_text": "Extracted from image",
                        "content_type": "all"
                    },
                    "options": ["Please describe what you want to filter"]
                }
                
        except Exception as e:
            logger.error(f"Error processing image: {e}", exc_info=True)
            raise LLMError(f"Error processing image: {e}")