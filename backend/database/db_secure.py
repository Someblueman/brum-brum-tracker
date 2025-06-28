"""
Database module for caching aircraft information with enhanced error handling.
Manages SQLite connection and aircraft image cache.
"""

import sqlite3
import json
import logging
import threading
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager

from backend.config import config

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


class AircraftDatabase:
    """Manages aircraft data caching using SQLite with proper error handling."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        if hasattr(self, '_initialized'):
            return
        
        self.db_path = db_path or config.DATABASE_PATH
        self.connection = None
        self._local = threading.local()
        
        try:
            self._ensure_db_directory()
            self._connect()
            self.create_tables()
            self.create_logbook_table()
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
    
    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        try:
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise DatabaseError(f"Failed to create database directory: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path, 
                timeout=30.0, 
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable Write-Ahead Logging for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA busy_timeout=30000")
        return self._local.connection
    
    def _connect(self) -> None:
        """Establish initial database connection."""
        try:
            self.connection = self._get_connection()
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to database: {e}")
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise DatabaseError(f"Transaction failed: {e}")
    
    def create_tables(self) -> None:
        """Create the aircraft cache table if it doesn't exist."""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS aircraft (
                        icao24 TEXT PRIMARY KEY,
                        image_url TEXT,
                        type TEXT,
                        manufacturer TEXT,
                        model TEXT,
                        registration TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        data JSON
                    )
                """)
                
                # Create index for faster lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_aircraft_last_updated 
                    ON aircraft(last_updated)
                """)
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to create aircraft table: {e}")

    def create_logbook_table(self) -> None:
        """
        Create or update the logbook table schema.
        Includes sighting count and last spotted timestamp.
        """
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                # Create the table with all columns
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS logbook (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        aircraft_type TEXT NOT NULL,
                        image_url TEXT,
                        first_spotted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_spotted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sighting_count INTEGER DEFAULT 1,
                        notes TEXT,
                        UNIQUE(aircraft_type)
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_logbook_last_spotted 
                    ON logbook(last_spotted DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_logbook_aircraft_type 
                    ON logbook(aircraft_type)
                """)
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to create logbook table: {e}")

    def add_to_logbook(self, aircraft_type: str, image_url: Optional[str] = None) -> bool:
        """
        Add a new aircraft to the logbook or update an existing one.
        
        Args:
            aircraft_type: Type of the aircraft
            image_url: URL of the aircraft image
            
        Returns:
            True if successful, False otherwise
        """
        if not aircraft_type:
            logger.warning("Cannot add empty aircraft type to logbook")
            return False
        
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO logbook (aircraft_type, image_url, last_spotted, sighting_count)
                    VALUES (?, ?, CURRENT_TIMESTAMP, 1)
                    ON CONFLICT(aircraft_type) DO UPDATE SET
                        sighting_count = sighting_count + 1,
                        last_spotted = CURRENT_TIMESTAMP,
                        image_url = CASE 
                            WHEN image_url IS NULL OR image_url = '' 
                            THEN excluded.image_url 
                            ELSE image_url 
                        END
                """, (aircraft_type, image_url))
                
                logger.info(f"Added/updated aircraft in logbook: {aircraft_type}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to add to logbook: {e}")
            return False

    def get_logbook(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve logbook entries with pagination.
        
        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            List of logbook entries
        """
        try:
            # Validate inputs
            limit = max(1, min(limit, 1000))  # Between 1 and 1000
            offset = max(0, offset)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id,
                    aircraft_type,
                    image_url,
                    first_spotted,
                    last_spotted,
                    sighting_count,
                    notes
                FROM logbook
                ORDER BY last_spotted DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            entries = []
            for row in cursor.fetchall():
                entries.append({
                    'id': row['id'],
                    'aircraft_type': row['aircraft_type'],
                    'image_url': row['image_url'],
                    'first_spotted': row['first_spotted'],
                    'last_spotted': row['last_spotted'],
                    'sighting_count': row['sighting_count'],
                    'notes': row['notes']
                })
            
            return entries
            
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve logbook: {e}")
            return []

    def get_aircraft_from_cache(self, icao24: str) -> Optional[Dict[str, Any]]:
        """
        Get cached aircraft data.
        
        Args:
            icao24: ICAO24 identifier
            
        Returns:
            Cached aircraft data or None
        """
        if not icao24:
            return None
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check cache expiry
            expiry_date = datetime.now() - timedelta(days=config.CACHE_EXPIRY_DAYS)
            
            cursor.execute("""
                SELECT * FROM aircraft 
                WHERE icao24 = ? AND last_updated > ?
            """, (icao24.lower(), expiry_date))
            
            row = cursor.fetchone()
            if row:
                result = {
                    'icao24': row['icao24'],
                    'image_url': row['image_url'],
                    'type': row['type'],
                    'manufacturer': row['manufacturer'],
                    'model': row['model'],
                    'registration': row['registration']
                }
                
                # Parse additional JSON data if present
                if row['data']:
                    try:
                        additional_data = json.loads(row['data'])
                        result.update(additional_data)
                    except json.JSONDecodeError:
                        pass
                
                return result
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get aircraft from cache: {e}")
        
        return None

    def add_aircraft_to_cache(self, icao24: str, data: Dict[str, Any]) -> bool:
        """
        Add or update aircraft in cache.
        
        Args:
            icao24: ICAO24 identifier
            data: Aircraft data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not icao24:
            return False
        
        try:
            # Extract main fields
            image_url = data.get('image_url')
            aircraft_type = data.get('type') or data.get('aircraft_type')
            manufacturer = data.get('manufacturer')
            model = data.get('model')
            registration = data.get('registration')
            
            # Store additional data as JSON
            additional_data = {k: v for k, v in data.items() 
                             if k not in ['image_url', 'type', 'aircraft_type', 
                                         'manufacturer', 'model', 'registration']}
            
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO aircraft (
                        icao24, image_url, type, manufacturer, 
                        model, registration, data, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(icao24) DO UPDATE SET
                        image_url = excluded.image_url,
                        type = excluded.type,
                        manufacturer = excluded.manufacturer,
                        model = excluded.model,
                        registration = excluded.registration,
                        data = excluded.data,
                        last_updated = CURRENT_TIMESTAMP
                """, (
                    icao24.lower(), image_url, aircraft_type, 
                    manufacturer, model, registration,
                    json.dumps(additional_data) if additional_data else None
                ))
                
                logger.debug(f"Added aircraft to cache: {icao24}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to add aircraft to cache: {e}")
            return False

    def cleanup_old_cache(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        try:
            expiry_date = datetime.now() - timedelta(days=config.CACHE_EXPIRY_DAYS)
            
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM aircraft 
                    WHERE last_updated < ?
                """, (expiry_date,))
                
                deleted = cursor.rowcount
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} expired cache entries")
                
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup cache: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get table sizes
            cursor.execute("SELECT COUNT(*) FROM aircraft")
            aircraft_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM logbook")
            logbook_count = cursor.fetchone()[0]
            
            # Get database file size
            db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            
            return {
                'aircraft_cached': aircraft_count,
                'logbook_entries': logbook_count,
                'database_size_mb': round(db_size / 1024 / 1024, 2),
                'cache_expiry_days': config.CACHE_EXPIRY_DAYS
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    def close(self):
        """Close database connections."""
        try:
            if hasattr(self._local, 'connection') and self._local.connection:
                self._local.connection.close()
                self._local.connection = None
            if self.connection:
                self.connection.close()
                self.connection = None
        except Exception as e:
            logger.error(f"Error closing database: {e}")


# Create singleton instance
db = AircraftDatabase()

# Export convenience functions
def get_aircraft_from_cache(icao24: str) -> Optional[Dict[str, Any]]:
    """Get aircraft from cache."""
    return db.get_aircraft_from_cache(icao24)

def add_aircraft_to_cache(icao24: str, data: Dict[str, Any]) -> bool:
    """Add aircraft to cache."""
    return db.add_aircraft_to_cache(icao24, data)

def add_to_logbook(aircraft_type: str, image_url: Optional[str] = None) -> bool:
    """Add aircraft to logbook."""
    return db.add_to_logbook(aircraft_type, image_url)

def get_logbook(limit: int = 100) -> List[Dict[str, Any]]:
    """Get logbook entries."""
    return db.get_logbook(limit)