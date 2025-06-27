#!/usr/bin/env python3
"""
Script to reset/clear the logbook database entries.
This will remove all spotted aircraft from the logbook table.
"""

import sqlite3
from pathlib import Path


def reset_logbook():
    """Clear all entries from the logbook table."""
    # Database is in the backend directory
    db_path = Path(__file__).parent.parent / 'aircraft_cache.db'
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Count current entries
        cursor.execute("SELECT COUNT(*) FROM logbook")
        count = cursor.fetchone()[0]
        print(f"Found {count} entries in logbook")
        
        if count == 0:
            print("Logbook is already empty!")
            return
        
        # Confirm deletion
        response = input(f"\nAre you sure you want to delete all {count} logbook entries? (yes/no): ")
        
        if response.lower() == 'yes':
            # Delete all entries from logbook
            cursor.execute("DELETE FROM logbook")
            conn.commit()
            print(f"✓ Successfully deleted {count} entries from logbook")
            
            # Verify deletion
            cursor.execute("SELECT COUNT(*) FROM logbook")
            new_count = cursor.fetchone()[0]
            print(f"✓ Logbook now contains {new_count} entries")
        else:
            print("Operation cancelled")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    print("=== Brum Brum Tracker - Reset Logbook ===")
    print("This will remove all aircraft sightings from the logbook.\n")
    reset_logbook()