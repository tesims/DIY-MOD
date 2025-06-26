"""Platform-agnostic models for content handling and API responses"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

# Content Models
class ContentFilter(BaseModel):
    """Content filter configuration"""
    filter_text: str
    intensity: int
    filter_metadata: Dict[str, Any] = {}  # Renamed from metadata

class FilterMatch(BaseModel):
    """Result of content filter matching"""
    matched_filter_ids: List[int]
    confidence_scores: Dict[str, float]

class Post(BaseModel):
    """Base model for all social media posts"""
    id: str
    title: Optional[str] = None
    body: Optional[str] = None
    platform: str
    created_at: datetime
    metadata: Dict[str, Any] = {}  # Keep as metadata since this is Pydantic model
    processed_title: Optional[str] = None
    processed_body: Optional[str] = None

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
        title_match = re.search(r'\[TITLE\](.*?)\[/TITLE\]', processed_text,re.DOTALL)
        body_match = re.search(r'\[BODY\](.*?)\[/BODY\]', processed_text, re.DOTALL)
        
        if title_match:
            self.processed_title = title_match.group(1)
        if body_match:
            self.processed_body = body_match.group(1)

class ProcessingResult(BaseModel):
    """Result of content processing"""
    original: Post
    processed: Optional[Post] = None
    matched_filters: List[ContentFilter] = []
    max_intensity: int = 0
    error: Optional[str] = None

# API Response Models
class ChatResponse(BaseModel):
    """Chat interaction response"""
    text: str
    type: str = "message"  # message|error|clarify|intensity|duration
    options: List[str] = []
    filter_data: Optional[Dict[str, Any]] = None

class FeedResponse(BaseModel):
    """Feed processing response"""
    status: str = "success"
    feed: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class FilterResponse(BaseModel):
    """Filter management response"""
    status: str = "success"
    filters: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None