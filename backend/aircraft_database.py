"""
Aircraft database service using multiple data sources.
"""
import logging
import requests
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch_aircraft_data_from_hexdb(icao24: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Fetch aircraft data from hexdb.io API.
    
    Args:
        icao24: ICAO24 hex code
        
    Returns:
        Tuple of (registration, aircraft_type, operator)
    """
    try:
        # Normalize to lowercase (hexdb uses lowercase)
        icao24 = icao24.lower()
        
        # hexdb.io API endpoint
        api_url = f"https://hexdb.io/api/v1/aircraft/{icao24}"
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
        }
        
        response = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 404:
            logger.debug(f"No data found in hexdb for ICAO24: {icao24}")
            return None, None, None
            
        response.raise_for_status()
        
        data = response.json()
        
        # Extract data
        registration = data.get('Registration')
        aircraft_type = data.get('Type')
        operator = data.get('RegisteredOwners')
        
        logger.info(f"Found hexdb data for {icao24}: {registration} - {aircraft_type}")
        
        return registration, aircraft_type, operator
        
    except Exception as e:
        logger.error(f"Error fetching from hexdb for {icao24}: {e}")
        return None, None, None


def fetch_aircraft_data_from_adsb_exchange(icao24: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Fetch aircraft data from ADS-B Exchange database.
    Note: This requires the aircraft-database.csv file to be downloaded.
    
    Args:
        icao24: ICAO24 hex code
        
    Returns:
        Tuple of (registration, aircraft_type, operator)
    """
    try:
        # For now, return None as this would require downloading and parsing a large CSV
        # This is a placeholder for future implementation
        return None, None, None
    except Exception as e:
        logger.error(f"Error fetching from ADS-B Exchange for {icao24}: {e}")
        return None, None, None


def get_aircraft_metadata(icao24: str) -> Dict[str, Optional[str]]:
    """
    Get aircraft metadata from various sources.
    
    Args:
        icao24: ICAO24 hex code
        
    Returns:
        Dictionary with registration, type, and operator
    """
    # Try hexdb.io first
    registration, aircraft_type, operator = fetch_aircraft_data_from_hexdb(icao24)
    
    # If no data, try other sources (placeholder for now)
    if not registration and not aircraft_type:
        # Could try other APIs here
        pass
    
    return {
        'registration': registration,
        'type': aircraft_type,
        'operator': operator
    }