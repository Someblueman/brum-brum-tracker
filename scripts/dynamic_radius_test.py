#!/usr/bin/env python3
"""
Test dynamic radius adjustment to ensure we always find some aircraft.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.api.opensky_client import FlightDataClient
from backend.utils.config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_dynamic_radius():
    """Test fetching aircraft with dynamically expanding radius."""
    client = FlightDataClient()
    
    # Start with configured radius
    initial_radius = Config.SEARCH_RADIUS_KM
    max_radius = 200  # Maximum search radius
    radius_increment = 25  # How much to increase each time
    
    current_radius = initial_radius
    aircraft_found = []
    
    print(f"\nSearching for aircraft near {Config.HOME_LAT}, {Config.HOME_LON}")
    print("=" * 60)
    
    while current_radius <= max_radius and len(aircraft_found) == 0:
        print(f"\nTrying radius: {current_radius} km")
        
        # Build bounding box
        bbox = client.build_bounding_box(Config.HOME_LAT, Config.HOME_LON, current_radius)
        print(f"Bounding box: {bbox}")
        
        # Fetch aircraft
        aircraft_list = client.fetch_state_vectors(bbox)
        
        if aircraft_list:
            # Filter for airborne aircraft
            airborne = [a for a in aircraft_list if not a.get('on_ground', True)]
            print(f"Found {len(aircraft_list)} total aircraft, {len(airborne)} airborne")
            
            if airborne:
                aircraft_found = airborne
                print("\nAirborne aircraft found:")
                for i, aircraft in enumerate(airborne[:5]):
                    print(f"\n  {i+1}. {aircraft.get('callsign', 'Unknown')}")
                    print(f"     ICAO24: {aircraft.get('icao24')}")
                    print(f"     Position: ({aircraft.get('latitude')}, {aircraft.get('longitude')})")
                    print(f"     Altitude: {aircraft.get('baro_altitude')} meters")
                    print(f"     Country: {aircraft.get('origin_country')}")
        else:
            print("No aircraft found")
        
        if not aircraft_found:
            current_radius += radius_increment
    
    if aircraft_found:
        print(f"\n✓ Success! Found {len(aircraft_found)} airborne aircraft with {current_radius}km radius")
        print("\nRecommendation: Consider updating your SEARCH_RADIUS_KM to", current_radius)
    else:
        print(f"\n✗ No airborne aircraft found even with {max_radius}km radius")
        print("This might be due to the time of day or location")
    
    return aircraft_found, current_radius

def test_filter_and_visibility():
    """Test the filtering and visibility calculations."""
    client = FlightDataClient()
    
    # Use 100km radius since we know it finds aircraft
    radius = 100
    bbox = client.build_bounding_box(Config.HOME_LAT, Config.HOME_LON, radius)
    
    print(f"\n\nTesting filtering and visibility with {radius}km radius")
    print("=" * 60)
    
    aircraft_list = client.fetch_state_vectors(bbox)
    
    if aircraft_list:
        print(f"\nTotal aircraft fetched: {len(aircraft_list)}")
        
        # Apply filters
        filtered = client.filter_aircraft(aircraft_list)
        print(f"After filtering: {len(filtered)} aircraft")
        
        # Check visibility
        visible = []
        for aircraft in filtered:
            if client.is_visible(aircraft):
                visible.append(aircraft)
        
        print(f"Visible aircraft: {len(visible)}")
        
        if visible:
            print("\nVisible aircraft details:")
            for aircraft in visible:
                print(f"\n  Callsign: {aircraft.get('callsign', 'Unknown')}")
                print(f"  Distance: {aircraft.get('distance_km', 0):.1f} km")
                print(f"  Altitude: {aircraft.get('baro_altitude', 0):.0f} meters")
                print(f"  Elevation angle: {aircraft.get('elevation_angle', 0):.1f}°")
                print(f"  Bearing from home: {aircraft.get('bearing_from_home', 0):.0f}°")

if __name__ == "__main__":
    # Test 1: Dynamic radius
    aircraft, radius = test_dynamic_radius()
    
    # Test 2: Filtering and visibility
    test_filter_and_visibility()