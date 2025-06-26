"""
OpenSky Network API client for fetching real-time flight data.
"""

import time
import math
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple

try:
    from opensky_api import OpenSkyApi
    OPENSKY_API_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("opensky_api package not found, will use HTTP fallback")
    OPENSKY_API_AVAILABLE = False

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

def _get_mock_aircraft_state() -> List[Dict[str, Any]]:
    """
    Returns a list with a single, hardcoded mock aircraft for testing.
    """
    logger.info("--- USING MOCK AIRCRAFT DATA ---")
    mock_plane = {
        'icao24': '3474CB',
        'callsign': 'BCS2886',
        'origin_country': 'United Kingdom',
        'longitude': 1.35,      # Was 1.735
        'latitude': 51.3,       # Was 51.1633
        'baro_altitude': 11887,  # meters
        'velocity': 230,        # m/s (approx 450 knots)
        'true_track': 270,      # Flying due west
        'on_ground': False,
        'vertical_rate': 0,
        'last_contact': time.time()
    }
    return [mock_plane]


class FlightDataClient:
    """Client for fetching and processing flight data from OpenSky Network."""
    
    def __init__(self):
        """Initialize the OpenSky API client."""
        self.last_request_time = 0
        # Force HTTP fallback due to OAuth2 requirements
        self.use_http_fallback = True
        self.access_token = None
        self.token_expires_at = 0
        
        # Initialize API client with or without credentials
        if self.use_http_fallback:
            self.api = None
            self.session = requests.Session()
            # Note: Basic auth doesn't work well with requests Session for OpenSky
            # We'll add auth headers manually in each request
            logger.info("Using HTTP fallback (authentication will be added per-request)")
        else:
            if OPENSKY_USERNAME and OPENSKY_PASSWORD:
                self.api = OpenSkyApi(username=OPENSKY_USERNAME, password=OPENSKY_PASSWORD)
                logger.info("Initialized OpenSky API with authentication")
            else:
                self.api = OpenSkyApi()
                logger.info("Initialized OpenSky API without authentication (rate limited)")
    
    def _fetch_via_http(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """
        Fetch aircraft data directly via HTTP API.
        
        Args:
            bbox: Tuple of (min_lat, max_lat, min_lon, max_lon)
            
        Returns:
            List of aircraft state dictionaries
        """
        url = "https://opensky-network.org/api/states/all"
        params = {
            'lamin': bbox[0],
            'lamax': bbox[1],
            'lomin': bbox[2],
            'lomax': bbox[3]
        }
        
        logger.debug(f"HTTP request to {url} with params: {params}")
        
        try:
            headers = {}
            token = self._get_oauth_token()
            if token:
                headers['Authorization'] = f'Bearer {token}'
                logger.debug("Using OAuth2 authentication")
            else:
                logger.debug("No authentication - using anonymous access")
            
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            
            logger.debug(f"Response headers: {dict(response.headers)}")
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"HTTP response status: {response.status_code}")
            logger.debug(f"Response keys: {data.keys() if isinstance(data, dict) else 'not a dict'}")
            
            if not isinstance(data, dict) or 'states' not in data:
                logger.warning(f"Unexpected response format: {type(data)}")
                return []
            
            states = data.get('states') # Get the states, may be None
            
            # --- THIS IS THE FIX ---
            # If states is None (null in JSON), treat it as an empty list
            if states is None:
                logger.info("Received null for states, treating as 0 aircraft.")
                states = []
            # --- END OF FIX ---

            logger.info(f"Received {len(states)} states from HTTP API")
            
            # Convert raw state arrays to dictionaries
            aircraft_list = []
            for idx, state in enumerate(states):
                if len(state) < 17:
                    continue
                    
                aircraft = {
                    'icao24': state[0],
                    'callsign': state[1].strip() if state[1] else '',
                    'origin_country': state[2],
                    'time_position': state[3],
                    'last_contact': state[4],
                    'longitude': state[5],
                    'latitude': state[6],
                    'baro_altitude': state[7],
                    'on_ground': state[8],
                    'velocity': state[9],
                    'true_track': state[10],
                    'vertical_rate': state[11],
                    'sensors': state[12],
                    'geo_altitude': state[13],
                    'squawk': state[14],
                    'spi': state[15],
                    'position_source': state[16]
                }
                
                if idx < 3:
                    logger.debug(f"Aircraft {idx}: {aircraft['icao24']}, "
                               f"pos=({aircraft['latitude']}, {aircraft['longitude']}), "
                               f"alt={aircraft['baro_altitude']}")
                
                aircraft_list.append(aircraft)
            
            return aircraft_list
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing HTTP response: {e}", exc_info=True)
            return []
    
    def _get_oauth_token(self) -> Optional[str]:
        """
        Get OAuth2 access token from OpenSky auth server.
        
        Returns:
            Access token string or None if authentication fails
        """
        # Check if we have valid cached token
        current_time = time.time()
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token
        
        # Need to get new token
        if not OPENSKY_USERNAME or not OPENSKY_PASSWORD:
            logger.debug("No OAuth2 credentials configured")
            return None
        
        logger.info("Fetching new OAuth2 access token")
        
        token_url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': OPENSKY_USERNAME,  # This is actually the OAuth2 client_id
            'client_secret': OPENSKY_PASSWORD  # This is actually the OAuth2 client_secret
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            
            # Token expires in 30 minutes, but we'll refresh 5 minutes early
            expires_in = token_data.get('expires_in', 1800)
            self.token_expires_at = current_time + expires_in - 300
            
            logger.info(f"OAuth2 token obtained, expires in {expires_in}s")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get OAuth2 token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error processing OAuth2 token response: {e}")
            return None
    
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
        USE_MOCK_DATA = True

        if USE_MOCK_DATA:
            return _get_mock_aircraft_state()

        self._enforce_rate_limit()
        
        # Debug: Log the bounding box being used
        logger.info(f"Fetching state vectors with bbox: min_lat={bbox[0]:.4f}, max_lat={bbox[1]:.4f}, "
                   f"min_lon={bbox[2]:.4f}, max_lon={bbox[3]:.4f}")
        
        try:
            if self.use_http_fallback:
                # Use HTTP fallback
                logger.info("Using HTTP fallback to fetch aircraft data")
                aircraft_list = self._fetch_via_http(bbox)
                self.last_request_time = time.time()
                return aircraft_list
            
            # Debug: Log API call attempt
            logger.debug(f"Calling OpenSky API get_states() with bbox={bbox}")
            
            # Fetch states from API
            states = self.api.get_states(bbox=bbox)
            self.last_request_time = time.time()
            
            # Debug: Log API response
            logger.info(f"OpenSky API response: states={states}, "
                       f"has states: {states is not None and hasattr(states, 'states')}")
            
            if not states:
                logger.warning("No states returned from OpenSky API (states is None or empty)")
                return []
            
            if not hasattr(states, 'states') or not states.states:
                logger.warning(f"States object has no 'states' attribute or it's empty. "
                              f"Type: {type(states)}, Dir: {dir(states) if states else 'N/A'}")
                return []
            
            # Debug: Log number of states
            logger.info(f"Processing {len(states.states)} aircraft states")
            
            # Convert state vectors to dictionaries
            aircraft_list = []
            for idx, state in enumerate(states.states):
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
                
                # Debug: Log first few aircraft details
                if idx < 3:
                    logger.debug(f"Aircraft {idx}: icao24={aircraft['icao24']}, "
                               f"lat={aircraft['latitude']}, lon={aircraft['longitude']}, "
                               f"alt={aircraft['baro_altitude']}, on_ground={aircraft['on_ground']}")
                
                aircraft_list.append(aircraft)
            
            logger.info(f"Fetched {len(aircraft_list)} aircraft from OpenSky")
            return aircraft_list
            
        except Exception as e:
            logger.error(f"Error fetching state vectors: {e}", exc_info=True)
            # Debug: Log more details about the error
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception args: {e.args}")
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