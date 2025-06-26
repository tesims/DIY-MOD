from . import prompts
import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel
from utils.config import ConfigManager
from utils.errors import LLMError, handle_processing_errors
from utils import safe_json_loads, validate_llm_response
from datetime import datetime
logger = logging.getLogger(__name__)

class ContentFilter(BaseModel):
    filter_text: str
    intensity: int
    content_type: str = 'all'
    is_temporary: bool = False
    expires_at: Optional[datetime] = None
    filter_metadata: Dict[str, Any] = {}

    def to_llm_format(self) -> Dict[str, Any]:
        """Convert filter to LLM-friendly format with only relevant fields"""
        return {
            "filter_text": self.filter_text,
            "intensity": self.intensity,
            "content_type": self.content_type,
            "filter_metadata": self.filter_metadata
        }

class FilterMatch(BaseModel):
    matched_filter_ids: List[int]
    confidence_scores: Dict[str, float]

class LLMProcessor:
    def __init__(self):
        config = ConfigManager()
        llm_config = config.get_llm_config()
        
        # Validate API key
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise LLMError("GOOGLE_API_KEY not found in environment")
            
        # Use Gemini client exclusively
        self.llm_client = genai.Client(api_key=api_key)
        self.content_model = llm_config.content_model
        self.temperature = llm_config.temperature
        self.max_tokens = llm_config.max_tokens
        
        # Get processing configuration
        proc_config = config.get_processing_config()
        self.mode = proc_config.default_mode
        
        # Define markers for content modification
        self.MARKERS = {
            'blur': ("__BLUR_START__", "__BLUR_END__"),
            'overlay': ("__OVERLAY_START__", "__OVERLAY_END__"),
            'rewrite': ("__REWRITE_START__", "__REWRITE_END__")
        }
        
        # Confidence thresholds - adjust based on mode
        self.CONFIDENCE_THRESHOLDS = {
            'balanced': {
                1: 0.8,
                2: 0.8,
                3: 0.7,
                4: 0.7,
                5: 0.7
            },
            'aggressive': {
                1: 0.7,
                2: 0.6,
                3: 0.5,
                4: 0.4,
                5: 0.3
            }
        }[self.mode]
        
        logger.info(f"Initialized LLMProcessor in {self.mode} mode using {self.content_model}")
        
    async def _gemini_request(self, prompt: str, is_json: bool = False) -> str:
        """Reusable Gemini request function with error handling"""
        try:
            config = types.GenerateContentConfig(
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            if is_json:
                config.response_mime_type = 'application/json'

            response = await self.llm_client.aio.models.generate_content(
                model=self.content_model,
                contents=[prompt],
                config=config
            )
            return response.candidates[0].content.parts[0].text
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}")
            raise LLMError(f"Gemini API error: {e}") from e

    @handle_processing_errors
    async def evaluate_content(self, text: str, filters: List[ContentFilter]) -> List[ContentFilter]:
        """Evaluate if content matches any filters"""
        if not text.strip() or not filters:
            logger.debug("Empty content or no filters to evaluate")
            return []
            
        logger.debug(f"Evaluating content in {self.mode} mode against {len(filters)} filters")
        
        if self.mode == 'aggressive':
            filters = self._combine_similar_filters(filters)
            
        try:
            prompt = f"{prompts.FILTER_EVALUATION_PROMPT}\n\nUser Input: {json.dumps({'text': text, 'filters': [f.to_llm_format() for f in filters]})}"
            response_text = await self._gemini_request(prompt, is_json=True)
            
            response_data = validate_llm_response(
                response_text,
                ['matched_filter_ids', 'confidence_scores']
            )
            
            if not response_data:
                raise LLMError("Invalid response format from Gemini", {"response": response_text[:200]})
            
            matches = FilterMatch(**response_data)
            
            validated_matches = []
            for idx in matches.matched_filter_ids:
                if idx >= len(filters):
                    logger.warning(f"Gemini returned invalid filter index: {idx}")
                    continue
                    
                filter_data = filters[idx]
                confidence = matches.confidence_scores.get(str(idx), 0.0)
                threshold = self.CONFIDENCE_THRESHOLDS.get(filter_data.intensity, 0.7)
                
                if confidence >= threshold:
                    validated_matches.append(filter_data)
                    logger.debug(f"Filter '{filter_data.filter_text}' matched with {confidence:.2f} confidence (threshold: {threshold})")
                else:
                    logger.debug(f"Filter '{filter_data.filter_text}' below threshold: {confidence:.2f} < {threshold}")
            
            if validated_matches:
                logger.info(f"Found {len(validated_matches)} valid matches out of {len(matches.matched_filter_ids)} total matches")
                    
            return validated_matches
            
        except LLMError as e:
            logger.warning(f"Gemini evaluation failed, falling back to basic matching: {e}")
            return self._basic_filter_matching(text, filters)
        except Exception as e:
            raise LLMError(f"Error in content evaluation: {e}", {
                "text_sample": text[:100],
                "filter_count": len(filters)
            })

    def _validate_markers(self, text: str) -> str:
        """Validate marker structure and fix any issues"""
        try:
            # Check for nested markers of same type
            for marker_type in self.MARKERS.values():
                start, end = marker_type
                # Find all start and end positions
                starts = [m.start() for m in re.finditer(re.escape(start), text)]
                ends = [m.start() for m in re.finditer(re.escape(end), text)]
                
                if len(starts) != len(ends):
                    logger.warning(f"Mismatched markers found: {len(starts)} starts and {len(ends)} ends")
                    # Remove all markers of this type and re-add outermost
                    text = text.replace(start, "").replace(end, "")
                    text = f"{start}{text}{end}"
                    
                # Check for correct nesting
                for s, e in zip(starts, ends):
                    inner_starts = [i for i in starts if s < i < e]
                    if inner_starts:
                        logger.warning(f"Nested markers found, fixing...")
                        # Keep only outermost markers
                        text = text.replace(start, "", len(inner_starts))
                        text = text.replace(end, "", len(inner_starts))
            
            # Ensure TITLE/BODY tags are preserved
            for tag in ['TITLE', 'BODY']:
                tag_pattern = f'\\[{tag}\\](.*?)\\[/{tag}\\]'
                matches = list(re.finditer(tag_pattern, text))
                for match in matches:
                    # Extract content with potential markers
                    full_match = match.group(0)
                    content = match.group(1)
                    # Preserve markers inside section but ensure they don't wrap the tags
                    text = text.replace(full_match, f'[{tag}]{content}[/{tag}]')
            
            return text
            
        except Exception as e:
            logger.error(f"Error validating markers: {e}")
            return text

    @handle_processing_errors
    async def process_content(self, text: str, intensity: int, matched_filters: List[ContentFilter]) -> str:
        """Process content based on intensity level and mode"""
        if not text.strip() or not matched_filters:
            return text
            
        try:
            result = ""
            if self.mode == 'aggressive':
                result = await self._process_aggressive(text, intensity, matched_filters)
            else:
                if intensity < 3:
                    result = await self._process_low_intensity(text, matched_filters)
                elif intensity == 3:
                    result = await self._process_medium_intensity(text, matched_filters)
                else:
                    result = await self._process_high_intensity(text, matched_filters)
            return self._validate_markers(result)
        except Exception as e:
            logger.error(f"Gemini processing failed, falling back to basic processing: {e}")
            return self._validate_markers(self._basic_content_processing(text, intensity, matched_filters))

    def _basic_content_processing(self, text: str, intensity: int, filters: List[ContentFilter]) -> str:
        """Basic content processing without LLM when more sophisticated processing fails"""
        try:
            title_match = re.search(r'\[TITLE\](.*?)\[/TITLE\]', text, re.DOTALL)
            body_match = re.search(r'\[BODY\](.*?)\[/BODY\]', text, re.DOTALL)
            
            result = text
            if intensity < 3:
                # For low intensity, blur exact filter text matches
                if title_match:
                    title_content = title_match.group(1)
                    processed_title = self._apply_basic_blur(title_content, filters)
                    result = result.replace(title_match.group(0), f'[TITLE]{processed_title}[/TITLE]')
                    
                if body_match:
                    body_content = body_match.group(1)
                    processed_body = self._apply_basic_blur(body_content, filters)
                    result = result.replace(body_match.group(0), f'[BODY]{processed_body}[/BODY]')
                    
                if not (title_match or body_match):
                    result = self._apply_basic_blur(text, filters)
                    
            elif intensity == 3:
                # For medium intensity, add overlay
                warning = f"Warning: This content may contain sensitive topics"
                
                if title_match:
                    result = result.replace(
                        title_match.group(0),
                        f'[TITLE]{self.MARKERS["overlay"][0]}{warning}|{title_match.group(1)}{self.MARKERS["overlay"][1]}[/TITLE]'
                    )
                    
                if body_match:
                    result = result.replace(
                        body_match.group(0),
                        f'[BODY]{self.MARKERS["overlay"][0]}{warning}|{body_match.group(1)}{self.MARKERS["overlay"][1]}[/BODY]'
                    )
                    
                if not (title_match or body_match):
                    result = f'{self.MARKERS["overlay"][0]}{warning}|{text}{self.MARKERS["overlay"][1]}'
                    
            else:
                # For high intensity, mark sections for rewrite
                if title_match:
                    result = result.replace(
                        title_match.group(0),
                        f'[TITLE]{self.MARKERS["rewrite"][0]}Content filtered{self.MARKERS["rewrite"][1]}[/TITLE]'
                    )
                    
                if body_match:
                    result = result.replace(
                        body_match.group(0),
                        f'[BODY]{self.MARKERS["rewrite"][0]}Content filtered due to sensitive topics{self.MARKERS["rewrite"][1]}[/BODY]'
                    )
                    
                if not (title_match or body_match):
                    result = f'{self.MARKERS["rewrite"][0]}Content filtered due to sensitive topics{self.MARKERS["rewrite"][1]}'
            
            return result
            
        except Exception as e:
            logger.error(f"Error in basic content processing: {e}")
            return text
            
    def _apply_basic_blur(self, text: str, filters: List[ContentFilter]) -> str:
        """Apply blur markers to exact filter text matches"""
        result = text
        for f in filters:
            if f.filter_text in result:
                result = result.replace(
                    f.filter_text,
                    f"{self.MARKERS['blur'][0]}{f.filter_text}{self.MARKERS['blur'][1]}"
                )
        return result

    def _clean_llm_markers(self, text: str) -> str:
        """Remove any markers that might have been added by LLM"""
        for marker_type in self.MARKERS.values():
            start, end = marker_type
            # Remove any existing markers
            text = text.replace(start, "").replace(end, "")
        return text

    def _process_section_content(self, text: str, section_match: re.Match, marker_type: str, warning: str = None) -> str:
        """Process a section (TITLE or BODY) with proper marker handling"""
        content = section_match.group(1)
        # Clean any existing markers first
        content = self._clean_llm_markers(content)
        
        if marker_type == 'blur':
            return content  # Will be processed by _apply_blur_markers
        elif marker_type == 'overlay':
            overlay_warning = warning or "Warning: Filtered Content"
            return f'{self.MARKERS["overlay"][0]}{overlay_warning}|{content}{self.MARKERS["overlay"][1]}'
        elif marker_type == 'rewrite':
            return f'{self.MARKERS["rewrite"][0]}{content}{self.MARKERS["rewrite"][1]}'
        return content

    @handle_processing_errors
    async def _process_low_intensity(self, text: str, filters: List[ContentFilter]) -> str:
        """Process text for low intensity - blur specific words"""
        prompt = f"{prompts.LOW_INTENSITY_PROMPT}\n\nUser Input: {json.dumps({'text': text, 'filters': [f.to_llm_format() for f in filters]})}"
        response_text = await self._gemini_request(prompt)
        
        words_to_blur = [self._clean_llm_markers(word.strip()) for word in response_text.strip().split('\n') if word.strip()]
        
        # Process by preserving [TITLE] and [BODY] sections
        title_match = re.search(r'\[TITLE\](.*?)\[/TITLE\]', text, re.DOTALL)
        body_match = re.search(r'\[BODY\](.*?)\[/BODY\]', text, re.DOTALL)
        
        result = text
        if title_match:
            title_content = self._process_section_content(text, title_match, 'blur')
            processed_title = self._apply_blur_markers(title_content, words_to_blur)
            result = result.replace(title_match.group(0), f'[TITLE]{processed_title}[/TITLE]')
            
        if body_match:
            body_content = self._process_section_content(text, body_match, 'blur')
            processed_body = self._apply_blur_markers(body_content, words_to_blur)
            result = result.replace(body_match.group(0), f'[BODY]{processed_body}[/BODY]')
            
        if not (title_match or body_match):
            result = self._apply_blur_markers(self._clean_llm_markers(text), words_to_blur)
        
        logger.debug(f"_low_intensity_processed: {result}")
        return result

    def _apply_blur_markers(self, text: str, segments_to_blur: List[str]) -> str:
        """Apply blur markers to specific text segments"""
        result = text
        for segment in segments_to_blur:
            segment = segment.strip()
            if segment and segment in result:
                result = result.replace(
                    segment,
                    f"{self.MARKERS['blur'][0]}{segment}{self.MARKERS['blur'][1]}"
                )
        return result

    @handle_processing_errors
    async def _process_medium_intensity(self, text: str, filters: List[ContentFilter]) -> str:
        """Process text for medium intensity - add content warning overlay"""
        prompt = f"{prompts.MEDIUM_INTENSITY_PROMPT}\n\nUser Input: {json.dumps({'text': text, 'filters': [f.to_llm_format() for f in filters]})}"
        warning = self._clean_llm_markers(await self._gemini_request(prompt))
        
        # Process by preserving [TITLE] and [BODY] sections
        title_match = re.search(r'\[TITLE\](.*?)\[/TITLE\]', text, re.DOTALL)
        body_match = re.search(r'\[BODY\](.*?)\[/BODY\]', text, re.DOTALL)
        
        result = text
        if title_match:
            title_content = self._process_section_content(text, title_match, 'overlay', warning)
            result = result.replace(title_match.group(0), f'[TITLE]{title_content}[/TITLE]')
            
        if body_match:
            body_content = self._process_section_content(text, body_match, 'overlay', warning)
            result = result.replace(body_match.group(0), f'[BODY]{body_content}[/BODY]')
            
        if not (title_match or body_match):
            clean_text = self._clean_llm_markers(text)
            result = f'{self.MARKERS["overlay"][0]}{warning}|{clean_text}{self.MARKERS["overlay"][1]}'
        
        logger.debug(f"_medium_intensity_processed: {result}")
        return result

    @handle_processing_errors
    async def _process_high_intensity(self, text: str, filters: List[ContentFilter]) -> str:
        """Process text for high intensity - rewrite content"""
        prompt = f"{prompts.HIGH_INTENSITY_PROMPT}\n\nUser Input: {json.dumps({'text': text, 'filters': [f.to_llm_format() for f in filters]})}"
        rewritten = self._clean_llm_markers(await self._gemini_request(prompt))
        
        # Process by preserving [TITLE] and [BODY] sections
        title_match = re.search(r'\[TITLE\](.*?)\[/TITLE\]', rewritten, re.DOTALL)
        body_match = re.search(r'\[BODY\](.*?)\[/BODY\]', rewritten, re.DOTALL)
        
        result = rewritten
        if title_match and body_match:
            # Reconstruct with markers if both are present
            result = f"{self.MARKERS['rewrite'][0]}{title_match.group(1)}{self.MARKERS['rewrite'][1]}\n{self.MARKERS['rewrite'][0]}{body_match.group(1)}{self.MARKERS['rewrite'][1]}"
        elif title_match:
            result = f"{self.MARKERS['rewrite'][0]}{title_match.group(1)}{self.MARKERS['rewrite'][1]}"
        elif body_match:
            result = f"{self.MARKERS['rewrite'][0]}{body_match.group(1)}{self.MARKERS['rewrite'][1]}"
        else:
            result = f"{self.MARKERS['rewrite'][0]}{rewritten}{self.MARKERS['rewrite'][1]}"
        
        # Re-add section tags for frontend parsing
        final_result = ""
        if title_match:
            final_result += f"[TITLE]{title_match.group(1)}[/TITLE]\n"
        if body_match:
            final_result += f"[BODY]{body_match.group(1)}[/BODY]"
        
        processed_text = final_result if (title_match or body_match) else rewritten

        # Add rewrite markers to the processed text
        final_processed_text = re.sub(r'(\[TITLE\]|\[BODY\])(.*?)(\[\/TITLE\]|\[\/BODY\])',
                              r'\1' + self.MARKERS['rewrite'][0] + r'\2' + self.MARKERS['rewrite'][1] + r'\3',
                              processed_text,
                              flags=re.DOTALL)

        logger.debug(f"_high_intensity_processed: {final_processed_text}")
        return final_processed_text

    @handle_processing_errors
    async def _process_aggressive(self, text: str, intensity: int, filters: List[ContentFilter]) -> str:
        """Aggressively process content while preserving section boundaries"""
        prompt = f"{prompts.AGGRESSIVE_MODE_PROMPT}\n\nUser Input: {json.dumps({'text': text, 'intensity': intensity, 'filters': [f.to_llm_format() for f in filters]})}"
        rewritten = self._clean_llm_markers(await self._gemini_request(prompt))
        
        # Extract and process sections separately
        title_match = re.search(r'\[TITLE\](.*?)\[/TITLE\]', rewritten, re.DOTALL)
        body_match = re.search(r'\[BODY\](.*?)\[/BODY\]', rewritten, re.DOTALL)
        
        result = text
        if title_match:
            title_content = self._process_section_content(rewritten, title_match, 'rewrite')
            # For aggressive mode, add both overlay and rewrite
            processed_title = (
                f'{self.MARKERS["overlay"][0]}Warning: Filtered Content|'
                f'{title_content}'
                f'{self.MARKERS["overlay"][1]}'
            )
            result = result.replace(title_match.group(0), f'[TITLE]{processed_title}[/TITLE]')
            
        if body_match:
            body_content = self._process_section_content(rewritten, body_match, 'rewrite')
            # For aggressive mode, add both overlay and rewrite
            processed_body = (
                f'{self.MARKERS["overlay"][0]}Warning: Filtered Content|'
                f'{body_content}'
                f'{self.MARKERS["overlay"][1]}'
            )
            result = result.replace(body_match.group(0), f'[BODY]{processed_body}[/BODY]')
            
        if not (title_match or body_match):
            clean_text = self._clean_llm_markers(rewritten)
            result = (
                f'{self.MARKERS["overlay"][0]}Warning: Filtered Content|'
                f'{self.MARKERS["rewrite"][0]}{clean_text}{self.MARKERS["rewrite"][1]}'
                f'{self.MARKERS["overlay"][1]}'
            )
        
        logger.debug(f"_aggressive_processed: {result}")
        return result

    def _combine_similar_filters(self, filters: List[ContentFilter]) -> List[ContentFilter]:
        """Combine filters with similar themes for aggressive mode"""
        # This is a placeholder for a more sophisticated implementation
        # For now, it just returns the original filters
        return filters

    def _basic_filter_matching(self, text: str, filters: List[ContentFilter]) -> List[ContentFilter]:
        """Basic keyword matching as a fallback"""
        matched_filters = []
        lower_text = text.lower()
        for f in filters:
            if f.filter_text.lower() in lower_text:
                matched_filters.append(f)
        return matched_filters