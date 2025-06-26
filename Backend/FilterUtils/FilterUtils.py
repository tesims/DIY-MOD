import json
import os
import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlparse
from utils.errors import LLMError, handle_processing_errors
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from PIL import Image as PILImage
import aiohttp
from io import BytesIO

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
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise LLMError("GOOGLE_API_KEY not found in environment")
    
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

# Initialize client with validated API key
try:
    api_key = validate_api_key()
    client = genai.Client(api_key=api_key)
    logger.info("Google Gemini client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Google Gemini client: {e}")
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
    """Get filter information for an image with comprehensive retry logic"""
    if not client:
        logger.error("Google Gemini client not initialized")
        return []
    
    if not filters:
        logger.warning("No filters provided")
        return []
    
    for attempt in range(FilterUtilsConfig.MAX_RETRIES):
        try:
            # Download image with retry
            img_bytes = await download_image_with_retry(image_url)
            
            # Load and validate image
            try:
                image = PILImage.open(BytesIO(img_bytes))
                image.verify()  # Verify image integrity
                image = PILImage.open(BytesIO(img_bytes))  # Reload after verify
            except Exception as e:
                raise ValueError(f"Invalid image data: {e}")
            
            prompt = f"""
You are a helpful assistant whose task is to analyze an image and evaluate the presence and importance of a list of elements.

For each element, provide:
1. 'present': 1 if the element is clearly visible in the image, otherwise 0.
2. 'coverage': a score from 0 to 10 representing how much of the image's area the element visually occupies (0 = very little, 10 = dominant).
3. 'centrality': a score from 0 to 10 representing how important the element is to the main idea or theme of the image (0 = minor background detail, 10 = core/only subject of the image).

The elements to analyze are: {filters}.

Please respond with a JSON array of objects, each including: 'element', 'present', 'coverage', and 'centrality'.
Example format: [{"element": "guitar", "present": 1, "coverage": 8, "centrality": 9}]
"""
            
            # Make API call with retry
            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, image],
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    max_output_tokens=2048,
                    temperature=0.2,
                )
            )
            
            # Parse response
            content = response.candidates[0].content.parts[0].text
            
            # Try to find JSON array in the response
            start_index = content.find('[')
            end_index = content.rfind(']') + 1
            
            if start_index != -1 and end_index > start_index:
                json_response = content[start_index:end_index]
                parsed_response = json.loads(json_response)
            else:
                # If no array found, try parsing the entire content
                parsed_response = json.loads(content)
            
            # Validate and process response
            if isinstance(parsed_response, list):
                valid_entries = []
                logger.info("Entries present in the image:")
                
                for entry in parsed_response:
                    if isinstance(entry, dict) and all(key in entry for key in ['element', 'present', 'coverage']):
                        if entry.get('present', 0) != 0:
                            valid_entries.append(entry)
                            logger.info(f"- {entry.get('element', 'unknown')} (coverage: {entry.get('coverage', 0)})")
                
                logger.info(f"Found {len(valid_entries)} valid entries")
                return valid_entries
            else:
                logger.warning(f"Unexpected response format: {type(parsed_response)}")
                return []
                
        except (ClientError, ServerError) as e:
            error_code = getattr(e, 'status_code', 'unknown')
            error_msg = str(e)
            
            # Handle specific Google API errors
            if "API key not valid" in error_msg or "INVALID_ARGUMENT" in error_msg:
                logger.error(f"Invalid Google API key - check your GOOGLE_API_KEY environment variable")
                raise LLMError("Invalid Google API key")
            
            elif is_retryable_error(e) and attempt < FilterUtilsConfig.MAX_RETRIES - 1:
                logger.warning(f"Google API error (attempt {attempt + 1}): {error_code} - {error_msg}")
                await exponential_backoff(attempt + 1)
                continue
            else:
                logger.error(f"Google API error after {attempt + 1} attempts: {error_code} - {error_msg}")
                return []
                
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error parsing JSON response: {e}")
            if attempt < FilterUtilsConfig.MAX_RETRIES - 1:
                await exponential_backoff(attempt + 1)
                continue
            else:
                return []
                
        except Exception as e:
            if is_retryable_error(e) and attempt < FilterUtilsConfig.MAX_RETRIES - 1:
                logger.warning(f"Error processing image (attempt {attempt + 1}): {e}")
                await exponential_backoff(attempt + 1)
                continue
            else:
                logger.error(f"Error in get_image_filter_information_async after {attempt + 1} attempts: {e}", exc_info=True)
                return []
    
    return []

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

# print(get_best_filter(["guitar", "cat", "dog"], "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSZiVs94nLMLkp_Xi4148Ux9zMZ-9dP7p8xSw&s"))