#!/bin/bash

# Deploy DIY-MOD to Render
# This script automates the deployment process from EC2 to Render

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

echo "🚀 DIY-MOD Render Deployment Script"
echo "=================================="
echo ""

# Step 1: Verify we're in the correct directory
if [ ! -f "render.yaml" ]; then
    print_error "render.yaml not found! Please run this script from the project root directory."
    exit 1
fi

print_success "Found render.yaml configuration"

# Step 2: Check if we have the required environment variables
print_status "Step 1: Checking environment variables..."

if [ -z "$GOOGLE_API_KEY" ]; then
    print_warning "GOOGLE_API_KEY not set in environment"
    read -p "Enter your Google AI Studio API key: " GOOGLE_API_KEY
    if [ -z "$GOOGLE_API_KEY" ]; then
        print_error "Google API key is required!"
        exit 1
    fi
fi

if [ -z "$OPENAI_API_KEY" ]; then
    print_warning "OPENAI_API_KEY not set in environment"
    read -p "Enter your OpenAI API key: " OPENAI_API_KEY
    if [ -z "$OPENAI_API_KEY" ]; then
        print_error "OpenAI API key is required!"
        exit 1
    fi
fi

print_success "API keys verified"

# Step 3: Check if Git repository is clean and up to date
print_status "Step 2: Checking Git repository status..."

if [ -n "$(git status --porcelain)" ]; then
    print_warning "You have uncommitted changes. Render will deploy from the latest commit."
    read -p "Do you want to commit changes now? (y/n): " commit_changes
    
    if [ "$commit_changes" = "y" ] || [ "$commit_changes" = "Y" ]; then
        git add .
        git commit -m "Prepare for Render deployment - $(date)"
        print_success "Changes committed"
    else
        print_warning "Proceeding with uncommitted changes. They won't be deployed."
    fi
fi

# Step 4: Push to GitHub (required for Render)
print_status "Step 3: Pushing to GitHub..."

git push origin main
print_success "Code pushed to GitHub"

# Step 5: Display deployment instructions
echo ""
print_status "Step 4: Render Deployment Instructions"
echo "======================================="
echo ""
echo "1. Go to https://dashboard.render.com"
echo "2. Click 'New +' → 'Web Service'"
echo "3. Connect your GitHub repository"
echo "4. Render will auto-detect render.yaml and create all services:"
echo "   ✓ Web Service (FastAPI backend)"
echo "   ✓ PostgreSQL Database"
echo "   ✓ Redis Instance"
echo "   ✓ Celery Worker"
echo ""
echo "5. After deployment, set these environment variables:"
echo "   GOOGLE_API_KEY=${GOOGLE_API_KEY:0:20}..."
echo "   OPENAI_API_KEY=${OPENAI_API_KEY:0:20}..."
echo "   LLM_PROVIDER=gemini"
echo "   PRIMARY_MODEL=gemini-2.0-flash"
echo "   FALLBACK_MODEL=gpt-4o-mini"
echo "   USE_GEMINI_FOR_VISION=true"
echo "   USE_GEMINI_FOR_TEXT=true"
echo ""

# Step 6: Update browser extension configuration
print_status "Step 5: Browser Extension Configuration"
echo "======================================="
echo ""
echo "After deployment:"
echo "1. Note your Render service URL (e.g., https://diy-content-moderation.onrender.com)"
echo "2. Update the browser extension configuration if needed:"
echo "   File: BrowserExtension/modernized-extension/src/shared/config.ts"
echo "   Replace 'diy-content-moderation.onrender.com' with your actual URL"
echo "3. Rebuild the extension:"
echo "   cd BrowserExtension/modernized-extension"
echo "   npm run build"
echo ""

# Step 7: Testing checklist
print_status "Step 6: Testing Checklist"
echo "========================"
echo ""
echo "After deployment, test these endpoints:"
echo "□ Health check: https://your-app.onrender.com/ping"
echo "□ API test with extension"
echo "□ WebSocket connections"
echo "□ Image processing"
echo "□ Filter management"
echo ""

# Step 8: Migration cleanup
print_status "Step 7: EC2 Cleanup (After Successful Deployment)"
echo "=================================================="
echo ""
echo "Once everything is working on Render:"
echo "□ Stop EC2 services"
echo "□ Terminate EC2 instance"
echo "□ Remove SSH tunnel scripts"
echo "□ Update any other references to EC2 URLs"
echo ""

print_success "Deployment preparation complete!"
echo ""
print_warning "Remember to:"
echo "1. Set environment variables in Render Dashboard"
echo "2. Update browser extension baseUrl if different from 'diy-content-moderation.onrender.com'"
echo "3. Test all functionality before shutting down EC2"
echo ""
print_status "Happy deploying! 🎉" 