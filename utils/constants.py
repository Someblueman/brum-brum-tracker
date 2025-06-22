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

# OpenSky Network OAuth2 credentials (optional)
# For accounts created after March 2025, these should be OAuth2 client credentials
OPENSKY_USERNAME = os.getenv('OPENSKY_USERNAME', '')  # OAuth2 client_id
OPENSKY_PASSWORD = os.getenv('OPENSKY_PASSWORD', '')  # OAuth2 client_secret

# Search and visibility parameters
SEARCH_RADIUS_KM = 50  # Search radius in kilometers (optimized for <25 sq deg, 1 credit)
MIN_ELEVATION_ANGLE = 20  # Minimum elevation angle in degrees for visibility
POLLING_INTERVAL = 5  # Seconds between API calls (faster updates with lower credit usage)
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