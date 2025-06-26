#!/bin/bash

# DIY Content Moderation - Server Startup Script with Environment Variables
echo "🚀 Starting DIY Content Moderation Server..."

# Kill any existing uvicorn processes
echo "🛑 Stopping existing server processes..."
pkill -f uvicorn
sleep 3

# Set API keys explicitly
echo "🔧 Setting up API keys..."
export GOOGLE_API_KEY="YOUR_GOOGLE_KEY_HERE"
export OPENAI_API_KEY="YOUR_OPENAI_KEY_HERE"

# Load from .env file if it exists
if [ -f "/opt/DIY-MOD/Backend/.env" ]; then
    echo "📁 Loading environment from .env file..."
    source /opt/DIY-MOD/Backend/.env
fi

# Verify API keys are set
echo "✅ Environment verification:"
echo "GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:20}..."
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:20}..."

if [ -z "$GOOGLE_API_KEY" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: API keys not found in environment!"
    exit 1
fi

# Navigate to backend directory
cd /opt/DIY-MOD/Backend

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Start the server with environment variables
echo "🌐 Starting FastAPI server on port 5000..."
echo "📡 Server will be available at http://127.0.0.1:5000"
echo "📖 API docs at http://127.0.0.1:5000/docs"

# Start uvicorn with the environment variables
GOOGLE_API_KEY="$GOOGLE_API_KEY" OPENAI_API_KEY="$OPENAI_API_KEY" uvicorn fastapi_app:app --host 127.0.0.1 --port 5000 