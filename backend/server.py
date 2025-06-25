"""
WebSocket server for real-time aircraft data streaming.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Set, Dict, Any, Optional, List
import websockets
from websockets.server import WebSocketServerProtocol

from backend.opensky_client import (
    build_bounding_box,
    fetch_state_vectors,
    filter_aircraft,
    is_visible,
    select_best_plane
)
from backend.db import get_aircraft_from_cache
from backend.aircraft_data import get_aircraft_data
from utils.constants import (
    WEBSOCKET_HOST,
    WEBSOCKET_PORT,
    HOME_LAT,
    HOME_LON,
    SEARCH_RADIUS_KM,
    MIN_ELEVATION_ANGLE,
    POLLING_INTERVAL,
    LOG_FILE,
    LOG_LEVEL
)


# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# Also set debug level for our modules during debugging
logging.getLogger('backend.opensky_client').setLevel(logging.DEBUG)
logging.getLogger('utils.geometry').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

def _simplify_aircraft_type(type_string: Optional[str]) -> str:
    """
    Translates a technical aircraft type string into a simple, kid-friendly name.
    """
    if not type_string:
        return "Aircraft"

    type_string_upper = type_string.upper()

    # CORRECTED dictionary to be more flexible with Boeing codes.
    type_map = {
        # Boeing (now without the 'B' prefix)
        "787": "Boeing 787 Dreamliner",
        "777": "Boeing 777",
        "767": "Boeing 767",
        "747": "Boeing 747 'Jumbo Jet'",
        "737": "Boeing 737",  # This will now correctly match "737NG..."

        # Airbus
        "A20N": "Airbus A320neo",
        "A21N": "Airbus A321neo",
        "A33": "Airbus A330",
        "A34": "Airbus A340",
        "A35": "Airbus A350",
        "A38": "Airbus A380 'Superjumbo'",
        "A32": "Airbus A320",

        # Others
        "E19": "Embraer E-Jet",
        "E17": "Embraer E-Jet",
        "C172": "Cessna Skyhawk",
        "C25C": "Cessna Citation",
        "LEAR": "Learjet",
        "GLF": "Gulfstream Jet",
        "BOMBARDIER": "Bombardier Jet",
        "CRJ": "CRJ Jet"
    }

    for code, name in type_map.items():
        if code in type_string_upper:
            return name

    # If no specific match is found, try a general one
    if "BOEING" in type_string_upper: return "Boeing Aircraft"
    if "AIRBUS" in type_string_upper: return "Airbus Aircraft"
    if "EMBRAER" in type_string_upper: return "Embraer Aircraft"
    
    # A better final fallback
    return "Prop Plane"


class AircraftTracker:
    """Manages aircraft tracking and WebSocket connections."""
    
    def __init__(self):
        """Initialize the tracker."""
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.last_aircraft_data: Optional[Dict[str, Any]] = None
        self.is_polling = False
        self.spotted_aircraft: Set[str] = set()  # Track all aircraft we've ever seen
        self.visible_aircraft: Set[str] = set()  # Track aircraft that have been visible
        self.polling_task: Optional[asyncio.Task] = None
    
    def format_aircraft_message(self, aircraft: Dict[str, Any]) -> Dict[str, Any]:
            """
            Format aircraft data for frontend consumption.
            
            Args:
                aircraft: Aircraft state dictionary
                
            Returns:
                Formatted message dictionary
            """
            # Get image data using scraper (checks cache first)
            media_data = get_aircraft_data(aircraft['icao24'])

            # Gets both raw and simplified aircraft type for debugging
            raw_type = media_data.get('type')
            simple_type = _simplify_aircraft_type(raw_type)
            
            # Convert altitude from meters to feet
            altitude_ft = aircraft['baro_altitude'] * 3.28084 if aircraft['baro_altitude'] else 0
            
            # Convert velocity from m/s to km/h
            speed_kmh = aircraft['velocity'] * 3.6 if aircraft['velocity'] else 0
            
            message = {
                'type': 'aircraft_update',
                'timestamp': datetime.utcnow().isoformat(),
                'icao24': aircraft['icao24'],
                'callsign': aircraft.get('callsign', ''),
                'bearing': round(aircraft['bearing_from_home'], 1),
                'distance_km': round(aircraft['distance_km'], 1),
                'altitude_ft': round(altitude_ft),
                'speed_kmh': round(speed_kmh),
                'elevation_angle': round(aircraft['elevation_angle'], 1),
                'aircraft_type': simple_type,
                'aircraft_type_raw': raw_type,
                'image_url': media_data.get('image_url', '')
            }
            
            return message

    
    def format_aircraft_list_message(self, aircraft_list: List[Dict[str, Any]]) -> Dict[str, Any]:
            """
            Format a list of approaching aircraft for the dashboard.
            
            Args:
                aircraft_list: List of aircraft state dictionaries
                
            Returns:
                Formatted message with aircraft list and ETAs
            """
            from utils.geometry import calculate_eta
            
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
                
                # Get image data using scraper (checks cache first)
                media_data = get_aircraft_data(aircraft['icao24'])

                # Gets both raw and simplified aircraft type for debugging
                raw_type = media_data.get('type')
                simple_type = _simplify_aircraft_type(raw_type)
                
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
                    'aircraft_type': simple_type,
                    'aircraft_type_raw': raw_type,
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
    
    async def broadcast_message(self, message: Dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Message dictionary to send
        """
        if not self.connected_clients:
            return
        
        # Serialize message
        message_json = json.dumps(message)
        
        # Send to all connected clients
        disconnected_clients = set()
        for client in self.connected_clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected_clients
        
        if disconnected_clients:
            logger.info(f"Removed {len(disconnected_clients)} disconnected clients")
    
    async def polling_loop(self) -> None:
        """Main polling loop for fetching aircraft data."""
        logger.info("Starting aircraft polling loop")
        logger.info(f"Home location: lat={HOME_LAT}, lon={HOME_LON}")
        logger.info(f"Search radius: {SEARCH_RADIUS_KM}km")
        logger.info(f"Polling interval: {POLLING_INTERVAL}s")
        
        while self.is_polling:
            try:
                # Build search area
                bbox = build_bounding_box(HOME_LAT, HOME_LON)
                logger.debug(f"Built bounding box: {bbox}")
                
                # Fetch aircraft data
                logger.info("Fetching aircraft data from OpenSky...")
                all_aircraft = fetch_state_vectors(bbox)
                logger.info(f"Received {len(all_aircraft)} aircraft from API")
                
                if all_aircraft:
                    logger.debug(f"Processing {len(all_aircraft)} aircraft")
                    
                    # Filter aircraft
                    filtered = filter_aircraft(all_aircraft)
                    logger.info(f"Filtered to {len(filtered)} aircraft within criteria")
                    
                    # Log first-time spotted aircraft
                    for aircraft in filtered:
                        icao = aircraft['icao24']
                        if icao not in self.spotted_aircraft:
                            self.spotted_aircraft.add(icao)
                            logger.info(f"FIRST SPOTTED: {icao} (callsign: {aircraft.get('callsign', 'N/A')}) "
                                      f"at {aircraft['distance_km']:.1f}km, altitude: {aircraft['baro_altitude']}m")
                    
                    # Find visible aircraft
                    visible = [a for a in filtered if is_visible(a)]
                    logger.info(f"Found {len(visible)} visible aircraft (elevation > {MIN_ELEVATION_ANGLE}°)")
                    
                    # Log first-time visible aircraft
                    for aircraft in visible:
                        icao = aircraft['icao24']
                        if icao not in self.visible_aircraft:
                            self.visible_aircraft.add(icao)
                            logger.info(f"FIRST VISIBLE: {icao} (callsign: {aircraft.get('callsign', 'N/A')}) "
                                      f"at {aircraft['distance_km']:.1f}km, elevation: {aircraft['elevation_angle']:.1f}°")
                    
                    # Send list of all approaching aircraft for dashboard
                    if filtered:
                        list_message = self.format_aircraft_list_message(filtered)
                        await self.broadcast_message(list_message)
                        logger.debug(f"Sent approaching aircraft list: {list_message['aircraft_count']} planes")
                    
                    # Select best aircraft for main display
                    best_aircraft = select_best_plane(visible)
                    
                    if best_aircraft:
                        # Format message with all visible aircraft
                        message = self.format_aircraft_message(best_aircraft)
                        
                        # Add all visible aircraft to the message
                        all_visible_formatted = []
                        for aircraft in visible:
                            formatted = self.format_aircraft_message(aircraft)
                            all_visible_formatted.append(formatted)
                        
                        # Sort by distance
                        all_visible_formatted.sort(key=lambda x: x['distance_km'])
                        
                        # Update message to include all aircraft
                        message['type'] = 'aircraft_update'
                        message['closest'] = message.copy()
                        message['all_aircraft'] = all_visible_formatted
                        
                        await self.broadcast_message(message)
                        
                        # Log event
                        logger.info(f"Sent aircraft update: {best_aircraft['icao24']} "
                                  f"at {best_aircraft['distance_km']:.1f}km, "
                                  f"{best_aircraft['elevation_angle']:.1f}° elevation "
                                  f"(total visible: {len(visible)})")
                        
                        # Store last aircraft data
                        self.last_aircraft_data = message
                    else:
                        # Send "no aircraft" message if we previously had one
                        if self.last_aircraft_data:
                            no_aircraft_msg = {
                                'type': 'no_aircraft',
                                'timestamp': datetime.utcnow().isoformat()
                            }
                            await self.broadcast_message(no_aircraft_msg)
                            self.last_aircraft_data = None
                            logger.info("No visible aircraft")
                
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
            
            # Wait for next polling interval
            await asyncio.sleep(POLLING_INTERVAL)
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """
        Handle a new WebSocket client connection.
        
        Args:
            websocket: WebSocket connection
            path: Request path
        """
        try:
            client_address = getattr(websocket, 'remote_address', 'unknown')
        except:
            client_address = 'unknown'
        logger.info(f"New client connected from {client_address}")
        
        # Add to connected clients
        self.connected_clients.add(websocket)
        
        # Send welcome message
        welcome_msg = {
            'type': 'welcome',
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Connected to Brum Brum Tracker'
        }
        await websocket.send(json.dumps(welcome_msg))
        
        # Send last aircraft data if available, otherwise send searching message
        if self.last_aircraft_data:
            await websocket.send(json.dumps(self.last_aircraft_data))
        else:
            # Send initial searching message
            searching_msg = {
                'type': 'searching',
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'Searching for aircraft...'
            }
            await websocket.send(json.dumps(searching_msg))
        
        # Start polling if this is the first client
        if len(self.connected_clients) == 1 and not self.is_polling:
            self.is_polling = True
            self.polling_task = asyncio.create_task(self.polling_loop())
        
        try:
            # Keep connection alive and handle messages
            async for message in websocket:
                # Handle client messages if needed (e.g., configuration)
                try:
                    data = json.loads(message)
                    logger.debug(f"Received from client: {data}")
                    
                    # Echo back for now
                    await websocket.send(json.dumps({
                        'type': 'echo',
                        'data': data
                    }))
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_address} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            # Remove from connected clients
            self.connected_clients.discard(websocket)
            
            # Stop polling if no clients remain
            if not self.connected_clients and self.is_polling:
                self.is_polling = False
                if self.polling_task:
                    self.polling_task.cancel()
                    try:
                        await self.polling_task
                    except asyncio.CancelledError:
                        pass
                logger.info("Stopped polling - no clients connected")


# Global tracker instance
tracker = AircraftTracker()


async def websocket_handler(websocket):
    """WebSocket connection handler."""
    # Extract path from websocket.path if needed
    path = getattr(websocket, 'path', '/')
    await tracker.handle_client(websocket, path)




async def main():
    """Main server entry point."""
    logger.info(f"Starting WebSocket server on {WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    
    # Start WebSocket server with additional parameters for better compatibility
    async with websockets.serve(
        websocket_handler,
        WEBSOCKET_HOST,
        WEBSOCKET_PORT,
        # Additional parameters for better connection handling
        compression=None,  # Disable compression for better compatibility
        max_size=10 * 1024 * 1024,  # 10MB max message size
        ping_interval=20,  # Send ping every 20 seconds
        ping_timeout=10,  # Wait 10 seconds for pong
        close_timeout=10,  # Wait 10 seconds for close
    ):
        logger.info(f"Server running at ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}/ws")
        logger.info("WebSocket parameters: compression=None, ping_interval=20s")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")