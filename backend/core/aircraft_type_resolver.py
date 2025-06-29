"""
Aircraft type resolver with multiple fallback sources.

This module provides a unified interface for resolving aircraft types
using multiple data sources in a prioritized order.
"""

import logging
import json
from typing import Dict, Any

from backend.database.db import get_aircraft_from_cache, save_aircraft_to_cache, AircraftDatabase
from backend.utils.aircraft_database import fetch_aircraft_details_from_hexdb
from backend.core.planespotters_client import get_aircraft_type_string

logger = logging.getLogger(__name__)

# List of generic/unidentified aircraft types to log
GENERIC_AIRCRAFT_TYPES = [
    "Unknown Aircraft",
    "Aircraft",
    "Boeing Aircraft",
    "Airbus Aircraft",
    "CRJ Jet",
    "Unknown Model",
    "Prop Plane",
    "Small Plane",
    "Private Jet",
    "Regional Jet"
]


def should_log_as_unidentified(aircraft_type: str) -> bool:
    """Check if an aircraft type is generic and should be logged for improvement."""
    if not aircraft_type:
        return True
    
    # Check exact matches
    if aircraft_type in GENERIC_AIRCRAFT_TYPES:
        return True
    
    # Check if it ends with generic terms
    generic_endings = ["Aircraft", "Plane", "Jet", "Model"]
    for ending in generic_endings:
        if aircraft_type.endswith(ending) and len(aircraft_type.split()) <= 2:
            return True
    
    return False


def simplify_aircraft_type(manufacturer: str, type_name: str) -> str:
    """
    Convert technical aircraft type to kid-friendly names.
    """
    # Clean up the input
    manufacturer = (manufacturer or '').strip()
    type_name = (type_name or '').strip()
    
    # Common aircraft type mappings
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
    
    # Check for common patterns in the type name
    full_type = f"{manufacturer} {type_name}".upper()
    
    for pattern, friendly_name in type_mappings.items():
        if pattern.upper() in full_type:
            return friendly_name
    
    # Special handling for specific manufacturers
    if 'BOEING' in manufacturer.upper():
        if type_name:
            return f"Boeing {type_name}"
        return "Boeing Aircraft"
    elif 'AIRBUS' in manufacturer.upper():
        if type_name:
            return f"Airbus {type_name}"
        return "Airbus Aircraft"
    elif 'CESSNA' in manufacturer.upper():
        return "Cessna Small Plane"
    elif 'PIPER' in manufacturer.upper():
        return "Piper Small Plane"
    elif 'BEECH' in manufacturer.upper() or 'BEECHCRAFT' in manufacturer.upper():
        return "Beechcraft Small Plane"
    
    # If we have both manufacturer and type, combine them nicely
    if manufacturer and type_name:
        return f"{manufacturer} {type_name}"
    elif manufacturer:
        return f"{manufacturer} Aircraft"
    elif type_name:
        return type_name
    
    return None  # Return None instead of "Unknown Aircraft"


def resolve_aircraft_type(icao24: str, additional_data: Dict[str, Any] = None) -> str:
    """
    Resolve aircraft type using multiple data sources with fallback.
    
    Priority order:
    1. Local cache database
    2. Hexdb (local aircraft database)
    3. Planespotters API (external API)
    4. "Unknown Aircraft" as final fallback
    
    Args:
        icao24: Aircraft ICAO24 hex identifier
        additional_data: Optional dict with callsign, registration, etc.
        
    Returns:
        Resolved aircraft type string
    """
    logger.debug(f"Resolving aircraft type for {icao24}")
    
    # Initialize database connection for logging
    db = AircraftDatabase()
    log_data = {
        'icao24': icao24,
        'data_source': 'none',
        'raw_type': '',
        'simplified_type': '',
        'manufacturer': '',
        'type_name': ''
    }
    
    if additional_data:
        log_data.update({
            'callsign': additional_data.get('callsign', ''),
            'registration': additional_data.get('registration', ''),
            'operator': additional_data.get('operator', '')
        })
    
    # 1. Check local cache first
    cached_data = get_aircraft_from_cache(icao24)
    if cached_data and cached_data.get('type'):
        cached_type = cached_data['type']
        # Skip if it's a placeholder or unknown
        if 'placeholder' not in cached_type.lower() and cached_type != 'Unknown Aircraft':
            logger.debug(f"Found type in cache for {icao24}: {cached_type}")
            return cached_type
    
    # 2. Try hexdb (local database)
    try:
        aircraft_details = fetch_aircraft_details_from_hexdb(icao24)
        if aircraft_details and 'Manufacturer' in aircraft_details:
            manufacturer = aircraft_details.get('Manufacturer', '')
            type_name = aircraft_details.get('Type', '')
            simplified_type = simplify_aircraft_type(manufacturer, type_name)
            
            if simplified_type:
                logger.info(f"Found type in hexdb for {icao24}: {simplified_type}")
                
                # Update log data
                log_data.update({
                    'data_source': 'hexdb',
                    'raw_type': f"{manufacturer} {type_name}",
                    'simplified_type': simplified_type,
                    'manufacturer': manufacturer,
                    'type_name': type_name,
                    'raw_api_response': json.dumps(aircraft_details)
                })
                
                # Log if it's a generic type
                if should_log_as_unidentified(simplified_type):
                    db.log_unidentified_aircraft(log_data)
                
                # Cache the result
                if cached_data:
                    cached_data['type'] = simplified_type
                    save_aircraft_to_cache(cached_data)
                else:
                    save_aircraft_to_cache({
                        'icao24': icao24,
                        'type': simplified_type,
                        'image_url': ''
                    })
                return simplified_type
    except Exception as e:
        logger.error(f"Error fetching from hexdb for {icao24}: {e}")
    
    # 3. Try Planespotters API as fallback
    try:
        planespotters_type = get_aircraft_type_string(icao24)
        if planespotters_type:
            logger.info(f"Found type in Planespotters for {icao24}: {planespotters_type}")
            # Simplify the Planespotters type
            # Extract manufacturer and model if possible
            parts = planespotters_type.split(' ', 1)
            if len(parts) >= 2:
                simplified_type = simplify_aircraft_type(parts[0], parts[1])
            else:
                simplified_type = simplify_aircraft_type('', planespotters_type)
            
            final_type = simplified_type or planespotters_type
            
            # Update log data
            log_data.update({
                'data_source': 'planespotters',
                'raw_type': planespotters_type,
                'simplified_type': final_type,
                'manufacturer': parts[0] if len(parts) >= 2 else '',
                'type_name': parts[1] if len(parts) >= 2 else planespotters_type
            })
            
            # Log if it's a generic type
            if should_log_as_unidentified(final_type):
                db.log_unidentified_aircraft(log_data)
            
            # Cache the result
            if cached_data:
                cached_data['type'] = final_type
                save_aircraft_to_cache(cached_data)
            else:
                save_aircraft_to_cache({
                    'icao24': icao24,
                    'type': final_type,
                    'image_url': ''
                })
            return final_type
    except Exception as e:
        logger.error(f"Error fetching from Planespotters for {icao24}: {e}")
    
    # 4. Final fallback
    logger.warning(f"No aircraft type found for {icao24}, using fallback")
    
    # Log the unknown aircraft
    log_data.update({
        'data_source': 'fallback',
        'simplified_type': 'Unknown Aircraft'
    })
    db.log_unidentified_aircraft(log_data)
    
    return "Unknown Aircraft"


def get_aircraft_info_with_fallbacks(icao24: str) -> Dict[str, Any]:
    """
    Get comprehensive aircraft information using all available sources.
    
    Args:
        icao24: Aircraft ICAO24 hex identifier
        
    Returns:
        Dictionary with aircraft information including type, image_url, etc.
    """
    # Get type using resolver
    aircraft_type = resolve_aircraft_type(icao24)
    
    # Get cached data for other fields
    cached_data = get_aircraft_from_cache(icao24)
    
    return {
        'icao24': icao24,
        'type': aircraft_type,
        'image_url': cached_data.get('image_url', '') if cached_data else '',
        'last_updated': cached_data.get('last_updated') if cached_data else None
    }