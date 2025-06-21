"""
WebSocket server for real-time aircraft data streaming.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Set, Dict, Any, Optional
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
from utils.constants import (
    WEBSOCKET_HOST,
    WEBSOCKET_PORT,
    HOME_LAT,
    HOME_LON,
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
logger = logging.getLogger(__name__)


class AircraftTracker:
    """Manages aircraft tracking and WebSocket connections."""
    
    def __init__(self):
        """Initialize the tracker."""
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.last_aircraft_data: Optional[Dict[str, Any]] = None
        self.is_polling = False
        self.polling_task: Optional[asyncio.Task] = None
    
    def format_aircraft_message(self, aircraft: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format aircraft data for frontend consumption.
        
        Args:
            aircraft: Aircraft state dictionary
            
        Returns:
            Formatted message dictionary
        """
        # Get cached image data if available
        cached_data = get_aircraft_from_cache(aircraft['icao24'])
        
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
            'aircraft_type': cached_data['type'] if cached_data else '',
            'image_url': cached_data['image_url'] if cached_data else ''
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
        
        while self.is_polling:
            try:
                # Build search area
                bbox = build_bounding_box(HOME_LAT, HOME_LON)
                
                # Fetch aircraft data
                all_aircraft = fetch_state_vectors(bbox)
                
                if all_aircraft:
                    # Filter aircraft
                    filtered = filter_aircraft(all_aircraft)
                    
                    # Find visible aircraft
                    visible = [a for a in filtered if is_visible(a)]
                    
                    # Select best aircraft
                    best_aircraft = select_best_plane(visible)
                    
                    if best_aircraft:
                        # Format and broadcast message
                        message = self.format_aircraft_message(best_aircraft)
                        await self.broadcast_message(message)
                        
                        # Log event
                        logger.info(f"Sent aircraft update: {best_aircraft['icao24']} "
                                  f"at {best_aircraft['distance_km']:.1f}km, "
                                  f"{best_aircraft['elevation_angle']:.1f}° elevation")
                        
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
        
        # Send last aircraft data if available
        if self.last_aircraft_data:
            await websocket.send(json.dumps(self.last_aircraft_data))
        
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


async def websocket_handler(websocket: WebSocketServerProtocol):
    """WebSocket connection handler."""
    await tracker.handle_client(websocket, "/")


async def main():
    """Main server entry point."""
    logger.info(f"Starting WebSocket server on {WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    
    # Start WebSocket server
    async with websockets.serve(
        websocket_handler,
        WEBSOCKET_HOST,
        WEBSOCKET_PORT
    ):
        logger.info(f"Server running at ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}/ws")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")