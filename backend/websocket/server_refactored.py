"""
Refactored WebSocket server using service layer architecture.
"""

import asyncio
import json
import logging
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol
from datetime import datetime

from backend.core.aircraft_service import AircraftService
from backend.core.logbook_service import LogbookService
from backend.api.opensky_client import select_best_plane
from utils.constants import (
    WEBSOCKET_HOST,
    WEBSOCKET_PORT,
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
    """Main WebSocket server class using service layer."""
    
    def __init__(self):
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.is_polling = False
        self.polling_task = None
        self.last_aircraft_data = None
        
        # Initialize services
        self.aircraft_service = AircraftService()
        self.logbook_service = LogbookService()
    
    async def polling_loop(self) -> None:
        """
        Main polling loop to fetch and broadcast aircraft data.
        """
        logger.info("Starting polling loop")
        
        while self.is_polling and self.connected_clients:
            try:
                # Fetch aircraft data
                visible_aircraft = await self.aircraft_service.fetch_aircraft_data()
                
                if visible_aircraft:
                    # Select best aircraft
                    best_aircraft = select_best_plane(visible_aircraft)
                    
                    if best_aircraft:
                        # Format aircraft message
                        message = self.aircraft_service.format_aircraft_message(best_aircraft)
                        
                        # Process for logbook
                        self.logbook_service.process_aircraft_for_logbook(
                            best_aircraft['icao24'],
                            message['aircraft_type'],
                            message.get('image_url')
                        )
                        
                        # Store and broadcast
                        self.last_aircraft_data = message
                        await self.broadcast_message(message)
                    else:
                        # Send searching message
                        await self.broadcast_searching_message()
                        self.last_aircraft_data = None
                else:
                    # No visible aircraft
                    await self.broadcast_searching_message()
                    self.last_aircraft_data = None
                
                # Also send dashboard update
                if visible_aircraft:
                    dashboard_message = self.aircraft_service.format_aircraft_list_message(visible_aircraft)
                    await self.broadcast_message(dashboard_message)
                
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
            
            # Wait for next polling interval
            await asyncio.sleep(POLLING_INTERVAL)
    
    async def broadcast_message(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        if not self.connected_clients:
            return
        
        message_json = json.dumps(message)
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
    
    async def broadcast_searching_message(self) -> None:
        """Broadcast a searching message when no aircraft are visible."""
        message = {
            'type': 'searching',
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Searching for aircraft...'
        }
        await self.broadcast_message(message)
    
    async def handle_client_message(self, websocket: WebSocketServerProtocol, message: str) -> None:
        """Handle incoming messages from clients."""
        try:
            data = json.loads(message)
            logger.debug(f"Received from client: {data}")
            
            if data.get('type') == 'get_logbook':
                # Handle logbook request
                since = data.get('since')
                response = self.logbook_service.format_logbook_response(since)
                await websocket.send(json.dumps(response))
            else:
                # Echo back other messages for now
                await websocket.send(json.dumps({
                    'type': 'echo',
                    'data': data
                }))
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client: {message}")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle a new WebSocket client connection."""
        try:
            client_address = getattr(websocket, 'remote_address', 'unknown')
        except:
            client_address = 'unknown'
        
        logger.info(f"New client connected from {client_address}")
        
        # Add to connected clients
        self.connected_clients.add(websocket)
        
        try:
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
            else:
                await self.broadcast_searching_message()
            
            # Start polling if this is the first client
            if len(self.connected_clients) == 1 and not self.is_polling:
                self.is_polling = True
                self.polling_task = asyncio.create_task(self.polling_loop())
            
            # Handle incoming messages
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        
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
    path = getattr(websocket, 'path', '/')
    await tracker.handle_client(websocket, path)


async def main():
    """Main server entry point."""
    logger.info(f"Starting WebSocket server on {WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    
    async with websockets.serve(
        websocket_handler,
        WEBSOCKET_HOST,
        WEBSOCKET_PORT,
        compression=None,
        max_size=10 * 1024 * 1024,
        ping_interval=20,
        ping_timeout=10,
        close_timeout=10,
    ):
        logger.info(f"Server running at ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}/ws")
        logger.info("Using refactored service layer architecture")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")