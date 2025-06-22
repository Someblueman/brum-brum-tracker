"""
Aircraft image scraper for fetching photos from planespotters.net
"""
import logging
import re
import time
from typing import Dict, Optional, Tuple
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from backend.db import get_aircraft_from_cache, save_aircraft_to_cache

logger = logging.getLogger(__name__)

# Constants
PLANESPOTTERS_BASE_URL = "https://www.planespotters.net"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
REQUEST_TIMEOUT = 10
RATE_LIMIT_DELAY = 1  # Seconds between requests to be respectful


def scrape_planespotters_image(icao24: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch aircraft image from planespotters.net API and type from hexdb.io.
    
    Args:
        icao24: ICAO24 hex code (e.g., '4ca1d3')
        
    Returns:
        Tuple of (image_url, aircraft_type) or (None, None) if not found
    """
    from backend.aircraft_database import get_aircraft_metadata
    
    try:
        # Normalize ICAO24 to uppercase for planespotters
        icao24_upper = icao24.upper()
        
        # Get aircraft metadata (type, registration, etc.)
        metadata = get_aircraft_metadata(icao24)
        aircraft_type = metadata.get('type')
        
        # Build API URL for photos
        api_url = f"https://api.planespotters.net/pub/photos/hex/{icao24_upper}"
        
        logger.info(f"Fetching aircraft photo for ICAO24: {icao24_upper} from API")
        
        # Make request with headers
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
        }
        
        response = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        logger.debug(f"Photo API response status: {response.status_code}")
        
        image_url = None
        
        if response.status_code == 200:
            # Parse JSON response
            data = response.json()
            
            # Check if we have photos in the response
            if 'photos' in data and data['photos']:
                # Get the first photo
                first_photo = data['photos'][0]
                
                # Prefer large thumbnail
                if 'thumbnail_large' in first_photo:
                    image_url = first_photo['thumbnail_large']['src']
                elif 'thumbnail' in first_photo:
                    image_url = first_photo['thumbnail']['src']
                
                logger.debug(f"Found image URL: {image_url}")
        
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
        
        return image_url, aircraft_type
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching data for ICAO24: {icao24}")
        return None, None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for ICAO24 {icao24}: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error fetching ICAO24 {icao24}: {e}")
        return None, None





def get_plane_media(icao24: str) -> Dict[str, Optional[str]]:
    """
    Get plane media information from Planespotters API, using cache if available.
    
    Args:
        icao24: ICAO24 hex code
        
    Returns:
        Dictionary with 'image_url' and 'type' keys
    """
    # Check cache first
    cached_data = get_aircraft_from_cache(icao24)
    if cached_data and (cached_data.get('image_url') or cached_data.get('type')):
        logger.debug(f"Found cached data for ICAO24: {icao24}")
        return {
            'image_url': cached_data.get('image_url'),
            'type': cached_data.get('type')
        }
    
    # Fetch from API if not in cache
    logger.info(f"No cache found for ICAO24: {icao24}, fetching from API...")
    image_url, aircraft_type = scrape_planespotters_image(icao24)
    
    # Save to cache if we got data
    if image_url or aircraft_type:
        record = {
            'icao24': icao24,
            'image_url': image_url or '',
            'type': aircraft_type or ''
        }
        save_aircraft_to_cache(record)
        logger.info(f"Cached data for ICAO24: {icao24}")
    
    return {
        'image_url': image_url,
        'type': aircraft_type
    }




# For testing
if __name__ == "__main__":
    # Test with a known aircraft
    test_icao = "4ca1d3"  # Example ICAO24
    result = get_plane_media(test_icao)
    print(f"Result for {test_icao}: {result}")