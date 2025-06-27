"""
Optimized database operations with query improvements and caching.
Provides batch operations, prepared statements, and query optimization.
"""

import sqlite3
import json
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
from backend.db_pool import get_pooled_database, PooledAircraftDatabase

logger = logging.getLogger(__name__)


class OptimizedAircraftDatabase:
    """Optimized database operations with caching and batch processing."""
    
    def __init__(self):
        """Initialize with pooled database connection."""
        self.db = get_pooled_database()
        self._prepare_optimizations()
        
        # Cache settings
        self.cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, float] = {}
    
    def _prepare_optimizations(self) -> None:
        """Prepare database optimizations and compiled statements."""
        with self.db.pool.get_connection() as conn:
            # Enable query optimizer
            conn.execute("PRAGMA optimize")
            
            # Analyze tables for better query planning
            conn.execute("ANALYZE aircraft")
            conn.execute("ANALYZE logbook")
    
    @lru_cache(maxsize=1000)
    def get_aircraft_from_cache_optimized(self, icao24: str) -> Optional[Dict[str, Any]]:
        """
        Get aircraft with LRU caching.
        
        Args:
            icao24: Aircraft ICAO24 identifier
            
        Returns:
            Cached aircraft data or None
        """
        # Check if cache is still valid
        cache_key = f"aircraft_{icao24}"
        if cache_key in self._cache_timestamps:
            if time.time() - self._cache_timestamps[cache_key] > self.cache_ttl:
                # Invalidate cache
                self.get_aircraft_from_cache_optimized.cache_clear()
                del self._cache_timestamps[cache_key]
        
        result = self.db.get_aircraft_from_cache(icao24)
        if result:
            self._cache_timestamps[cache_key] = time.time()
        return result
    
    def batch_get_aircraft(self, icao24_list: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Batch retrieve multiple aircraft in a single query.
        
        Args:
            icao24_list: List of ICAO24 identifiers
            
        Returns:
            Dictionary mapping ICAO24 to aircraft data
        """
        if not icao24_list:
            return {}
        
        # First check cache
        results = {}
        uncached = []
        
        for icao24 in icao24_list:
            cached = self.get_aircraft_from_cache_optimized(icao24)
            if cached:
                results[icao24] = cached
            else:
                uncached.append(icao24.lower())
        
        # Batch query for uncached items
        if uncached:
            with self.db.pool.get_connection() as conn:
                placeholders = ','.join(['?' for _ in uncached])
                query = f"""
                    SELECT icao24, image_url, type, last_updated
                    FROM aircraft 
                    WHERE icao24 IN ({placeholders})
                """
                cursor = conn.cursor()
                cursor.execute(query, uncached)
                
                for row in cursor.fetchall():
                    aircraft_data = dict(row)
                    icao24 = aircraft_data['icao24']
                    results[icao24] = aircraft_data
                    # Update cache
                    self.get_aircraft_from_cache_optimized.cache_clear()
                    self.get_aircraft_from_cache_optimized(icao24)
        
        return results
    
    def batch_save_aircraft(self, aircraft_list: List[Dict[str, Any]]) -> int:
        """
        Batch save multiple aircraft in a single transaction.
        
        Args:
            aircraft_list: List of aircraft records
            
        Returns:
            Number of records saved
        """
        if not aircraft_list:
            return 0
        
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Prepare batch data
            batch_data = [
                (
                    record['icao24'].lower(),
                    record.get('image_url', ''),
                    record.get('type', ''),
                    datetime.utcnow().isoformat()
                )
                for record in aircraft_list
            ]
            
            # Use executemany for efficiency
            cursor.executemany("""
                INSERT OR REPLACE INTO aircraft (icao24, image_url, type, last_updated)
                VALUES (?, ?, ?, ?)
            """, batch_data)
            
            conn.commit()
            
            # Clear cache for updated items
            for record in aircraft_list:
                cache_key = f"aircraft_{record['icao24']}"
                if cache_key in self._cache_timestamps:
                    del self._cache_timestamps[cache_key]
            self.get_aircraft_from_cache_optimized.cache_clear()
            
            return cursor.rowcount
    
    def get_logbook_optimized(self, 
                            since: Optional[str] = None, 
                            limit: int = 100,
                            offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get logbook entries with pagination and count.
        
        Args:
            since: ISO timestamp to filter entries
            limit: Maximum number of entries
            offset: Number of entries to skip
            
        Returns:
            Tuple of (entries, total_count)
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get total count first
            if since:
                cursor.execute(
                    "SELECT COUNT(*) as count FROM logbook WHERE first_spotted > ?",
                    (since,)
                )
            else:
                cursor.execute("SELECT COUNT(*) as count FROM logbook")
            
            total_count = cursor.fetchone()['count']
            
            # Get paginated results
            if since:
                cursor.execute("""
                    SELECT aircraft_type, image_url, first_spotted, 
                           last_spotted, sighting_count
                    FROM logbook 
                    WHERE first_spotted > ? 
                    ORDER BY first_spotted DESC
                    LIMIT ? OFFSET ?
                """, (since, limit, offset))
            else:
                cursor.execute("""
                    SELECT aircraft_type, image_url, first_spotted, 
                           last_spotted, sighting_count
                    FROM logbook 
                    ORDER BY first_spotted DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            entries = [dict(row) for row in cursor.fetchall()]
            
        return entries, total_count
    
    def get_logbook_stats(self) -> Dict[str, Any]:
        """
        Get logbook statistics efficiently.
        
        Returns:
            Dictionary with logbook statistics
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Single query to get multiple stats
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT aircraft_type) as unique_types,
                    COUNT(*) as total_entries,
                    SUM(sighting_count) as total_sightings,
                    MAX(last_spotted) as most_recent,
                    MIN(first_spotted) as oldest
                FROM logbook
            """)
            
            stats = dict(cursor.fetchone())
            
            # Get top aircraft types
            cursor.execute("""
                SELECT aircraft_type, sighting_count
                FROM logbook
                ORDER BY sighting_count DESC
                LIMIT 5
            """)
            
            stats['top_aircraft'] = [
                dict(row) for row in cursor.fetchall()
            ]
            
            # Get recent additions
            cursor.execute("""
                SELECT aircraft_type, first_spotted
                FROM logbook
                ORDER BY first_spotted DESC
                LIMIT 5
            """)
            
            stats['recent_additions'] = [
                dict(row) for row in cursor.fetchall()
            ]
            
        return stats
    
    def add_to_logbook_with_dedup(self, 
                                 aircraft_type: str, 
                                 image_url: str,
                                 check_recent: bool = True) -> Tuple[bool, str]:
        """
        Add to logbook with duplicate checking.
        
        Args:
            aircraft_type: Type of aircraft
            image_url: URL of aircraft image
            check_recent: Check if recently added (within 1 hour)
            
        Returns:
            Tuple of (success, message)
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if recently added
            if check_recent:
                one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
                cursor.execute("""
                    SELECT last_spotted FROM logbook 
                    WHERE aircraft_type = ? AND last_spotted > ?
                """, (aircraft_type, one_hour_ago))
                
                if cursor.fetchone():
                    return False, "Aircraft recently spotted"
            
            # Add or update
            cursor.execute("""
                INSERT INTO logbook (aircraft_type, image_url, last_spotted, sighting_count)
                VALUES (?, ?, CURRENT_TIMESTAMP, 1)
                ON CONFLICT(aircraft_type) DO UPDATE SET
                    sighting_count = sighting_count + 1,
                    last_spotted = CURRENT_TIMESTAMP,
                    image_url = CASE 
                        WHEN logbook.image_url = '' OR logbook.image_url IS NULL 
                        THEN excluded.image_url 
                        ELSE logbook.image_url 
                    END
            """, (aircraft_type, image_url or ''))
            
            conn.commit()
            
            # Check if it was an insert or update
            if cursor.lastrowid:
                return True, "New aircraft added to logbook"
            else:
                return True, "Aircraft sighting count updated"
    
    def vacuum_database(self) -> None:
        """
        Vacuum database to reclaim space and optimize.
        Should be run during low activity periods.
        """
        with self.db.pool.get_connection() as conn:
            # Can't run VACUUM in a transaction
            conn.isolation_level = None
            conn.execute("VACUUM")
            conn.isolation_level = ""
            logger.info("Database vacuumed successfully")
    
    def get_database_health(self) -> Dict[str, Any]:
        """Get database health metrics."""
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check fragmentation
            cursor.execute("PRAGMA freelist_count")
            freelist = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            # Check integrity
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]
            
            # Get cache stats
            cursor.execute("PRAGMA cache_size")
            cache_size = cursor.fetchone()[0]
            
            # Get table stats
            cursor.execute("""
                SELECT name, 
                       (SELECT COUNT(*) FROM sqlite_master 
                        WHERE type='index' AND tbl_name=m.name) as index_count
                FROM sqlite_master m 
                WHERE type='table' AND name IN ('aircraft', 'logbook')
            """)
            
            table_stats = {}
            for row in cursor.fetchall():
                table_stats[row[0]] = {'index_count': row[1]}
            
        return {
            'integrity': integrity,
            'fragmentation_ratio': freelist / page_count if page_count > 0 else 0,
            'cache_size': cache_size,
            'table_stats': table_stats,
            'pool_stats': self.db.pool.get_stats()
        }


# Singleton instance
_optimized_db: Optional[OptimizedAircraftDatabase] = None


def get_optimized_database() -> OptimizedAircraftDatabase:
    """Get or create optimized database instance."""
    global _optimized_db
    if _optimized_db is None:
        _optimized_db = OptimizedAircraftDatabase()
    return _optimized_db


# Optimized module-level functions
def get_aircraft_batch(icao24_list: List[str]) -> Dict[str, Dict[str, Any]]:
    """Batch get aircraft data."""
    return get_optimized_database().batch_get_aircraft(icao24_list)


def save_aircraft_batch(aircraft_list: List[Dict[str, Any]]) -> int:
    """Batch save aircraft data."""
    return get_optimized_database().batch_save_aircraft(aircraft_list)


def get_logbook_paginated(since: Optional[str] = None, 
                        limit: int = 100,
                        offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
    """Get paginated logbook entries."""
    return get_optimized_database().get_logbook_optimized(since, limit, offset)


def get_logbook_statistics() -> Dict[str, Any]:
    """Get logbook statistics."""
    return get_optimized_database().get_logbook_stats()


def add_to_logbook_smart(aircraft_type: str, image_url: str) -> Tuple[bool, str]:
    """Add to logbook with smart duplicate detection."""
    return get_optimized_database().add_to_logbook_with_dedup(aircraft_type, image_url)


def get_database_health() -> Dict[str, Any]:
    """Get database health information."""
    return get_optimized_database().get_database_health()