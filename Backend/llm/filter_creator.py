"""Filter creation and management through LLM"""
from typing import Dict, Optional
import logging
import os
import json
# Google GenAI imports
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from database import add_filter
from datetime import datetime, timedelta
from .prompts import FILTER_CREATION_PROMPT
from utils import safe_json_loads

logger = logging.getLogger(__name__)

class MockGeminiFilterCreatorClient:
    """Mock Gemini client for filter creation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        logger.info("Using mock Gemini FilterCreator client")
        
    async def aio_models_generate_content(self, model: str, contents: List[str], config: Dict = None) -> Dict:
        """Mock content generation to simulate filter creation"""
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "filter_text": "Mocked filter",
                            "filter_type": "keyword",
                            "content_type": "all",
                            "intensity": 3,
                            "is_temporary": False,
                            "duration": "permanent",
                            "filter_metadata": {
                                "context": "Mocked context",
                                "related_terms": ["mock", "test"]
                            }
                        })
                    }]
                }
            }]
        }

class FilterCreator:
    """Handles creation and processing of content filters using LLM"""
    
    def __init__(self):
        # Validate API key or use mock
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('TESTING_MODE', '')
        if not api_key:
            if os.getenv('TESTING_MODE'):
                api_key = 'test_key_mock'
            else:
                raise EnvironmentError("GOOGLE_API_KEY not found in environment")
        
        # Initialize client
        if GEMINI_AVAILABLE and not os.getenv('TESTING_MODE'):
            self.client = genai.Client(api_key=api_key)
            logger.info("Using real Gemini client")
        else:
            self.client = MockGeminiFilterCreatorClient(api_key=api_key)
            logger.info("Using mock FilterCreator client")
            
        self.model = "gemini-2.0-flash"  # Use Gemini model
        
    async def create_filter(self, text: str) -> Optional[Dict]:
        """Use LLM to create structured filter data from text"""
        try:
            prompt = f"{FILTER_CREATION_PROMPT}\n\nUser Input: {text}"
            
            response = await self.client.aio_models_generate_content(
                model=self.model,
                contents=[prompt],
            )
            
            response_text = response["candidates"][0]["content"]["parts"][0]["text"]
            filter_data = safe_json_loads(response_text)
            
            if not filter_data:
                return None
                
            return self._process_filter_data(filter_data)
            
        except Exception as e:
            logger.error(f"Error creating filter: {e}", exc_info=True)
            return None
            
    def store_filter(self, user_id: str, filter_data: Dict) -> bool:
        """Process and store filter in database"""
        try:
            # Calculate expiration if temporary
            expires_at = None
            if filter_data.get('is_temporary'):
                duration = filter_data.get('duration')
                if duration == "1 day":
                    expires_at = datetime.now() + timedelta(days=1)
                elif duration == "1 week":
                    expires_at = datetime.now() + timedelta(weeks=1)
                elif duration == "1 month":
                    expires_at = datetime.now() + timedelta(days=30)
            
            # Store in database with processed metadata
            filter_metadata = {
                "context": filter_data.get('filter_metadata', {}).get('context'),
                "related_terms": filter_data.get('filter_metadata', {}).get('related_terms', []),
                "category_specific": filter_data.get('filter_metadata', {}).get('category_specific', {}),
                "filter_type": filter_data.get('filter_type'),
                "content_type": filter_data.get('content_type'),
                "is_temporary": filter_data.get('is_temporary'),
                "expires_at": expires_at.isoformat() if expires_at else None
            }
            
            add_filter(
                user_id=user_id,
                filter_data={
                    "filter_text": filter_data['filter_text'],
                    "intensity": filter_data['intensity'],
                    "filter_metadata": filter_metadata
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Error storing filter: {e}", exc_info=True)
            return False
            
    def _process_filter_data(self, data: Dict) -> Optional[Dict]:
        """Validate and process filter data"""
        required_fields = ['filter_text', 'filter_type', 'content_type', 'intensity']
        if not all(field in data for field in required_fields):
            logger.error(f"Missing required fields in filter data: {data}")
            return None
            
        if not isinstance(data['intensity'], int) or not 1 <= data['intensity'] <= 5:
            logger.error(f"Invalid intensity value: {data['intensity']}")
            return None
            
        return data