#!/bin/bash

# DIY Content Moderation - Local Development Setup
# This script sets up the entire system for local development

set -e  # Exit on any error

echo "🚀 DIY Content Moderation - Local Development Setup"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "Backend" ] || [ ! -d "BrowserExtension" ]; then
    print_error "Please run this script from the DIY_Mod root directory"
    exit 1
fi

print_status "Setting up local development environment..."

# Step 1: Setup Python Virtual Environment
print_status "Step 1: Setting up Python virtual environment..."
cd Backend

if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_success "Python dependencies installed"
else
    print_error "requirements.txt not found"
    exit 1
fi

# Step 2: Setup Local Environment Variables
print_status "Step 2: Setting up local environment variables..."

# Create local .env file
cat > .env.local << 'EOF'
# Local Development Environment Variables
# Copy this to .env and fill in your actual values

# API Keys (REQUIRED)
GOOGLE_API_KEY="your_google_api_key_here"
OPENAI_API_KEY="your_openai_api_key_here"

# AWS S3 Configuration (Optional - can use local storage)
AWS_ACCESS_KEY_ID="your_aws_access_key"
AWS_SECRET_ACCESS_KEY="your_aws_secret_key" 
AWS_STORAGE_BUCKET_NAME="diymod"
AWS_S3_REGION_NAME="us-east-2"

# Debug Configuration
DEBUG_MODE="DEBUG"
LOG_LEVEL="DEBUG"

# Model Configuration
FILTER_CREATION_MODEL="gpt-4o-2024-08-06"
CHAT_MODEL="gpt-4o"
CONTENT_PROCESS_MODEL="gpt-4o-mini-2024-07-18"

# Processing Configuration
PROCESSING_MODE="balanced"
PARALLEL_WORKERS=4
MAX_IMAGES_PER_POST=3

# Local Development Settings
ENVIRONMENT="development"
API_HOST="localhost"
API_PORT="8000"
CORS_ORIGINS="*"

# Database Configuration (SQLite for local dev)
DATABASE_URL="sqlite:///./local_dev.db"
EOF

if [ ! -f ".env" ]; then
    cp .env.local .env
    print_warning "Created .env file - PLEASE UPDATE WITH YOUR API KEYS!"
    print_warning "Edit Backend/.env and add your Google API key and OpenAI API key"
else
    print_warning ".env file already exists - check if API keys are configured"
fi

# Step 3: Create local development FastAPI launcher
print_status "Step 3: Creating local development launcher..."

cat > start_local_dev.sh << 'EOF'
#!/bin/bash

# Local Development Server Launcher
echo "🚀 Starting DIY Content Moderation - Local Development Server"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found. Please run local_dev_setup.sh first"
    exit 1
fi

# Check if API keys are configured
if [ "$GOOGLE_API_KEY" = "your_google_api_key_here" ]; then
    echo "❌ Please configure your GOOGLE_API_KEY in .env file"
    exit 1
fi

if [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo "❌ Please configure your OPENAI_API_KEY in .env file"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Start the development server
echo "🌟 Starting FastAPI development server on http://localhost:8000"
echo "📝 API Documentation available at http://localhost:8000/docs"
echo "🔄 Auto-reload enabled for development"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --reload --log-level debug
EOF

chmod +x start_local_dev.sh

# Step 4: Setup Browser Extension for Local Development  
print_status "Step 4: Setting up browser extension for local development..."
cd ../BrowserExtension/modernized-extension

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js and npm first."
    print_status "Visit: https://nodejs.org/"
    exit 1
fi

# Install npm dependencies
if [ -f "package.json" ]; then
    print_status "Installing npm dependencies..."
    npm install
    print_success "npm dependencies installed"
else
    print_error "package.json not found in browser extension directory"
    exit 1
fi

# Create local development configuration
print_status "Creating local development configuration..."

cat > src/config/local.config.js << 'EOF'
// Local Development Configuration
export const LOCAL_CONFIG = {
  // Local API endpoint
  API_BASE_URL: 'http://localhost:8000',
  
  // Development settings
  DEBUG: true,
  LOG_LEVEL: 'debug',
  
  // API endpoints
  ENDPOINTS: {
    PROCESS_FEED: '/get_feed',
    GET_IMAGE_RESULT: '/get_img_result',
    PING: '/ping',
    HEALTH: '/health'
  },
  
  // Extension settings
  POLLING_INTERVAL: 5000,  // 5 seconds for development
  RETRY_ATTEMPTS: 3,
  TIMEOUT: 30000,
  
  // Feature flags for development
  FEATURES: {
    IMAGE_PROCESSING: true,
    TEXT_PROCESSING: true,
    ADVANCED_FILTERS: true,
    PERFORMANCE_MONITORING: true
  }
};
EOF

# Create local build script
cat > build-local.sh << 'EOF'
#!/bin/bash

echo "🔨 Building DIY Content Moderation Extension for Local Development"

# Build for development with local API
npm run build:dev

echo "✅ Extension built for local development"
echo "📁 Load the extension from: $(pwd)/dist"
echo "🌐 Make sure your local API server is running on http://localhost:8000"
EOF

chmod +x build-local.sh

# Step 5: Create unified development launcher
print_status "Step 5: Creating unified development launcher..."
cd ../../

cat > start_local_system.sh << 'EOF'
#!/bin/bash

# DIY Content Moderation - Complete Local Development System
echo "🚀 DIY Content Moderation - Starting Complete Local System"
echo "========================================================"

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    echo "🔄 Stopping process on port $1..."
    lsof -ti:$1 | xargs kill -9 2>/dev/null || true
    sleep 2
}

# Clean up any existing processes
if check_port 8000; then
    echo "⚠️  Port 8000 is in use, stopping existing process..."
    kill_port 8000
fi

# Start backend in background
echo "🖥️  Starting Backend API Server..."
cd Backend
source venv/bin/activate

# Check environment
if [ ! -f ".env" ]; then
    echo "❌ Backend .env file not found. Run local_dev_setup.sh first"
    exit 1
fi

# Start backend
./start_local_dev.sh &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Check if backend is running
if check_port 8000; then
    echo "✅ Backend API Server running on http://localhost:8000"
    echo "📝 API Documentation: http://localhost:8000/docs"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Build browser extension
echo "🔨 Building Browser Extension..."
cd ../BrowserExtension/modernized-extension
./build-local.sh

echo ""
echo "🎉 Local Development System Started Successfully!"
echo "================================================"
echo "📊 Backend API: http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo "🔧 Extension: Load from BrowserExtension/modernized-extension/dist"
echo ""
echo "📋 Next Steps:"
echo "1. Load the extension in your browser:"
echo "   - Chrome: Go to chrome://extensions/, enable Developer mode, click 'Load unpacked'"
echo "   - Select the 'dist' folder from BrowserExtension/modernized-extension/"
echo "2. Navigate to Reddit or Twitter to test the extension"
echo "3. Check the browser console and backend logs for debugging"
echo ""
echo "🛑 To stop: Press Ctrl+C"
echo ""

# Keep script running and monitor backend
wait $BACKEND_PID
EOF

chmod +x start_local_system.sh

# Step 6: Create quick API test script
print_status "Step 6: Creating API test utilities..."

cat > test_local_api.sh << 'EOF'
#!/bin/bash

# Quick API Test Script
echo "🧪 Testing Local DIY Content Moderation API"

# Test if server is running
echo "🔍 Checking if API server is running..."
if curl -s http://localhost:8000/ping > /dev/null; then
    echo "✅ API server is running"
else
    echo "❌ API server is not running. Start it with: ./start_local_system.sh"
    exit 1
fi

# Test ping endpoint
echo "📡 Testing ping endpoint..."
curl -s http://localhost:8000/ping | jq . || echo "Response received"

# Test health endpoint
echo "🏥 Testing health endpoint..."
curl -s http://localhost:8000/health | jq . || echo "Response received"

echo "✅ API tests completed"
echo "📖 Full API documentation: http://localhost:8000/docs"
EOF

chmod +x test_local_api.sh

cd Backend

print_success "✅ Local development setup completed!"
print_status ""
print_status "🚀 Quick Start Guide:"
print_status "==================="
print_status "1. Configure API keys in Backend/.env file"
print_status "2. Run: ./start_local_system.sh"
print_status "3. Load browser extension from BrowserExtension/modernized-extension/dist"
print_status ""
print_warning "⚠️  IMPORTANT: Edit Backend/.env and add your API keys before starting!"
print_status "" 