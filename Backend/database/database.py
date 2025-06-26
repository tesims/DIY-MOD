import databases
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./filters.db")

# Create a database instance
database = databases.Database(DATABASE_URL)

metadata = MetaData()

Base = declarative_base()

class Filter(Base):
    __tablename__ = "filters"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    filter_text = Column(String, nullable=False)
    intensity = Column(Integer, nullable=False)
    content_type = Column(String, default="all")
    is_temporary = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    filter_metadata = Column(JSON, default={})

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSON, default={})

class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    platform = Column(String)
    content_hash = Column(String, index=True)
    matched_filters = Column(JSON)
    processing_time = Column(Integer) # in ms
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_metadata = Column(JSON, default={})

# Setup database engine
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        raise

async def connect_to_db():
    try:
        await database.connect()
        create_tables() 
        logger.info("Database connection established.")
    except Exception as e:
        logger.error(f"Could not connect to the database: {e}", exc_info=True)
        # In a production environment, you might want to exit or retry
        # For now, we will log the error and continue, though most db operations will fail
        
async def disconnect_from_db():
    try:
        if database.is_connected:
            await database.disconnect()
            logger.info("Database connection closed.")
    except Exception as e:
        logger.error(f"Error disconnecting from database: {e}", exc_info=True) 