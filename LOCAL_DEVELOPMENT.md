# Local Development Setup Guide

This guide helps you set up the DIY Content Moderation System for local development.

## Prerequisites

- Python 3.12+
- Node.js 18+
- Google API Key (Gemini)
- OpenAI API Key (optional)

## Quick Setup

### 1. Automated Setup (Recommended)

```bash
./local_dev_setup.sh
```

This script will:
- Create Python virtual environment
- Install all dependencies
- Set up environment variables
- Build the browser extension

### 2. Manual Setup

If the automated setup fails, follow these manual steps:

#### Backend Setup
```bash
cd Backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

#### Environment Configuration
Create `Backend/.env`:
```env
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

#### Browser Extension Setup
```bash
cd BrowserExtension/modernized-extension
npm install
npm run build
```

## Running the System

### Local Development Server
```bash
./start_local_system.sh
```

This starts the backend on `http://localhost:8000`

### Remote EC2 Server (Recommended for Testing)
```bash
# SSH tunnel to EC2 server
ssh -i ~/Downloads/rayhan-keypair.pem -L 5001:localhost:5000 ubuntu@13.58.180.224 -N
```

## Load Extension in Browser

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `BrowserExtension/modernized-extension/dist`

## Configuration

### Development vs Production Mode

Set extension mode in browser console:
```javascript
// For local development
localStorage.setItem('diy_mod_dev_mode', 'true');

// For EC2 server (recommended)
localStorage.setItem('diy_mod_dev_mode', 'false');
```

## Common Issues

### Import Errors (Local Development)
If you see `ImportError: cannot import name 'genai' from 'google'`:
- Local development has package conflicts
- **Recommended**: Use EC2 server instead with SSH tunnel

### SSH Tunnel Issues
- Ensure the correct key file path: `~/Downloads/rayhan-keypair.pem`
- Check if port 5001 is already in use: `lsof -i :5001`
- Kill existing tunnels: `pkill -f "ssh.*rayhan"`

### Extension Not Loading
- Verify the extension is built: `npm run build`
- Check browser console for errors
- Ensure manifest.json is valid

## Development Workflow

1. **Use EC2 Server**: The remote server works reliably
2. **SSH Tunnel**: Connect locally via `localhost:5001`
3. **Extension Development**: Make changes and rebuild
4. **Testing**: Use Reddit/Twitter feeds for testing

## Project Structure

```
Backend/
├── fastapi_app.py              # Main FastAPI application
├── processors/                 # Content processing
├── llm/                        # LLM integration
├── ImageProcessor/             # Image processing
├── FilterUtils/                # Filter utilities
├── database/                   # Database operations
├── utils/                      # Utility modules
└── venv/                       # Python virtual environment

BrowserExtension/modernized-extension/
├── src/                        # TypeScript source
├── dist/                       # Built extension
├── manifest.json               # Extension manifest
└── package.json                # Dependencies
```

## System Status

**✅ Working on EC2:**
- Reddit content processing (text + images)
- Twitter/X content processing (text + images)
- Image analysis with Google Vision API
- LLM-based content rewriting

**🚧 Local Development Issues:**
- Google GenAI package import conflicts
- Python environment mixing

**💡 Recommendation:**
Use the EC2 server with SSH tunnel for reliable development and testing. 