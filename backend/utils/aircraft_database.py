"""
Aircraft database service using multiple data sources.
"""

import logging
import requests
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = 10
USER_AGENT = "BrumBrumTracker/1.0"
HEXDB_BASE_URL = "https://hexdb.io/api/v1"

def fetch_aircraft_details_from_hexdb(icao24: str) -> Optional[Dict]:
    """
    Fetch aircraft details (type, manufacturer, etc.) from hexdb.io API.
    """
    try:
        url = f"{HEXDB_BASE_URL}/aircraft/{icao24.lower()}"
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        logger.debug(f"No aircraft details found in hexdb for ICAO24: {icao24}")
        return None
    except requests.RequestException as e:
        logger.error(f"Error fetching from hexdb for {icao24}: {e}")
        return None

def fetch_flight_route_from_hexdb(callsign: str) -> Optional[Dict]:
    """
    Fetch flight route by callsign from hexdb.io API.
    """
    if not callsign:
        return None
    try:
        url = f"{HEXDB_BASE_URL}/route/icao/{callsign}"
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        logger.error(f"Failed to fetch route for {callsign}: {e}")
        return None

def fetch_airport_info_from_hexdb(icao: str) -> Optional[Dict]:
    """
    Fetch airport information by ICAO code from hexdb.io API.
    """
    if not icao:
        return None
    try:
        url = f"{HEXDB_BASE_URL}/airport/icao/{icao}"
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        logger.error(f"Failed to fetch airport info for {icao}: {e}")
        return None