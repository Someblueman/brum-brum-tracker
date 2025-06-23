#!/usr/bin/env python3
"""
Complete test of the fixed system
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.opensky_client import FlightDataClient, build_bounding_box
from utils.constants import HOME_LAT, HOME_LON, SEARCH_RADIUS_KM

async def test_complete_flow():
    print("Complete System Test")
    print("=" * 60)
    
    # 1. Test API connection
    print("\n1. Testing API connection...")
    client = FlightDataClient()
    bbox = build_bounding_box(HOME_LAT, HOME_LON)
    
    aircraft = client.fetch_state_vectors(bbox)
    print(f"   ✓ Found {len(aircraft)} aircraft in region")
    
    if not aircraft:
        print("   No aircraft found - API might be rate limited or no aircraft in area")
        return
    
    # 2. Test filtering
    print("\n2. Testing aircraft filtering...")
    filtered = client.filter_aircraft(aircraft)
    print(f"   ✓ Filtered to {len(filtered)} aircraft meeting criteria")
    
    # 3. Test visibility calculation
    print("\n3. Testing visibility calculation...")
    visible = [a for a in filtered if client.is_visible(a)]
    print(f"   ✓ Found {len(visible)} visible aircraft (elevation > 20°)")
    
    # 4. Test best plane selection
    if visible:
        print("\n4. Testing best plane selection...")
        best = client.select_best_plane(visible)
        if best:
            print(f"   ✓ Selected aircraft {best['icao24']}:")
            print(f"     - Distance: {best['distance_km']:.1f} km")
            print(f"     - Elevation: {best['elevation_angle']:.1f}°")
            print(f"     - Altitude: {best['baro_altitude']:.0f} m ({best['baro_altitude']*3.28084:.0f} ft)")
            print(f"     - Bearing: {best['bearing_from_home']:.0f}°")
    
    # 5. Test message formatting
    print("\n5. Testing message formatting...")
    from backend.server import AircraftTracker
    tracker = AircraftTracker()
    
    if visible:
        message = tracker.format_aircraft_message(visible[0])
        print(f"   ✓ Aircraft message formatted with type: {message['type']}")
    
    if filtered:
        list_message = tracker.format_aircraft_list_message(filtered)
        print(f"   ✓ List message formatted with {list_message['aircraft_count']} aircraft")
        
        if list_message['aircraft']:
            print("\n   First aircraft in list:")
            first = list_message['aircraft'][0]
            print(f"     - ICAO24: {first['icao24']}")
            print(f"     - ETA: {first['eta_minutes']:.1f} minutes")
    
    print("\n" + "=" * 60)
    print("All systems operational! ✓")

if __name__ == "__main__":
    asyncio.run(test_complete_flow())