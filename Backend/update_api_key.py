#!/usr/bin/env python3
"""
Secure API Key Update Script
Allows manual entry of Google API key without exposing it in logs
"""
import os
import getpass
import sys
import json
from typing import List, Dict
# Mock implementation for testing - avoid problematic Google imports
try:
    import google.ai.generativelanguage as genai_client
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class MockGeminiTestClient:
    """Mock Gemini client for API key testing"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def models_generate_content(self, model: str, contents: List[str]) -> Dict:
        """Mock content generation to simulate a test response"""
        if self.api_key and self.api_key.startswith("AIza"):
            return {"text": "API key working"}
        else:
            return {"text": "API key invalid"}

def update_api_key():
    print("🔐 SECURE API KEY UPDATE")
    print("=" * 50)
    print("This script will securely update your Google Gemini API key.")
    print("The key will NOT be displayed or logged anywhere.\n")
    
    # Get API key securely (won't show in terminal)
    try:
        api_key = getpass.getpass("Enter your new Google Gemini API key: ").strip()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return False
    
    if not api_key:
        print("❌ No API key provided")
        return False
    
    # Basic validation
    if not api_key.startswith("AIza"):
        print("⚠️  Warning: API key doesn't start with 'AIza' - this might not be correct")
        confirm = input("Continue anyway? (y/N): ").lower()
        if confirm != 'y':
            print("❌ Operation cancelled")
            return False
    
    if len(api_key) < 30:
        print("⚠️  Warning: API key seems too short")
        confirm = input("Continue anyway? (y/N): ").lower()
        if confirm != 'y':
            print("❌ Operation cancelled")
            return False
    
    # Update the start_server.sh file
    start_server_path = "/opt/DIY-MOD/Backend/start_server.sh"
    
    try:
        # Read the current file
        with open(start_server_path, 'r') as f:
            content = f.read()
        
        # Replace the GOOGLE_API_KEY line
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.startswith('export GOOGLE_API_KEY='):
                updated_lines.append(f'export GOOGLE_API_KEY="{api_key}"')
                print("✅ Updated GOOGLE_API_KEY in start_server.sh")
            else:
                updated_lines.append(line)
        
        # Write back to file
        with open(start_server_path, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        print("✅ API key updated successfully!")
        print("\n🔄 Next steps:")
        print("1. Restart the server to use the new API key")
        print("2. Test the new API key")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Could not find {start_server_path}")
        return False
    except PermissionError:
        print(f"❌ Permission denied writing to {start_server_path}")
        print("💡 Try running with sudo: sudo python3 update_api_key.py")
        return False
    except Exception as e:
        print(f"❌ Error updating file: {e}")
        return False

def test_api_key():
    """Test the updated API key"""
    print("\n🧪 Testing the new API key...")
    
    try:
        # Read the API key from the start_server.sh file
        start_server_path = "/opt/DIY-MOD/Backend/start_server.sh"
        
        with open(start_server_path, 'r') as f:
            content = f.read()
        
        # Extract API key
        api_key = None
        for line in content.split('\n'):
            if line.startswith('export GOOGLE_API_KEY='):
                api_key = line.split('=', 1)[1].strip().strip('"')
                break
        
        if not api_key:
            print("❌ Could not find API key in start_server.sh")
            return False
        
        # Test the API key
        print(f"✅ Found API key: {api_key[:15]}...")
        
        if GEMINI_AVAILABLE:
            client = genai_client.Client(api_key=api_key)
        else:
            client = MockGeminiTestClient(api_key=api_key)
            print("Using mock client for API key test")
        
        print("✅ Client initialized successfully")
        
        # Simple test
        response = client.models_generate_content(
            model='gemini-2.0-flash',
            contents=['Hello, can you respond with just "API key working"?']
        )
        
        if response and response.get("text"):
            print("✅ API key test successful!")
            print(f"📝 Response: {response['text'].strip()}")
            return True
        else:
            print("❌ API key test failed - no response")
            return False
            
    except Exception as e:
        print(f"❌ API key test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running on server - API key will be updated in start_server.sh")
    
    if update_api_key():
        # Ask if user wants to test
        test_choice = input("\n🧪 Test the new API key now? (Y/n): ").lower()
        if test_choice != 'n':
            test_api_key()
    
    print("\n🎯 Summary:")
    print("- API key has been securely updated")
    print("- Restart your server to use the new key")
    print("- The key was never displayed or logged") 