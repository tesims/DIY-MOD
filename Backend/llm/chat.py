"""Handles chat-based filter creation and management"""
from typing import Dict, List
import json
import os
import logging
# Google GenAI imports
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    
from dotenv import load_dotenv
from .processor import ContentFilter
from .chat_system_prompt import CHAT_SYSTEM_PROMPT
from utils.config import ConfigManager
from database.operations import get_user_filters

logger = logging.getLogger(__name__)

class MockGeminiChatClient:
    """Mock Gemini client for chat functionality"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        logger.info("Using mock Gemini Chat client")
        
    def models_generate_content(self, model: str, contents: List[str], config: Dict = None) -> Dict:
        """Mock content generation to simulate a chat response"""
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "text": "This is a mocked response. How can I help you create a filter?",
                            "type": "clarify",
                            "options": ["Filter text", "Filter images"],
                            "conversation_state": "initial",
                            "filter_data": {}
                        })
                    }]
                }
            }]
        }

class FilterCreationChat:
    """Manages chat-based filter creation workflow"""
    
    def __init__(self):
        # Initialize config first
        config = ConfigManager()
        llm_config = config.get_llm_config()
        
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
            self.client = MockGeminiChatClient(api_key=api_key)
            logger.info("Using mock FilterCreationChat client")
            
        self.chat_model = llm_config.chat_model
        logger.info(f"Initialized FilterCreationChat with model {self.chat_model}")
        
    def process_chat(self, message: str, history: List[Dict], user_id: str = None) -> Dict:
        """Process chat messages and return structured response"""
        logger.debug(f"Processing message: {message}")
        logger.debug(f"History: {history}")
        
        # Get user's filter history if user_id is provided
        user_filters = []
        if user_id:
            try:
                user_filters = get_user_filters(user_id)
                logger.debug(f"Retrieved {len(user_filters)} existing filters for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to retrieve user filters: {e}")
        
        # Check if this is a retry after an error
        if message.lower() in ['try again', 'start over']:
            if message.lower() == 'start over':
                history = []
                logger.info("Starting new conversation")
            else:
                history = [msg for msg in history if not (
                    isinstance(msg.get('content'), dict) and 
                    msg.get('content', {}).get('type') == 'error'
                )]
                logger.info("Retrying after removing error messages")
        
        # Clean history
        cleaned_history = []
        for msg in history:
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                cleaned_history.append(msg)
        
        # Build system prompt with user context
        system_prompt = CHAT_SYSTEM_PROMPT
        if user_filters:
            filter_texts = [f["filter_text"] for f in user_filters]
            system_prompt += f"\n\nUser's existing filters: {', '.join(filter_texts[:5])}"
            if len(filter_texts) > 5:
                system_prompt += f" (and {len(filter_texts) - 5} more)"
        
        # Construct prompt for Gemini
        prompt = f"{system_prompt}\n\nConversation history:\n"
        for msg in cleaned_history[-5:]:  # Include last 5 messages for context
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if isinstance(content, dict):
                content = json.dumps(content)
            prompt += f"{role}: {content}\n"
        
        prompt += f"\nuser: {message}\n\nPlease respond in JSON format with the required fields."

        try:
            response = self.client.models_generate_content(
                model=self.chat_model,
                contents=[prompt]
            )
            
            raw_response = response["candidates"][0]["content"]["parts"][0]["text"]
            logger.debug(f"Raw Chat LLM response: {raw_response}")
            
            try:
                response_data = json.loads(raw_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                raise ValueError(f"Invalid JSON response from LLM: {raw_response[:100]}...")
                
            # Ensure required fields exist
            if not all(k in response_data for k in ['text', 'type']):
                raise ValueError("Missing required fields in response")
                
            if 'options' not in response_data:
                response_data['options'] = []
                
            return response_data
                
        except Exception as e:
            logger.error(f"Error in chat process: {e}", exc_info=True)
            
            # Get most recent valid filter data and conversation state
            prev_filter_data = None
            conversation_state = "initial"
            
            for msg in reversed(history):
                if isinstance(msg.get('content'), dict):
                    content = msg.get('content', {})
                    if 'filter_data' in content:
                        prev_filter_data = content['filter_data']
                        # Try to determine the conversation state
                        if content.get('type') == 'ready_for_config':
                            conversation_state = "filter_config"
                        break
            
            # Return error with preserved context
            return {
                "text": "Something went wrong. Would you like to try again?",
                "options": ["Try again", "Start over"],
                "type": "error",
                "conversation_state": conversation_state,
                **({"filter_data": prev_filter_data} if prev_filter_data else {})
            }

    def _determine_conversation_state(self, history: List[Dict]) -> str:
        """Determine the current state of conversation based on history"""
        if not history:
            return "initial"
            
        last_assistant_msg = next((msg for msg in reversed(history) 
                                if msg.get('role') == 'assistant'), None)
        if not last_assistant_msg:
            return "initial"
            
        content = last_assistant_msg.get('content', '').lower()
        
        if "should this apply to just images" in content:
            return "content_type"
        elif "how strict" in content:
            return "intensity"
        elif "how long" in content or "duration" in content:
            return "duration"
        
        return "initial"

    def _format_plain_text_response(self, text: str, state: str, history: List[Dict]) -> Dict:
        """Convert plain text response to proper JSON format based on conversation state"""

    # Get previous filter data if available
        prev_filter_data = {}
        for msg in reversed(history):
            if msg.get('role') == 'assistant' and isinstance(msg.get('content'), dict):
                filter_data = msg.get('content').get('filter_data', {})
                if filter_data:
                    prev_filter_data = filter_data
                    break
        
        if state == "intensity":
            return {
                "text": text,
                "type": "intensity",
                "options": ["Very strict", "Moderate", "Mild"],
                "filter_data": {
                    **prev_filter_data,
                    "content_type": "both" if "both" in history[-1].get('content', '').lower() else "image"
                }
            }
        elif state == "duration":
            return {
                "text": "How long would you like this filter to be active?",
                "type": "duration",
                "options": ["Permanent", "24 hours", "1 week"],
                "filter_data": prev_filter_data
            }
        
# Default response for other states
        return {
            "text": text,
            "type": "clarify",
            "options": []
        }