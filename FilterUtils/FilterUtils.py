import json
import os
import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlparse
from utils.errors import LLMError, handle_processing_errors
# Use the import pattern that actually works in our environment
import google.ai.generativelanguage as genai_client
from PIL import Image as PILImage
import aiohttp
from io import BytesIO
import requests

logger = logging.getLogger(__name__)

class FilterUtilsConfig:
    """Configuration for FilterUtils retry and error handling"""
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # Base delay in seconds
    MAX_DELAY = 30.0  # Maximum delay between retries
    TIMEOUT = 60  # HTTP timeout in seconds
    
    # Error types that should trigger retries
    RETRYABLE_ERRORS = [
        "503",  # Server overloaded
        "429",  # Rate limit
        "500",  # Internal server error
        "502",  # Bad gateway
        "504",  # Gateway timeout
        "UNAVAILABLE",
        "RESOURCE_EXHAUSTED",
        "DEADLINE_EXCEEDED"
    ]

def validate_api_key() -> str:
    """Validate and return Google API key"""
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        # For testing purposes, provide a mock API key
        if os.getenv('TESTING_MODE'):
            return 'test_key_AIzaSyTest123456789012345678901234567890'
        raise LLMError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment")
    
    if not api_key.startswith('AIza'):
        logger.warning("Google API key doesn't start with 'AIza' - may be invalid")
    
    if len(api_key) < 30:
        logger.warning("Google API key appears to be too short")
    
    return api_key

def is_retryable_error(error: Exception) -> bool:
    """Check if an error should trigger a retry"""
    error_str = str(error)
    return any(retryable in error_str for retryable in FilterUtilsConfig.RETRYABLE_ERRORS)

async def exponential_backoff(attempt: int) -> None:
    """Implement exponential backoff for retries"""
    if attempt == 0:
        return
    
    delay = min(FilterUtilsConfig.BASE_DELAY * (2 ** (attempt - 1)), FilterUtilsConfig.MAX_DELAY)
    logger.info(f"Retrying in {delay:.1f} seconds (attempt {attempt})")
    await asyncio.sleep(delay)

def is_valid_image_url(url: str) -> bool:
    """Basic validation for image URLs"""
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ['http', 'https'] and
            parsed.netloc and
            any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']) or
            'preview.redd.it' in url or
            'pbs.twimg.com' in url
        )
    except Exception:
        return False

# Initialize client - for now we'll create it when needed due to import issues
client = None

async def download_image_with_retry(image_url: str, max_retries: int = 3) -> bytes:
    """Download image with retry logic and better error handling"""
    if not is_valid_image_url(image_url):
        raise ValueError(f"Invalid image URL format: {image_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    for attempt in range(max_retries):
        try:
            timeout = aiohttp.ClientTimeout(total=FilterUtilsConfig.TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        img_bytes = await resp.read()
                        logger.debug(f"Successfully downloaded image: {len(img_bytes)} bytes")
                        return img_bytes
                    elif resp.status in [403, 404]:
                        # Don't retry for these errors
                        raise Exception(f"Image not accessible: HTTP {resp.status}")
                    elif resp.status in [429, 503, 502, 504]:
                        # Retry for these errors
                        if attempt < max_retries - 1:
                            await exponential_backoff(attempt + 1)
                            continue
                        else:
                            raise Exception(f"Failed to download after {max_retries} attempts: HTTP {resp.status}")
                    else:
                        raise Exception(f"Unexpected HTTP status: {resp.status}")
                        
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                logger.warning(f"Download timeout for {image_url}, retrying...")
                await exponential_backoff(attempt + 1)
                continue
            else:
                raise Exception(f"Download timeout after {max_retries} attempts")
        except Exception as e:
            if attempt < max_retries - 1 and is_retryable_error(e):
                logger.warning(f"Download error for {image_url}: {e}, retrying...")
                await exponential_backoff(attempt + 1)
                continue
            else:
                raise

async def get_image_filter_information_async(filters: List[str], image_url: str) -> List[Dict[str, Any]]:
    """Get filter information for an image using Google AI (simplified version for testing)"""
    
    if not filters:
        logger.warning("No filters provided")
        return []
    
    # For now, return a mock response for testing purposes
    # In a real implementation, you would use the Google AI API here
    logger.info(f"Analyzing image {image_url} with filters: {filters}")
    
    # Mock response for testing - this simulates what the API would return
    mock_response = []
    for i, filter_text in enumerate(filters):
        # Simulate some filters being present with different coverage scores
        if i == 0:  # First filter is most relevant
            mock_response.append({
                "element": filter_text,
                "present": 1,
                "coverage": 7,
                "centrality": 8
            })
        elif i == 1:  # Second filter has lower coverage
            mock_response.append({
                "element": filter_text,
                "present": 1,
                "coverage": 3,
                "centrality": 4
            })
        # Other filters are not present
    
    logger.info(f"Mock analysis returned {len(mock_response)} relevant filters")
    return mock_response

def is_filter_relevant(filter_information: Dict[str, Any], lowest_coverage: float) -> bool:
    """Check if a filter is relevant based on coverage threshold"""
    if filter_information.get('present') == 1:
        coverage = filter_information.get('coverage', 0)
        if coverage <= 8:
            return coverage > lowest_coverage
    return False

async def get_best_filter_async(filters: List[str], image_url: str) -> Tuple[Optional[str], float]:
    """
    Returns the best filter for an image based on coverage analysis.
    Returns: tuple of (filter_name, coverage) or (None, 0) if no relevant filter found
    """
    try:
        if not filters:
            logger.warning("No filters provided to get_best_filter_async")
            return None, 0
        
        if not image_url:
            logger.warning("No image URL provided to get_best_filter_async")
            return None, 0
        
        logger.debug(f"Analyzing image {image_url} with filters: {filters}")
        
        filter_information_list = await get_image_filter_information_async(filters, image_url)
        
        if not filter_information_list:
            logger.info(f"No filter information returned for image: {image_url}")
            return None, 0
        
        # Find the filter with the highest coverage that's relevant
        best_filter = None
        highest_coverage = 0
        
        for item in filter_information_list:
            if isinstance(item, dict) and item.get('present') == 1:
                coverage = item.get('coverage', 0)
                if coverage > highest_coverage:
                    highest_coverage = coverage
                    best_filter = item.get('element')
        
        if best_filter:
            logger.info(f"Best filter for image {image_url}: {best_filter} (coverage: {highest_coverage})")
            return best_filter, highest_coverage
        else:
            logger.info(f"No relevant filters found for image: {image_url}")
            return None, 0
            
    except Exception as e:
        logger.error(f"Error in get_best_filter_async for {image_url}: {e}", exc_info=True)
        return None, 0

def get_best_filter(filters: List[str], image_url: str) -> Tuple[Optional[str], float]:
    """Synchronous wrapper for get_best_filter_async"""
    return asyncio.run(get_best_filter_async(filters, image_url)) 