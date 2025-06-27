"""
Aircraft image scraper for fetching photos from planespotters.net
"""
import logging
from typing import Dict, Optional

import requests

from backend.db import get_aircraft_from_cache, save_aircraft_to_cache

logger = logging.getLogger(__name__)

# Constants
PLANESPOTTERS_BASE_URL = "https://www.planespotters.net"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
REQUEST_TIMEOUT = 10


# --- START OF FIX ---
# This function is now simplified to only fetch the image URL.
def scrape_planespotters_image(icao24: str) -> Optional[str]:
    """
    Fetch aircraft image URL from planespotters.net API.
    
    Args:
        icao24: ICAO24 hex code (e.g., '4ca1d3')
        
    Returns:
        The image URL string, or None if not found.
    """
    try:
        # Normalize ICAO24 to uppercase for planespotters
        icao24_upper = icao24.upper()
        
        # Build API URL for photos
        api_url = f"https://api.planespotters.net/pub/photos/hex/{icao24_upper}"
        
        logger.info(f"Fetching aircraft photo for ICAO24: {icao24_upper} from API")
        
        headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json'}
        response = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        logger.debug(f"Photo API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'photos' in data and data['photos']:
                first_photo = data['photos'][0]
                image_url = first_photo.get('thumbnail_large', {}).get('src') or first_photo.get('thumbnail', {}).get('src')
                logger.debug(f"Found image URL: {image_url}")
                return image_url
        
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for ICAO24 {icao24}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching image for ICAO24 {icao24}: {e}")
        return None

# This function is also simplified.
def get_plane_media(icao24: str) -> Dict[str, Optional[str]]:
    """
    Get plane image URL from Planespotters, using cache if available.
    
    Args:
        icao24: ICAO24 hex code
        
    Returns:
        Dictionary with 'image_url' key.
    """
    # Check cache first for the image
    cached_data = get_aircraft_from_cache(icao24)
    if cached_data and cached_data.get('image_url'):
        logger.debug(f"Found cached image for ICAO24: {icao24}")
        return {'image_url': cached_data.get('image_url')}
    
    # Fetch from API if not in cache
    logger.info(f"No cached image for ICAO24: {icao24}, fetching from API...")
    image_url = scrape_planespotters_image(icao24)
    
    # Save to cache if we got an image
    if image_url:
        # We only save the image here, the type is handled elsewhere.
        record = {'icao24': icao24, 'image_url': image_url, 'type': ''}
        save_aircraft_to_cache(record)
        logger.info(f"Cached image for ICAO24: {icao24}")
    
    return {'image_url': image_url}
# --- END OF FIX ---


# For testing
if __name__ == "__main__":
    # Test with a known aircraft
    test_icao = "4ca1d3"  # Example ICAO24
    result = get_plane_media(test_icao)
    print(f"Result for {test_icao}: {result}")