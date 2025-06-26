#!/bin/bash

# DIY Content Moderation - Local Development Starter
# This script starts the entire system locally for development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

echo "🚀 DIY Content Moderation - Local Development System"
echo "=================================================="

# Kill any existing processes
print_status "Stopping any existing processes..."
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 2

# Step 1: Check Python environment
print_status "Step 1: Checking Python environment..."
cd Backend

if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Running setup..."
    cd ..
    ./local_dev_setup.sh
    cd Backend
fi

# Activate virtual environment
source venv/bin/activate
print_success "Python virtual environment activated"

# Step 2: Load environment variables
print_status "Step 2: Loading environment variables..."
if [ -f ".env.local" ]; then
    set -a  # automatically export all variables
    source .env.local
    set +a
    print_success "Local environment variables loaded"
elif [ -f ".env" ]; then
    set -a
    source .env
    set +a
    print_success "Environment variables loaded from .env"
else
    print_error "No environment file found! Please run ./local_dev_setup.sh first"
    exit 1
fi

# Step 3: Check API keys
print_status "Step 3: Validating API keys..."
if [ -z "$GOOGLE_API_KEY" ] || [ "$GOOGLE_API_KEY" = "your_google_api_key_here" ]; then
    print_error "GOOGLE_API_KEY not configured!"
    print_warning "Please edit Backend/.env.local and add your Google API key"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    print_error "OPENAI_API_KEY not configured!"
    print_warning "Please edit Backend/.env.local and add your OpenAI API key"
    exit 1
fi

print_success "API keys validated"

# Step 4: Start the backend server
print_status "Step 4: Starting FastAPI backend server..."
echo "[INFO] Backend will be available at: http://localhost:8000"
echo "[INFO] API docs will be available at: http://localhost:8000/docs"

# Ensure the correct python and uvicorn from the venv are used
BACKEND_DIR="Backend"
VENV_PYTHON="$BACKEND_DIR/venv/bin/python"
VENV_UVICORN="$BACKEND_DIR/venv/bin/uvicorn"

if [ ! -f "$VENV_UVICORN" ]; then
    print_error "Uvicorn not found in virtual environment. Please run local_dev_setup.sh"
    exit 1
fi

(
    # Use the venv's uvicorn directly instead of activating
    "$VENV_UVICORN" fastapi_app:app --host "0.0.0.0" --port "8000" --reload --app-dir "$BACKEND_DIR"
) &
BACKEND_PID=$!

# Wait for backend to start
print_status "Waiting for backend to start..."
sleep 5

# Check if backend is running
if ! curl -s http://localhost:8000/ping > /dev/null; then
    print_error "Backend failed to start properly"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

print_success "Backend started successfully (PID: $BACKEND_PID)"

# Step 5: Build browser extension for local development
print_status "Step 5: Setting up browser extension for local development..."
cd ../BrowserExtension/modernized-extension

# Update configuration for local development
if [ ! -f "src/shared/config.ts.backup" ]; then
    cp src/shared/config.ts src/shared/config.ts.backup
fi

# Update the config to point to local server
sed -i '' 's/baseUrl: [^,]*/baseUrl: "http:\/\/localhost:8000"/' src/shared/config.ts || true
print_success "Browser extension configured for local development"

# Build the extension
print_status "Building browser extension..."
npm run build:dev

if [ $? -eq 0 ]; then
    print_success "Browser extension built successfully"
    print_status "Extension files are in: BrowserExtension/modernized-extension/dist"
else
    print_warning "Extension build had some issues, but you can load it manually"
fi

cd ../..

# Step 6: Display final information
echo ""
echo "🎉 Local Development System Started Successfully!"
echo "==============================================="
echo ""
echo "📍 Backend API:"
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/ping"
echo ""
echo "🔧 Browser Extension:"
echo "   Location: BrowserExtension/modernized-extension/dist"
echo "   Install: Load as unpacked extension in Chrome/Edge"
echo ""
echo "📝 Development Notes:"
echo "   • Backend auto-reloads on file changes"
echo "   • Extension needs manual reload after changes"
echo "   • Logs are displayed in this terminal"
echo ""
echo "🛑 To stop the system:"
echo "   Press Ctrl+C or run: pkill -f uvicorn"
echo ""

# Function to cleanup on exit
cleanup() {
    print_status "Shutting down local development system..."
    kill $BACKEND_PID 2>/dev/null || true
    
    # Restore original config
    if [ -f "BrowserExtension/modernized-extension/src/shared/config.ts.backup" ]; then
        mv BrowserExtension/modernized-extension/src/shared/config.ts.backup BrowserExtension/modernized-extension/src/shared/config.ts
    fi
    
    print_success "Cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Keep the script running and show logs
print_status "System is running. Press Ctrl+C to stop."
print_status "Watching backend logs..."

# Follow the logs
wait $BACKEND_PID 