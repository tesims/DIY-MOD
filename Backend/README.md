# DIY-MOD Backend Server

The backend server for DIY-MOD provides intelligent content filtering and moderation using LLM-powered analysis. It processes content requests from the browser extension and manages user filter preferences.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
  - [Content Processing](#content-processing)
  - [Filter Management](#filter-management)
  - [Chat & Vision Integration](#chat--vision-integration)
  - [Platform Support](#platform-support)
- [API Endpoints](#api-endpoints)
- [Setup and Installation](#setup-and-installation)
- [Configuration](#configuration)
- [Development](#development)
  - [Adding a New Platform](#adding-a-new-platform)
  - [Error Handling](#error-handling)
  - [Logging](#logging)
- [Content Markers](#content-markers)
- [Troubleshooting](#troubleshooting)

## Overview

DIY-MOD (Do It Yourself MODeration) is a browser extension supported by this Flask-based backend server. The backend handles:

1. Processing social media content (Reddit, Twitter) for filtering
2. Managing user-defined content filters with database persistence
3. Providing a chat interface for natural language filter creation
4. Processing images through GPT-4V for visual content analysis
5. Maintaining user preferences and settings

## Architecture

The system follows a modular architecture with clear separation of concerns:

```
Backend/
├── app.py                 # Main Flask application with endpoints
├── models.py              # Pydantic models for data validation
├── processors/            # Platform-specific content processors
│   ├── base_processor.py  # Abstract base class for content processing
│   ├── reddit_processor.py
│   └── twitter_processor.py
├── ImageProcessor/        # Image analysis and modification components
│   ├── ImageProcessor.py  # Main image processing coordination
│   ├── ObjectDetector/    # Content detection in images
│   ├── ImageConverter/    # URL-to-image and image-to-URL conversion
│   └── ImageModifier/     # Image intervention implementations (blur, etc.)
├── llm/                   # LLM integration components
│   ├── chat.py            # Chat-based filter creation
│   ├── processor.py       # Content processing with LLM
│   └── vision.py          # Image processing with GPT-4V
├── database/              # Database operations
├── ServerCache/           # Caching system for processed content
│   ├── Cache.py           # Base caching functionality
│   ├── CacheManager.py    # Cache management and coordination
│   └── RedisCache.py      # Redis-based cache implementation
├── FilterUtils/           # Filter handling utilities
├── utils/                 # Utility modules
└── config.yaml            # Configuration settings
```

The server uses asynchronous processing with Hypercorn for improved performance and concurrency.

## Features

### Content Processing

- **Multi-platform Support**: Processes content from Reddit and Twitter with extensible architecture
- **Intelligent Analysis**: Uses GPT-4 models to understand context and nuance in content
- **Configurable Filtering Intensity**:
  - Level 1-2: Selective word/phrase blurring
  - Level 3: Content warning overlays
  - Level 4-5: AI-powered content rewriting
- **Parallel Processing**: Handles multiple content items simultaneously
- **Section-aware Processing**: Separate handling for titles, bodies, and media
- **Content Markers**: Standardized markup for frontend rendering
- **Platform-Specific Processing**: Specialized handling for Reddit posts and Twitter tweets
- **Media Type Detection**: Automatic identification of images, galleries, and video thumbnails

### Filter Management

- **Database Persistence**: SQLite storage for user filters
- **Filter Types**: Support for permanent and temporary filters with expiration
- **Filter Properties**:
  - Text-based filtering pattern
  - Content type targeting (text, image, or both)
  - Intensity level (1-5)
  - Duration (day, week, month, permanent)
- **CRUD Operations**: Complete filter lifecycle management

### Chat & Vision Integration

- **Natural Language Filter Creation**: Conversational interface for creating filters
- **Image-based Filtering**: Vision model integration for analyzing visual content
- **Guided Workflow**: Step-by-step process to define filter parameters
- **Filter Recommendations**: AI-assisted suggestions based on user input
- **Multi-stage Image Analysis**: Processing pipeline for detecting and handling sensitive content
- **Content Context Understanding**: Vision models evaluate the context of visual elements

### Platform Support

- **Reddit**: Processes Reddit feeds including posts, comments, and media
  - Specialized handling for posts, galleries, and video thumbnails
  - Adaptive media detection for different Reddit content types
- **Twitter**: Processes Twitter timelines and tweet content
  - Support for tweet text content and embedded media
  - Handling of extended entities and media attachments
- **Extensible Framework**: Base processor class for adding new platforms
- **Platform-specific Configuration**: Customizable settings for each supported platform

## API Endpoints

### Health Check
- `GET /ping` - Server health check

### Content Processing
- `POST /get_feed` - Process social media content
  - Required: `user_id`, `url`, `data` (with `feed_info.response`)
  - Returns processed content with filter markers

### Filter Management
- `GET /filters` - Get user's filters
  - Query param: `user_id`
- `POST /filters` - Create a new filter
  - Required: `user_id`, `filter_text`, `content_type`, `intensity`, `duration`
- `PUT /filters/<filter_id>` - Update a filter
  - Required: `user_id` and filter parameters
- `DELETE /filters/<filter_id>` - Delete a filter
  - Query param: `user_id`

### Chat Interface
- `POST /chat` - Process text chat for filter creation
  - Required: `message`, optional: `history`, `user_id`
- `POST /chat/image` - Process image uploads for filter creation
  - Multipart form with `image` file, optional: `message`, `history`, `user_id`

## Setup and Installation

1. Clone the repository and navigate to the Backend folder:
   ```bash
   cd Backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv diymod-venv
   source diymod-venv/bin/activate  # On Windows: diymod-venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with required environment variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

5. Start the server:
   ```bash
   python app.py
   ```

The server will start on port 5000 by default.

## Configuration

The system uses a YAML configuration file (`config.yaml`) with Pydantic models for validation:

### LLM Settings
```yaml
llm:
  content_model: "gpt-4o-mini"  # For processing feed content
  filter_model: "gpt-4o"        # For filter creation
  chat_model: "gpt-4o"          # For chat interactions
  temperature: 0.1
  max_tokens: 1000
```

### Processing Settings
```yaml
processing:
  parallel_workers: 4           # Number of parallel processing workers
  cache_timeout: 60             # Cache timeout in seconds
  default_mode: "balanced"      # Default processing mode
  default_intensity: 3          # Default filter intensity
  
  image_processing:
    enabled: true
    max_images_per_post: 3      # Limit images processed per post
    max_posts_with_images: 5    # Limit total posts with images to process
  
  # Platform-specific configurations
  reddit_specific:
    reddit_max_carousel_images: 3  # Max images to process from Reddit carousels
    process_video_thumbnails: true # Whether to process video thumbnails
  
  twitter_specific:
    twitter_max_carousel_images: 3 # Max images to process from Twitter carousels
    process_video_thumbnails: true # Whether to process video thumbnails
```

### Database Settings
```yaml
database:
  url: "sqlite:///filters.db"   # Database connection string
  pool_size: 5                  # Connection pool size
  max_overflow: 10              # Max overflow connections
```

## Development

### Adding a New Platform

1. Create a new processor class that extends `ContentProcessor`:
   ```python
   from .base_processor import ContentProcessor, Post

   class NewPlatformProcessor(ContentProcessor):
       def __init__(self, user_id: str, feed_info: Dict[str, Any]):
           super().__init__(user_id, feed_info)
           # Platform-specific initialization

       async def work_on_feed(self) -> str:
           # Parse feed, create posts, process them
           # Return processed HTML/JSON
   ```

2. Register in `app.py`:
   ```python
   PLATFORM_PROCESSORS = {
       'reddit': RedditProcessor,
       'twitter': TwitterProcessor,
       'new_platform': NewPlatformProcessor
   }
   ```

3. Add platform detection to `get_platform_from_url()` function

### Error Handling

The backend uses a comprehensive decorator-based error handling system:

```python
@handle_api_errors
def endpoint_function():
    # Function body
```

Errors are logged and returned in a standardized format:
```json
{
  "status": "error",
  "message": "Error message",
  "details": { "additional": "information" }
}
```

### Logging

- Configurable logging levels in `config.yaml`
- File logging to `debug.log`
- Function timing and performance metrics
- Request/response logging for debugging

## Content Markers

The backend uses standardized markers that the frontend recognizes:

### Blur Markers
```
__BLUR_START__sensitive content__BLUR_END__
```

### Overlay Markers
```
__OVERLAY_START__Warning Message|content to hide__OVERLAY_END__
```

### Rewrite Markers
```
__REWRITE_START__modified content__REWRITE_END__
```

### Section Markers
```
[TITLE]Post title content[/TITLE]
[BODY]Post body content[/BODY]
```

## Troubleshooting

### Common Issues

1. **OpenAI API Key Issues**
   - Check `.env` file for correct API key
   - Verify API key has access to required models

2. **Database Errors**
   - Ensure `filters.db` file has correct permissions
   - Check SQLite version compatibility

3. **Performance Issues**
   - Adjust `parallel_workers` in config
   - Check for memory leaks in image processing

4. **LLM Response Issues**
   - Check internet connectivity
   - Verify model availability in OpenAI dashboard
   - Review system prompts in `llm/prompts.py`