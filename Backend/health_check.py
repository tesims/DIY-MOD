#!/usr/bin/env python3
"""
DIY Content Moderation System Health Check
Validates all components are working correctly
"""
import os
import sys
import asyncio
import aiohttp
import json
from pathlib import Path
import logging

# Add the Backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def check_api_keys():
    """Check if required API keys are present and valid"""
    print("\n🔑 Checking API keys...")
    issues = []
    
    # Check Google API key
    google_key = os.getenv('GOOGLE_API_KEY')
    if not google_key:
        issues.append("❌ GOOGLE_API_KEY not found in environment")
    elif not google_key.startswith('AIza'):
        issues.append("⚠️  GOOGLE_API_KEY doesn't appear to be valid format")
    elif len(google_key) < 20:
        issues.append("⚠️  GOOGLE_API_KEY appears too short")
    else:
        print("✅ GOOGLE_API_KEY found and appears valid")
    
    return issues

async def check_google_api():
    """Test Google Gemini API connection"""
    print("\n🤖 Testing Google Gemini API...")
    
    try:
        from google import genai
        from google.genai import types
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return ["❌ Cannot test Google API - no API key"]
        
        client = genai.Client(api_key=api_key)
        
        # Simple test call
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=["What is 2+2?"],
            config=types.GenerateContentConfig(
                max_output_tokens=50,
                temperature=0.1,
            )
        )
        
        if response and response.candidates:
            print("✅ Google Gemini API is working")
            return []
        else:
            return ["❌ Google API returned empty response"]
            
    except Exception as e:
        error_msg = str(e)
        if "API key not valid" in error_msg:
            return ["❌ Google API key is invalid"]
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            return ["⚠️  Google API quota/rate limit exceeded"]
        else:
            return [f"❌ Google API error: {error_msg}"]

async def check_image_processing():
    """Test image processing functionality"""
    print("\n🖼️  Testing Image Processing...")
    
    try:
        from FilterUtils import get_best_filter_async
        
        # Test with a simple public image
        test_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Vd-Orig.png/256px-Vd-Orig.png"
        test_filters = ["test filter"]
        
        result = await get_best_filter_async(test_filters, test_url)
        
        if result is not None:
            filter_name, coverage = result
            print(f"✅ Image processing working (filter: {filter_name}, coverage: {coverage})")
            return []
        else:
            return ["❌ Image processing returned None"]
            
    except Exception as e:
        error_msg = str(e)
        if "API key" in error_msg:
            return ["❌ Image processing failed due to API key issue"]
        else:
            return [f"❌ Image processing error: {error_msg}"]

async def check_server_status():
    """Check if the FastAPI server is running"""
    print("\n🌐 Checking Server Status...")
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get('http://localhost:5000/ping') as response:
                if response.status == 200:
                    print("✅ FastAPI server is responding")
                    return []
                else:
                    return [f"❌ Server returned status {response.status}"]
    except aiohttp.ClientConnectorError:
        return ["❌ Cannot connect to server - is it running on port 5000?"]
    except asyncio.TimeoutError:
        return ["❌ Server connection timeout"]
    except Exception as e:
        return [f"❌ Server check error: {e}"]

async def check_database():
    """Check database connectivity"""
    print("\n🗄️  Checking Database...")
    
    try:
        from database.operations import get_all_users
        
        # Try to query users (this will test DB connection)
        users = get_all_users()
        print(f"✅ Database connected ({len(users)} users found)")
        return []
        
    except Exception as e:
        return [f"❌ Database error: {e}"]

def check_file_structure():
    """Check if all required files exist"""
    print("\n📁 Checking File Structure...")
    
    required_files = [
        "fastapi_app.py",
        "start_server.sh",
        "FilterUtils/FilterUtils.py",
        "ImageProcessor/ImageProcessor.py",
        "config.yaml"
    ]
    
    issues = []
    
    for file_path in required_files:
        full_path = backend_dir / file_path
        if not full_path.exists():
            issues.append(f"❌ Missing file: {file_path}")
        else:
            print(f"✅ Found: {file_path}")
    
    return issues

async def main():
    """Run comprehensive health check"""
    print("🏥 DIY Content Moderation System Health Check")
    print("=" * 60)
    
    all_issues = []
    
    # File structure check (synchronous)
    all_issues.extend(check_file_structure())
    
    # API key check (synchronous)
    all_issues.extend(await check_api_keys())
    
    # Server status check
    all_issues.extend(await check_server_status())
    
    # Database check
    all_issues.extend(await check_database())
    
    # Google API check
    all_issues.extend(await check_google_api())
    
    # Image processing check
    all_issues.extend(await check_image_processing())
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 HEALTH CHECK SUMMARY")
    print("=" * 60)
    
    if not all_issues:
        print("🎉 ALL CHECKS PASSED! System is healthy.")
        return 0
    else:
        print(f"⚠️  Found {len(all_issues)} issues:")
        for issue in all_issues:
            print(f"   {issue}")
        
        print("\n💡 Recommended fixes:")
        
        if any("API key" in issue for issue in all_issues):
            print("   - Run: python3 fix_api_key.py")
        
        if any("server" in issue.lower() for issue in all_issues):
            print("   - Start server: ./start_server.sh")
        
        if any("database" in issue.lower() for issue in all_issues):
            print("   - Check database configuration and connection")
        
        return 1

if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.ERROR)  # Only show errors during health check
    
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n❌ Health check interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Health check failed: {e}")
        sys.exit(1) 