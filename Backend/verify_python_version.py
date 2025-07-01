#!/usr/bin/env python3
"""
Script to verify Python version compatibility for the DIY Mod deployment.
"""
import sys
import pkg_resources

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    print(f"Current Python version: {sys.version}")
    
    if version.major == 3 and version.minor == 12:
        print("✅ Python 3.12 - Perfect! This is our target version.")
        return True
    elif version.major == 3 and version.minor == 13:
        print("⚠️  Python 3.13 - Should work with SQLAlchemy 2.0.41+")
        return True
    elif version.major == 3 and version.minor >= 11:
        print("✅ Python 3.11+ - Should be compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} - May have compatibility issues")
        return False

def check_sqlalchemy_version():
    """Check SQLAlchemy version."""
    try:
        sqlalchemy_version = pkg_resources.get_distribution("SQLAlchemy").version
        print(f"SQLAlchemy version: {sqlalchemy_version}")
        
        # Parse version to check if it's 2.0.41 or higher
        major, minor, patch = map(int, sqlalchemy_version.split('.'))
        
        if (major == 2 and minor == 0 and patch >= 41) or (major > 2) or (major == 2 and minor > 0):
            print("✅ SQLAlchemy version supports Python 3.13")
            return True
        else:
            print("⚠️  SQLAlchemy version may not support Python 3.13")
            return False
            
    except pkg_resources.DistributionNotFound:
        print("❌ SQLAlchemy not installed")
        return False

if __name__ == "__main__":
    print("🔍 DIY Mod Python Environment Check")
    print("=" * 40)
    
    python_ok = check_python_version()
    print()
    sqlalchemy_ok = check_sqlalchemy_version()
    print()
    
    if python_ok and sqlalchemy_ok:
        print("✅ All checks passed! Ready for deployment.")
        sys.exit(0)
    else:
        print("❌ Some compatibility issues found.")
        sys.exit(1) 