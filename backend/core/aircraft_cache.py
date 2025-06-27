"""
Aircraft data caching module for improved performance.
Implements multi-level caching with TTL and LRU eviction.
"""

import time
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
from threading import Lock
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a single cache entry with TTL."""
    
    def __init__(self, data: Any, ttl: int):
        self.data = data
        self.expires_at = time.time() + ttl
        self.hits = 0
        self.created_at = time.time()
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() > self.expires_at
    
    def access(self) -> Any:
        """Access the cached data and increment hit count."""
        self.hits += 1
        return self.data


class LRUCache:
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = Lock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                self.stats['expirations'] += 1
                self.stats['misses'] += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.stats['hits'] += 1
            
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        with self.lock:
            # Remove if exists to update position
            if key in self.cache:
                del self.cache[key]
            
            # Add new entry
            self.cache[key] = CacheEntry(value, ttl or self.default_ttl)
            
            # Evict oldest if over capacity
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.stats['evictions'] += 1
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                **self.stats,
                'size': len(self.cache),
                'hit_rate': round(hit_rate, 3),
                'total_requests': total_requests
            }


class AircraftCache:
    """Multi-level aircraft data cache with different TTLs for different data types."""
    
    def __init__(self):
        """Initialize multi-level cache system."""
        # Different caches for different data types with appropriate TTLs
        self.position_cache = LRUCache(max_size=500, default_ttl=30)  # 30 seconds for positions
        self.details_cache = LRUCache(max_size=200, default_ttl=3600)  # 1 hour for details
        self.route_cache = LRUCache(max_size=100, default_ttl=1800)  # 30 minutes for routes
        self.image_cache = LRUCache(max_size=300, default_ttl=86400)  # 24 hours for images
        self.api_cache = LRUCache(max_size=50, default_ttl=60)  # 1 minute for API responses
        
        # Batch request cache for aggregated results
        self.batch_cache = LRUCache(max_size=20, default_ttl=15)  # 15 seconds for batch results
        
        logger.info("Aircraft cache initialized")
    
    def _generate_position_key(self, lat: float, lon: float, radius: float) -> str:
        """Generate cache key for position-based queries."""
        # Round to reduce cache misses from minor variations
        lat_rounded = round(lat, 3)
        lon_rounded = round(lon, 3)
        radius_rounded = round(radius, 0)
        return f"pos_{lat_rounded}_{lon_rounded}_{radius_rounded}"
    
    def _generate_batch_key(self, aircraft_list: List[str]) -> str:
        """Generate cache key for batch requests."""
        # Sort to ensure consistent keys
        sorted_list = sorted(aircraft_list)
        key_string = "_".join(sorted_list)
        # Use hash for long lists
        if len(key_string) > 100:
            key_string = hashlib.md5(key_string.encode()).hexdigest()
        return f"batch_{key_string}"
    
    def get_aircraft_positions(self, lat: float, lon: float, radius: float) -> Optional[List[Dict[str, Any]]]:
        """Get cached aircraft positions for a given area."""
        key = self._generate_position_key(lat, lon, radius)
        return self.position_cache.get(key)
    
    def set_aircraft_positions(self, lat: float, lon: float, radius: float, 
                             aircraft: List[Dict[str, Any]]) -> None:
        """Cache aircraft positions for a given area."""
        key = self._generate_position_key(lat, lon, radius)
        self.position_cache.set(key, aircraft)
    
    def get_aircraft_details(self, icao24: str) -> Optional[Dict[str, Any]]:
        """Get cached aircraft details."""
        return self.details_cache.get(f"details_{icao24}")
    
    def set_aircraft_details(self, icao24: str, details: Dict[str, Any]) -> None:
        """Cache aircraft details."""
        self.details_cache.set(f"details_{icao24}", details)
    
    def get_flight_route(self, callsign: str) -> Optional[Dict[str, Any]]:
        """Get cached flight route."""
        return self.route_cache.get(f"route_{callsign}")
    
    def set_flight_route(self, callsign: str, route: Dict[str, Any]) -> None:
        """Cache flight route."""
        self.route_cache.set(f"route_{callsign}", route)
    
    def get_aircraft_image(self, icao24: str) -> Optional[str]:
        """Get cached aircraft image URL."""
        return self.image_cache.get(f"image_{icao24}")
    
    def set_aircraft_image(self, icao24: str, image_url: str) -> None:
        """Cache aircraft image URL."""
        self.image_cache.set(f"image_{icao24}", image_url)
    
    def get_api_response(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached API response."""
        param_str = json.dumps(params, sort_keys=True)
        key = f"api_{endpoint}_{hashlib.md5(param_str.encode()).hexdigest()}"
        return self.api_cache.get(key)
    
    def set_api_response(self, endpoint: str, params: Dict[str, Any], response: Any) -> None:
        """Cache API response."""
        param_str = json.dumps(params, sort_keys=True)
        key = f"api_{endpoint}_{hashlib.md5(param_str.encode()).hexdigest()}"
        self.api_cache.set(key, response)
    
    def get_batch_details(self, aircraft_list: List[str]) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get cached batch aircraft details."""
        key = self._generate_batch_key(aircraft_list)
        return self.batch_cache.get(key)
    
    def set_batch_details(self, aircraft_list: List[str], 
                         details: Dict[str, Dict[str, Any]]) -> None:
        """Cache batch aircraft details."""
        key = self._generate_batch_key(aircraft_list)
        self.batch_cache.set(key, details)
    
    def invalidate_position_cache(self) -> None:
        """Invalidate all position caches (useful for testing)."""
        self.position_cache.clear()
        logger.info("Position cache cleared")
    
    def invalidate_aircraft(self, icao24: str) -> None:
        """Invalidate all caches for a specific aircraft."""
        # Clear from all caches
        keys_to_clear = [
            f"details_{icao24}",
            f"image_{icao24}"
        ]
        
        # Clear from individual caches
        for key in keys_to_clear:
            if key.startswith("details_"):
                with self.details_cache.lock:
                    if key in self.details_cache.cache:
                        del self.details_cache.cache[key]
            elif key.startswith("image_"):
                with self.image_cache.lock:
                    if key in self.image_cache.cache:
                        del self.image_cache.cache[key]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches."""
        return {
            'position_cache': self.position_cache.get_stats(),
            'details_cache': self.details_cache.get_stats(),
            'route_cache': self.route_cache.get_stats(),
            'image_cache': self.image_cache.get_stats(),
            'api_cache': self.api_cache.get_stats(),
            'batch_cache': self.batch_cache.get_stats()
        }
    
    def cleanup_expired(self) -> Dict[str, int]:
        """Clean up expired entries from all caches."""
        cleaned = {}
        
        for cache_name, cache in [
            ('position', self.position_cache),
            ('details', self.details_cache),
            ('route', self.route_cache),
            ('image', self.image_cache),
            ('api', self.api_cache),
            ('batch', self.batch_cache)
        ]:
            with cache.lock:
                expired_keys = []
                for key, entry in cache.cache.items():
                    if entry.is_expired():
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del cache.cache[key]
                
                cleaned[cache_name] = len(expired_keys)
        
        return cleaned


# Global cache instance
aircraft_cache = AircraftCache()


# Decorator for caching function results
def cache_result(cache_type: str, ttl: Optional[int] = None):
    """
    Decorator to cache function results.
    
    Args:
        cache_type: Type of cache to use ('position', 'details', 'route', 'image', 'api')
        ttl: Optional TTL override
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = "_".join(key_parts)
            
            # Get appropriate cache
            cache_map = {
                'position': aircraft_cache.position_cache,
                'details': aircraft_cache.details_cache,
                'route': aircraft_cache.route_cache,
                'image': aircraft_cache.image_cache,
                'api': aircraft_cache.api_cache
            }
            
            cache = cache_map.get(cache_type)
            if not cache:
                return func(*args, **kwargs)
            
            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator