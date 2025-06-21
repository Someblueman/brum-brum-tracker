#!/usr/bin/env python3
"""
Interactive visual test - Control aircraft position with keyboard
"""

import asyncio
import json
import math
import sys
import termios
import tty
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol
from typing import Set, Optional
import threading
import select

# Test configuration
WEBSOCKET_HOST = '0.0.0.0'
WEBSOCKET_PORT = 8000

class InteractiveAircraftServer:
    """Interactive test server where you can control the aircraft."""
    
    def __init__(self):
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.bearing = 0.0  # North
        self.distance = 30.0  # km
        self.altitude = 8000.0  # meters
        self.speed = 850.0  # km/h
        self.running = True
        
    def calculate_elevation(self):
        """Calculate elevation angle based on distance and altitude."""
        distance_m = self.distance * 1000
        return math.degrees(math.atan(self.altitude / distance_m))
    
    def generate_aircraft_data(self):
        """Generate aircraft data based on current position."""
        elevation = self.calculate_elevation()
        
        return {
            'type': 'aircraft_update',
            'timestamp': datetime.utcnow().isoformat(),
            'icao24': 'INTER01',
            'callsign': 'TEST123',
            'bearing': round(self.bearing, 1),
            'distance_km': round(self.distance, 1),
            'altitude_ft': round(self.altitude * 3.28084),
            'speed_kmh': round(self.speed),
            'elevation_angle': round(elevation, 1),
            'aircraft_type': 'Test Aircraft',
            'image_url': 'https://cdn.jetphotos.com/400/6/83701_1583340880.jpg'
        }
    
    async def broadcast_update(self):
        """Broadcast current aircraft position to all clients."""
        if not self.connected_clients:
            return
        
        message = self.generate_aircraft_data()
        message_json = json.dumps(message)
        
        disconnected = set()
        for client in self.connected_clients:
            try:
                await client.send(message_json)
            except:
                disconnected.add(client)
        
        self.connected_clients -= disconnected
    
    def print_status(self):
        """Print current aircraft status."""
        elevation = self.calculate_elevation()
        print(f"\rBearing: {self.bearing:6.1f}° | Distance: {self.distance:5.1f}km | "
              f"Altitude: {self.altitude:6.0f}m | Elevation: {elevation:5.1f}° | "
              f"Clients: {len(self.connected_clients)}", end='', flush=True)
    
    async def control_loop(self):
        """Handle keyboard input for controlling the aircraft."""
        print("\nInteractive Aircraft Control:")
        print("-" * 60)
        print("Arrow Keys: LEFT/RIGHT = Change bearing (±5°)")
        print("            UP/DOWN = Change distance (±2km)")
        print("Page Up/Down: Change altitude (±500m)")
        print("Q: Quit")
        print("-" * 60)
        print()
        
        # Set terminal to raw mode for immediate key response
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            
            while self.running:
                # Check if key is available
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    
                    if key == '\x1b':  # ESC sequence
                        seq = sys.stdin.read(2)
                        if seq == '[A':  # Up arrow - decrease distance
                            self.distance = max(5, self.distance - 2)
                        elif seq == '[B':  # Down arrow - increase distance
                            self.distance = min(100, self.distance + 2)
                        elif seq == '[C':  # Right arrow - increase bearing
                            self.bearing = (self.bearing + 5) % 360
                        elif seq == '[D':  # Left arrow - decrease bearing
                            self.bearing = (self.bearing - 5) % 360
                        elif seq == '[5':  # Page Up
                            sys.stdin.read(1)  # consume ~
                            self.altitude = min(15000, self.altitude + 500)
                        elif seq == '[6':  # Page Down
                            sys.stdin.read(1)  # consume ~
                            self.altitude = max(1000, self.altitude - 500)
                    
                    elif key.lower() == 'q':
                        self.running = False
                        break
                
                # Update display and broadcast
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                self.print_status()
                await self.broadcast_update()
                tty.setraw(sys.stdin.fileno())
                
                await asyncio.sleep(0.1)
                
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            print("\n\nShutting down...")
    
    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Handle WebSocket client connections."""
        print(f"\nNew client connected from {websocket.remote_address}")
        self.connected_clients.add(websocket)
        
        # Send welcome and initial position
        welcome = {
            'type': 'welcome',
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Connected to Interactive Test Server'
        }
        await websocket.send(json.dumps(welcome))
        await websocket.send(json.dumps(self.generate_aircraft_data()))
        
        try:
            async for message in websocket:
                pass  # Just keep connection alive
        except:
            pass
        finally:
            self.connected_clients.discard(websocket)
            print(f"\nClient disconnected")


async def main():
    """Main entry point."""
    server = InteractiveAircraftServer()
    
    # Start control loop
    control_task = asyncio.create_task(server.control_loop())
    
    # Start WebSocket server
    print(f"Starting interactive WebSocket server on ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    
    try:
        async with websockets.serve(server.handle_client, WEBSOCKET_HOST, WEBSOCKET_PORT):
            await control_task
    except KeyboardInterrupt:
        server.running = False


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")