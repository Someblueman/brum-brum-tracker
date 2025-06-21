#!/usr/bin/env python3
"""
Visual test server - Sends mock aircraft data to test frontend visuals
"""

import asyncio
import json
import math
import time
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol
from typing import Set

# Test configuration
WEBSOCKET_HOST = '0.0.0.0'
WEBSOCKET_PORT = 8000
UPDATE_INTERVAL = 2  # Send updates every 2 seconds

class MockAircraftServer:
    """Test server that sends simulated aircraft data."""
    
    def __init__(self):
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.time_offset = 0
    
    def generate_mock_aircraft(self, time_offset: float):
        """
        Generate mock aircraft data that moves in a circle around the observer.
        
        Args:
            time_offset: Time offset for animation (seconds)
            
        Returns:
            Mock aircraft data dictionary
        """
        # Create a circular flight path
        angle_rad = (time_offset * 0.1) % (2 * math.pi)  # Complete circle every ~63 seconds
        
        # Calculate bearing (0-360 degrees where 0 is North)
        bearing = math.degrees(angle_rad)
        
        # Simulate changing distance (20-50 km)
        distance = 35 + 15 * math.sin(time_offset * 0.05)
        
        # Simulate changing altitude (5000-10000 meters)
        altitude_m = 7500 + 2500 * math.cos(time_offset * 0.03)
        altitude_ft = altitude_m * 3.28084
        
        # Calculate elevation angle
        distance_m = distance * 1000
        elevation_angle = math.degrees(math.atan(altitude_m / distance_m))
        
        # Simulate speed variation
        speed_kmh = 800 + 100 * math.sin(time_offset * 0.07)
        
        aircraft_data = {
            'type': 'aircraft_update',
            'timestamp': datetime.utcnow().isoformat(),
            'icao24': 'TEST123',
            'callsign': 'BRUM001',
            'bearing': round(bearing, 1),
            'distance_km': round(distance, 1),
            'altitude_ft': round(altitude_ft),
            'speed_kmh': round(speed_kmh),
            'elevation_angle': round(elevation_angle, 1),
            'aircraft_type': 'Boeing 737-800',
            'image_url': 'https://cdn.jetphotos.com/400/6/83701_1583340880.jpg'  # Sample aircraft image
        }
        
        return aircraft_data
    
    def generate_aircraft_list(self, time_offset: float):
        """
        Generate a list of approaching aircraft for the dashboard.
        
        Args:
            time_offset: Time offset for animation
            
        Returns:
            Mock aircraft list message
        """
        aircraft_list = []
        
        # Generate 5 mock aircraft at different positions
        for i in range(5):
            angle_offset = (2 * math.pi / 5) * i  # Evenly spaced
            angle_rad = (time_offset * 0.05 + angle_offset) % (2 * math.pi)
            
            bearing = math.degrees(angle_rad)
            distance = 20 + i * 15  # Different distances
            speed_kmh = 700 + i * 50
            
            # Calculate mock ETA
            eta_hours = distance / speed_kmh
            eta_seconds = eta_hours * 3600
            
            aircraft_list.append({
                'icao24': f'TEST{i:03d}',
                'callsign': f'BRUM{i:03d}',
                'bearing': round(bearing, 1),
                'distance_km': round(distance, 1),
                'altitude_ft': 25000 + i * 2000,
                'speed_kmh': round(speed_kmh),
                'eta_seconds': round(eta_seconds),
                'eta_minutes': round(eta_seconds / 60, 1),
                'aircraft_type': ['Boeing 737', 'Airbus A320', 'Boeing 777', 'Airbus A350', 'Boeing 787'][i]
            })
        
        message = {
            'type': 'approaching_aircraft_list',
            'timestamp': datetime.utcnow().isoformat(),
            'aircraft_count': len(aircraft_list),
            'aircraft': aircraft_list
        }
        
        return message
    
    async def broadcast_message(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.connected_clients:
            return
        
        message_json = json.dumps(message)
        
        # Send to all clients
        disconnected = set()
        for client in self.connected_clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected
    
    async def test_loop(self):
        """Main test loop that sends mock data."""
        print("Starting mock aircraft data loop...")
        
        while True:
            if self.connected_clients:
                # Send main aircraft update
                aircraft_data = self.generate_mock_aircraft(self.time_offset)
                await self.broadcast_message(aircraft_data)
                
                print(f"Sent aircraft at bearing {aircraft_data['bearing']:.0f}°, "
                      f"distance {aircraft_data['distance_km']:.1f}km, "
                      f"elevation {aircraft_data['elevation_angle']:.1f}°")
                
                # Every 3rd update, also send the aircraft list
                if int(self.time_offset) % 6 == 0:
                    list_data = self.generate_aircraft_list(self.time_offset)
                    await self.broadcast_message(list_data)
                    print(f"Sent list of {list_data['aircraft_count']} approaching aircraft")
            
            self.time_offset += UPDATE_INTERVAL
            await asyncio.sleep(UPDATE_INTERVAL)
    
    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Handle a new WebSocket client connection."""
        client_address = websocket.remote_address
        print(f"New client connected from {client_address}")
        
        # Add to connected clients
        self.connected_clients.add(websocket)
        
        # Send welcome message
        welcome_msg = {
            'type': 'welcome',
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Connected to Brum Brum Tracker (Test Mode)'
        }
        await websocket.send(json.dumps(welcome_msg))
        
        # Send initial aircraft data
        aircraft_data = self.generate_mock_aircraft(self.time_offset)
        await websocket.send(json.dumps(aircraft_data))
        
        try:
            # Keep connection alive
            async for message in websocket:
                # Echo any messages back (for testing)
                data = json.loads(message)
                print(f"Received from client: {data}")
                
        except websockets.exceptions.ConnectionClosed:
            print(f"Client {client_address} disconnected")
        finally:
            self.connected_clients.discard(websocket)


async def main():
    """Main entry point."""
    server = MockAircraftServer()
    
    # Start the test loop
    test_task = asyncio.create_task(server.test_loop())
    
    # Start WebSocket server
    print(f"Starting mock WebSocket server on ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    print("This will send rotating aircraft data for visual testing")
    print("Open the frontend in a browser to see the aircraft moving in a circle")
    print("-" * 60)
    
    async with websockets.serve(server.handle_client, WEBSOCKET_HOST, WEBSOCKET_PORT):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down test server...")