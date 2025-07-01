#!/bin/bash

# Verify DIY-MOD Render Deployment
# This script tests the deployed Render service

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default URL - update this with your actual Render URL
RENDER_URL="https://diy-content-moderation.onrender.com"

echo "🔍 DIY-MOD Render Deployment Verification"
echo "========================================="
echo ""

# Allow user to specify custom URL
if [ "$1" ]; then
    RENDER_URL="$1"
    print_status "Using custom URL: $RENDER_URL"
else
    print_status "Using default URL: $RENDER_URL"
    print_warning "You can specify a custom URL: ./scripts/verify_render_deployment.sh https://your-app.onrender.com"
fi

echo ""

# Test 1: Health Check
print_status "Test 1: Health Check (/ping)"
echo "------------------------------"

response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$RENDER_URL/ping" || echo "HTTPSTATUS:000")
http_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
body=$(echo "$response" | sed -e 's/HTTPSTATUS\:.*//g')

if [ "$http_code" -eq 200 ]; then
    print_success "Health check passed"
    echo "Response: $body"
else
    print_error "Health check failed (HTTP $http_code)"
    if [ "$http_code" -eq 000 ]; then
        print_error "Cannot connect to server. Check if the URL is correct and the service is running."
    fi
    echo "Response: $body"
fi

echo ""

# Test 2: API Documentation
print_status "Test 2: API Documentation (/docs)"
echo "----------------------------------"

response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$RENDER_URL/docs" || echo "HTTPSTATUS:000")
http_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')

if [ "$http_code" -eq 200 ]; then
    print_success "API documentation accessible"
    print_status "You can view it at: $RENDER_URL/docs"
else
    print_warning "API documentation not accessible (HTTP $http_code)"
fi

echo ""

# Summary
print_status "Summary"
echo "-------"

if [ "$http_code" -eq 200 ]; then
    print_success "✅ Render deployment appears to be working!"
    echo ""
    print_status "Next steps:"
    echo "1. Set environment variables in Render Dashboard"
    echo "2. Update browser extension if using different URL"
    echo "3. Test with actual browser extension"
    echo "4. Monitor Render logs for any issues"
    echo ""
    print_status "Useful URLs:"
    echo "📊 Render Dashboard: https://dashboard.render.com"
    echo "🔍 Service URL: $RENDER_URL"
    echo "📖 API Docs: $RENDER_URL/docs"
    echo "❤️ Health Check: $RENDER_URL/ping"
else
    print_error "❌ Deployment verification failed"
    echo ""
    print_status "Troubleshooting:"
    echo "1. Check Render service logs in dashboard"
    echo "2. Verify render.yaml configuration"
    echo "3. Ensure all dependencies are in requirements.txt"
    echo "4. Check if build command completed successfully"
fi

echo ""
print_status "Verification complete! 🎉" 