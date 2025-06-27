"""
WebSocket server for real-time aircraft data streaming with security enhancements.
"""

import asyncio
import json
import logging
import time
import uuid
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
from backend.db import get_aircraft_from_cache, add_to_logbook, get_logbook
from backend.aircraft_data import get_aircraft_data
from backend.aircraft_database import (
    fetch_aircraft_details_from_hexdb,
    fetch_flight_route_from_hexdb,
    fetch_airport_info_from_hexdb
)
from backend.message_validator import MessageValidator, ValidationError, MessageType
from backend.rate_limiter import RateLimiter, RateLimitExceeded, ConnectionThrottler
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
    
    # Check manufacturer first
    for key, friendly_name in type_mappings.items():
        if key in manufacturer or key in type_name:
            return friendly_name
    
    # Try type code mappings (B763 -> Boeing 767, A333 -> Airbus A330)
    if type_name:
        if type_name.startswith('B7'):
            return f"Boeing 7{type_name[2]}{type_name[3] if len(type_name) > 3 else ''}"
        elif type_name.startswith('A3'):
            return f"Airbus A3{type_name[2]}{type_name[3] if len(type_name) > 3 else ''}"
        elif type_name.startswith('B73'):
            return "Boeing 737"
        elif type_name.startswith('B74'):
            return "Boeing 747 Jumbo Jet"
        elif type_name.startswith('B77'):
            return "Boeing 777"
        elif type_name.startswith('B78'):
            return "Boeing 787 Dreamliner"
        elif type_name.startswith('A32'):
            return f"Airbus A32{type_name[3] if len(type_name) > 3 else '0'}"
        elif type_name.startswith('A38'):
            return "Airbus A380 Super Jumbo"
        elif type_name.startswith('A35'):
            return "Airbus A350"
        elif type_name.startswith('E1'):
            return f"Embraer E1{type_name[2:]}" if len(type_name) > 2 else "Embraer Jet"
        elif type_name.startswith('CRJ'):
            return "Bombardier CRJ"
        elif type_name.startswith('DH8'):
            return "Bombardier Dash 8"
        elif type_name.startswith('AT'):
            return "ATR Propeller Plane"
    
    # Fallback to manufacturer if available
    if manufacturer:
        return manufacturer
    
    # Final fallback
    return type_name or "Unknown Aircraft"


class SecureWebSocketServer:
    """WebSocket server with enhanced security features."""
    
    def __init__(self):
        """Initialize the WebSocket server."""
        self.clients: Set[WebSocketServerProtocol] = set()
        self.selected_plane: Optional[Dict[str, Any]] = None
        self.last_update_time: float = 0
        self.tracking_task: Optional[asyncio.Task] = None
        self.tracked_aircraft: Set[str] = set()
        self.connection_info: Dict[str, Dict[str, Any]] = {}
        
        # Initialize security components
        self.rate_limiter = RateLimiter()
        self.api_throttler = ConnectionThrottler(requests_per_minute=60)
        self.validator = MessageValidator()
    
    async def start(self):
        """Start the rate limiter cleanup task."""
        await self.rate_limiter.start()
    
    async def stop(self):
        """Stop the rate limiter cleanup task."""
        await self.rate_limiter.stop()
    
    def get_client_ip(self, websocket: WebSocketServerProtocol) -> str:
        """Extract client IP address from websocket connection."""
        if hasattr(websocket, 'remote_address'):
            return websocket.remote_address[0]
        return "unknown"
    
    async def register(self, websocket: WebSocketServerProtocol):
        """
        Register a new WebSocket client with rate limiting.
        
        Args:
            websocket: The WebSocket connection
        """
        client_ip = self.get_client_ip(websocket)
        connection_id = str(uuid.uuid4())
        
        try:
            # Check rate limit
            self.rate_limiter.check_connection_allowed(client_ip)
            
            # Register the client
            self.clients.add(websocket)
            self.connection_info[connection_id] = {
                "websocket": websocket,
                "ip": client_ip,
                "connected_at": datetime.now(),
                "message_count": 0
            }
            
            # Store connection ID for later use
            websocket.connection_id = connection_id
            
            logger.info(f"Client connected from {client_ip} (ID: {connection_id})")
            logger.info(f"Total clients: {len(self.clients)}")
            
            # Start tracking if this is the first client
            if len(self.clients) == 1:
                await self.start_tracking()
            
            # Send current aircraft if any
            if self.selected_plane:
                message = {
                    "type": MessageType.AIRCRAFT_UPDATE.value,
                    **self.selected_plane
                }
                try:
                    validated_message = self.validator.validate_server_message(message)
                    await websocket.send(json.dumps(validated_message))
                except ValidationError as e:
                    logger.error(f"Failed to validate initial aircraft message: {e}")
                    
        except RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded for {client_ip}: {e}")
            await websocket.close(code=1008, reason="Rate limit exceeded")
            return
    
    async def unregister(self, websocket: WebSocketServerProtocol):
        """
        Unregister a WebSocket client.
        
        Args:
            websocket: The WebSocket connection
        """
        if websocket in self.clients:
            self.clients.remove(websocket)
            
            # Clean up connection info
            connection_id = getattr(websocket, 'connection_id', None)
            if connection_id:
                client_ip = self.connection_info.get(connection_id, {}).get("ip", "unknown")
                self.rate_limiter.connection_closed(client_ip, connection_id)
                del self.connection_info[connection_id]
            
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
            
            # Stop tracking if no clients remain
            if len(self.clients) == 0:
                await self.stop_tracking()
    
    async def send_to_all(self, message: Dict[str, Any]):
        """
        Send a message to all connected clients with validation.
        
        Args:
            message: The message dictionary to send
        """
        if not self.clients:
            return
        
        try:
            # Validate message before sending
            validated_message = self.validator.validate_server_message(message)
            message_json = json.dumps(validated_message)
            
            # Send to all clients
            disconnected_clients = []
            for client in self.clients:
                try:
                    await client.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.append(client)
                except Exception as e:
                    logger.error(f"Error sending to client: {e}")
                    disconnected_clients.append(client)
            
            # Clean up disconnected clients
            for client in disconnected_clients:
                await self.unregister(client)
                
        except ValidationError as e:
            logger.error(f"Failed to validate message: {e}")
    
    async def handle_client_message(self, websocket: WebSocketServerProtocol, message: str):
        """
        Handle messages from clients with validation and rate limiting.
        
        Args:
            websocket: The WebSocket connection
            message: The raw message string
        """
        connection_id = getattr(websocket, 'connection_id', None)
        if not connection_id:
            return
        
        try:
            # Check message rate limit
            self.rate_limiter.check_message_allowed(connection_id)
            
            # Validate and parse message
            data = self.validator.validate_client_message(message)
            
            # Update message count
            self.connection_info[connection_id]["message_count"] += 1
            
            # Handle different message types
            if data["type"] == MessageType.CLIENT_HELLO.value:
                logger.info(f"Received hello from client {connection_id}")
                
            elif data["type"] == MessageType.GET_LOGBOOK.value:
                limit = data.get("limit", 100)
                try:
                    entries = get_logbook(limit=limit)
                    response = {
                        "type": MessageType.LOGBOOK_DATA.value,
                        "entries": entries
                    }
                    validated_response = self.validator.validate_server_message(response)
                    await websocket.send(json.dumps(validated_response))
                except Exception as e:
                    logger.error(f"Error fetching logbook: {e}")
                    error_response = {
                        "type": MessageType.ERROR.value,
                        "error": "Failed to fetch logbook"
                    }
                    await websocket.send(json.dumps(error_response))
                    
        except RateLimitExceeded as e:
            logger.warning(f"Message rate limit exceeded for {connection_id}: {e}")
            error_response = {
                "type": MessageType.ERROR.value,
                "error": "Rate limit exceeded. Please slow down."
            }
            await websocket.send(json.dumps(error_response))
            
        except ValidationError as e:
            logger.warning(f"Invalid message from {connection_id}: {e}")
            error_response = {
                "type": MessageType.ERROR.value,
                "error": f"Invalid message: {str(e)}"
            }
            await websocket.send(json.dumps(error_response))
    
    async def start_tracking(self):
        """Start the aircraft tracking task."""
        if not self.tracking_task:
            self.tracking_task = asyncio.create_task(self.track_aircraft())
            logger.info("Started aircraft tracking")
    
    async def stop_tracking(self):
        """Stop the aircraft tracking task."""
        if self.tracking_task:
            self.tracking_task.cancel()
            try:
                await self.tracking_task
            except asyncio.CancelledError:
                pass
            self.tracking_task = None
            self.selected_plane = None
            self.tracked_aircraft.clear()
            logger.info("Stopped aircraft tracking")
    
    async def track_aircraft(self):
        """Main aircraft tracking loop with error handling."""
        bbox = build_bounding_box(HOME_LAT, HOME_LON, SEARCH_RADIUS_KM)
        
        while True:
            try:
                # Throttle API requests
                await self.api_throttler.acquire()
                
                # Fetch aircraft data with error handling
                try:
                    states, raw_aircraft = await fetch_state_vectors(bbox)
                except Exception as e:
                    logger.error(f"Error fetching aircraft data: {e}")
                    await asyncio.sleep(POLLING_INTERVAL)
                    continue
                
                if states:
                    logger.info(f"Received {len(raw_aircraft)} aircraft from API")
                    
                    # Filter for visible aircraft
                    visible_aircraft = []
                    for aircraft in raw_aircraft:
                        try:
                            if is_visible(aircraft, HOME_LAT, HOME_LON, MIN_ELEVATION_ANGLE):
                                visible_aircraft.append(aircraft)
                        except Exception as e:
                            logger.error(f"Error checking visibility for aircraft: {e}")
                    
                    if visible_aircraft:
                        # Select best aircraft
                        try:
                            best_aircraft = select_best_plane(visible_aircraft, HOME_LAT, HOME_LON)
                            
                            if best_aircraft:
                                await self.process_aircraft(best_aircraft)
                        except Exception as e:
                            logger.error(f"Error selecting best aircraft: {e}")
                
                await asyncio.sleep(POLLING_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Aircraft tracking cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in tracking loop: {e}", exc_info=True)
                await asyncio.sleep(POLLING_INTERVAL)
    
    async def process_aircraft(self, aircraft: Dict[str, Any]):
        """Process and send aircraft data to clients."""
        icao24 = aircraft.get('icao24', '').strip()
        
        if not icao24:
            return
        
        # Check if this is a new aircraft
        is_new_aircraft = icao24 not in self.tracked_aircraft
        
        if is_new_aircraft:
            self.tracked_aircraft.add(icao24)
            
            # Get aircraft details with error handling
            try:
                cached_data = get_aircraft_from_cache(icao24)
                
                if not cached_data:
                    # Fetch from external sources
                    aircraft_info = await get_aircraft_data(icao24)
                    if aircraft_info:
                        aircraft.update(aircraft_info)
                else:
                    aircraft.update(cached_data)
                    
            except Exception as e:
                logger.error(f"Error fetching aircraft data for {icao24}: {e}")
        
        # Prepare message
        aircraft_type_raw = aircraft.get('aircraft_type', 'Unknown')
        manufacturer = aircraft.get('manufacturer', '')
        aircraft_type = simplify_aircraft_type(manufacturer, aircraft_type_raw)
        
        # Sanitize data before sending
        message_data = {
            "callsign": aircraft.get('callsign', icao24),
            "distance": round(aircraft.get('distance', 0), 1),
            "altitude": round(aircraft.get('altitude', 0)),
            "speed": round(aircraft.get('speed', 0)),
            "bearing": round(aircraft.get('bearing', 0)),
            "elevation": round(aircraft.get('elevation', 0), 1),
            "track": aircraft.get('track', 0),
            "image_url": aircraft.get('image_url'),
            "aircraft_type": aircraft_type,
            "aircraft_type_raw": aircraft_type_raw,
            "latitude": aircraft.get('latitude'),
            "longitude": aircraft.get('longitude')
        }
        
        # Sanitize string fields
        sanitized_data = self.validator.sanitize_aircraft_data(message_data)
        
        # Store for new clients
        self.selected_plane = sanitized_data
        self.last_update_time = time.time()
        
        # Send to all clients
        message = {
            "type": MessageType.AIRCRAFT_UPDATE.value,
            **sanitized_data
        }
        await self.send_to_all(message)
        
        # Add to logbook if new
        if is_new_aircraft and aircraft.get('image_url'):
            try:
                add_to_logbook(aircraft_type, aircraft.get('image_url'))
            except Exception as e:
                logger.error(f"Error adding to logbook: {e}")


# WebSocket handler
async def handle_websocket(websocket: WebSocketServerProtocol, path: str, server: SecureWebSocketServer):
    """
    Handle individual WebSocket connections.
    
    Args:
        websocket: The WebSocket connection
        path: The request path
        server: The WebSocket server instance
    """
    await server.register(websocket)
    
    try:
        async for message in websocket:
            await server.handle_client_message(websocket, message)
    except websockets.exceptions.ConnectionClosed:
        logger.info("Client connection closed")
    except Exception as e:
        logger.error(f"Error handling client: {e}", exc_info=True)
    finally:
        await server.unregister(websocket)


async def main():
    """Main entry point for the secure WebSocket server."""
    server = SecureWebSocketServer()
    
    # Start server components
    await server.start()
    
    try:
        # Start WebSocket server
        async with websockets.serve(
            lambda ws, path: handle_websocket(ws, path, server),
            WEBSOCKET_HOST,
            WEBSOCKET_PORT
        ):
            logger.info(f"Secure WebSocket server started on ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
            await asyncio.Future()  # Run forever
    finally:
        # Cleanup
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())