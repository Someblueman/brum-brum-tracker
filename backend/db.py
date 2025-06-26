"""
Database module for caching aircraft information.
Manages SQLite connection and aircraft image cache.
"""

import sqlite3
import json
from typing import Optional, Dict, Any, List
from pathlib import Path


class AircraftDatabase:
    """Manages aircraft data caching using SQLite."""
    
    def __init__(self, db_path: str = "backend/aircraft_cache.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        self._ensure_db_directory()
        self._connect()
        self.create_tables()
        self.create_logbook_table()
    
    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _connect(self) -> None:
        """Establish database connection."""
        # Enable WAL mode for better concurrent access
        self.connection = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        # Enable Write-Ahead Logging for better concurrency
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA busy_timeout=30000")
    
    def create_tables(self) -> None:
        """Create the aircraft cache table if it doesn't exist."""
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aircraft (
                icao24 TEXT PRIMARY KEY,
                image_url TEXT,
                type TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()

    def create_logbook_table(self) -> None:
        """Create the logbook table if it doesn't exist."""
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logbook (
                aircraft_type TEXT PRIMARY KEY,
                image_url TEXT,
                first_spotted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()

    def add_to_logbook(self, aircraft_type: str, image_url: str) -> None:
        """Add a new unique aircraft type to the logbook."""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO logbook (aircraft_type, image_url)
            VALUES (?, ?)
        """, (aircraft_type, image_url or ''))
        self.connection.commit()

    def get_logbook(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve entries from the logbook, optionally filtering by date.
        
        Args:
            since: An ISO 8601 timestamp. If provided, only entries newer
                   than this timestamp are returned.
        """
        cursor = self.connection.cursor()
        if since:
            cursor.execute(
                "SELECT * FROM logbook WHERE first_spotted > ? ORDER BY first_spotted DESC",
                (since,)
            )
        else:
            cursor.execute(
                "SELECT * FROM logbook ORDER BY first_spotted DESC"
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_aircraft_from_cache(self, icao24: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached aircraft data by ICAO24 identifier.
        
        Args:
            icao24: Aircraft ICAO24 hex identifier
            
        Returns:
            Dictionary with aircraft data or None if not found
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM aircraft WHERE icao24 = ?",
            (icao24.lower(),)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                'icao24': row['icao24'],
                'image_url': row['image_url'],
                'type': row['type'],
                'last_updated': row['last_updated']
            }
        return None
    
    def save_aircraft_to_cache(self, record: Dict[str, Any]) -> None:
        """
        Save or update aircraft data in cache.
        
        Args:
            record: Dictionary containing icao24, image_url, and type
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO aircraft (icao24, image_url, type)
            VALUES (?, ?, ?)
        """, (
            record['icao24'].lower(),
            record.get('image_url', ''),
            record.get('type', '')
        ))
        self.connection.commit()
    
    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Module-level functions for backwards compatibility
# Note: We no longer keep a global instance to avoid connection issues


def create_tables() -> None:
    """Create database tables."""
    with AircraftDatabase() as db:
        db.create_tables()


def get_aircraft_from_cache(icao24: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached aircraft data.
    
    Args:
        icao24: Aircraft ICAO24 identifier
        
    Returns:
        Aircraft data dictionary or None
    """
    with AircraftDatabase() as db:
        return db.get_aircraft_from_cache(icao24)


def save_aircraft_to_cache(record: Dict[str, Any]) -> None:
    """
    Save aircraft data to cache.
    
    Args:
        record: Aircraft data dictionary
    """
    with AircraftDatabase() as db:
        db.save_aircraft_to_cache(record)

def get_logbook(since: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all logbook entries."""
    with AircraftDatabase() as db:
        return db.get_logbook(since=since)

def add_to_logbook(aircraft_type: str, image_url: str) -> None:
    """Add an entry to the logbook."""
    with AircraftDatabase() as db:
        db.add_to_logbook(aircraft_type, image_url)