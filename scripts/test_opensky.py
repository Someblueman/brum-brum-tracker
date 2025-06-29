#!/usr/bin/env python3
"""
Test script for debugging OpenSky Network API issues.
This script makes direct API calls to help diagnose connectivity and data retrieval problems.
"""

import os
import sys
import time
import json
import math
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import our config after path is set
from backend.utils.config import Config

def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def format_timestamp(ts: int) -> str:
    """Convert Unix timestamp to human-readable format."""
    if ts:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    return "No timestamp"

def calculate_bounding_box(lat: float, lon: float, radius_km: float) -> Tuple[float, float, float, float]:
    """Calculate bounding box for given center and radius."""
    lat_degree_km = 111.0
    lon_degree_km = 111.0 * abs(math.cos(math.radians(lat)))
    
    lat_offset = radius_km / lat_degree_km
    lon_offset = radius_km / lon_degree_km
    
    min_lat = lat - lat_offset
    max_lat = lat + lat_offset
    min_lon = lon - lon_offset
    max_lon = lon + lon_offset
    
    return (min_lat, max_lat, min_lon, max_lon)

def test_direct_api_call(bbox: Tuple[float, float, float, float], auth_token: Optional[str] = None) -> Dict:
    """Make a direct API call to OpenSky Network."""
    url = "https://opensky-network.org/api/states/all"
    params = {
        'lamin': bbox[0],
        'lamax': bbox[1],
        'lomin': bbox[2],
        'lomax': bbox[3]
    }
    
    headers = {}
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    
    print(f"Making request to: {url}")
    print(f"Parameters: {json.dumps(params, indent=2)}")
    if auth_token:
        print("Using OAuth2 authentication")
    else:
        print("Using anonymous access")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error Response: {response.text}")
            return {}
    except Exception as e:
        print(f"Request failed: {e}")
        return {}

def get_oauth_token(username: str, password: str) -> Optional[str]:
    """Get OAuth2 token from OpenSky auth server."""
    if not username or not password:
        return None
    
    token_url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': username,
        'client_secret': password
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=10)
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token')
        else:
            print(f"OAuth2 authentication failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"OAuth2 request failed: {e}")
        return None

def analyze_response(data: Dict) -> None:
    """Analyze and display the API response."""
    if not data:
        print("No data received")
        return
    
    # Display timestamp information
    if 'time' in data:
        timestamp = data['time']
        print(f"\nAPI Response Time: {timestamp} ({format_timestamp(timestamp)})")
        current_time = int(time.time())
        print(f"Current Time: {current_time} ({format_timestamp(current_time)})")
        print(f"Time Difference: {current_time - timestamp} seconds")
    
    # Display states information
    states = data.get('states')
    if states is None:
        print("\nStates field is null/None - No aircraft in the area")
    elif isinstance(states, list):
        print(f"\nNumber of aircraft found: {len(states)}")
        
        if states:
            print("\nFirst 5 aircraft:")
            for i, state in enumerate(states[:5]):
                if len(state) >= 17:
                    print(f"\n  Aircraft {i+1}:")
                    print(f"    ICAO24: {state[0]}")
                    print(f"    Callsign: {state[1]}")
                    print(f"    Country: {state[2]}")
                    print(f"    Position: ({state[6]}, {state[5]}) if available")
                    print(f"    Altitude: {state[7]} meters")
                    print(f"    On Ground: {state[8]}")
                    print(f"    Velocity: {state[9]} m/s")
    else:
        print(f"\nUnexpected states type: {type(states)}")

def test_location(name: str, lat: float, lon: float, radius_km: float, auth_token: Optional[str] = None):
    """Test API call for a specific location."""
    print_header(f"Testing {name}")
    print(f"Center: {lat}, {lon}")
    print(f"Radius: {radius_km} km")
    
    bbox = calculate_bounding_box(lat, lon, radius_km)
    print(f"Bounding box: {bbox}")
    
    data = test_direct_api_call(bbox, auth_token)
    analyze_response(data)

def main():
    """Main test function."""
    print_header("OpenSky Network API Test Script")
    
    # Load configuration
    print("Configuration:")
    print(f"  HOME_LAT: {Config.HOME_LAT}")
    print(f"  HOME_LON: {Config.HOME_LON}")
    print(f"  SEARCH_RADIUS_KM: {Config.SEARCH_RADIUS_KM}")
    print(f"  OPENSKY_USERNAME: {'Set' if Config.OPENSKY_USERNAME else 'Not set'}")
    print(f"  OPENSKY_PASSWORD: {'Set' if Config.OPENSKY_PASSWORD else 'Not set'}")
    
    # Try to get OAuth2 token
    auth_token = None
    if Config.OPENSKY_USERNAME and Config.OPENSKY_PASSWORD:
        print("\nAttempting OAuth2 authentication...")
        auth_token = get_oauth_token(Config.OPENSKY_USERNAME, Config.OPENSKY_PASSWORD)
        if auth_token:
            print("OAuth2 authentication successful!")
        else:
            print("OAuth2 authentication failed, continuing with anonymous access")
    
    # Test 1: Current configuration
    test_location(
        "Current Configuration",
        Config.HOME_LAT,
        Config.HOME_LON,
        Config.SEARCH_RADIUS_KM,
        auth_token
    )
    
    # Test 2: Larger radius
    test_location(
        "Larger Radius (100km)",
        Config.HOME_LAT,
        Config.HOME_LON,
        100,
        auth_token
    )
    
    # Test 3: Major airports
    airports = [
        ("London Heathrow", 51.4700, -0.4543),
        ("Amsterdam Schiphol", 52.3105, 4.7683),
        ("Frankfurt", 50.0379, 8.5622),
        ("Paris CDG", 49.0097, 2.5479),
        ("New York JFK", 40.6413, -73.7781),
    ]
    
    print_header("Testing Major Airports (50km radius)")
    for name, lat, lon in airports:
        test_location(name, lat, lon, 50, auth_token)
        time.sleep(2)  # Rate limiting
    
    # Test 4: Raw API test without parameters
    print_header("Testing Raw API (no bbox parameters)")
    url = "https://opensky-network.org/api/states/all"
    headers = {}
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            states = data.get('states')
            if states is None:
                print("States is null - no data available")
            else:
                print(f"Total aircraft worldwide: {len(states) if isinstance(states, list) else 'Unknown'}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print_header("Test Complete")

if __name__ == "__main__":
    main()