"""
Connection pooling for external API calls.

This module provides connection pooling and session management for HTTP requests
to external APIs like OpenSky Network, reducing connection overhead and improving
performance.
"""

import time
import logging
import threading
from typing import Dict, Optional, Any, Tuple
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class APIConnectionPool:
    """
    Manages connection pools for external API calls with automatic retry,
    connection reuse, and rate limiting.
    """
    
    def __init__(self, 
                 pool_connections: int = 10,
                 pool_maxsize: int = 20,
                 max_retries: int = 3,
                 backoff_factor: float = 0.3,
                 timeout: Tuple[float, float] = (5.0, 30.0)):
        """
        Initialize the API connection pool.
        
        Args:
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections to save in the pool
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for retries
            timeout: Tuple of (connect_timeout, read_timeout) in seconds
        """
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        
        # Thread-safe session management
        self._sessions: Dict[str, requests.Session] = {}
        self._lock = threading.Lock()
        
        # Rate limiting tracking
        self._last_request_times: Dict[str, float] = {}
        self._rate_limits: Dict[str, float] = {}  # hostname -> min seconds between requests
        
        logger.info(f"Initialized API connection pool with {pool_connections} connections, "
                   f"max size {pool_maxsize}")
    
    def set_rate_limit(self, hostname: str, min_interval: float) -> None:
        """
        Set rate limit for a specific hostname.
        
        Args:
            hostname: The hostname to rate limit
            min_interval: Minimum seconds between requests
        """
        with self._lock:
            self._rate_limits[hostname] = min_interval
            logger.debug(f"Set rate limit for {hostname}: {min_interval}s")
    
    def _create_session(self, base_url: str) -> requests.Session:
        """
        Create a new session with connection pooling and retry logic.
        
        Args:
            base_url: Base URL for the API
            
        Returns:
            Configured requests Session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
            backoff_factor=self.backoff_factor
        )
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
            max_retries=retry_strategy
        )
        
        # Mount adapter for both HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': 'BrumBrumTracker/1.0',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
        
        logger.debug(f"Created new session for {base_url}")
        return session
    
    def get_session(self, url: str) -> requests.Session:
        """
        Get or create a session for the given URL.
        
        Args:
            url: The URL to get a session for
            
        Returns:
            Configured requests Session
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        with self._lock:
            if base_url not in self._sessions:
                self._sessions[base_url] = self._create_session(base_url)
            
            return self._sessions[base_url]
    
    def _enforce_rate_limit(self, hostname: str) -> None:
        """
        Enforce rate limiting for a hostname.
        
        Args:
            hostname: The hostname to check rate limit for
        """
        if hostname not in self._rate_limits:
            return
        
        with self._lock:
            min_interval = self._rate_limits[hostname]
            last_request = self._last_request_times.get(hostname, 0)
            
            current_time = time.time()
            time_since_last = current_time - last_request
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                logger.debug(f"Rate limiting {hostname}: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
            
            self._last_request_times[hostname] = time.time()
    
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make an HTTP request using the connection pool.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response object
        """
        # Apply default timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        # Get hostname for rate limiting
        parsed = urlparse(url)
        hostname = parsed.netloc
        
        # Enforce rate limit
        self._enforce_rate_limit(hostname)
        
        # Get or create session
        session = self.get_session(url)
        
        # Make request
        logger.debug(f"{method} {url}")
        response = session.request(method, url, **kwargs)
        
        # Log response
        logger.debug(f"Response: {response.status_code} in {response.elapsed.total_seconds():.2f}s")
        
        return response
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request."""
        return self.request('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Make a POST request."""
        return self.request('POST', url, **kwargs)
    
    def close(self) -> None:
        """Close all sessions and clean up resources."""
        with self._lock:
            for session in self._sessions.values():
                session.close()
            self._sessions.clear()
            logger.info("Closed all API connection pools")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global connection pool instance
_global_pool: Optional[APIConnectionPool] = None
_pool_lock = threading.Lock()


def get_global_pool() -> APIConnectionPool:
    """
    Get the global connection pool instance.
    
    Returns:
        Global APIConnectionPool instance
    """
    global _global_pool
    
    if _global_pool is None:
        with _pool_lock:
            if _global_pool is None:
                _global_pool = APIConnectionPool()
                # Set rate limits for known APIs
                _global_pool.set_rate_limit('opensky-network.org', 5.0)  # 5 seconds between requests
                _global_pool.set_rate_limit('auth.opensky-network.org', 1.0)  # 1 second for auth
    
    return _global_pool


def close_global_pool() -> None:
    """Close the global connection pool."""
    global _global_pool
    
    if _global_pool is not None:
        with _pool_lock:
            if _global_pool is not None:
                _global_pool.close()
                _global_pool = None
                logger.info("Closed global API connection pool")