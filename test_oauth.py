#!/usr/bin/env python3
"""
Test OAuth2 authentication with OpenSky API
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.constants import OPENSKY_USERNAME, OPENSKY_PASSWORD

print("Testing OpenSky OAuth2 Authentication")
print("=" * 60)

# Check credentials
print(f"\nCredentials configured:")
print(f"  Client ID (OPENSKY_USERNAME): {'Set' if OPENSKY_USERNAME else 'Not set'}")
print(f"  Client Secret (OPENSKY_PASSWORD): {'Set' if OPENSKY_PASSWORD else 'Not set'}")

if not OPENSKY_USERNAME or not OPENSKY_PASSWORD:
    print("\n⚠️  No OAuth2 credentials configured!")
    print("Please set OPENSKY_USERNAME and OPENSKY_PASSWORD in your .env file")
    print("These should be your OAuth2 client_id and client_secret from OpenSky")
    sys.exit(1)

# Test token acquisition
print("\nTesting OAuth2 token acquisition...")
import requests

token_url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
data = {
    'grant_type': 'client_credentials',
    'client_id': OPENSKY_USERNAME,
    'client_secret': OPENSKY_PASSWORD
}

try:
    response = requests.post(token_url, data=data, timeout=10)
    print(f"  Token endpoint status: {response.status_code}")
    
    if response.status_code == 200:
        token_data = response.json()
        token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 0)
        
        print(f"  ✓ Token obtained successfully!")
        print(f"  Token expires in: {expires_in} seconds")
        print(f"  Token preview: {token[:20]}..." if token else "No token")
        
        # Test API call with token
        print("\nTesting API call with OAuth2 token...")
        api_url = "https://opensky-network.org/api/states/all"
        headers = {'Authorization': f'Bearer {token}'}
        
        api_response = requests.get(api_url, headers=headers, timeout=10)
        print(f"  API status: {api_response.status_code}")
        
        if api_response.status_code == 200:
            data = api_response.json()
            states = data.get('states', [])
            print(f"  ✓ API call successful!")
            print(f"  Aircraft worldwide: {len(states)}")
        else:
            print(f"  ✗ API call failed: {api_response.text}")
            
    else:
        print(f"  ✗ Token request failed: {response.status_code}")
        print(f"  Response: {response.text}")
        
except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n" + "=" * 60)