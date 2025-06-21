"""
OpenSky Network API client for fetching real-time flight data.
"""

import time
import math
import logging
from typing import List, Dict, Any, Optional, Tuple
from opensky_api import OpenSkyApi

from utils.constants import (
    OPENSKY_USERNAME, 
    OPENSKY_PASSWORD, 
    HOME_LAT, 
    HOME_LON,
    SEARCH_RADIUS_KM,
    MIN_ELEVATION_ANGLE,
    POLLING_INTERVAL
)
from utils.geometry import (
    haversine_distance, 
    bearing_between, 
    elevation_angle,
    is_plane_approaching
)


logger = logging.getLogger(__name__)


class FlightDataClient:
    """Client for fetching and processing flight data from OpenSky Network."""
    
    def __init__(self):
        """Initialize the OpenSky API client."""
        self.last_request_time = 0
        
        # Initialize API client with or without credentials
        if OPENSKY_USERNAME and OPENSKY_PASSWORD:
            self.api = OpenSkyApi(username=OPENSKY_USERNAME, password=OPENSKY_PASSWORD)
            logger.info("Initialized OpenSky API with authentication")
        else:
            self.api = OpenSkyApi()
            logger.info("Initialized OpenSky API without authentication (rate limited)")
    
    def _enforce_rate_limit(self) -> None:
        """Ensure we respect the API rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < POLLING_INTERVAL:
            sleep_time = POLLING_INTERVAL - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.1f} seconds")
            time.sleep(sleep_time)
    
    def fetch_state_vectors(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """
        Fetch aircraft state vectors within a bounding box.
        
        Args:
            bbox: Tuple of (min_lat, max_lat, min_lon, max_lon)
            
        Returns:
            List of aircraft state dictionaries
        """
        self._enforce_rate_limit()
        
        try:
            # Fetch states from API
            states = self.api.get_states(bbox=bbox)
            self.last_request_time = time.time()
            
            if not states:
                return []
            
            # Convert state vectors to dictionaries
            aircraft_list = []
            for state in states.states:
                aircraft = {
                    'icao24': state.icao24,
                    'callsign': state.callsign.strip() if state.callsign else '',
                    'origin_country': state.origin_country,
                    'longitude': state.longitude,
                    'latitude': state.latitude,
                    'baro_altitude': state.baro_altitude,  # meters
                    'velocity': state.velocity,  # m/s
                    'true_track': state.true_track,  # degrees
                    'on_ground': state.on_ground,
                    'vertical_rate': state.vertical_rate,  # m/s
                    'last_contact': state.time_position
                }
                aircraft_list.append(aircraft)
            
            logger.info(f"Fetched {len(aircraft_list)} aircraft from OpenSky")
            return aircraft_list
            
        except Exception as e:
            logger.error(f"Error fetching state vectors: {e}")
            return []
    
    def build_bounding_box(self, home_lat: float, home_lon: float, 
                          radius_km: float = SEARCH_RADIUS_KM) -> Tuple[float, float, float, float]:
        """
        Build a bounding box around a center point.
        
        Args:
            home_lat: Center latitude
            home_lon: Center longitude
            radius_km: Search radius in kilometers
            
        Returns:
            Tuple of (min_lat, max_lat, min_lon, max_lon)
        """
        # Approximate degrees per kilometer
        lat_degree_km = 111.0
        lon_degree_km = 111.0 * abs(math.cos(math.radians(home_lat)))
        
        # Calculate offsets
        lat_offset = radius_km / lat_degree_km
        lon_offset = radius_km / lon_degree_km
        
        # Build bounding box
        min_lat = home_lat - lat_offset
        max_lat = home_lat + lat_offset
        min_lon = home_lon - lon_offset
        max_lon = home_lon + lon_offset
        
        return (min_lat, max_lat, min_lon, max_lon)
    
    def filter_aircraft(self, aircraft_list: List[Dict[str, Any]], 
                       home_lat: float = HOME_LAT, 
                       home_lon: float = HOME_LON) -> List[Dict[str, Any]]:
        """
        Filter aircraft based on various criteria.
        
        Args:
            aircraft_list: List of aircraft state dictionaries
            home_lat: Home latitude
            home_lon: Home longitude
            
        Returns:
            Filtered list of aircraft
        """
        filtered = []
        
        for aircraft in aircraft_list:
            # Skip if on ground
            if aircraft['on_ground']:
                continue
            
            # Skip if no altitude data
            if aircraft['baro_altitude'] is None:
                continue
            
            # Skip if altitude is too low (< 500m)
            if aircraft['baro_altitude'] < 500:
                continue
            
            # Calculate distance from home
            distance = haversine_distance(
                home_lat, home_lon,
                aircraft['latitude'], aircraft['longitude']
            )
            aircraft['distance_km'] = distance
            
            # Skip if outside search radius
            if distance > SEARCH_RADIUS_KM:
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
            
            # Skip if plane is moving away (if we have track data)
            if aircraft['true_track'] is not None:
                if not is_plane_approaching(
                    home_to_plane, plane_to_home, 
                    aircraft['true_track']
                ):
                    continue
            
            filtered.append(aircraft)
        
        logger.debug(f"Filtered {len(aircraft_list)} aircraft to {len(filtered)}")
        return filtered
    
    def is_visible(self, aircraft: Dict[str, Any]) -> bool:
        """
        Check if an aircraft is visible based on elevation angle.
        
        Args:
            aircraft: Aircraft state dictionary with distance_km
            
        Returns:
            True if aircraft is visible
        """
        if 'distance_km' not in aircraft:
            return False
        
        # Calculate elevation angle
        angle = elevation_angle(
            aircraft['distance_km'],
            aircraft['baro_altitude']
        )
        aircraft['elevation_angle'] = angle
        
        return angle >= MIN_ELEVATION_ANGLE
    
    def select_best_plane(self, visible_planes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Select the best plane to track based on visibility.
        
        Args:
            visible_planes: List of visible aircraft
            
        Returns:
            Best aircraft to track or None
        """
        if not visible_planes:
            return None
        
        # Sort by elevation angle (highest first)
        sorted_planes = sorted(
            visible_planes,
            key=lambda p: p.get('elevation_angle', 0),
            reverse=True
        )
        
        best = sorted_planes[0]
        logger.info(f"Selected aircraft {best['icao24']} with elevation {best['elevation_angle']:.1f}°")
        
        return best


# Module-level convenience functions
_client = None


def get_client() -> FlightDataClient:
    """Get or create the flight data client."""
    global _client
    if _client is None:
        _client = FlightDataClient()
    return _client


def fetch_state_vectors(bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
    """Fetch aircraft state vectors within a bounding box."""
    client = get_client()
    return client.fetch_state_vectors(bbox)


def build_bounding_box(home_lat: float, home_lon: float, 
                      radius_km: float = SEARCH_RADIUS_KM) -> Tuple[float, float, float, float]:
    """Build a bounding box for the search area."""
    client = get_client()
    return client.build_bounding_box(home_lat, home_lon, radius_km)


def filter_aircraft(aircraft_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter aircraft based on visibility criteria."""
    client = get_client()
    return client.filter_aircraft(aircraft_list)


def is_visible(aircraft: Dict[str, Any]) -> bool:
    """Check if an aircraft is visible."""
    client = get_client()
    return client.is_visible(aircraft)


def select_best_plane(visible_planes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Select the best plane to track."""
    client = get_client()
    return client.select_best_plane(visible_planes)