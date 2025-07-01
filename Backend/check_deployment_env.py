#!/usr/bin/env python3
"""
Deployment environment verification script for DIY Mod on Render.
Run this during build to verify Python version and SQLAlchemy compatibility.
"""
import sys
import os
import subprocess

def main():
    print("🔍 DIY Mod Deployment Environment Check")
    print("=" * 50)
    
    # Check Python version
    version = sys.version_info
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Python path: {sys.path[0] if sys.path else 'None'}")
    print()
    
    # Check environment variables
    print("Environment Variables:")
    python_version_env = os.environ.get('PYTHON_VERSION', 'Not set')
    print(f"PYTHON_VERSION: {python_version_env}")
    print(f"PATH: {os.environ.get('PATH', 'Not set')[:100]}...")
    print()
    
    # Check available Python versions
    print("Available Python executables:")
    try:
        result = subprocess.run(['ls', '-la', '/usr/bin/python*'], 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        else:
            print("No Python executables found in /usr/bin/")
    except Exception as e:
        print(f"Error checking Python executables: {e}")
    
    print()
    
    # Check if we're in the right version
    if version.major == 3 and version.minor == 12:
        print("✅ Using Python 3.12 - Perfect!")
        return 0
    elif version.major == 3 and version.minor == 13:
        print("⚠️  Using Python 3.13 - Should work with SQLAlchemy 2.0.41+")
        print("   But we prefer Python 3.12 for this deployment")
        return 0
    else:
        print(f"❌ Using Python {version.major}.{version.minor} - Unexpected version!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 