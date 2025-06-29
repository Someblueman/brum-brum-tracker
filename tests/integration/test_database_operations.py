"""
Integration tests for database operations.

Tests database functions including:
- Logbook operations
- Aircraft caching
- Database initialization
"""

import pytest
import sqlite3
import tempfile
import os
import sys
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.db import (
    init_db,
    add_to_logbook,
    get_logbook,
    add_to_cache,
    get_aircraft_from_cache,
    cleanup_old_cache
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Override the default database path
    import backend.db
    original_db_path = backend.db.DB_PATH
    backend.db.DB_PATH = path
    
    # Initialize the database
    init_db()
    
    yield path
    
    # Cleanup
    backend.db.DB_PATH = original_db_path
    os.unlink(path)


def test_database_initialization(temp_db):
    """Test that database tables are created correctly."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Check logbook table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='logbook'
    """)
    assert cursor.fetchone() is not None
    
    # Check aircraft_cache table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='aircraft_cache'
    """)
    assert cursor.fetchone() is not None
    
    conn.close()


def test_add_to_logbook(temp_db):
    """Test adding entries to the logbook."""
    # Add an entry
    add_to_logbook('Boeing 737', 'https://example.com/image.jpg')
    
    # Retrieve and verify
    logbook = get_logbook()
    assert len(logbook) == 1
    assert logbook[0]['aircraft_type'] == 'Boeing 737'
    assert logbook[0]['image_url'] == 'https://example.com/image.jpg'
    assert 'id' in logbook[0]
    assert 'spotted_at' in logbook[0]


def test_get_logbook_with_since(temp_db):
    """Test retrieving logbook entries with since parameter."""
    # Add multiple entries
    add_to_logbook('Boeing 737', 'https://example.com/737.jpg')
    add_to_logbook('Airbus A320', 'https://example.com/a320.jpg')
    
    # Get all entries
    all_entries = get_logbook()
    assert len(all_entries) == 2
    
    # Get entries since a future timestamp (should be empty)
    future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    recent_entries = get_logbook(since=future_time)
    assert len(recent_entries) == 0
    
    # Get entries since a past timestamp (should get all)
    past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    past_entries = get_logbook(since=past_time)
    assert len(past_entries) == 2


def test_add_to_cache(temp_db):
    """Test adding aircraft to cache."""
    aircraft_data = {
        'icao24': 'abc123',
        'image_url': 'https://example.com/plane.jpg',
        'aircraft_type': 'Boeing 747',
        'registration': 'N12345'
    }
    
    add_to_cache('abc123', aircraft_data)
    
    # Verify it was added
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM aircraft_cache WHERE icao24 = ?", ('abc123',))
    row = cursor.fetchone()
    
    assert row is not None
    assert row[0] == 'abc123'  # icao24
    
    # Parse JSON data
    import json
    data = json.loads(row[1])
    assert data['aircraft_type'] == 'Boeing 747'
    
    conn.close()


def test_get_aircraft_from_cache(temp_db):
    """Test retrieving aircraft from cache."""
    # Add to cache
    aircraft_data = {
        'icao24': 'def456',
        'image_url': 'https://example.com/plane2.jpg',
        'aircraft_type': 'Airbus A380'
    }
    
    add_to_cache('def456', aircraft_data)
    
    # Retrieve from cache
    cached_data = get_aircraft_from_cache('def456')
    
    assert cached_data is not None
    assert cached_data['icao24'] == 'def456'
    assert cached_data['aircraft_type'] == 'Airbus A380'
    
    # Try non-existent aircraft
    missing_data = get_aircraft_from_cache('xyz999')
    assert missing_data is None


def test_cache_expiry(temp_db):
    """Test that cache entries expire after 24 hours."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Add an old entry directly
    old_time = datetime.utcnow() - timedelta(hours=25)
    cursor.execute("""
        INSERT INTO aircraft_cache (icao24, data, cached_at)
        VALUES (?, ?, ?)
    """, ('old123', '{"test": "data"}', old_time.isoformat()))
    
    # Add a recent entry
    add_to_cache('new123', {'test': 'recent'})
    
    conn.commit()
    
    # Old entry should not be retrievable
    old_data = get_aircraft_from_cache('old123')
    assert old_data is None
    
    # New entry should be retrievable
    new_data = get_aircraft_from_cache('new123')
    assert new_data is not None
    
    conn.close()


def test_cleanup_old_cache(temp_db):
    """Test cleanup of old cache entries."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Add old entries
    old_time = datetime.utcnow() - timedelta(hours=25)
    for i in range(3):
        cursor.execute("""
            INSERT INTO aircraft_cache (icao24, data, cached_at)
            VALUES (?, ?, ?)
        """, (f'old{i}', '{"test": "data"}', old_time.isoformat()))
    
    # Add recent entries
    for i in range(2):
        add_to_cache(f'new{i}', {'test': 'recent'})
    
    conn.commit()
    
    # Count before cleanup
    cursor.execute("SELECT COUNT(*) FROM aircraft_cache")
    count_before = cursor.fetchone()[0]
    assert count_before == 5
    
    # Run cleanup
    cleanup_old_cache()
    
    # Count after cleanup
    cursor.execute("SELECT COUNT(*) FROM aircraft_cache")
    count_after = cursor.fetchone()[0]
    assert count_after == 2  # Only recent entries remain
    
    conn.close()


def test_logbook_ordering(temp_db):
    """Test that logbook entries are returned in correct order."""
    # Add entries with slight delays
    import time
    
    add_to_logbook('First', 'url1')
    time.sleep(0.1)
    add_to_logbook('Second', 'url2')
    time.sleep(0.1)
    add_to_logbook('Third', 'url3')
    
    # Get logbook - should be in reverse chronological order
    logbook = get_logbook()
    
    assert len(logbook) == 3
    assert logbook[0]['aircraft_type'] == 'Third'
    assert logbook[1]['aircraft_type'] == 'Second'
    assert logbook[2]['aircraft_type'] == 'First'


def test_concurrent_database_access(temp_db):
    """Test that concurrent database access works correctly."""
    import threading
    import time
    
    results = []
    errors = []
    
    def add_entries(thread_id):
        try:
            for i in range(5):
                add_to_logbook(f'Aircraft-{thread_id}-{i}', f'url-{thread_id}-{i}')
                time.sleep(0.01)  # Small delay to increase chance of conflicts
            results.append(thread_id)
        except Exception as e:
            errors.append(e)
    
    # Create multiple threads
    threads = []
    for i in range(3):
        t = threading.Thread(target=add_entries, args=(i,))
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Check results
    assert len(errors) == 0
    assert len(results) == 3
    
    # Verify all entries were added
    logbook = get_logbook()
    assert len(logbook) == 15  # 3 threads * 5 entries each


if __name__ == '__main__':
    pytest.main([__file__, '-v'])