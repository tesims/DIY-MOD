"""Database operations for filter management"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from contextlib import contextmanager
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from .models import Base, User, Filter, ProcessingLog, ContentType
from utils.config import ConfigManager
from utils.default_filters import get_default_filters

logger = logging.getLogger(__name__)

# Initialize database connection using config
config = ConfigManager().get_database_config()
engine = create_engine(
    config.url,
    pool_size=config.pool_size,
    max_overflow=config.max_overflow
)
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_db():
    """Provide a transactional scope around a series of operations"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()

def get_user_filters(user_id: str) -> List[Dict[str, Any]]:
    """Get active, non-expired filters for a user"""
    with get_db() as db:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id)
            db.add(user)
            db.flush()
            logger.info(f"Created new user {user_id} in database")
        else:
            user.last_active = func.now()
            logger.info(f"Found existing user {user_id} (created: {user.created_at}, last active: {user.last_active})")
            
        # If configured, add default filters for new user
        if not user.filters:  # Only add default filters if user has no filters
            config = ConfigManager()
            testing_config = config.get_testing_config()
            if testing_config.create_default_filters:  # Access attribute directly instead of using .get()
                logger.info(f"Creating default test filters for user {user_id}")
                for default_filter in get_default_filters():
                    new_filter = Filter(
                        user_id=user_id,
                        **default_filter
                    )
                    db.add(new_filter)
                db.flush()
        
        # Get active filters
        filters = (
            db.query(Filter)
            .filter(
                Filter.user_id == user_id,
                Filter.is_active == True,
                (Filter.expires_at.is_(None) | (Filter.expires_at > datetime.now()))
            )
            .all()
        )
        
        logger.info(f"Found {len(filters)} active filters for user {user_id}")
        
        return [
            {
                "id": f.id,
                "filter_text": f.filter_text,
                "filter_type": f.filter_type,
                "content_type": f.content_type.name if isinstance(f.content_type, ContentType) else f.content_type,  # Handle both enum and string cases
                "intensity": f.intensity,
                "filter_metadata": f.filter_metadata or {},
                "is_temporary": f.is_temporary,
                "expires_at": f.expires_at.isoformat() if f.expires_at else None
            }
            for f in filters
        ]

def add_filter(user_id: str, filter_data: Dict[str, Any]) -> int:
    """Add a new filter for a user"""
    with get_db() as db:
        # Check if user exists by explicitly querying
        user = db.query(User).filter(User.id == user_id).first()
        is_new_user = user is None or user.created_at is None
        
        if is_new_user:
            user = User(id=user_id)
            db.add(user)
            db.flush()
            
        # Convert content_type string to enum
        content_type_str = filter_data.get('content_type', 'all').lower()
        try:
            content_type = ContentType[content_type_str]
        except KeyError:
            logger.warning(f"Invalid content_type '{content_type_str}', defaulting to 'all'")
            content_type = ContentType.all
        
        # Create filter with renamed metadata field
        new_filter = Filter(
            user_id=user_id,
            filter_text=filter_data['filter_text'],
            filter_type=filter_data.get('filter_type'),
            content_type=content_type,
            intensity=filter_data['intensity'],
            filter_metadata=filter_data.get('filter_metadata', {}),
            is_temporary=filter_data.get('is_temporary', False),
            expires_at=filter_data.get('expires_at')
        )
        db.add(new_filter)
        db.flush()
        return new_filter.id

def update_filter(user_id: str, filter_id: int, filter_data: Dict[str, Any]) -> bool:
    """Update an existing filter"""
    with get_db() as db:
        filter_obj = db.query(Filter).filter(
            Filter.id == filter_id,
            Filter.user_id == user_id,
            Filter.is_active == True
        ).first()
        
        if not filter_obj:
            return False
            
        # Update fields if provided
        if 'filter_text' in filter_data:
            filter_obj.filter_text = filter_data['filter_text']
        if 'filter_type' in filter_data:
            filter_obj.filter_type = filter_data['filter_type']
        if 'content_type' in filter_data:
            try:
                filter_obj.content_type = ContentType[filter_data['content_type'].lower()]
            except KeyError:
                logger.warning(f"Invalid content_type '{filter_data['content_type']}', ignoring update")
        if 'intensity' in filter_data:
            filter_obj.intensity = filter_data['intensity']
        if 'filter_metadata' in filter_data:
            filter_obj.filter_metadata = filter_data['filter_metadata']
        if 'expires_at' in filter_data:
            filter_obj.expires_at = filter_data['expires_at']
        if 'is_temporary' in filter_data:
            filter_obj.is_temporary = filter_data['is_temporary']
        
        return True

def remove_filter(user_id: str, filter_id: int) -> bool:
    """Soft delete a filter by marking it inactive"""
    with get_db() as db:
        filter_obj = db.query(Filter).filter(
            Filter.id == filter_id,
            Filter.user_id == user_id,
            Filter.is_active == True
        ).first()
        
        if not filter_obj:
            return False
            
        filter_obj.is_active = False
        return True

async def log_processing_async(
    user_id: str,
    platform: str,
    content_hash: str,
    matched_filters: List[int],
    processing_time: float,
    processing_metadata: Optional[Dict] = None
) -> None:
    """Async version of log_processing"""
    def _do_log():
        with get_db() as db:
            log = ProcessingLog(
                user_id=user_id,
                platform=platform,
                content_hash=content_hash,
                matched_filters=matched_filters,
                processing_time=processing_time,
                processing_metadata=processing_metadata
            )
            db.add(log)
    
    # Run database operation in a thread pool
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _do_log)

def log_processing(
    user_id: str,
    platform: str,
    content_hash: str,
    matched_filters: List[int],
    processing_time: float,
    processing_metadata: Optional[Dict] = None
) -> None:
    """Log content processing details - handles both sync and async contexts"""
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context
        coroutine = log_processing_async(
            user_id=user_id,
            platform=platform,
            content_hash=content_hash,
            matched_filters=matched_filters,
            processing_time=processing_time,
            processing_metadata=processing_metadata
        )
        asyncio.create_task(coroutine)
    except RuntimeError:
        # We're in a sync context
        with get_db() as db:
            log = ProcessingLog(
                user_id=user_id,
                platform=platform,
                content_hash=content_hash,
                matched_filters=matched_filters,
                processing_time=processing_time,
                processing_metadata=processing_metadata
            )
            db.add(log)

def get_user_preferences(user_id: str) -> Dict[str, Any]:
    """Get user preferences"""
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        is_new_user = user is None or user.created_at is None
        
        if is_new_user:
            user = User(id=user_id)
            db.add(user)
            db.flush()
        return user.preferences or {}

def update_all_filters_to_max_intensity():
    """Update all existing filters to have maximum intensity (5)"""
    with get_db() as db:
        # Update all filters to have intensity 5
        db.query(Filter).update({"intensity": 5})
        logger.info("Updated all filters to maximum intensity (5)")