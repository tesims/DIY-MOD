import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import hashlib
from llm import LLMProcessor, ContentFilter
from database import get_user_filters, log_processing, log_processing_async
from utils import PreferenceManager, ConfigManager
from utils.errors import ProcessorError, handle_processing_errors
from utils.monitoring import track_performance, metrics
from ImageProcessor import ImageProcessor    
logger = logging.getLogger(__name__)

class Post:
    """Platform-agnostic post structure"""
    def __init__(
        self,
        id: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        platform: str = 'unknown',
        created_at: datetime = None,
        metadata: Dict[str, Any] = None,
        media_urls: List[str] = None
    ):
        self.id = id
        self.title = title
        self.body = body
        self.platform = platform
        self.created_at = created_at or datetime.now()
        self.metadata = metadata or {}
        self.processed_title = None
        self.processed_body = None
        self.media_urls = media_urls or []
        self.processed_media_urls = []

    def get_combined_text(self) -> str:
        """Get title and body combined with markers"""
        combined = ""
        if self.title:
            combined += f"[TITLE]{self.title}[/TITLE]\n"
        if self.body:
            combined += f"[BODY]{self.body}[/BODY]"
        return combined

    def update_processed_content(self, processed_text: str):
        """Update processed content from marked text"""
        import re
        title_match = re.search(r'\[TITLE\](.*?)\[/TITLE\]', processed_text, re.DOTALL)
        body_match = re.search(r'\[BODY\](.*?)\[/BODY\]', processed_text, re.DOTALL)
        logger.debug(f"Processed text: {processed_text} \n Title match:{title_match} \nBody match: {body_match}")
        if title_match:
            self.processed_title = title_match.group(1)
        if body_match:
            self.processed_body = body_match.group(1)

class ContentProcessor:
    """Base class for all platform-specific content processors"""
    
    def __init__(self, user_id: str, feed_info: Dict[str, Any], url: str):
        self.user_id = user_id
        self.feed_info = feed_info
        self.url = url
        self.filters = []
        self.max_workers = ConfigManager().get_processing_config().parallel_workers
        
        # Initialize LLM processor
        self.llm_processor = LLMProcessor()
        
        # Initialize image processor (using outsourced processor instead of local)
        self.image_processor = ImageProcessor()
        
        # Get user preferences
        prefs = PreferenceManager(user_id)
        self.mode = prefs.get_processing_config().get('mode', 'balanced')
        
        # Load filters
        self.refresh_filters()
        logger.info(f"Initialized {self.__class__.__name__} for user {user_id} in {self.mode} mode")

    @track_performance('refresh_filters')
    def refresh_filters(self):
        """Refresh filters from database"""
        self.filters = [
            ContentFilter(**f) for f in get_user_filters(self.user_id)
        ]
        logger.info(f"Loaded {len(self.filters)} active filters")

    @track_performance('process_post')
    @handle_processing_errors
    async def process_post(self, post: Post) -> Post:
        """Process a single post through LLM"""
        try:
            combined_text = post.get_combined_text()
            if not combined_text:
                return post
                
            # Create content hash for logging
            content_hash = hashlib.md5(combined_text.encode()).hexdigest()
            start_time = datetime.now().timestamp()
            
            # Process content
            matching_filters = await self.llm_processor.evaluate_content(combined_text, self.filters)
            
            if matching_filters:
                # Always use maximum intensity level (5) - intensity levels removed
                max_intensity = 5
                processed_text = await self.llm_processor.process_content(
                    combined_text, 
                    max_intensity,
                    matching_filters
                )
                post.update_processed_content(processed_text)
                
            # Get image processing configuration
            config = ConfigManager()
            img_config = config.get_processing_config().image_processing
            
            # Process images if available and enabled in config
            if post.media_urls and img_config.enabled:
                # Limit the number of images to process per post
                limited_media_urls = post.media_urls[:img_config.max_images_per_post]
                logger.info(f"Processing {len(limited_media_urls)} out of {len(post.media_urls)} images for post {post.id}")
                
                for img_url in limited_media_urls:
                    logger.debug(f"Processing image: {img_url}\nFilters: {[f.filter_text for f in self.filters]}")
                    
                    try:
                        image_process_result = await self.image_processor.process_image(img_url, self.filters, self.user_id)
                        image_url = image_process_result.get("image_url", img_url)
                        img_config = None
                        intervention_type = image_process_result.get("intervention_type")
                        
                        if intervention_type == "error":
                            error_msg = image_process_result.get('error', 'Unknown error')
                            logger.error(f"Error processing image {img_url}: {error_msg}")
                            
                            # Check if it's an API key error
                            if "API key" in error_msg or "LLM error" in error_msg:
                                logger.critical(f"Critical API error for image processing: {error_msg}")
                                # Continue processing other images but log the critical error
                            
                            # Skip this image but add it with error status for debugging
                            post.processed_media_urls.append({
                                "url": image_url,
                                "config": {
                                    "type": "error",
                                    "error": error_msg,
                                    "status": "ERROR"
                                }
                            })
                            continue
                        
                        elif not intervention_type:
                            logger.info(f"No relevant filters found for image: {img_url}")
                        
                        else:
                            best_filter_name = image_process_result.get('best_filter_name')
                            logger.info(f"Best filter for image {img_url}: {best_filter_name}")
                            
                            if intervention_type == "overlay" or intervention_type == "blur":
                                bounding_boxes = image_process_result.get("bounding_boxes")
                                # Parse the bounding_boxes string into a list of coordinates
                                try:
                                    parsed_boxes = eval(bounding_boxes) if bounding_boxes else []
                                    if parsed_boxes:
                                        # Create a configuration object with overlay type and coordinates
                                        img_config = {
                                            "type": intervention_type,
                                            "coordinates": [
                                                {"x1": box[0], "y1": box[1], "x2": box[2], "y2": box[3]} 
                                                for box in parsed_boxes
                                            ]
                                        }
                                        logger.info(f"Created image config with {len(parsed_boxes)} boxes")
                                except Exception as e:
                                    logger.error(f"Error parsing bounding boxes: {e}")
                            
                            elif intervention_type == "cartoonish":
                                img_config = {
                                    "type": intervention_type,
                                    "status": image_process_result.get("status"),
                                    "filters": image_process_result.get("filters"),
                                    "best_filter_name": best_filter_name
                                }
                            elif intervention_type == "edit_to_replace":
                                img_config = {
                                    "type": "cartoonish",
                                    "status": image_process_result.get("status", "DEFERRED"),
                                    "filters": image_process_result.get("filters"),
                                    "best_filter_name": best_filter_name
                                }
                            else:
                                logger.warning(f"Unknown intervention type: {intervention_type}")
                                img_config = {
                                    "type": "unknown",
                                    "intervention_type": intervention_type,
                                    "status": "UNKNOWN"
                                }
                        
                        # Store both URL and configuration in processed_media_urls
                        post.processed_media_urls.append({
                            "url": image_url,
                            "config": img_config
                        })
                        
                    except Exception as e:
                        logger.error(f"Unexpected error processing image {img_url}: {e}", exc_info=True)
                        # Add image with error status
                        post.processed_media_urls.append({
                            "url": img_url,
                            "config": {
                                "type": "error",
                                "error": str(e),
                                "status": "ERROR"
                            }
                        })
            
            # Log processing details using async logging
            processing_time = datetime.now().timestamp() - start_time
            await log_processing_async(
                user_id=self.user_id,
                platform=self.__class__.__name__.lower().replace('processor', ''),
                content_hash=content_hash,
                matched_filters=[f.filter_text for f in matching_filters],
                processing_time=processing_time,
                processing_metadata={
                    "mode": self.mode,
                }
            )
                
            return post
            
        except Exception as e:
            raise ProcessorError(f"Error processing post: {e}", {
                "post": str(post),
                "mode": self.mode
            })

    @track_performance('work_on_feed')
    async def work_on_feed(self) -> Any:
        """Process the entire feed - to be implemented by platform-specific classes"""
        raise NotImplementedError("Platform-specific classes must implement work_on_feed")

    def cleanup(self):
        """Clean up resources"""
        # Log final performance statistics
        metrics.log_all_stats()
        # Implement if needed by derived classes
        pass