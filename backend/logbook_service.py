"""
Logbook service module for handling logbook-related business logic.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.db import add_to_logbook, get_logbook

logger = logging.getLogger(__name__)


class LogbookService:
    """Service for managing logbook data and operations."""
    
    def __init__(self):
        self.spotted_aircraft = set()  # Track spotted aircraft to avoid duplicates
    
    def is_aircraft_spotted(self, icao24: str) -> bool:
        """Check if aircraft has already been spotted in this session."""
        return icao24 in self.spotted_aircraft
    
    def mark_aircraft_spotted(self, icao24: str) -> None:
        """Mark an aircraft as spotted in this session."""
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
        
        Args:
            icao24: Aircraft ICAO24 identifier
            aircraft_type: Type of aircraft
            
        Returns:
            True if should be added, False otherwise
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
        
        Args:
            icao24: Aircraft ICAO24 identifier
            aircraft_type: Type of aircraft
            image_url: Optional URL of aircraft image
            
        Returns:
            True if added to logbook, False otherwise
        """
        if not self.should_add_to_logbook(icao24, aircraft_type):
            return False
        
        # Add to logbook
        success = self.add_aircraft_to_logbook(aircraft_type, image_url)
        
        if success:
            # Mark as spotted
            self.mark_aircraft_spotted(icao24)
        
        return success