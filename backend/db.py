"""
Database module for caching aircraft information.
Manages SQLite connection and aircraft image cache.
"""

import sqlite3
import json
from typing import Optional, Dict, Any
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
    
    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _connect(self) -> None:
        """Establish database connection."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
    
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
_db_instance = None


def get_db() -> AircraftDatabase:
    """Get or create database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = AircraftDatabase()
    return _db_instance


def create_tables() -> None:
    """Create database tables."""
    db = get_db()
    db.create_tables()


def get_aircraft_from_cache(icao24: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached aircraft data.
    
    Args:
        icao24: Aircraft ICAO24 identifier
        
    Returns:
        Aircraft data dictionary or None
    """
    db = get_db()
    return db.get_aircraft_from_cache(icao24)


def save_aircraft_to_cache(record: Dict[str, Any]) -> None:
    """
    Save aircraft data to cache.
    
    Args:
        record: Aircraft data dictionary
    """
    db = get_db()
    db.save_aircraft_to_cache(record)