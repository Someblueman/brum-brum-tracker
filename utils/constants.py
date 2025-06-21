"""
Configuration constants loaded from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Home location coordinates
HOME_LAT = float(os.getenv('HOME_LAT', '0.0'))
HOME_LON = float(os.getenv('HOME_LON', '0.0'))

# OpenSky Network credentials (optional)
OPENSKY_USERNAME = os.getenv('OPENSKY_USERNAME', '')
OPENSKY_PASSWORD = os.getenv('OPENSKY_PASSWORD', '')

# Search and visibility parameters
SEARCH_RADIUS_KM = 100  # Search radius in kilometers
MIN_ELEVATION_ANGLE = 20  # Minimum elevation angle in degrees for visibility
POLLING_INTERVAL = 10  # Seconds between API calls (respects rate limit)
UPDATE_INTERVAL = 5  # Seconds between frontend updates

# WebSocket configuration
WEBSOCKET_HOST = '0.0.0.0'
WEBSOCKET_PORT = 8000

# Frontend server configuration
FRONTEND_HOST = '0.0.0.0'
FRONTEND_PORT = 8080

# Cache configuration
CACHE_EXPIRY_DAYS = 30  # Days before cached aircraft images expire

# Logging configuration
LOG_FILE = 'events.log'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')