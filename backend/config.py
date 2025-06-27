"""
Centralized configuration module for the backend.
All configuration values should be accessed through this module.
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv


# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class Config:
    """Configuration class with all backend settings."""
    
    # Environment
    ENV = os.getenv('ENV', 'development')
    DEBUG = ENV == 'development'
    
    # Home location
    HOME_LAT = float(os.getenv('HOME_LAT', '0.0'))
    HOME_LON = float(os.getenv('HOME_LON', '0.0'))
    
    # OpenSky Network API
    OPENSKY_USERNAME = os.getenv('OPENSKY_USERNAME', '')
    OPENSKY_PASSWORD = os.getenv('OPENSKY_PASSWORD', '')
    OPENSKY_API_URL = 'https://opensky-network.org/api'
    
    # Search parameters
    SEARCH_RADIUS_KM = int(os.getenv('SEARCH_RADIUS_KM', '50'))
    MIN_ELEVATION_ANGLE = int(os.getenv('MIN_ELEVATION_ANGLE', '20'))
    MAX_DISTANCE_KM = int(os.getenv('MAX_DISTANCE_KM', '30'))
    
    # Polling intervals
    POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', '5'))
    UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '5'))
    
    # WebSocket configuration
    WEBSOCKET_HOST = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
    WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT', '8000'))
    WEBSOCKET_SSL_PORT = int(os.getenv('WEBSOCKET_SSL_PORT', '8001'))
    
    # Frontend server configuration
    FRONTEND_HOST = os.getenv('FRONTEND_HOST', '0.0.0.0')
    FRONTEND_PORT = int(os.getenv('FRONTEND_PORT', '8080'))
    FRONTEND_HTTPS_PORT = int(os.getenv('FRONTEND_HTTPS_PORT', '8443'))
    
    # Security settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8080,http://localhost:8443').split(',')
    MAX_CONNECTIONS_PER_IP = int(os.getenv('MAX_CONNECTIONS_PER_IP', '3'))
    CONNECTION_RATE_LIMIT = int(os.getenv('CONNECTION_RATE_LIMIT', '5'))
    CONNECTION_RATE_WINDOW = int(os.getenv('CONNECTION_RATE_WINDOW', '60'))
    MESSAGE_RATE_LIMIT = int(os.getenv('MESSAGE_RATE_LIMIT', '100'))
    MESSAGE_RATE_WINDOW = int(os.getenv('MESSAGE_RATE_WINDOW', '60'))
    
    # Database configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'backend/aircraft_cache.db')
    CACHE_EXPIRY_DAYS = int(os.getenv('CACHE_EXPIRY_DAYS', '30'))
    
    # Logging configuration
    LOG_FILE = os.getenv('LOG_FILE', 'events.log')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # SSL/TLS configuration
    SSL_CERT_FILE = os.getenv('SSL_CERT_FILE', 'cert.pem')
    SSL_KEY_FILE = os.getenv('SSL_KEY_FILE', 'key.pem')
    
    # API rate limiting
    API_REQUESTS_PER_MINUTE = int(os.getenv('API_REQUESTS_PER_MINUTE', '60'))
    
    # Performance tuning
    MAX_VISIBLE_AIRCRAFT = int(os.getenv('MAX_VISIBLE_AIRCRAFT', '10'))
    CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', '300'))  # 5 minutes
    
    # Feature flags
    ENABLE_LOGBOOK = os.getenv('ENABLE_LOGBOOK', 'true').lower() == 'true'
    ENABLE_AIRCRAFT_IMAGES = os.getenv('ENABLE_AIRCRAFT_IMAGES', 'true').lower() == 'true'
    ENABLE_FLIGHT_ROUTES = os.getenv('ENABLE_FLIGHT_ROUTES', 'false').lower() == 'true'
    
    @classmethod
    def validate(cls) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of error messages, empty if valid
        """
        errors = []
        
        # Check required settings
        if cls.HOME_LAT == 0.0 and cls.HOME_LON == 0.0:
            errors.append("HOME_LAT and HOME_LON must be set to valid coordinates")
        
        if not -90 <= cls.HOME_LAT <= 90:
            errors.append("HOME_LAT must be between -90 and 90")
        
        if not -180 <= cls.HOME_LON <= 180:
            errors.append("HOME_LON must be between -180 and 180")
        
        if cls.SEARCH_RADIUS_KM <= 0:
            errors.append("SEARCH_RADIUS_KM must be positive")
        
        if cls.MIN_ELEVATION_ANGLE < 0 or cls.MIN_ELEVATION_ANGLE > 90:
            errors.append("MIN_ELEVATION_ANGLE must be between 0 and 90")
        
        # Check file paths
        if cls.ENV == 'production':
            if not os.path.exists(cls.SSL_CERT_FILE):
                errors.append(f"SSL certificate file not found: {cls.SSL_CERT_FILE}")
            
            if not os.path.exists(cls.SSL_KEY_FILE):
                errors.append(f"SSL key file not found: {cls.SSL_KEY_FILE}")
        
        # Check rate limits
        if cls.CONNECTION_RATE_LIMIT <= 0:
            errors.append("CONNECTION_RATE_LIMIT must be positive")
        
        if cls.MESSAGE_RATE_LIMIT <= 0:
            errors.append("MESSAGE_RATE_LIMIT must be positive")
        
        return errors
    
    @classmethod
    def get_safe_cors_origins(cls) -> List[str]:
        """
        Get CORS origins with validation.
        
        Returns:
            List of validated CORS origins
        """
        origins = []
        for origin in cls.CORS_ORIGINS:
            origin = origin.strip()
            if origin and (origin.startswith('http://') or origin.startswith('https://')):
                origins.append(origin)
        
        # Add default origins if none specified
        if not origins:
            if cls.ENV == 'development':
                origins = [
                    f'http://localhost:{cls.FRONTEND_PORT}',
                    f'https://localhost:{cls.FRONTEND_HTTPS_PORT}'
                ]
            else:
                # In production, should specify actual domains
                origins = []
        
        return origins
    
    @classmethod
    def to_dict(cls) -> dict:
        """
        Export configuration as dictionary (excluding sensitive data).
        
        Returns:
            Configuration dictionary
        """
        return {
            'ENV': cls.ENV,
            'DEBUG': cls.DEBUG,
            'HOME_LAT': cls.HOME_LAT,
            'HOME_LON': cls.HOME_LON,
            'SEARCH_RADIUS_KM': cls.SEARCH_RADIUS_KM,
            'MIN_ELEVATION_ANGLE': cls.MIN_ELEVATION_ANGLE,
            'POLLING_INTERVAL': cls.POLLING_INTERVAL,
            'WEBSOCKET_HOST': cls.WEBSOCKET_HOST,
            'WEBSOCKET_PORT': cls.WEBSOCKET_PORT,
            'CORS_ORIGINS': cls.CORS_ORIGINS,
            'LOG_LEVEL': cls.LOG_LEVEL,
            'ENABLE_LOGBOOK': cls.ENABLE_LOGBOOK,
            'ENABLE_AIRCRAFT_IMAGES': cls.ENABLE_AIRCRAFT_IMAGES,
            'ENABLE_FLIGHT_ROUTES': cls.ENABLE_FLIGHT_ROUTES,
        }


# Create singleton instance
config = Config()