#!/bin/bash

echo "🚀 Starting DIY Mod Mock Server for WebSocket Testing"
echo "=================================================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "mock-server.js" ]; then
    echo "❌ mock-server.js not found. Please run this script from the modernized-extension directory."
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install express ws cors
fi

# Start the mock server
echo "🔌 Starting mock server on port 5001..."
echo "📡 WebSocket endpoint: ws://localhost:5001/ws/{user_id}"
echo "🏓 HTTP ping endpoint: http://localhost:5001/ping"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

node mock-server.js 