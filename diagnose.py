#!/usr/bin/env python3
"""
Diagnostic script to check environment and configuration
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("Brum Brum Tracker - Diagnostics")
print("=" * 60)

# Check Python version
print(f"\nPython Version: {sys.version}")

# Check .env file
env_path = Path(".env")
print(f"\n.env file exists: {env_path.exists()}")

if env_path.exists():
    from utils.constants import HOME_LAT, HOME_LON, OPENSKY_USERNAME, OPENSKY_PASSWORD
    
    print(f"\nConfiguration:")
    print(f"  HOME_LAT: {HOME_LAT}")
    print(f"  HOME_LON: {HOME_LON}")
    print(f"  OPENSKY_USERNAME: {'Set' if OPENSKY_USERNAME else 'Not set'}")
    print(f"  OPENSKY_PASSWORD: {'Set' if OPENSKY_PASSWORD else 'Not set'}")
    
    if HOME_LAT == 0.0 and HOME_LON == 0.0:
        print("\n⚠️  WARNING: Home location not configured!")
        print("   Please set HOME_LAT and HOME_LON in your .env file")
else:
    print("\n⚠️  WARNING: No .env file found!")
    print("   Copy .env.example to .env and configure it")

# Check imports
print("\nChecking imports:")
modules = [
    ('requests', 'requests'),
    ('websockets', 'websockets'),
    ('beautifulsoup4', 'bs4'),
    ('python-dotenv', 'dotenv'),
    ('opensky-api', 'opensky_api'),
    ('Pillow', 'PIL')
]

for package_name, import_name in modules:
    try:
        __import__(import_name)
        print(f"  ✓ {package_name}")
    except ImportError:
        print(f"  ✗ {package_name} - Not installed")

# Check network connectivity
print("\nChecking network connectivity:")
import requests
try:
    response = requests.get("https://opensky-network.org", timeout=5)
    print(f"  ✓ Can reach opensky-network.org (status: {response.status_code})")
except Exception as e:
    print(f"  ✗ Cannot reach opensky-network.org: {e}")

print("\n" + "=" * 60)