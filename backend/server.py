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
from backend.db import get_aircraft_from_cache, add_to_logbook, get_logbook
from backend.aircraft_data import get_aircraft_data
from backend.aircraft_database import (
    fetch_flight_route_from_hexdb,
    fetch_airport_info_from_hexdb
)
from backend.aircraft_type_resolver import resolve_aircraft_type
from backend.auth import require_auth
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


# Moved to aircraft_type_resolver.py


class AircraftTracker:
    """Manages aircraft tracking and WebSocket connections."""
    
    def __init__(self):
        """Initialize the tracker."""
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.last_aircraft_data: Optional[Dict[str, Any]] = None
        self.is_polling = False
        # Use dict with timestamps to track aircraft and enable cleanup
        self.spotted_aircraft: Dict[str, float] = {}  # icao24 -> first_seen_timestamp
        self.visible_aircraft: Dict[str, float] = {}  # icao24 -> last_seen_timestamp
        self.polling_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        # Cleanup old entries every hour
        self.MAX_TRACKING_AGE_HOURS = 24  # Keep aircraft data for 24 hours
        self.CLEANUP_INTERVAL_SECONDS = 3600  # Run cleanup every hour
    
    def format_aircraft_message(self, aircraft: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format aircraft data for frontend consumption, including details from hexdb.
        """
        icao24 = aircraft['icao24']
        callsign = aircraft.get('callsign', '')

        # 1. Get Aircraft Type using resolver with multiple fallbacks
        # Priority: Cache -> Hexdb -> Planespotters -> Unknown
        aircraft_type = resolve_aircraft_type(icao24)

        # 2. Get Image Data (uses existing logic)
        media_data = get_aircraft_data(icao24)

        # 3. Get Route Information from hexdb
        origin_info = None
        destination_info = None
        flight_route = fetch_flight_route_from_hexdb(callsign)
        if flight_route and 'route' in flight_route:
            route_parts = flight_route['route'].split('-')
            if len(route_parts) == 2:
                origin_icao, dest_icao = route_parts
                origin_info = fetch_airport_info_from_hexdb(origin_icao)
                destination_info = fetch_airport_info_from_hexdb(dest_icao)

        # 4. Format the final message for the frontend
        altitude_ft = aircraft['baro_altitude'] * 3.28084 if aircraft['baro_altitude'] else 0
        speed_kmh = aircraft['velocity'] * 3.6 if aircraft['velocity'] else 0
        
        message = {
            'type': 'aircraft_update',
            'timestamp': datetime.utcnow().isoformat(),
            'icao24': icao24,
            'callsign': callsign,
            'bearing': round(aircraft['bearing_from_home'], 1),
            'distance_km': round(aircraft['distance_km'], 1),
            'altitude_ft': round(altitude_ft),
            'speed_kmh': round(speed_kmh),
            'elevation_angle': round(aircraft['elevation_angle'], 1),
            'aircraft_type': aircraft_type,
            'image_url': media_data.get('image_url', ''),
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

                    # Get Aircraft Type using resolver
                    icao24 = aircraft['icao24']
                    aircraft_type = resolve_aircraft_type(icao24)

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
                        'aircraft_type': aircraft_type, # Use the new aircraft_type
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
    
    def cleanup_old_aircraft(self) -> None:
        """Remove old aircraft entries to prevent memory leaks."""
        current_time = time.time()
        max_age_seconds = self.MAX_TRACKING_AGE_HOURS * 3600
        
        # Clean spotted aircraft
        old_spotted = [icao for icao, timestamp in self.spotted_aircraft.items() 
                      if current_time - timestamp > max_age_seconds]
        for icao in old_spotted:
            del self.spotted_aircraft[icao]
        
        # Clean visible aircraft
        old_visible = [icao for icao, timestamp in self.visible_aircraft.items() 
                      if current_time - timestamp > max_age_seconds]
        for icao in old_visible:
            del self.visible_aircraft[icao]
        
        if old_spotted or old_visible:
            logger.info(f"Cleaned up {len(old_spotted)} spotted and {len(old_visible)} visible aircraft entries")
    
    async def periodic_cleanup(self) -> None:
        """Periodically clean up old aircraft entries."""
        while self.is_polling:
            await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
            self.cleanup_old_aircraft()
    
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
                    current_time = time.time()
                    for aircraft in filtered:
                        icao = aircraft['icao24']
                        if icao not in self.spotted_aircraft:
                            self.spotted_aircraft[icao] = current_time
                            logger.info(f"FIRST SPOTTED: {icao} (callsign: {aircraft.get('callsign', 'N/A')}) "
                                      f"at {aircraft['distance_km']:.1f}km, altitude: {aircraft['baro_altitude']}m")
                    
                    # Find visible aircraft
                    visible = [a for a in filtered if is_visible(a)]
                    logger.info(f"Found {len(visible)} visible aircraft (elevation > {MIN_ELEVATION_ANGLE}°)")
                    
                    # Log first-time visible aircraft
                    for aircraft in visible:
                        icao = aircraft['icao24']
                        if icao not in self.visible_aircraft:
                            self.visible_aircraft[icao] = current_time
                            # Get formatted data to log
                            formatted_plane = self.format_aircraft_message(aircraft)
                            plane_type = formatted_plane['aircraft_type']
                            image_url = formatted_plane['image_url']
                            
                            add_to_logbook(plane_type, image_url)

                            logger.info(f"FIRST VISIBLE & LOGGED: {icao} ({plane_type}) "
                                      f"at {aircraft['distance_km']:.1f}km, elevation: {aircraft['elevation_angle']:.1f}°")
                    
                    # Send list of all approaching aircraft for dashboard
                    if filtered:
                        list_message = self.format_aircraft_list_message(filtered)
                        await self.broadcast_message(list_message)
                        logger.debug(f"Sent approaching aircraft list: {list_message['aircraft_count']} planes")
                    
                    if visible:
                        # Format all visible planes
                        all_visible_formatted = [self.format_aircraft_message(a) for a in visible]
                        
                        # Sort them by distance to find the closest
                        all_visible_formatted.sort(key=lambda x: x['distance_km'])
                        
                        # The closest plane is now always the first in the list.
                        # We send the whole list, and the frontend will know what to do.
                        message = {
                            'type': 'aircraft_update',
                            'all_aircraft': all_visible_formatted
                        }
                        await self.broadcast_message(message)
                        
                        # Log the event with the new primary aircraft
                        closest_plane = all_visible_formatted[0]
                        logger.info(f"Sent aircraft update, closest is: {closest_plane['icao24']} "
                                  f"at {closest_plane['distance_km']:.1f}km")
                        
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
    
    @require_auth
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
            self.cleanup_task = asyncio.create_task(self.periodic_cleanup())
        
        try:
            # Keep connection alive and handle messages
            async for message in websocket:
                # Handle client messages if needed (e.g., configuration)
                try:
                    data = json.loads(message)
                    logger.debug(f"Received from client: {data}")
                    
                    # Handle batched messages
                    if data.get('type') == 'batch':
                        messages = data.get('messages', [])
                        logger.debug(f"Received batch of {len(messages)} messages")
                        for msg in messages:
                            await self._handle_single_message(websocket, msg)
                    else:
                        await self._handle_single_message(websocket, data)
                    
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
                if self.cleanup_task:
                    self.cleanup_task.cancel()
                    try:
                        await self.cleanup_task
                    except asyncio.CancelledError:
                        pass
                logger.info("Stopped polling and cleanup - no clients connected")
    
    async def _handle_single_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle a single message from the client."""
        if data.get('type') == 'get_logbook':
            since = data.get('since') if data.get('since') else None
            log_data = get_logbook(since=since) # Pass it to the get_logbook function
            response = {
                'type': 'logbook_data',
                'log': log_data
            }
            await websocket.send(json.dumps(response))
        elif data.get('type') == 'get_config':
            # Send configuration to frontend
            config_response = {
                'type': 'config',
                'config': {
                    'home': {
                        'lat': HOME_LAT,
                        'lon': HOME_LON
                    },
                    'search': {
                        'radiusKm': SEARCH_RADIUS_KM,
                        'minElevationAngle': MIN_ELEVATION_ANGLE
                    }
                }
            }
            await websocket.send(json.dumps(config_response))
        else:
            # Echo back other messages for now
            await websocket.send(json.dumps({
                'type': 'echo',
                'data': data
            }))


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