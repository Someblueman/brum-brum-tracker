"""
Aircraft data service with multiple data sources and fallbacks.
"""
import logging
import random
from typing import Dict, Optional

from backend.db import save_aircraft_to_cache

logger = logging.getLogger(__name__)

# Fallback aircraft types based on common patterns
AIRCRAFT_TYPE_PATTERNS = {
    # Airlines often have patterns in their fleet
    'Boeing 737': ['737-800', '737-900', '737 MAX 8'],
    'Airbus A320': ['A320-200', 'A320neo', 'A321'],
    'Boeing 777': ['777-200ER', '777-300ER'],
    'Airbus A350': ['A350-900', 'A350-1000'],
    'Embraer': ['E175', 'E190', 'E195'],
    'Bombardier': ['CRJ900', 'CRJ700', 'Q400'],
}

# Placeholder images for different aircraft types
PLACEHOLDER_IMAGES = {
    'narrow_body': [
        'https://images.unsplash.com/photo-1556388158-158ea5ccacbd?w=800',  # 737-like
        'https://images.unsplash.com/photo-1569629743817-70d8db6c323b?w=800',  # A320-like
    ],
    'wide_body': [
        'https://images.unsplash.com/photo-1540339832862-474599807836?w=800',  # 777-like
        'https://images.unsplash.com/photo-1569165003085-e8a1b2f75346?w=800',  # A350-like
    ],
    'regional': [
        'https://images.unsplash.com/photo-1474302770737-173ee21bab63?w=800',  # Regional jet
    ],
    'general': [
        'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=800',  # Generic aircraft
    ]
}


def get_aircraft_data(icao24: str, use_placeholders: bool = True) -> Dict[str, Optional[str]]:
    """
    Get aircraft data from cache, API, or generate placeholder data.
    
    Args:
        icao24: ICAO24 hex code
        use_placeholders: Whether to use placeholder data if API fails
        
    Returns:
        Dictionary with 'image_url' and 'type' keys
    """
    # Import here to avoid circular imports
    from backend.image_scraper import get_plane_media
    
    # Try to get real data from API (which checks cache first)
    try:
        api_data = get_plane_media(icao24)
        if api_data.get('image_url') or api_data.get('type'):
            return api_data
    except Exception as e:
        logger.error(f"Error fetching from API for {icao24}: {e}")
    
    # If no API data and placeholders disabled, return empty
    if not use_placeholders:
        return {'image_url': '', 'type': ''}
    
    # Generate placeholder data based on ICAO24
    # Use ICAO24 as seed for consistent results
    random.seed(icao24)
    
    # Select aircraft type category
    categories = list(AIRCRAFT_TYPE_PATTERNS.keys())
    selected_category = random.choice(categories)
    
    # Select specific type
    aircraft_type = random.choice(AIRCRAFT_TYPE_PATTERNS[selected_category])
    
    # Select appropriate image category
    if 'Boeing 737' in selected_category or 'Airbus A320' in selected_category:
        image_category = 'narrow_body'
    elif 'Boeing 777' in selected_category or 'Airbus A350' in selected_category:
        image_category = 'wide_body'
    elif 'Embraer' in selected_category or 'Bombardier' in selected_category:
        image_category = 'regional'
    else:
        image_category = 'general'
    
    # Select image
    image_url = random.choice(PLACEHOLDER_IMAGES[image_category])
    
    # Reset random seed
    random.seed()
    
    # Cache the placeholder data
    record = {
        'icao24': icao24,
        'image_url': image_url,
        'type': f"{aircraft_type} (placeholder)"  # Mark as placeholder
    }
    save_aircraft_to_cache(record)
    logger.info(f"Generated placeholder data for ICAO24: {icao24} - Type: {aircraft_type}")
    
    return {
        'image_url': image_url,
        'type': aircraft_type
    }
