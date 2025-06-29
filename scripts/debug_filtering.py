#!/usr/bin/env python3
"""
Debug the filtering logic to understand why aircraft are being filtered out.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.api.opensky_client import FlightDataClient
from backend.utils.config import Config
from backend.utils.geometry import haversine_distance, bearing_between, is_plane_approaching
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_filtering():
    """Debug why aircraft are being filtered out."""
    client = FlightDataClient()
    
    # Use 100km radius
    radius = 100
    bbox = client.build_bounding_box(Config.HOME_LAT, Config.HOME_LON, radius)
    
    print(f"\nDebug Filtering - Home: {Config.HOME_LAT}, {Config.HOME_LON}")
    print(f"Search radius: {Config.SEARCH_RADIUS_KM} km (configured)")
    print(f"Min elevation angle: {Config.MIN_ELEVATION_ANGLE}°")
    print("=" * 80)
    
    aircraft_list = client.fetch_state_vectors(bbox)
    
    if not aircraft_list:
        print("No aircraft fetched")
        return
    
    print(f"\nTotal aircraft fetched: {len(aircraft_list)}")
    
    # Manual filtering with detailed logging
    for idx, aircraft in enumerate(aircraft_list):
        print(f"\n--- Aircraft {idx + 1}: {aircraft.get('callsign', 'Unknown')} ---")
        print(f"ICAO24: {aircraft.get('icao24')}")
        print(f"Country: {aircraft.get('origin_country')}")
        
        # Check on_ground
        on_ground = aircraft.get('on_ground', None)
        print(f"On ground: {on_ground}")
        if on_ground:
            print("  → FILTERED: Aircraft is on ground")
            continue
        
        # Check altitude
        altitude = aircraft.get('baro_altitude')
        print(f"Altitude: {altitude} meters")
        if altitude is None:
            print("  → FILTERED: No altitude data")
            continue
        if altitude < 500:
            print(f"  → FILTERED: Altitude too low ({altitude} < 500m)")
            continue
        
        # Calculate distance
        lat = aircraft.get('latitude')
        lon = aircraft.get('longitude')
        print(f"Position: ({lat}, {lon})")
        
        if lat is None or lon is None:
            print("  → FILTERED: No position data")
            continue
        
        distance = haversine_distance(Config.HOME_LAT, Config.HOME_LON, lat, lon)
        print(f"Distance from home: {distance:.1f} km")
        
        if distance > Config.SEARCH_RADIUS_KM:
            print(f"  → FILTERED: Outside search radius ({distance:.1f} > {Config.SEARCH_RADIUS_KM} km)")
            continue
        
        # Calculate bearings
        home_to_plane = bearing_between(Config.HOME_LAT, Config.HOME_LON, lat, lon)
        plane_to_home = bearing_between(lat, lon, Config.HOME_LAT, Config.HOME_LON)
        print(f"Bearing from home: {home_to_plane:.0f}°")
        print(f"Bearing to home: {plane_to_home:.0f}°")
        
        # Check if approaching
        true_track = aircraft.get('true_track')
        print(f"True track: {true_track}°")
        
        if true_track is not None:
            approaching = is_plane_approaching(home_to_plane, plane_to_home, true_track)
            print(f"Is approaching: {approaching}")
            if not approaching:
                print("  → FILTERED: Plane is moving away")
                continue
        
        print("  ✓ PASSED ALL FILTERS")

if __name__ == "__main__":
    debug_filtering()