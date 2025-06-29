"""
CORS (Cross-Origin Resource Sharing) handler for WebSocket servers.
Provides proper CORS configuration instead of wildcard '*'.
"""

import logging
from typing import List, Optional, Callable
from urllib.parse import urlparse

from backend.config import config

logger = logging.getLogger(__name__)


class CORSHandler:
    """Handles CORS validation and headers for WebSocket connections."""
    
    def __init__(self, allowed_origins: Optional[List[str]] = None):
        """
        Initialize CORS handler.
        
        Args:
            allowed_origins: List of allowed origins. If None, uses config.
        """
        self.allowed_origins = allowed_origins or config.get_safe_cors_origins()
        logger.info(f"CORS Handler initialized with origins: {self.allowed_origins}")
    
    def is_origin_allowed(self, origin: str) -> bool:
        """
        Check if an origin is allowed.
        
        Args:
            origin: The origin to check
            
        Returns:
            True if origin is allowed, False otherwise
        """
        if not origin:
            return False
        
        # In development, allow localhost with any port
        if config.ENV == 'development':
            try:
                parsed = urlparse(origin)
                if parsed.hostname in ['localhost', '127.0.0.1', '::1']:
                    return True
            except Exception:
                pass
        
        # Check against allowed origins
        return origin in self.allowed_origins
    
    def get_cors_headers(self, origin: str) -> dict:
        """
        Get CORS headers for a given origin.
        
        Args:
            origin: The request origin
            
        Returns:
            Dictionary of CORS headers
        """
        headers = {}
        
        if self.is_origin_allowed(origin):
            headers['Access-Control-Allow-Origin'] = origin
            headers['Access-Control-Allow-Credentials'] = 'true'
        else:
            # Don't include CORS headers for disallowed origins
            logger.warning(f"Rejected CORS request from origin: {origin}")
        
        # Always include these headers
        headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        headers['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return headers
    
    def validate_websocket_origin(self, headers: dict) -> bool:
        """
        Validate WebSocket connection origin.
        
        Args:
            headers: Request headers dictionary
            
        Returns:
            True if origin is valid, False otherwise
        """
        origin = headers.get('Origin') or headers.get('origin')
        
        if not origin:
            # No origin header - could be a non-browser client
            logger.warning("WebSocket connection without Origin header")
            # In production, you might want to reject these
            return config.ENV == 'development'
        
        is_allowed = self.is_origin_allowed(origin)
        
        if not is_allowed:
            logger.warning(f"Rejected WebSocket connection from origin: {origin}")
        
        return is_allowed
    
    def add_origin(self, origin: str) -> bool:
        """
        Dynamically add an allowed origin.
        
        Args:
            origin: Origin to add
            
        Returns:
            True if added, False if invalid
        """
        try:
            # Validate origin format
            parsed = urlparse(origin)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid origin format")
            
            if origin not in self.allowed_origins:
                self.allowed_origins.append(origin)
                logger.info(f"Added allowed origin: {origin}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add origin {origin}: {e}")
        
        return False
    
    def remove_origin(self, origin: str) -> bool:
        """
        Remove an allowed origin.
        
        Args:
            origin: Origin to remove
            
        Returns:
            True if removed, False if not found
        """
        if origin in self.allowed_origins:
            self.allowed_origins.remove(origin)
            logger.info(f"Removed allowed origin: {origin}")
            return True
        return False
    
    def get_allowed_origins(self) -> List[str]:
        """Get list of allowed origins."""
        return self.allowed_origins.copy()


def create_cors_middleware(cors_handler: CORSHandler) -> Callable:
    """
    Create CORS middleware for HTTP servers.
    
    Args:
        cors_handler: CORSHandler instance
        
    Returns:
        Middleware function
    """
    def cors_middleware(handler):
        async def middleware_handler(request):
            origin = request.headers.get('Origin')
            
            # Handle preflight requests
            if request.method == 'OPTIONS':
                headers = cors_handler.get_cors_headers(origin)
                return web.Response(status=200, headers=headers)
            
            # Process request
            response = await handler(request)
            
            # Add CORS headers to response
            if origin:
                cors_headers = cors_handler.get_cors_headers(origin)
                response.headers.update(cors_headers)
            
            return response
        
        return middleware_handler
    
    return cors_middleware


# Create global CORS handler instance
cors_handler = CORSHandler()