import json
import asyncio
from .ObjectDetector import GroundingDINODetector
from .ImageConverter import OpenCVImageConverterFromURL, OpenCVImageConverterToURL
from .ImageModifier import BlurModifier
from FilterUtils import get_best_filter_async
from CartoonImager import make_image_replacement_gemini
from ServerCache import image_cache
from utils.monitoring import track_performance
from utils.errors import LLMError
import logging

logger = logging.getLogger(__name__)

image_detector = GroundingDINODetector()
image_to_url = OpenCVImageConverterToURL()
image_from_url = OpenCVImageConverterFromURL()
image_modifier = BlurModifier()

class ImageProcessor:
    @staticmethod
    def get_intervention_type(filter_obj):
        if not filter_obj:
            return None
        # Always use maximum intervention (image replacement) - intensity levels removed
        return 'edit_to_replace'

    @staticmethod
    def get_deferred_image_result(image_url, filters):
        return image_cache.get_processed_value_from_cache(image_url=image_url, filters=filters)

    @track_performance('process_image')
    async def process_image(self, image_url, filters, user_id=None):
        """Process an image to determine appropriate intervention"""
        if not image_url:
            logger.warning("No image URL provided to process_image")
            return {"image_url": "", "intervention_type": "error", "error": "No image URL provided"}
        
        if not filters:
            logger.warning("No filters provided to process_image")
            return {"image_url": image_url, "intervention_type": None}
        
        try:
            logger.debug(f"Starting image processing for {image_url} with {len(filters)} filters")
            
            # Get filter texts for analysis
            filter_texts = [f.filter_text for f in filters]
            
            # Call FilterUtils with improved error handling
            best_filter_name, best_filter_coverage = await get_best_filter_async(filter_texts, image_url)
            logger.debug(f"get_best_filter_async returned: name={best_filter_name}, coverage={best_filter_coverage}")

            if not best_filter_name:
                logger.debug(f"No best filter found, returning None intervention type")
                return {"image_url": image_url, "intervention_type": None}

            logger.debug(f"Best filter found: {best_filter_name}, looking for filter object")
            filter_obj = next((f for f in filters if f.filter_text == best_filter_name), None)
            logger.debug(f"Filter object found: {filter_obj is not None}")
            
            if not filter_obj:
                logger.warning(f"Filter object not found for filter name: {best_filter_name}")
                return {"image_url": image_url, "intervention_type": None}
            
            intervention_type = self.get_intervention_type(filter_obj)
            logger.debug(f"Intervention type determined: {intervention_type}")

            if not intervention_type:
                logger.debug(f"No intervention type, returning None intervention type")
                return {"image_url": image_url, "intervention_type": None}

            result = {
                "image_url": image_url,
                "best_filter_name": best_filter_name,
                "intervention_type": intervention_type,
            }

            if intervention_type in ["overlay", "blur"]:
                try:
                    bounding_boxes = await self.get_bounding_boxes_for_image(image_url, [best_filter_name])
                    result["bounding_boxes"] = bounding_boxes
                except Exception as e:
                    logger.error(f"Error getting bounding boxes for {image_url}: {e}")
                    result["bounding_boxes"] = "[]"
            
            elif intervention_type == "edit_to_replace":
                try:
                    task_data = json.dumps({
                        "url": image_url, 
                        "filter": filter_obj.filter_text,
                        "user_id": user_id or "unknown"
                    })
                    make_image_replacement_gemini.delay(task_data)
                    result.update({
                        "status": "DEFERRED",
                        "filters": [filter_obj.filter_text]
                    })
                except Exception as e:
                    logger.error(f"Error queuing image replacement task for {image_url}: {e}")
                    result.update({
                        "status": "ERROR",
                        "error": str(e)
                    })

            return result

        except LLMError as e:
            logger.error(f"LLM error processing image {image_url}: {e}")
            return {
                "image_url": image_url, 
                "intervention_type": "error", 
                "error": f"LLM error: {str(e)}"
            }
        except ValueError as e:
            logger.error(f"Invalid image URL or data for {image_url}: {e}")
            return {
                "image_url": image_url, 
                "intervention_type": "error", 
                "error": f"Invalid image: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error processing image {image_url}: {e}", exc_info=True)
            return {
                "image_url": image_url, 
                "intervention_type": "error", 
                "error": str(e)
            }

    @track_performance('get_bounding_boxes')
    async def get_bounding_boxes_for_image(self, image_url, filters):
        """Get bounding boxes for objects in an image"""
        if not image_url or not filters:
            logger.warning("Missing image_url or filters for bounding box detection")
            return "[]"
        
        cached_boxes = image_cache.get_processed_value_from_cache(image_url, filters)
        if cached_boxes:
            return cached_boxes
        
        try:
            image = await asyncio.to_thread(image_from_url.convert, image_url)
            if image is None:
                raise Exception("Image conversion failed")

            object_boxes = await asyncio.to_thread(image_detector.detect, image, filters)
            if object_boxes is None:
                raise Exception("Object detection failed")
            
            stringified_boxes = str(object_boxes)
            image_cache.set_processed_value_to_cache(image_url, filters, stringified_boxes)
            return stringified_boxes

        except Exception as e:
            logger.error(f"Error in get_bounding_boxes_for_image for {image_url}: {e}", exc_info=True)
            return "[]"
    