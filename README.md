# DIY Content Moderation System

A browser extension that provides real-time content filtering and moderation for social media feeds using AI-powered analysis and rewriting.

## 🏗️ Architecture

### Backend (FastAPI + Python)
- **FastAPI Server**: RESTful API with **real-time WebSocket support**
- **Content Processing**: LLM-powered text analysis and rewriting
- **Image Processing**: Google Vision API integration for image analysis
- **Database**: SQLite for user data and filter management
- **Real-time Processing**: WebSocket-based processing with HTTP fallback

### Browser Extension (TypeScript + Chrome Extension API)
- **Content Interception**: Real-time DOM manipulation
- **Platform Support**: Reddit, Twitter/X
- **User Interface**: Dynamic filter management
- **Local Storage**: User preferences and configuration

## 📁 Project Structure

```
DIY_Mod/
├── Backend/
│   ├── fastapi_app.py              # Main FastAPI application
│   ├── processors/                 # Content processing modules
│   │   ├── base_processor.py       # Base content processor
│   │   ├── reddit_processor.py     # Reddit-specific processing
│   │   └── twitter_processor.py    # Twitter-specific processing
│   ├── llm/                        # LLM integration
│   │   ├── processor.py            # Main LLM processing logic
│   │   ├── prompts.py              # LLM prompt templates
│   │   └── chat.py                 # Chat interface
│   ├── ImageProcessor/             # Image processing
│   │   └── ImageProcessor.py       # Google Vision API integration
│   ├── FilterUtils/                # Filter utilities
│   │   └── FilterUtils.py          # Filter matching and scoring
│   ├── database/                   # Database operations
│   ├── utils/                      # Utility modules
│   ├── start_server.sh             # Production server startup
│   ├── start_local_system.sh       # Local development startup
│   └── requirements.txt            # Python dependencies
├── BrowserExtension/
│   └── modernized-extension/       # Chrome extension
│       ├── src/                    # TypeScript source code
│       ├── manifest.json           # Extension manifest
│       ├── package.json            # Node.js dependencies
│       └── dist/                   # Built extension (generated)
├── EXTENSION_TESTING.md            # Testing guide
├── LOCAL_DEVELOPMENT.md            # Development setup guide
└── README.md                       # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Google API Key (Gemini)
- OpenAI API Key (optional)

### 1. Backend Setup

```bash
cd Backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 2. Environment Configuration

Create `Backend/.env`:
```env
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Browser Extension Setup

```bash
cd BrowserExtension/modernized-extension
npm install
npm run build
```

### 4. Start the System

**Production (EC2 server):**
```bash
cd Backend
./start_server.sh
```

**Local Development:**
```bash
./start_local_system.sh
```

### 5. Load Extension in Browser

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `BrowserExtension/modernized-extension/dist` folder

## 🔧 Development

### Local Development
See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) for detailed setup instructions.

### Testing
See [EXTENSION_TESTING.md](EXTENSION_TESTING.md) for testing procedures.

### Key Features
- ✅ Real-time content filtering on Reddit and Twitter/X
- ✅ AI-powered content rewriting and moderation
- ✅ Image analysis and filtering using Google Vision API
- ✅ User-customizable filters with intensity levels
- ✅ Retry logic for API failures
- ✅ Comprehensive error handling and logging

## 🐛 Troubleshooting

### Common Issues

**Extension not loading:**
- Ensure the extension is built: `npm run build`
- Check browser console for errors
- Verify manifest.json is valid

**Backend connection issues:**
- Check if server is running on correct port
- Verify API keys are set in environment
- Check firewall/network settings

**API errors:**
- Verify Google API key is valid and has proper permissions
- Check rate limits and quotas
- Review server logs for detailed error messages

## 🔄 WebSocket Implementation

The system now uses **real-time WebSocket communication** for faster processing:

- **Default Mode**: WebSocket-based processing with automatic HTTP fallback
- **Performance**: Eliminates polling delays and reduces server load  
- **Reliability**: Auto-reconnection with exponential backoff
- **Compatibility**: Falls back to HTTP if WebSocket fails

See [WEBSOCKET_IMPLEMENTATION.md](WEBSOCKET_IMPLEMENTATION.md) for detailed technical information.

## 📝 System Status

**✅ Working Components:**
- Reddit content processing (text + images)
- Twitter/X content processing (text + images)
- LLM-based content rewriting
- Image analysis with Google Vision API
- Filter management and user preferences
- **Real-time WebSocket communication**
- Browser extension functionality with auto-fallback

**🚧 Known Issues:**
- SSH tunnel connectivity can be unstable
- Local development environment has some import conflicts
- Rate limiting may cause temporary API failures

## 🤝 Contributing

1. Follow the project structure guidelines
2. Use TypeScript for browser extension code
3. Follow Python PEP 8 for backend code
4. Add tests for new functionality
5. Update documentation as needed

## 📄 License

This project is for educational and research purposes.
