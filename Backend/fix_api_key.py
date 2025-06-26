#!/usr/bin/env python3
"""
Fix Google API Key Script
Updates the Google API key in the start_server.sh file securely
"""
import os
import sys
import getpass
import subprocess
from pathlib import Path

def main():
    print("🔧 DIY Content Moderation - API Key Fix")
    print("=" * 50)
    print("This script will update your Google Gemini API key.")
    print("The key will NOT be displayed or logged anywhere.\n")
    
    # Get the current working directory
    backend_dir = Path(__file__).parent
    start_server_path = backend_dir / "start_server.sh"
    
    if not start_server_path.exists():
        print(f"❌ start_server.sh not found at {start_server_path}")
        print("💡 Make sure you're running this from the Backend directory")
        return 1
    
    # Get API key securely
    try:
        api_key = getpass.getpass("Enter your Google Gemini API key (starts with 'AIza'): ").strip()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return 1
    
    if not api_key:
        print("❌ No API key provided")
        return 1
    
    # Basic validation
    if not api_key.startswith("AIza"):
        print("⚠️  Warning: API key doesn't start with 'AIza'")
        confirm = input("Continue anyway? (y/N): ").lower()
        if confirm != 'y':
            print("❌ Operation cancelled")
            return 1
    
    if len(api_key) < 30:
        print("⚠️  Warning: API key seems too short")
        confirm = input("Continue anyway? (y/N): ").lower()
        if confirm != 'y':
            print("❌ Operation cancelled")
            return 1
    
    # Update the start_server.sh file
    try:
        # Read current content
        with open(start_server_path, 'r') as f:
            lines = f.readlines()
        
        # Update GOOGLE_API_KEY line
        updated_lines = []
        key_updated = False
        
        for line in lines:
            if line.strip().startswith('export GOOGLE_API_KEY='):
                updated_lines.append(f'export GOOGLE_API_KEY="{api_key}"\n')
                key_updated = True
                print("✅ Updated GOOGLE_API_KEY in start_server.sh")
            else:
                updated_lines.append(line)
        
        # If no existing key line found, add it
        if not key_updated:
            # Find a good place to insert it (after other exports)
            insert_index = 0
            for i, line in enumerate(updated_lines):
                if line.strip().startswith('export '):
                    insert_index = i + 1
            
            updated_lines.insert(insert_index, f'export GOOGLE_API_KEY="{api_key}"\n')
            print("✅ Added GOOGLE_API_KEY to start_server.sh")
        
        # Write back to file
        with open(start_server_path, 'w') as f:
            f.writelines(updated_lines)
        
        print("✅ API key updated successfully!")
        
        # Make the script executable
        try:
            os.chmod(start_server_path, 0o755)
            print("✅ Made start_server.sh executable")
        except Exception as e:
            print(f"⚠️  Could not make script executable: {e}")
        
        print("\n🔄 Next steps:")
        print("1. Restart the server: pkill -f uvicorn && ./start_server.sh")
        print("2. Test image processing")
        print("3. Check server logs for any remaining errors")
        
        return 0
        
    except PermissionError:
        print(f"❌ Permission denied writing to {start_server_path}")
        print("💡 Try running with sudo or check file permissions")
        return 1
    except Exception as e:
        print(f"❌ Error updating file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 