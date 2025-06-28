"""
Aircraft service module for handling aircraft-related business logic.

This module provides the core service layer for aircraft tracking operations,
including fetching real-time aircraft data, formatting messages for clients,
and simplifying technical aircraft information for user-friendly display.

The AircraftService class acts as the main orchestrator between the OpenSky API,
local aircraft databases, and WebSocket clients.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.api.opensky_client import (
    build_bounding_box,
    fetch_state_vectors,
    filter_aircraft,
    is_visible
)
from backend.utils.aircraft_data import get_aircraft_data
from backend.utils.aircraft_database import (
    fetch_aircraft_details_from_hexdb,
    fetch_flight_route_from_hexdb,
    fetch_airport_info_from_hexdb
)
from backend.utils.config import Config
from backend.utils.geometry import calculate_eta

logger = logging.getLogger(__name__)


class AircraftService:
    """
    Service for managing aircraft data and operations.
    
    This class handles all aircraft-related business logic including:
    - Fetching real-time aircraft positions from OpenSky Network
    - Enriching aircraft data with registration and route information
    - Formatting data for client consumption
    - Simplifying technical aircraft types for user-friendly display
    
    Attributes:
        last_aircraft_data: Cache of the most recent aircraft data fetched
    """
    
    def __init__(self):
        """Initialize the AircraftService with empty cache."""
        self.last_aircraft_data = None
    
    def simplify_aircraft_type(self, manufacturer: str, type_name: str) -> str:
        """
        Convert technical aircraft type codes to kid-friendly names.
        
        This method translates technical aircraft designations (like "B763" or "A388")
        into more recognizable names suitable for young users (like "Boeing 767" or 
        "Airbus A380 Super Jumbo").
        
        Args:
            manufacturer: The aircraft manufacturer name (e.g., "Boeing", "Airbus")
            type_name: The technical type designation (e.g., "737-800", "A320-214")
            
        Returns:
            A simplified, user-friendly aircraft type name
            
        Examples:
            >>> simplify_aircraft_type("Boeing", "737-800")
            'Boeing 737'
            >>> simplify_aircraft_type("Airbus", "A388")
            'Airbus A380 Super Jumbo'
        """
        manufacturer = (manufacturer or '').strip()
        type_name = (type_name or '').strip()
        
        # Mapping of technical codes to friendly names
        type_mappings = {
            # Boeing
            '737': 'Boeing 737',
            '747': 'Boeing 747 Jumbo Jet',
            '757': 'Boeing 757',
            '767': 'Boeing 767',
            '777': 'Boeing 777',
            '787': 'Boeing 787 Dreamliner',
            # Airbus
            'A319': 'Airbus A319',
            'A320': 'Airbus A320',
            'A321': 'Airbus A321',
            'A330': 'Airbus A330',
            'A340': 'Airbus A340',
            'A350': 'Airbus A350',
            'A380': 'Airbus A380 Super Jumbo',
            # Embraer
            'E170': 'Embraer E170',
            'E175': 'Embraer E175',
            'E190': 'Embraer E190',
            'E195': 'Embraer E195',
            'ERJ': 'Embraer Regional Jet',
            # Bombardier
            'CRJ': 'Bombardier CRJ',
            'Q400': 'Bombardier Dash 8',
            'DHC-8': 'Bombardier Dash 8',
            # ATR
            'ATR 42': 'ATR 42 Propeller',
            'ATR 72': 'ATR 72 Propeller',
            # Others
            'Cessna': 'Cessna Small Plane',
            'Beechcraft': 'Beechcraft Small Plane',
            'Gulfstream': 'Gulfstream Private Jet',
            'Learjet': 'Learjet',
            'Citation': 'Cessna Citation Jet',
        }
        
        # Try to match type name
        for key, friendly_name in type_mappings.items():
            if key in type_name:
                return friendly_name
        
        # Try manufacturer + type
        if manufacturer and type_name:
            full_type = f"{manufacturer} {type_name}"
            # Check if it's a known general aviation aircraft
            if any(ga in manufacturer.lower() for ga in ['cessna', 'piper', 'beechcraft', 'cirrus']):
                return f"{manufacturer} Small Plane"
            return full_type
        
        # Fallback
        return type_name if type_name else 'Unknown Aircraft'
    
    async def fetch_aircraft_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch current aircraft data from OpenSky API.
        
        This method performs the following operations:
        1. Builds a geographic bounding box around the home location
        2. Queries the OpenSky Network API for aircraft in that area
        3. Filters aircraft by distance and visibility criteria
        4. Returns only aircraft that are visible from the home location
        
        The visibility check ensures aircraft are above the minimum elevation
        angle, accounting for Earth's curvature and terrain.
        
        Returns:
            List of aircraft dictionaries with state data if successful,
            None if an error occurs or no aircraft are found
            
        Raises:
            Logs errors but doesn't raise exceptions to ensure graceful degradation
        """
        try:
            # Build bounding box
            bbox = build_bounding_box(Config.HOME_LAT, Config.HOME_LON, Config.SEARCH_RADIUS_KM)
            
            # Fetch state vectors
            aircraft_list = fetch_state_vectors(bbox)
            
            if not aircraft_list:
                logger.debug("No aircraft returned from API")
                return None
            
            logger.info(f"Received {len(aircraft_list)} aircraft from API")
            
            # Filter aircraft
            filtered = filter_aircraft(aircraft_list, Config.HOME_LAT, Config.HOME_LON, Config.SEARCH_RADIUS_KM)
            visible = [a for a in filtered if is_visible(a, Config.MIN_ELEVATION_ANGLE)]
            
            logger.info(f"After filtering: {len(filtered)} within range, {len(visible)} visible")
            
            return visible
        
        except Exception as e:
            logger.error(f"Error fetching aircraft data: {e}")
            return None
    
    def format_aircraft_message(self, aircraft: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a single aircraft for client display.
        
        This method enriches raw aircraft state data with additional information:
        - Aircraft registration and image from local database
        - Simplified aircraft type for user-friendly display
        - Flight route information (origin and destination airports)
        - Altitude conversion to feet
        - All measurements rounded for clean display
        
        Args:
            aircraft: Raw aircraft state dictionary containing:
                - icao24: ICAO 24-bit address
                - latitude/longitude: Current position
                - baro_altitude: Barometric altitude in meters
                - velocity: Ground speed in m/s
                - distance_km: Distance from home
                - bearing_from_home: Direction from home
            
        Returns:
            Formatted message dictionary ready for WebSocket transmission
            containing all display-ready fields for the frontend
        """
        icao24 = aircraft['icao24']
        
        # Get detailed information
        aircraft_info = get_aircraft_data(icao24)
        aircraft_details = fetch_aircraft_details_from_hexdb(icao24)
        
        # Get flight route info
        flight_route = fetch_flight_route_from_hexdb(icao24)
        
        # Get airport info
        origin_info = None
        destination_info = None
        
        if flight_route:
            if flight_route.get('origin'):
                origin_info = fetch_airport_info_from_hexdb(flight_route['origin'])
            if flight_route.get('destination'):
                destination_info = fetch_airport_info_from_hexdb(flight_route['destination'])
        
        # Simplify aircraft type
        if aircraft_details and 'Manufacturer' in aircraft_details:
            manufacturer = aircraft_details.get('Manufacturer', '')
            type_name = aircraft_details.get('Type', '')
            aircraft_type = self.simplify_aircraft_type(manufacturer, type_name)
        else:
            aircraft_type = 'Unknown Aircraft'
        
        # Format message
        message = {
            'type': 'aircraft_update',
            'timestamp': datetime.utcnow().isoformat(),
            'icao24': icao24,
            'callsign': aircraft.get('callsign', '').strip(),
            'latitude': aircraft['latitude'],
            'longitude': aircraft['longitude'],
            'altitude': aircraft['baro_altitude'],
            'altitude_ft': round(aircraft['baro_altitude'] * 3.28084) if aircraft['baro_altitude'] else 0,
            'velocity': aircraft['velocity'],
            'true_track': aircraft['true_track'],
            'distance_km': round(aircraft['distance_km'], 1),
            'bearing_from_home': round(aircraft['bearing_from_home'], 1),
            'elevation_angle': round(aircraft.get('elevation_angle', 0), 1),
            'registration': aircraft_info.get('registration'),
            'image_url': aircraft_info.get('image_url'),
            'aircraft_type': aircraft_type,
            'aircraft_type_raw': aircraft_details.get('Type', 'Unknown') if aircraft_details else 'Unknown',
            'operator': aircraft_details.get('RegisteredOwners', 'Unknown') if aircraft_details else 'Unknown',
            'origin': {
                'airport': origin_info.get('airport') if origin_info else 'Unknown',
                'country_code': origin_info.get('country_code') if origin_info else None,
                'region_name': origin_info.get('region_name') if origin_info else None,
            } if origin_info else None,
            'destination': {
                'airport': destination_info.get('airport') if destination_info else 'Unknown',
                'country_code': destination_info.get('country_code') if destination_info else None,
                'region_name': destination_info.get('region_name') if destination_info else None,
            } if destination_info else None,
        }
        
        return message
    
    def format_aircraft_list_message(self, aircraft_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format a list of approaching aircraft for the dashboard view.
        
        This method processes multiple aircraft to create a summary suitable for
        the "all planes" dashboard. It:
        - Calculates estimated time of arrival (ETA) for each aircraft
        - Filters out aircraft that are moving away (infinite ETA)
        - Enriches each aircraft with simplified type information
        - Sorts by ETA to show closest aircraft first
        - Limits results to 10 most relevant aircraft
        
        Args:
            aircraft_list: List of aircraft state dictionaries, each containing
                position, velocity, and distance information
            
        Returns:
            Formatted message dictionary containing:
                - type: 'approaching_aircraft_list'
                - timestamp: Current UTC time
                - aircraft_count: Number of approaching aircraft
                - aircraft: List of formatted aircraft sorted by ETA
        """
        formatted_aircraft = []
        
        for aircraft in aircraft_list:
            # Skip if no velocity data
            if aircraft.get('velocity') is None:
                continue
            
            # Calculate ETA
            eta_seconds = calculate_eta(
                aircraft['distance_km'],
                aircraft['velocity'],
                aircraft.get('elevation_angle', 0)
            )
            
            # Skip if ETA is infinite (not approaching)
            if eta_seconds == float('inf'):
                continue
            
            # Get aircraft type
            icao24 = aircraft['icao24']
            aircraft_details = fetch_aircraft_details_from_hexdb(icao24)
            if aircraft_details and 'Manufacturer' in aircraft_details:
                manufacturer = aircraft_details.get('Manufacturer', '')
                type_name = aircraft_details.get('Type', '')
                aircraft_type = self.simplify_aircraft_type(manufacturer, type_name)
            else:
                aircraft_type = 'Unknown Aircraft'
            
            # Convert altitude and speed
            altitude_ft = aircraft['baro_altitude'] * 3.28084 if aircraft['baro_altitude'] else 0
            speed_kmh = aircraft['velocity'] * 3.6 if aircraft['velocity'] else 0
            
            formatted_aircraft.append({
                'icao24': aircraft['icao24'],
                'callsign': aircraft.get('callsign', '').strip(),
                'bearing': round(aircraft['bearing_from_home'], 1),
                'distance_km': round(aircraft['distance_km'], 1),
                'altitude_ft': round(altitude_ft),
                'speed_kmh': round(speed_kmh),
                'eta_seconds': round(eta_seconds),
                'eta_minutes': round(eta_seconds / 60, 1),
                'aircraft_type': aircraft_type,
            })
        
        # Sort by ETA (closest first)
        formatted_aircraft.sort(key=lambda x: x['eta_seconds'])
        
        message = {
            'type': 'approaching_aircraft_list',
            'timestamp': datetime.utcnow().isoformat(),
            'aircraft_count': len(formatted_aircraft),
            'aircraft': formatted_aircraft[:10]  # Limit to 10 closest aircraft
        }
        
        return message