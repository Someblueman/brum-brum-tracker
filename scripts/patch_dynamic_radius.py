#!/usr/bin/env python3
"""
Patch to add dynamic radius expansion to the FlightDataClient.
This ensures we always try to find some aircraft, even if they're further away.
"""

# Here's the code to add to the FlightDataClient class in opensky_client.py:

def fetch_nearest_aircraft(self, home_lat: float = None, home_lon: float = None,
                          initial_radius: float = None, max_radius: float = 200,
                          radius_increment: float = 25) -> Tuple[List[Dict[str, Any]], float]:
    """
    Fetch aircraft with dynamic radius expansion to ensure we find something.
    
    Args:
        home_lat: Home latitude (defaults to Config.HOME_LAT)
        home_lon: Home longitude (defaults to Config.HOME_LON)
        initial_radius: Starting search radius (defaults to Config.SEARCH_RADIUS_KM)
        max_radius: Maximum search radius in km
        radius_increment: How much to increase radius each iteration
        
    Returns:
        Tuple of (aircraft_list, actual_radius_used)
    """
    if home_lat is None:
        home_lat = Config.HOME_LAT
    if home_lon is None:
        home_lon = Config.HOME_LON
    if initial_radius is None:
        initial_radius = Config.SEARCH_RADIUS_KM
    
    current_radius = initial_radius
    best_aircraft = []
    best_radius = initial_radius
    
    while current_radius <= max_radius:
        logger.info(f"Searching with radius: {current_radius} km")
        
        # Build bounding box
        bbox = self.build_bounding_box(home_lat, home_lon, current_radius)
        
        # Fetch aircraft
        aircraft_list = self.fetch_state_vectors(bbox)
        
        if aircraft_list:
            # Filter for airborne aircraft only
            airborne = [a for a in aircraft_list if not a.get('on_ground', True)]
            
            if airborne:
                logger.info(f"Found {len(airborne)} airborne aircraft with {current_radius}km radius")
                best_aircraft = airborne
                best_radius = current_radius
                break
        
        # Increase radius for next iteration
        current_radius += radius_increment
    
    if not best_aircraft:
        logger.warning(f"No airborne aircraft found even with {max_radius}km radius")
    
    return best_aircraft, best_radius


def filter_aircraft_dynamic(self, aircraft_list: List[Dict[str, Any]], 
                           home_lat: float = None, 
                           home_lon: float = None,
                           search_radius: float = None) -> List[Dict[str, Any]]:
    """
    Filter aircraft with dynamic search radius.
    
    Args:
        aircraft_list: List of aircraft state dictionaries
        home_lat: Home latitude
        home_lon: Home longitude
        search_radius: Override search radius (if None, uses distance of furthest aircraft)
        
    Returns:
        Filtered list of aircraft
    """
    if home_lat is None:
        home_lat = Config.HOME_LAT
    if home_lon is None:
        home_lon = Config.HOME_LON
    
    filtered = []
    
    for aircraft in aircraft_list:
        # Skip if on ground
        if aircraft.get('on_ground', True):
            continue
        
        # Skip if no altitude data
        if aircraft.get('baro_altitude') is None:
            continue
        
        # Skip if altitude is too low (< 500m)
        if aircraft.get('baro_altitude', 0) < 500:
            continue
        
        # Skip if no position
        if aircraft.get('latitude') is None or aircraft.get('longitude') is None:
            continue
        
        # Calculate distance from home
        distance = haversine_distance(
            home_lat, home_lon,
            aircraft['latitude'], aircraft['longitude']
        )
        aircraft['distance_km'] = distance
        
        # If search_radius is provided, use it; otherwise include all
        if search_radius is not None and distance > search_radius:
            continue
        
        # Calculate bearings
        home_to_plane = bearing_between(
            home_lat, home_lon,
            aircraft['latitude'], aircraft['longitude']
        )
        plane_to_home = bearing_between(
            aircraft['latitude'], aircraft['longitude'],
            home_lat, home_lon
        )
        
        aircraft['bearing_from_home'] = home_to_plane
        aircraft['bearing_to_home'] = plane_to_home
        
        # Include all aircraft regardless of direction when using dynamic radius
        filtered.append(aircraft)
    
    logger.debug(f"Filtered {len(aircraft_list)} aircraft to {len(filtered)}")
    return filtered


# Here's how to modify the server.py to use dynamic radius:
"""
In backend/server.py, modify the track_aircraft function:

async def track_aircraft():
    while True:
        try:
            # Try to get aircraft with dynamic radius
            aircraft_list, actual_radius = opensky_client.fetch_nearest_aircraft(
                initial_radius=Config.SEARCH_RADIUS_KM,
                max_radius=150,  # Don't search too far
                radius_increment=25
            )
            
            if actual_radius > Config.SEARCH_RADIUS_KM:
                logger.info(f"Expanded search radius from {Config.SEARCH_RADIUS_KM}km to {actual_radius}km")
            
            # Filter with the actual radius used
            filtered_aircraft = opensky_client.filter_aircraft_dynamic(
                aircraft_list,
                search_radius=actual_radius
            )
            
            # Rest of the function remains the same...
"""

print("Dynamic radius expansion code ready to be integrated.")
print("\nTo implement:")
print("1. Add the two methods above to FlightDataClient in backend/api/opensky_client.py")
print("2. Modify track_aircraft() in backend/server.py to use fetch_nearest_aircraft()")
print("\nThis will ensure the app always tries to find some aircraft, even if they're further away than the configured radius.")