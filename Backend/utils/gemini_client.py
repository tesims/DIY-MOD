"""
Gemini client initialization with fallback support for both old and new SDK
"""
import os
import logging

logger = logging.getLogger(__name__)

# Try to import the new SDK first, then fall back to the old one
GEMINI_AVAILABLE = False
USING_NEW_SDK = False

try:
    # Try new SDK first
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
    USING_NEW_SDK = True
    logger.info("Using new Google Gen AI SDK")
except ImportError:
    try:
        # Fall back to old SDK
        import google.generativeai as genai
        from google.generativeai import types
        GEMINI_AVAILABLE = True
        USING_NEW_SDK = False
        logger.info("Using legacy Google Generative AI SDK")
    except ImportError:
        logger.warning("No Google AI SDK available")

def create_client(api_key: str = None):
    """Create a Gemini client with the available SDK"""
    if not GEMINI_AVAILABLE:
        raise ImportError("No Google AI SDK available. Install with: pip install google-genai or google-generativeai")
    
    if not api_key:
        api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("No API key provided and GOOGLE_API_KEY not set in environment")
    
    if USING_NEW_SDK:
        # New SDK: create client
        return genai.Client(api_key=api_key)
    else:
        # Old SDK: configure and return module
        genai.configure(api_key=api_key)
        return genai

def generate_content(client, model_name: str, contents, **kwargs):
    """Generate content with the appropriate SDK method"""
    if USING_NEW_SDK:
        # New SDK method
        config_args = {}
        if 'generation_config' in kwargs:
            config_args.update(kwargs['generation_config'])
        if 'safety_settings' in kwargs:
            config_args['safety_settings'] = kwargs['safety_settings']
        
        config = types.GenerateContentConfig(**config_args) if config_args else None
        
        return client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config
        )
    else:
        # Old SDK method
        model = genai.GenerativeModel(model_name)
        return model.generate_content(contents, **kwargs)

async def generate_content_async(client, model_name: str, contents, **kwargs):
    """Generate content asynchronously with the appropriate SDK method"""
    if USING_NEW_SDK:
        # New SDK async method
        config_args = {}
        if 'generation_config' in kwargs:
            config_args.update(kwargs['generation_config'])
        if 'safety_settings' in kwargs:
            config_args['safety_settings'] = kwargs['safety_settings']
        
        config = types.GenerateContentConfig(**config_args) if config_args else None
        
        return await client.aio.models.generate_content(
            model=model_name,
            contents=contents,
            config=config
        )
    else:
        # Old SDK async method
        model = genai.GenerativeModel(model_name)
        return await model.generate_content_async(contents, **kwargs)

# Export what's available
__all__ = ['GEMINI_AVAILABLE', 'USING_NEW_SDK', 'genai', 'types', 'create_client', 'generate_content', 'generate_content_async'] 