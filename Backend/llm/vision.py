import os
import base64
import logging
import json
from typing import Dict, List, Any, Optional
from google import genai
from google.genai import types
from utils.errors import LLMError, handle_processing_errors
from utils.config import ConfigManager

logger = logging.getLogger(__name__)

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
        
        # Validate API key
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise LLMError("GOOGLE_API_KEY not found in environment")
            
        self.client = genai.Client(api_key=api_key)
        
        # Get model and parameters from config
        self.vision_model = llm_config.filter_model  # Use filter_model from config
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
            system_prompt = """
            You are a helpful assistant that analyzes images to understand content that a user might want to filter 
            from their social media. The user is trying to create a content filter for their DIY-MOD browser 
            extension that blocks, blurs, or rewrites content they don't want to see on social media.
            
            Your job is to:
            1. Analyze the image to understand what the user might want to filter
            2. Identify potential topics, themes, or content types present in the image that could be filtered
            3. Ask clarifying questions if needed
            4. Suggest a filter text that accurately describes what the user wants to filter
            
            DO NOT discuss potentially harmful uses of content filtering. Focus ONLY on helping the user 
            avoid content they personally don't wish to see.
            
            Respond in JSON format with: 
            1. "text" - a message to the user about what you found
            2. "filter_data" - with keys "filter_text" and "content_type" (one of: "text", "image", "all")
            3. "options" - suggested next steps as array of strings
            """
            
            # Prepare prompt with image
            prompt = system_prompt
            if message:
                prompt += f"\n\nUser message: {message}"
            
            # Log the request
            logger.info(f"Sending vision request for user {user_id}")
            
            # Call the Gemini vision model
            response = self.client.models.generate_content(
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
                ],
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
            )
            
            # Process response
            response_text = response.candidates[0].content.parts[0].text
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