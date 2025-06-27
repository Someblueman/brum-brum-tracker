"""
Logbook service module for handling logbook-related business logic.

This module manages the Captain's Logbook feature, which tracks all aircraft
spotted during tracking sessions. It prevents duplicate entries, manages the
SQLite database interactions, and formats logbook data for client display.

The logbook feature helps young users build a collection of different aircraft
types they've seen, encouraging engagement and learning about aviation.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.database.db import add_to_logbook, get_logbook

logger = logging.getLogger(__name__)


class LogbookService:
    """
    Service for managing the Captain's Logbook feature.
    
    The logbook tracks unique aircraft spotted during tracking sessions,
    storing aircraft type and optional images. This service ensures:
    - No duplicate entries for the same aircraft in a session
    - Clean data formatting for frontend display
    - Persistent storage across application restarts
    
    Attributes:
        spotted_aircraft: Set of ICAO24 addresses spotted in current session
    """
    
    def __init__(self):
        """Initialize the LogbookService with an empty spotted aircraft set."""
        self.spotted_aircraft = set()  # Track spotted aircraft to avoid duplicates
    
    def is_aircraft_spotted(self, icao24: str) -> bool:
        """
        Check if aircraft has already been spotted in this session.
        
        Used to prevent duplicate logbook entries for the same aircraft
        during a single tracking session.
        
        Args:
            icao24: The ICAO 24-bit address of the aircraft
            
        Returns:
            True if aircraft was already spotted, False otherwise
        """
        return icao24 in self.spotted_aircraft
    
    def mark_aircraft_spotted(self, icao24: str) -> None:
        """
        Mark an aircraft as spotted in this session.
        
        Once marked, the aircraft won't be added to the logbook again
        during the current session, preventing duplicates.
        
        Args:
            icao24: The ICAO 24-bit address of the aircraft
        """
        self.spotted_aircraft.add(icao24)
    
    def add_aircraft_to_logbook(self, aircraft_type: str, image_url: Optional[str] = None) -> bool:
        """
        Add an aircraft to the logbook.
        
        Args:
            aircraft_type: Type of aircraft
            image_url: Optional URL of aircraft image
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            add_to_logbook(aircraft_type, image_url)
            logger.info(f"Added {aircraft_type} to logbook")
            return True
        except Exception as e:
            logger.error(f"Error adding to logbook: {e}")
            return False
    
    def get_logbook_entries(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get logbook entries.
        
        Args:
            since: Optional datetime string to filter entries
            
        Returns:
            List of logbook entries
        """
        try:
            return get_logbook(since=since)
        except Exception as e:
            logger.error(f"Error retrieving logbook: {e}")
            return []
    
    def format_logbook_response(self, since: Optional[str] = None) -> Dict[str, Any]:
        """
        Format logbook data for client response.
        
        Args:
            since: Optional datetime string to filter entries
            
        Returns:
            Formatted response dictionary
        """
        log_data = self.get_logbook_entries(since)
        
        response = {
            'type': 'logbook_data',
            'timestamp': datetime.utcnow().isoformat(),
            'log': log_data,
            'count': len(log_data)
        }
        
        return response
    
    def should_add_to_logbook(self, icao24: str, aircraft_type: str) -> bool:
        """
        Determine if an aircraft should be added to the logbook.
        
        This method applies business rules to decide if an aircraft is worthy
        of being added to the Captain's Logbook:
        - Must not have been spotted already in this session
        - Must have a known aircraft type (not "Unknown Aircraft")
        
        These rules ensure the logbook contains meaningful, non-duplicate entries
        that help users learn about different aircraft types.
        
        Args:
            icao24: Aircraft ICAO24 identifier for duplicate checking
            aircraft_type: Type of aircraft to validate
            
        Returns:
            True if aircraft meets criteria for logbook entry, False otherwise
        """
        # Don't add if already spotted in this session
        if self.is_aircraft_spotted(icao24):
            return False
        
        # Don't add unknown aircraft types
        if aircraft_type == 'Unknown Aircraft':
            return False
        
        return True
    
    def process_aircraft_for_logbook(self, icao24: str, aircraft_type: str, 
                                   image_url: Optional[str] = None) -> bool:
        """
        Process an aircraft for potential logbook entry.
        
        This is the main entry point for adding aircraft to the logbook.
        It combines validation, database insertion, and session tracking
        in a single transaction-like operation.
        
        The method ensures that:
        1. Aircraft meets criteria (via should_add_to_logbook)
        2. Database insertion succeeds
        3. Session tracking is updated only on success
        
        Args:
            icao24: Aircraft ICAO24 identifier for tracking
            aircraft_type: Type of aircraft (e.g., "Boeing 737")
            image_url: Optional URL of aircraft image for visual reference
            
        Returns:
            True if successfully added to logbook, False if skipped or failed
            
        Example:
            >>> service.process_aircraft_for_logbook("ABC123", "Boeing 747", 
            ...     "https://example.com/747.jpg")
            True  # First time seeing this aircraft
            >>> service.process_aircraft_for_logbook("ABC123", "Boeing 747", 
            ...     "https://example.com/747.jpg")
            False  # Already spotted in this session
        """
        if not self.should_add_to_logbook(icao24, aircraft_type):
            return False
        
        # Add to logbook
        success = self.add_aircraft_to_logbook(aircraft_type, image_url)
        
        if success:
            # Mark as spotted only after successful database insertion
            self.mark_aircraft_spotted(icao24)
        
        return success