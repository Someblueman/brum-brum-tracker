#!/usr/bin/env python3
"""
Quick test to verify the fixes are working
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.opensky_client import FlightDataClient, build_bounding_box
from utils.constants import HOME_LAT, HOME_LON, SEARCH_RADIUS_KM

print("Testing fixed OpenSky client...")
print(f"Home: {HOME_LAT}, {HOME_LON}")
print(f"Radius: {SEARCH_RADIUS_KM}km")

client = FlightDataClient()
bbox = build_bounding_box(HOME_LAT, HOME_LON)
print(f"BBox: {bbox}")

aircraft = client.fetch_state_vectors(bbox)
print(f"\nFound {len(aircraft)} aircraft")

if aircraft:
    print("\nFiltering aircraft...")
    filtered = client.filter_aircraft(aircraft)
    print(f"Filtered to {len(filtered)} aircraft")
    
    visible = [a for a in filtered if client.is_visible(a)]
    print(f"Visible aircraft: {len(visible)}")
    
    if visible:
        best = client.select_best_plane(visible)
        if best:
            print(f"\nBest aircraft to track:")
            print(f"  ICAO24: {best['icao24']}")
            print(f"  Distance: {best['distance_km']:.1f}km")
            print(f"  Elevation: {best['elevation_angle']:.1f}°")
            print(f"  Altitude: {best['baro_altitude']}m")