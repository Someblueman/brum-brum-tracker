"""
Planespotters API client for fetching aircraft data.

This module provides functionality to fetch aircraft type and other details
from the Planespotters API as a fallback when other sources don't provide
the information.
"""

import logging
import time
from typing import Dict, Optional, Any
from backend.api.api_pool import get_global_pool

logger = logging.getLogger(__name__)

# Constants
PLANESPOTTERS_API_BASE = "https://api.planespotters.net/pub"
USER_AGENT = "BrumBrumTracker/1.0"
REQUEST_TIMEOUT = 10

# Cache for aircraft details to avoid repeated API calls
_aircraft_details_cache: Dict[str, Dict[str, Any]] = {}
_cache_timestamps: Dict[str, float] = {}
CACHE_TTL_SECONDS = 86400  # 24 hours


def fetch_aircraft_details(icao24: str) -> Optional[Dict[str, Any]]:
    """
    Fetch aircraft details from Planespotters API.
    
    Args:
        icao24: ICAO24 hex code (e.g., '4ca1d3')
        
    Returns:
        Dictionary with aircraft details including type, manufacturer, model, etc.
        Returns None if no data found or on error.
    """
    # Normalize ICAO24 to uppercase
    icao24_upper = icao24.upper()
    
    # Check cache first
    if icao24_upper in _aircraft_details_cache:
        cache_age = time.time() - _cache_timestamps.get(icao24_upper, 0)
        if cache_age < CACHE_TTL_SECONDS:
            logger.debug(f"Using cached aircraft details for {icao24_upper}")
            return _aircraft_details_cache[icao24_upper]
    
    try:
        # Get connection pool
        pool = get_global_pool()
        
        # Build API URL for aircraft details
        api_url = f"{PLANESPOTTERS_API_BASE}/aircraft/hex/{icao24_upper}"
        
        logger.info(f"Fetching aircraft details for ICAO24: {icao24_upper} from Planespotters API")
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json'
        }
        
        response = pool.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        logger.debug(f"Aircraft details API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract relevant aircraft information
            aircraft_info = {
                'icao24': icao24_upper,
                'registration': data.get('registration'),
                'aircraft_type': data.get('aircraft_type'),
                'aircraft_type_text': data.get('aircraft_type_text'),
                'model': data.get('model'),
                'manufacturer': data.get('manufacturer'),
                'serial_number': data.get('serial_number'),
                'airline_name': data.get('airline_name'),
                'airline_iata': data.get('airline_iata'),
                'airline_icao': data.get('airline_icao'),
                'country': data.get('country'),
                'built': data.get('built'),
                'engines': data.get('engines'),
                'age': data.get('age')
            }
            
            # Cache the result
            _aircraft_details_cache[icao24_upper] = aircraft_info
            _cache_timestamps[icao24_upper] = time.time()
            
            logger.info(f"Successfully fetched aircraft details for {icao24_upper}: "
                       f"{aircraft_info.get('manufacturer')} {aircraft_info.get('model')}")
            
            return aircraft_info
            
        elif response.status_code == 404:
            logger.info(f"No aircraft details found for ICAO24: {icao24_upper}")
            # Cache the negative result to avoid repeated lookups
            _aircraft_details_cache[icao24_upper] = None
            _cache_timestamps[icao24_upper] = time.time()
            return None
            
        else:
            logger.warning(f"Unexpected status code {response.status_code} for ICAO24: {icao24_upper}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching aircraft details for ICAO24 {icao24}: {e}")
        return None


def get_aircraft_type_string(icao24: str) -> Optional[str]:
    """
    Get a human-readable aircraft type string from Planespotters.
    
    This is a convenience function that fetches aircraft details and
    formats them into a readable type string.
    
    Args:
        icao24: ICAO24 hex code
        
    Returns:
        Formatted aircraft type string like "Boeing 737-800" or None
    """
    details = fetch_aircraft_details(icao24)
    
    if not details:
        return None
    
    # Try to build the most informative type string
    parts = []
    
    # Add manufacturer if available
    if details.get('manufacturer'):
        parts.append(details['manufacturer'])
    
    # Add model or aircraft_type_text
    if details.get('model'):
        parts.append(details['model'])
    elif details.get('aircraft_type_text'):
        parts.append(details['aircraft_type_text'])
    elif details.get('aircraft_type'):
        parts.append(details['aircraft_type'])
    
    if parts:
        return ' '.join(parts)
    
    return None


def get_airline_info(icao24: str) -> Optional[Dict[str, str]]:
    """
    Get airline information for an aircraft.
    
    Args:
        icao24: ICAO24 hex code
        
    Returns:
        Dictionary with airline_name, airline_iata, airline_icao or None
    """
    details = fetch_aircraft_details(icao24)
    
    if not details:
        return None
    
    airline_info = {}
    
    if details.get('airline_name'):
        airline_info['name'] = details['airline_name']
    if details.get('airline_iata'):
        airline_info['iata'] = details['airline_iata']
    if details.get('airline_icao'):
        airline_info['icao'] = details['airline_icao']
    
    return airline_info if airline_info else None


def clear_cache():
    """Clear the internal cache."""
    global _aircraft_details_cache, _cache_timestamps
    _aircraft_details_cache.clear()
    _cache_timestamps.clear()
    logger.info("Cleared Planespotters cache")


# Module-level convenience function
def get_aircraft_type_fallback(icao24: str, current_type: Optional[str] = None) -> str:
    """
    Get aircraft type with Planespotters as fallback.
    
    Args:
        icao24: ICAO24 hex code
        current_type: Current aircraft type (if any) from primary source
        
    Returns:
        Aircraft type string, either from current source or Planespotters fallback
    """
    # If we already have a good type, use it
    if current_type and current_type != 'Unknown Aircraft':
        return current_type
    
    # Try to get from Planespotters
    planespotters_type = get_aircraft_type_string(icao24)
    
    if planespotters_type:
        logger.info(f"Using Planespotters type for {icao24}: {planespotters_type}")
        return planespotters_type
    
    # Return the original type or 'Unknown Aircraft'
    return current_type or 'Unknown Aircraft'


if __name__ == "__main__":
    # Test the module
    import sys
    
    if len(sys.argv) > 1:
        test_icao = sys.argv[1]
    else:
        test_icao = "4ca1d3"  # Example ICAO24
    
    print(f"Testing with ICAO24: {test_icao}")
    
    # Test fetching details
    details = fetch_aircraft_details(test_icao)
    if details:
        print(f"Aircraft details: {details}")
        
        # Test type string
        type_string = get_aircraft_type_string(test_icao)
        print(f"Type string: {type_string}")
        
        # Test airline info
        airline = get_airline_info(test_icao)
        print(f"Airline info: {airline}")
    else:
        print("No aircraft details found")