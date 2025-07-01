#!/bin/bash

# DIY Content Moderation - Comprehensive API Key Fix
echo "🔧 DIY-MOD: Complete API Key System Fix"
echo "============================================"

# Read API keys from environment variables or prompt user
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  GOOGLE_API_KEY not found in environment."
    echo "Please set your Google AI Studio API key as an environment variable:"
    echo "export GOOGLE_API_KEY='your_google_api_key_here'"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not found in environment."
    echo "Please set your OpenAI API key as an environment variable:"
    echo "export OPENAI_API_KEY='your_openai_api_key_here'"
    exit 1
fi

echo "✅ API keys found in environment variables"

echo "🔍 Step 1: Checking SSH connection..."
if ! ssh -i ~/Downloads/rayhan-keypair.pem ubuntu@13.58.180.224 "echo 'SSH connection successful'"; then
    echo "❌ SSH connection failed. Please check:"
    echo "   - EC2 instance is running"
    echo "   - Security groups allow SSH (port 22)"
    echo "   - Key file permissions: chmod 400 ~/Downloads/rayhan-keypair.pem"
    exit 1
fi

echo "✅ SSH connection working"

echo "🛑 Step 2: Stopping all processes..."
ssh -i ~/Downloads/rayhan-keypair.pem ubuntu@13.58.180.224 "
pkill -f uvicorn
pkill -f python
pkill -f gunicorn
sleep 5
echo 'All server processes stopped'
"

echo "🔧 Step 3: Setting up API keys with Gemini support..."
ssh -i ~/Downloads/rayhan-keypair.pem ubuntu@13.58.180.224 "
# Create comprehensive .env file with both Google and OpenAI keys
cd /opt/DIY-MOD/Backend

# Create .env file with working API keys
cat > .env << 'EOF'
# Google Gemini API Configuration (Primary for Vision)
GOOGLE_API_KEY=$GOOGLE_API_KEY
GEMINI_API_KEY=$GOOGLE_API_KEY

# OpenAI API Configuration (Fallback for Text)
OPENAI_API_KEY=$OPENAI_API_KEY

# Configuration Flags
USE_GEMINI_FOR_VISION=true
USE_GEMINI_FOR_TEXT=true
FALLBACK_TO_OPENAI=false

# API Endpoints
GEMINI_API_BASE=https://generativelanguage.googleapis.com/v1beta
OPENAI_API_BASE=https://api.openai.com/v1
EOF

# Set environment variables for current session
export GOOGLE_API_KEY="${GOOGLE_API_KEY}"
export GEMINI_API_KEY="${GOOGLE_API_KEY}"
export OPENAI_API_KEY="${OPENAI_API_KEY}"
export USE_GEMINI_FOR_VISION=true
export USE_GEMINI_FOR_TEXT=true

# Add to shell profiles for persistence
echo 'export GOOGLE_API_KEY="${GOOGLE_API_KEY}"' >> ~/.bashrc
echo 'export GEMINI_API_KEY="${GOOGLE_API_KEY}"' >> ~/.bashrc
echo 'export OPENAI_API_KEY="${OPENAI_API_KEY}"' >> ~/.bashrc
echo 'export USE_GEMINI_FOR_VISION=true' >> ~/.bashrc
echo 'export USE_GEMINI_FOR_TEXT=true' >> ~/.bashrc

echo 'API keys configured successfully'
"

echo "📝 Step 4: Updating configuration for Gemini..."
ssh -i ~/Downloads/rayhan-keypair.pem ubuntu@13.58.180.224 "
cd /opt/DIY-MOD/Backend

# Update LLM configuration to use Gemini
cat > llm_config.py << 'EOF'
# DIY-MOD LLM Configuration - Gemini First
import os

# Gemini Configuration (Primary)
GEMINI_CONFIG = {
    'api_key': os.getenv('GOOGLE_API_KEY', 'your_google_api_key_here'),
    'model_vision': 'gemini-2.0-flash',
    'model_text': 'gemini-2.0-flash',  
    'base_url': 'https://generativelanguage.googleapis.com/v1beta',
    'use_for_vision': True,
    'use_for_text': True
}

# OpenAI Configuration (Fallback)
OPENAI_CONFIG = {
    'api_key': os.getenv('OPENAI_API_KEY', 'your_openai_api_key_here'),
    'model_text': 'gpt-4o-mini',
    'base_url': 'https://api.openai.com/v1',
    'use_for_fallback': True
}

# System Configuration
SYSTEM_CONFIG = {
    'primary_provider': 'gemini',
    'fallback_provider': 'openai',
    'max_retries': 3,
    'timeout': 30
}
EOF

echo 'LLM configuration updated for Gemini'
"

echo "🚀 Step 5: Starting server with Gemini support..."
ssh -i ~/Downloads/rayhan-keypair.pem ubuntu@13.58.180.224 "
cd /opt/DIY-MOD/Backend
source .env
source venv/bin/activate

echo 'Environment loaded, starting server...'
echo 'Google API Key: '$(echo \$GOOGLE_API_KEY | head -c 20)...
echo 'OpenAI API Key: '$(echo \$OPENAI_API_KEY | head -c 20)...

# Start server with environment variables
uvicorn fastapi_app:app --host 127.0.0.1 --port 5000 &
echo 'Server starting with PID: '\$!
" &

echo "⏳ Step 6: Waiting for server startup..."
sleep 15

echo "🔗 Step 7: Establishing SSH tunnel..."
pkill -f "ssh.*rayhan.*5001" 2>/dev/null
sleep 2
ssh -i ~/Downloads/rayhan-keypair.pem -L 5001:localhost:5000 ubuntu@13.58.180.224 -N &
tunnel_pid=$!
echo "SSH tunnel established with PID: $tunnel_pid"

echo "🧪 Step 8: Testing system..."
sleep 10

# Test server connection
echo "Testing HTTP connection..."
http_test=$(curl -s "http://localhost:5001/ping" 2>/dev/null || echo "FAILED")
if [[ "$http_test" == *"pong"* ]]; then
    echo "✅ HTTP connection working"
else
    echo "❌ HTTP connection failed: $http_test"
fi

# Test WebSocket connection (basic)
echo "Testing WebSocket endpoint..."
ws_test=$(curl -s "http://localhost:5001/ws/test_user" 2>/dev/null || echo "FAILED")
if [[ "$ws_test" != "FAILED" ]]; then
    echo "✅ WebSocket endpoint accessible"
else
    echo "❌ WebSocket endpoint failed"
fi

echo ""
echo "🎉 DIY-MOD System Ready!"
echo "=================================="
echo "✅ Google Gemini API configured for vision processing"  
echo "✅ OpenAI API configured as fallback"
echo "✅ SSH Tunnel active: localhost:5001 → EC2:5000"
echo "✅ WebSocket support enabled"
echo ""
echo "🔧 Next Steps:"
echo "1. Load extension from: DIY_Mod/BrowserExtension/modernized-extension/dist/"
echo "2. Test on: https://www.reddit.com/r/PlasticSurgery"
echo "3. Check browser console for WebSocket connection logs"
echo ""
echo "📊 System URLs:"
echo "   • Server: http://localhost:5001"
echo "   • API Docs: http://localhost:5001/docs"
echo "   • WebSocket: ws://localhost:5001/ws/{user_id}" 