#!/bin/bash
# DIY Content Moderation System Restart Script
# Safely restarts the system with improved error handling

echo "🔄 DIY Content Moderation System Restart"
echo "========================================="

# Function to check if process is running
check_process() {
    local process_name="$1"
    if pgrep -f "$process_name" > /dev/null; then
        return 0  # Process is running
    else
        return 1  # Process is not running
    fi
}

# Stop existing processes
echo "🛑 Stopping existing processes..."

if check_process "uvicorn"; then
    echo "   Stopping uvicorn server..."
    pkill -f "uvicorn"
    sleep 3
    
    # Force kill if still running
    if check_process "uvicorn"; then
        echo "   Force stopping uvicorn..."
        pkill -9 -f "uvicorn"
        sleep 2
    fi
fi

if check_process "celery"; then
    echo "   Stopping celery workers..."
    pkill -f "celery"
    sleep 2
fi

echo "✅ Processes stopped"

# Check for valid API key
echo "🔑 Checking API key..."
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  GOOGLE_API_KEY not set in environment"
    echo "💡 Run 'python3 fix_api_key.py' to set it up"
fi

# Start the server
echo "🚀 Starting server..."
if [ -f "./start_server.sh" ]; then
    chmod +x ./start_server.sh
    ./start_server.sh &
    SERVER_PID=$!
    echo "   Server started with PID: $SERVER_PID"
else
    echo "❌ start_server.sh not found"
    exit 1
fi

# Wait a bit for server to start
echo "⏳ Waiting for server to initialize..."
sleep 5

# Check if server is running
if check_process "uvicorn"; then
    echo "✅ Server is running"
    
    # Test server health
    echo "🏥 Testing server health..."
    if command -v curl > /dev/null; then
        if curl -s http://localhost:5000/ping > /dev/null; then
            echo "✅ Server is responding to requests"
        else
            echo "⚠️  Server not responding yet (may still be starting)"
        fi
    else
        echo "💡 Install curl to test server health automatically"
    fi
    
    echo ""
    echo "🎉 System restart complete!"
    echo ""
    echo "📋 Next steps:"
    echo "   - Run 'python3 health_check.py' for full system validation"
    echo "   - Check logs: tail -f debug.log"
    echo "   - Test image processing in browser extension"
    
else
    echo "❌ Server failed to start"
    echo "💡 Check debug.log for errors"
    exit 1
fi 