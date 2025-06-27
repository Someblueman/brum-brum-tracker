"""
Database connection pool for efficient connection management.
Provides thread-safe connection pooling with automatic cleanup.
"""

import sqlite3
import threading
import queue
import time
import logging
from typing import Optional, Dict, Any, List, ContextManager
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Thread-safe SQLite connection pool with automatic connection recycling."""
    
    def __init__(self, 
                 db_path: str, 
                 min_connections: int = 2,
                 max_connections: int = 10,
                 connection_timeout: float = 30.0,
                 max_lifetime: float = 3600.0):
        """
        Initialize connection pool.
        
        Args:
            db_path: Path to SQLite database file
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            connection_timeout: Timeout for acquiring a connection (seconds)
            max_lifetime: Maximum lifetime of a connection (seconds)
        """
        self.db_path = db_path
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.max_lifetime = max_lifetime
        
        self._pool = queue.Queue(maxsize=max_connections)
        self._active_connections = 0
        self._lock = threading.Lock()
        self._closed = False
        self._connection_info: Dict[int, float] = {}  # Track connection creation time
        
        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize minimum connections
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Initialize the connection pool with minimum connections."""
        for _ in range(self.min_connections):
            conn = self._create_connection()
            if conn:
                self._pool.put(conn)
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create a new database connection with optimized settings."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            
            # Optimize for concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            conn.execute("PRAGMA temp_store=MEMORY")
            
            # Track connection creation time
            conn_id = id(conn)
            self._connection_info[conn_id] = time.time()
            
            with self._lock:
                self._active_connections += 1
            
            logger.debug(f"Created new connection (total: {self._active_connections})")
            return conn
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None
    
    def _is_connection_expired(self, conn: sqlite3.Connection) -> bool:
        """Check if a connection has exceeded its maximum lifetime."""
        conn_id = id(conn)
        creation_time = self._connection_info.get(conn_id, 0)
        return (time.time() - creation_time) > self.max_lifetime
    
    def _close_connection(self, conn: sqlite3.Connection) -> None:
        """Close a database connection and clean up tracking info."""
        try:
            conn_id = id(conn)
            conn.close()
            
            # Remove from tracking
            if conn_id in self._connection_info:
                del self._connection_info[conn_id]
            
            with self._lock:
                self._active_connections -= 1
            
            logger.debug(f"Closed connection (remaining: {self._active_connections})")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
    
    @contextmanager
    def get_connection(self) -> ContextManager[sqlite3.Connection]:
        """
        Get a connection from the pool.
        
        Yields:
            A database connection that will be automatically returned to the pool.
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        conn = None
        start_time = time.time()
        
        try:
            # Try to get a connection from the pool
            while True:
                try:
                    conn = self._pool.get(timeout=1.0)
                    
                    # Check if connection is still valid
                    if self._is_connection_expired(conn):
                        self._close_connection(conn)
                        conn = None
                        continue
                    
                    # Test connection is still alive
                    conn.execute("SELECT 1")
                    break
                    
                except queue.Empty:
                    # Check if we can create a new connection
                    with self._lock:
                        if self._active_connections < self.max_connections:
                            conn = self._create_connection()
                            if conn:
                                break
                    
                    # Check timeout
                    if (time.time() - start_time) > self.connection_timeout:
                        raise TimeoutError(f"Could not acquire connection within {self.connection_timeout}s")
                
                except sqlite3.Error:
                    # Connection is dead, close it and try again
                    if conn:
                        self._close_connection(conn)
                        conn = None
            
            yield conn
            
        finally:
            # Return connection to pool
            if conn and not self._closed:
                try:
                    self._pool.put(conn, block=False)
                except queue.Full:
                    # Pool is full, close the connection
                    self._close_connection(conn)
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        self._closed = True
        
        # Close all pooled connections
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                self._close_connection(conn)
            except queue.Empty:
                break
        
        logger.info(f"Connection pool closed. Active connections: {self._active_connections}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        return {
            'pool_size': self._pool.qsize(),
            'active_connections': self._active_connections,
            'max_connections': self.max_connections,
            'min_connections': self.min_connections
        }


class PooledAircraftDatabase:
    """Aircraft database with connection pooling for improved performance."""
    
    def __init__(self, db_path: str = "backend/aircraft_cache.db"):
        """Initialize database with connection pool."""
        self.pool = ConnectionPool(db_path)
        self._ensure_tables()
    
    def _ensure_tables(self) -> None:
        """Ensure all required tables exist."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Aircraft cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS aircraft (
                    icao24 TEXT PRIMARY KEY,
                    image_url TEXT,
                    type TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_aircraft_updated 
                ON aircraft(last_updated)
            """)
            
            # Logbook table with enhanced schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logbook (
                    aircraft_type TEXT PRIMARY KEY,
                    image_url TEXT,
                    first_spotted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_spotted TIMESTAMP,
                    sighting_count INTEGER DEFAULT 1
                )
            """)
            
            # Create indexes for logbook queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logbook_first_spotted 
                ON logbook(first_spotted)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logbook_last_spotted 
                ON logbook(last_spotted)
            """)
            
            conn.commit()
    
    def get_aircraft_from_cache(self, icao24: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached aircraft data using connection pool."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM aircraft WHERE icao24 = ?",
                (icao24.lower(),)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def save_aircraft_to_cache(self, record: Dict[str, Any]) -> None:
        """Save aircraft data using connection pool."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO aircraft (icao24, image_url, type)
                VALUES (?, ?, ?)
            """, (
                record['icao24'].lower(),
                record.get('image_url', ''),
                record.get('type', '')
            ))
            conn.commit()
    
    def add_to_logbook(self, aircraft_type: str, image_url: str) -> None:
        """Add aircraft to logbook using connection pool."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO logbook (aircraft_type, image_url, last_spotted, sighting_count)
                VALUES (?, ?, CURRENT_TIMESTAMP, 1)
                ON CONFLICT(aircraft_type) DO UPDATE SET
                    sighting_count = sighting_count + 1,
                    last_spotted = CURRENT_TIMESTAMP,
                    image_url = COALESCE(excluded.image_url, image_url)
            """, (aircraft_type, image_url or ''))
            conn.commit()
    
    def get_logbook(self, since: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve logbook entries with optimized query.
        
        Args:
            since: ISO timestamp to filter entries
            limit: Maximum number of entries to return
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            if since:
                cursor.execute("""
                    SELECT * FROM logbook 
                    WHERE first_spotted > ? 
                    ORDER BY first_spotted DESC
                    LIMIT ?
                """, (since, limit))
            else:
                cursor.execute("""
                    SELECT * FROM logbook 
                    ORDER BY first_spotted DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_old_cache(self, days: int = 30) -> int:
        """
        Remove old cache entries to prevent database bloat.
        
        Args:
            days: Remove entries older than this many days
            
        Returns:
            Number of entries removed
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM aircraft 
                WHERE last_updated < datetime('now', '-' || ? || ' days')
            """, (days,))
            conn.commit()
            return cursor.rowcount
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database and connection pool statistics."""
        pool_stats = self.pool.get_stats()
        
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get table sizes
            cursor.execute("SELECT COUNT(*) as count FROM aircraft")
            aircraft_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM logbook")
            logbook_count = cursor.fetchone()['count']
            
            # Get database file size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()['size']
        
        return {
            'connection_pool': pool_stats,
            'database': {
                'aircraft_cached': aircraft_count,
                'logbook_entries': logbook_count,
                'size_bytes': db_size
            }
        }
    
    def close(self) -> None:
        """Close the connection pool."""
        self.pool.close_all()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance for the application
_pooled_db: Optional[PooledAircraftDatabase] = None


def get_pooled_database() -> PooledAircraftDatabase:
    """Get or create the pooled database instance."""
    global _pooled_db
    if _pooled_db is None:
        _pooled_db = PooledAircraftDatabase()
    return _pooled_db


# Updated module-level functions to use connection pooling
def get_aircraft_from_cache(icao24: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached aircraft data using pooled connections."""
    return get_pooled_database().get_aircraft_from_cache(icao24)


def save_aircraft_to_cache(record: Dict[str, Any]) -> None:
    """Save aircraft data using pooled connections."""
    get_pooled_database().save_aircraft_to_cache(record)


def add_to_logbook(aircraft_type: str, image_url: str) -> None:
    """Add aircraft to logbook using pooled connections."""
    get_pooled_database().add_to_logbook(aircraft_type, image_url)


def get_logbook(since: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve logbook entries using pooled connections."""
    return get_pooled_database().get_logbook(since)


def cleanup_old_cache(days: int = 30) -> int:
    """Clean up old cache entries."""
    return get_pooled_database().cleanup_old_cache(days)


def get_database_stats() -> Dict[str, Any]:
    """Get database and pool statistics."""
    return get_pooled_database().get_stats()