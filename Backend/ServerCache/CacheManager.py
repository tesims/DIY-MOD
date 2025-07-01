'''This file contains a method to try and reuse previously computed values from the cache.'''
import os
import json
from dotenv import load_dotenv
# Mock implementation for testing - avoid problematic Google imports
try:
    import google.ai.generativelanguage as genai_client
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    
from .Cache import Cache
from .RedisCache import RedisCache

class MockGeminiCacheClient:
    """Mock Gemini client for cache similarity matching"""
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def models_generate_content(self, model: str, contents: List[str], config: Dict = None) -> Dict:
        """Mock content generation to simulate a similarity match"""
        # For testing, we'll just return the first filter from the list
        # A real implementation would have more complex logic
        prompt = contents[0] if contents else ""
        try:
            # Extract list of strings from prompt
            filters_str = prompt.split("Here is a list of strings: ")[1].split(". From this list")[0]
            filters = [f.strip() for f in filters_str.split('.') if f.strip()]
            if filters:
                return {"candidates": [{"content": {"parts": [{"text": filters[0]}]}}]}
        except:
            pass
        return {"candidates": [{"content": {"parts": [{"text": ""}]}}]}

class ImageCacheManager():
    def __init__(self):
        load_dotenv()
        self.cache_sub_key_limit = 10
        self.cache: Cache = RedisCache()
        
        # Use mock client for testing if real one is not available
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("TESTING_MODE")
        if api_key and (GEMINI_AVAILABLE and not os.getenv("TESTING_MODE")):
            self.llm = genai_client.Client(api_key=api_key)
            self.model = "gemini-2.0-flash"
        else:
            self.llm = MockGeminiCacheClient(api_key="mock_key")
            self.model = "mock_model"

    def _get_filter_string(self, filters):
        # Handle both list of filters and a single filter string
        if isinstance(filters, str):
            filters = [filters]
            
        formatted_filters = []
        for f in filters:
            if f.endswith("."):
                formatted_filters.append(f.lower())
            else:
                formatted_filters.append(f.lower() + ".")
        return " ".join(formatted_filters)

    def _construct_llm_prompt(self, current_filters, new_filter):
        return [
            {
                "role": "user",
                "content": f'Here is a list of strings: {current_filters}. From this list return one string that matches the most with the string: {new_filter}. Only return the string from the list and nothing else. Also, if none of the items match, then return an empty string'
            }
        ]

    def _get_similar_filter_from_llm(self, llm_message_prompt):
        # Convert the message format to a single prompt
        prompt = "\n".join([msg["content"] for msg in llm_message_prompt])
        
        try:
            response = self.llm.models_generate_content(
                model=self.model,
                contents=[prompt],
            )
            return response["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            # Log the error and re-raise to be caught by caller
            print(f"Error calling LLM in CacheManager: {e}")
            raise

    def _get_value_of_similar_filter(self, current_value_dict, new_filter):
        # If LLM is not available, skip similarity matching
        if self.llm is None:
            return None
        
        current_filters = list(current_value_dict.keys())
        try:
            prompt = self._construct_llm_prompt(current_filters, new_filter)
            similar_filter = self._get_similar_filter_from_llm(prompt)
            return current_value_dict.get(similar_filter)
        except Exception as e:
            # If LLM call fails, gracefully return None
            print(f"Warning: LLM similarity matching failed: {e}")
            return None

    def _get_key(self, image_url, filters):
        return image_url + " " + self._get_filter_string(filters)

    def _add_sub_key_and_value(self, value_dict, sub_key, value):
        if len(value_dict) < self.cache_sub_key_limit:
            value_dict[sub_key] = value
        return value_dict
    
    def _get_existing_value_for_key(self, cache_key):
        value_json = self.cache.get(cache_key)
        if value_json is None:
            return None
        return json.loads(value_json)

    def _get_cache_transaction_details(self, cache_key, filters):
        filter_string = self._get_filter_string(filters)
        value_dict = self._get_existing_value_for_key(cache_key=cache_key)
        return filter_string, value_dict

    def get_processed_value_from_cache(self, image_url, filters):
        filter_string, value_dict = self._get_cache_transaction_details(cache_key=image_url, filters=filters)
        # Case where nothing has been stored for a key
        if value_dict is None:
            return None

        # Case for getting a similar filter key
        if not filter_string in value_dict:
            similar_filter_value = self._get_value_of_similar_filter(value_dict, filter_string)
            return similar_filter_value
        
        # Case where the filter string exists in the sub key dictionary
        return value_dict.get(filter_string)

    def set_processed_value_to_cache(self, image_url, filters, processed_url):
        filter_string, value_dict = self._get_cache_transaction_details(cache_key=image_url, filters=filters)
        if value_dict is None:
            value_dict = {}
        value_dict = self._add_sub_key_and_value(value_dict, filter_string, processed_url)

        return self.cache.set(image_url, json.dumps(value_dict))