#!/usr/bin/env python3
"""
Test script to verify OpenSky API connectivity and data retrieval
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from backend.opensky_client import (
    FlightDataClient,
    build_bounding_box,
    HOME_LAT,
    HOME_LON,
    SEARCH_RADIUS_KM,
)

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_direct_http():
    """Test direct HTTP connection to OpenSky API."""
    import requests

    print("+" * 60)
    print("Direct HTTP API Test")
    print("=" * 60)

    url = "https://opensky-network.org/api/states/all"

    # Test without bounding box first
    print("Testing API without bounding box...")
    try:
        response = requests.get(url, timeout=10)
        print(f"  Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            states = data.get("states", [])
            print(f"  Total aircraft worldwide: {len(states)}")
            if states:
                print(f"  First aircraft: {states[0][0]} (ICAO24)")
        else:
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"  Failed: {e}")

    # Test with bounding box
    if HOME_LAT != 0.0 and HOME_LON != 0.0:
        print(f"Testing API with bounding box around", ({HOME_LAT}, {HOME_LON}), "...")
        bbox = build_bounding_box(HOME_LAT, HOME_LON, SEARCH_RADIUS_KM)
        params = {
            "lamin": bbox[0],
            "lamax": bbox[1],
            "lomin": bbox[2],
            "lomax": bbox[3],
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            print(f"  Status Code: {response.status_code}")
            print(f"  URL: {response.url}")

            if response.status_code == 200:
                data = response.json()
                states = data.get("states", [])
                print(f"  Aircraft in region: {len(states)}")
            else:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"  Failed: {e}")


def test_opensky_api():
    """Test the OpenSky API connection and data retrieval."""
    print("=" * 60)
    print("OpenSky API Test")
    print("=" * 60)

    # Check configuration
    print(f"\nConfiguration:")
    print(f"  Home Location: {HOME_LAT}, {HOME_LON}")
    print(f"  Search Radius: {SEARCH_RADIUS_KM} km")

    if HOME_LAT == 0.0 and HOME_LON == 0.0:
        print("\nERROR: Home location not configured!")
        print("Please set HOME_LAT and HOME_LON in your .env file")
        return

    # Initialize client
    print("\nInitializing OpenSky client...")
    client = FlightDataClient()

    # Build bounding box
    print("\nBuilding search bounding box...")
    bbox = build_bounding_box(HOME_LAT, HOME_LON, SEARCH_RADIUS_KM)
    print(f"  Bounding box: {bbox}")

    # Fetch aircraft
    print("\nFetching aircraft data...")
    try:
        aircraft_list = client.fetch_state_vectors(bbox)
        print(f"\nResults:")
        print(f"  Total aircraft found: {len(aircraft_list)}")

        if aircraft_list:
            print("\nFirst 5 aircraft:")
            for i, aircraft in enumerate(aircraft_list[:5]):
                print(f"\n  Aircraft {i+1}:")
                print(f"    ICAO24: {aircraft['icao24']}")
                print(f"    Callsign: {aircraft['callsign']}")
                print(f"    Position: {aircraft['latitude']}, {aircraft['longitude']}")
                print(f"    Altitude: {aircraft['baro_altitude']} m")
                print(f"    On Ground: {aircraft['on_ground']}")
        else:
            print("\nNo aircraft found in the search area.")
            print("This could mean:")
            print("  1. No aircraft are currently in your search area")
            print("  2. The API is rate-limited (try again in a few seconds)")
            print("  3. There's a connection issue")

    except Exception as e:
        print(f"\nERROR: Failed to fetch aircraft data: {e}")
        logger.exception("Detailed error information:")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Test direct HTTP first
    test_direct_http()

    # Then test the client
    test_opensky_api()
