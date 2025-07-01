# DIY Content Moderation System

An AI-powered content moderation system that provides real-time filtering for social media platforms like Reddit and Twitter. The system uses advanced LLM models (Google Gemini, OpenAI GPT) to analyze and filter content based on user-defined preferences.

## 🚀 Features

- **Real-time Content Filtering**: Filter posts, comments, and images on Reddit and Twitter
- **AI-Powered Analysis**: Uses Google Gemini and OpenAI GPT models for intelligent content analysis
- **Browser Extension**: Seamless integration with social media platforms
- **Custom Filters**: Create personalized content filters with various intensity levels
- **WebSocket Support**: Real-time communication for instant content processing
- **Image Processing**: Advanced image analysis and filtering capabilities
- **User Preferences**: Customizable filtering rules and visual settings

## 📁 Project Structure

```
DIY_Mod/
├── Backend/              # FastAPI backend server
│   ├── database/         # Database models and operations
│   ├── llm/             # LLM integration and processing
│   ├── processors/      # Content processors (Reddit, Twitter)
│   ├── utils/           # Utility functions and configuration
│   └── fastapi_app.py   # Main FastAPI application
├── Extension/           # Browser extension
│   └── modernized-extension/  # Chrome/Edge extension source
├── docs/               # Documentation files
├── scripts/            # Deployment and utility scripts
├── tests/              # Test files and utilities
├── config/             # Configuration templates
└── render.yaml         # Render deployment configuration
```

## 🛠️ Quick Start

### 1. Deploy to Render (Recommended)

The easiest way to get started:

```bash
# 1. Clone this repository
git clone https://github.com/tesims/DIY-MOD.git
cd DIY-MOD

# 2. Deploy to Render
./scripts/deploy_to_render.sh

# 3. Follow the deployment guide
cat docs/RENDER_DEPLOYMENT.md
```

### 2. Local Development

For local development:

```bash
# 1. Set up local environment
./scripts/local_dev_setup.sh

# 2. Start the system
./scripts/start_local_system.sh

# 3. Load browser extension from Extension/modernized-extension/dist
```

## 🔧 Configuration

### Environment Variables

Set these in your Render dashboard or local `.env` file:

```bash
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
LLM_PROVIDER=gemini
PRIMARY_MODEL=gemini-2.0-flash
FALLBACK_MODEL=gpt-4o-mini
USE_GEMINI_FOR_VISION=true
USE_GEMINI_FOR_TEXT=true
```

### API Keys

- **Google AI Studio**: [Get API Key](https://aistudio.google.com/app/apikey)
- **OpenAI**: [Get API Key](https://platform.openai.com/api-keys)

## 📚 Documentation

- [🚀 Render Deployment Guide](docs/RENDER_DEPLOYMENT.md)
- [💻 Local Development Setup](docs/LOCAL_DEVELOPMENT.md)
- [🧪 Testing Instructions](docs/TESTING_SETUP.md)
- [🔌 Extension Testing](docs/EXTENSION_TESTING.md)
- [🌐 WebSocket Implementation](docs/WEBSOCKET_IMPLEMENTATION.md)

## 🧪 Testing

Verify your deployment:

```bash
# Test Render deployment
./scripts/verify_render_deployment.sh https://your-app.onrender.com

# Test local system
./scripts/verify_system.sh
```

## 🔒 Security

- **No Secrets in Code**: All API keys are set as environment variables
- **CORS Protection**: Configured for specific domains only
- **Input Validation**: All user inputs are validated and sanitized
- **Rate Limiting**: Built-in protection against abuse

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter issues:

1. Check the [documentation](docs/)
2. Review deployment logs in Render dashboard
3. Test with verification scripts
4. Open an issue on GitHub

## 🏗️ Architecture

- **Backend**: FastAPI with SQLAlchemy, Redis caching, Celery workers
- **Frontend**: TypeScript browser extension with Vite build system
- **AI/ML**: Google Gemini and OpenAI GPT integration
- **Deployment**: Render with PostgreSQL and Redis managed services
- **Real-time**: WebSocket connections for instant content processing

---

**Built with ❤️ for a safer, more personalized social media experience.**
