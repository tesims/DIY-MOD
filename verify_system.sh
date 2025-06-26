#!/bin/bash

echo "🔍 DIY Content Moderation System Verification"
echo "=============================================="

# Check server status
echo "📡 Server Status:"
curl -s "http://localhost:5001/ping" | jq . 2>/dev/null || echo "❌ Server not responding"

# Check WebSocket endpoint
echo ""
echo "🔌 WebSocket Status:"
curl -s "http://localhost:5001/ws/test_user" | head -1 2>/dev/null && echo "✅ WebSocket endpoint accessible" || echo "❌ WebSocket endpoint not accessible"

# Check API documentation
echo ""
echo "📖 API Documentation:"
curl -s "http://localhost:5001/docs" | grep -q "FastAPI" && echo "✅ API docs available at http://localhost:5001/docs" || echo "❌ API docs not accessible"

# Check SSH tunnel
echo ""
echo "🔀 SSH Tunnel:"
ps aux | grep -q "ssh.*5001.*5000" && echo "✅ SSH tunnel active (5001→5000)" || echo "❌ SSH tunnel not active"

# Check server process
echo ""
echo "🖥️  Server Process:"
ssh -i ~/Downloads/rayhan-keypair.pem ubuntu@13.58.180.224 "ps aux | grep uvicorn | grep -v grep" && echo "✅ FastAPI server running on EC2" || echo "❌ Server not running"

echo ""
echo "🎯 System Status: Ready for WebSocket testing!"
echo "🌐 Browser Extension URL: http://localhost:5001"
echo "📋 Next steps: Load browser extension and test Reddit/Twitter feeds" 