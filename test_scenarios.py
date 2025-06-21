#!/usr/bin/env python3
"""
Visual test scenarios - Cycles through different test cases
"""

import asyncio
import json
import math
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol
from typing import Set

WEBSOCKET_HOST = '0.0.0.0'
WEBSOCKET_PORT = 8000

class ScenarioTestServer:
    """Test server that cycles through different visual scenarios."""
    
    def __init__(self):
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.scenario = 0
        self.step = 0
        
        # Define test scenarios
        self.scenarios = [
            {
                'name': 'North to South Flyover',
                'description': 'Aircraft approaches from North, flies overhead',
                'steps': 20,
                'generate': self.north_south_flyover
            },
            {
                'name': 'Circling Pattern',
                'description': 'Aircraft circles at constant distance',
                'steps': 36,
                'generate': self.circling_pattern
            },
            {
                'name': 'Low Pass',
                'description': 'Low altitude pass from East',
                'steps': 15,
                'generate': self.low_pass
            },
            {
                'name': 'High Altitude',
                'description': 'High altitude aircraft barely visible',
                'steps': 10,
                'generate': self.high_altitude
            },
            {
                'name': 'Multiple Aircraft',
                'description': 'Several aircraft in different directions',
                'steps': 20,
                'generate': self.multiple_aircraft
            }
        ]
    
    def north_south_flyover(self, step, total_steps):
        """Aircraft flies from North to South overhead."""
        progress = step / total_steps
        
        # Start 50km North, end 50km South
        distance = 50 - (100 * progress)
        bearing = 0 if distance >= 0 else 180
        distance = abs(distance)
        
        # Peak altitude when overhead
        altitude = 9000 - 3000 * abs(progress - 0.5) * 2
        
        return {
            'bearing': bearing,
            'distance_km': distance,
            'altitude_m': altitude,
            'speed_kmh': 850
        }
    
    def circling_pattern(self, step, total_steps):
        """Aircraft circles at 30km distance."""
        angle = (step / total_steps) * 360
        
        return {
            'bearing': angle,
            'distance_km': 30,
            'altitude_m': 7500,
            'speed_kmh': 750
        }
    
    def low_pass(self, step, total_steps):
        """Low altitude pass from East to West."""
        progress = step / total_steps
        
        # East to West
        bearing = 90 - (180 * progress)
        if bearing < 0:
            bearing += 360
        
        # Closest approach at midpoint
        distance = 20 + 30 * abs(progress - 0.5) * 2
        
        return {
            'bearing': bearing,
            'distance_km': distance,
            'altitude_m': 3000,  # Low altitude
            'speed_kmh': 650
        }
    
    def high_altitude(self, step, total_steps):
        """High altitude aircraft."""
        progress = step / total_steps
        bearing = 45 + (90 * progress)  # NE to SE
        
        return {
            'bearing': bearing,
            'distance_km': 60,
            'altitude_m': 12000,  # High altitude
            'speed_kmh': 950
        }
    
    def multiple_aircraft(self, step, total_steps):
        """Simulate multiple aircraft - returns main aircraft only."""
        # Main aircraft does figure-8 pattern
        t = (step / total_steps) * 2 * math.pi
        
        # Figure-8 in polar coordinates
        r = 30 + 20 * math.sin(2 * t)
        theta = t
        
        bearing = math.degrees(theta) % 360
        
        return {
            'bearing': bearing,
            'distance_km': r,
            'altitude_m': 8000,
            'speed_kmh': 800
        }
    
    def generate_aircraft_data(self):
        """Generate aircraft data for current scenario and step."""
        scenario = self.scenarios[self.scenario]
        params = scenario['generate'](self.step, scenario['steps'])
        
        # Calculate elevation angle
        distance_m = params['distance_km'] * 1000
        elevation = math.degrees(math.atan(params['altitude_m'] / distance_m))
        
        return {
            'type': 'aircraft_update',
            'timestamp': datetime.utcnow().isoformat(),
            'icao24': f'SCEN{self.scenario:02d}',
            'callsign': f'TEST{self.scenario:03d}',
            'bearing': round(params['bearing'], 1),
            'distance_km': round(params['distance_km'], 1),
            'altitude_ft': round(params['altitude_m'] * 3.28084),
            'speed_kmh': round(params['speed_kmh']),
            'elevation_angle': round(elevation, 1),
            'aircraft_type': 'Test Aircraft',
            'image_url': 'https://cdn.jetphotos.com/400/6/83701_1583340880.jpg'
        }
    
    def get_scenario_info(self):
        """Get current scenario information."""
        scenario = self.scenarios[self.scenario]
        return {
            'type': 'scenario_info',
            'timestamp': datetime.utcnow().isoformat(),
            'scenario_num': self.scenario + 1,
            'total_scenarios': len(self.scenarios),
            'name': scenario['name'],
            'description': scenario['description'],
            'step': self.step + 1,
            'total_steps': scenario['steps']
        }
    
    async def broadcast_message(self, message: dict):
        """Broadcast message to all clients."""
        if not self.connected_clients:
            return
        
        message_json = json.dumps(message)
        disconnected = set()
        
        for client in self.connected_clients:
            try:
                await client.send(message_json)
            except:
                disconnected.add(client)
        
        self.connected_clients -= disconnected
    
    async def scenario_loop(self):
        """Main loop that cycles through scenarios."""
        print("Starting scenario test loop...")
        print("=" * 60)
        
        while True:
            if self.connected_clients:
                scenario = self.scenarios[self.scenario]
                
                # Send scenario info at start of each scenario
                if self.step == 0:
                    info = self.get_scenario_info()
                    await self.broadcast_message(info)
                    print(f"\nScenario {self.scenario + 1}/{len(self.scenarios)}: {scenario['name']}")
                    print(f"Description: {scenario['description']}")
                    await asyncio.sleep(2)  # Pause to read info
                
                # Send aircraft data
                aircraft_data = self.generate_aircraft_data()
                await self.broadcast_message(aircraft_data)
                
                # Print progress
                print(f"  Step {self.step + 1}/{scenario['steps']}: "
                      f"Bearing {aircraft_data['bearing']:.0f}°, "
                      f"Distance {aircraft_data['distance_km']:.1f}km, "
                      f"Elevation {aircraft_data['elevation_angle']:.1f}°")
                
                # Advance step
                self.step += 1
                if self.step >= scenario['steps']:
                    self.step = 0
                    self.scenario = (self.scenario + 1) % len(self.scenarios)
                    
                    # Send "no aircraft" between scenarios
                    no_aircraft = {
                        'type': 'no_aircraft',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    await self.broadcast_message(no_aircraft)
                    await asyncio.sleep(2)
            
            await asyncio.sleep(0.5)  # Update every 500ms for smooth animation
    
    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Handle WebSocket connections."""
        print(f"Client connected from {websocket.remote_address}")
        self.connected_clients.add(websocket)
        
        # Send welcome
        welcome = {
            'type': 'welcome',
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Connected to Scenario Test Server'
        }
        await websocket.send(json.dumps(welcome))
        
        # Send current scenario info and aircraft data
        await websocket.send(json.dumps(self.get_scenario_info()))
        await websocket.send(json.dumps(self.generate_aircraft_data()))
        
        try:
            async for message in websocket:
                pass
        except:
            pass
        finally:
            self.connected_clients.discard(websocket)
            print(f"Client disconnected")


async def main():
    """Main entry point."""
    server = ScenarioTestServer()
    
    # Start scenario loop
    loop_task = asyncio.create_task(server.scenario_loop())
    
    print(f"Starting scenario test server on ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    print("This will cycle through different visual test scenarios")
    print("Open the frontend to see the scenarios")
    print("=" * 60)
    
    async with websockets.serve(server.handle_client, WEBSOCKET_HOST, WEBSOCKET_PORT):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nShutdown complete")