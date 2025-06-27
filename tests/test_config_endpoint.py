#!/usr/bin/env python3
"""
Test script to verify configuration endpoint works correctly
"""

import asyncio
import json
import websockets


async def test_config_endpoint():
    """Test the WebSocket config endpoint"""
    uri = "ws://localhost:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket server")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            print(f"Welcome message: {welcome}")
            
            # Request configuration
            config_request = {"type": "get_config"}
            await websocket.send(json.dumps(config_request))
            print("Sent config request")
            
            # Wait for config response
            response = await websocket.recv()
            config_data = json.loads(response)
            
            if config_data.get('type') == 'config':
                print("\nReceived configuration:")
                print(f"HOME_LAT: {config_data['config']['home']['lat']}")
                print(f"HOME_LON: {config_data['config']['home']['lon']}")
                print(f"Search Radius: {config_data['config']['search']['radiusKm']}km")
                print(f"Min Elevation: {config_data['config']['search']['minElevationAngle']}°")
                print("\n✅ Configuration endpoint working correctly!")
            else:
                print(f"❌ Unexpected response type: {config_data.get('type')}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure the backend server is running (python backend/app.py)")


if __name__ == "__main__":
    asyncio.run(test_config_endpoint())