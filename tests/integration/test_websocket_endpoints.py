"""
Integration tests for WebSocket endpoints.

Tests the WebSocket server endpoints including:
- Connection handling
- get_config endpoint
- get_logbook endpoint
- Authentication flow (when enabled)
"""

import asyncio
import json
import pytest
import websockets
from unittest.mock import patch, MagicMock
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.server import AircraftTracker


@pytest.fixture
async def websocket_server():
    """Start a test WebSocket server."""
    tracker = AircraftTracker()
    server = await websockets.serve(
        tracker.handle_client,
        'localhost',
        0  # Use any available port
    )
    
    # Get the actual port
    port = server.sockets[0].getsockname()[1]
    
    yield f'ws://localhost:{port}'
    
    # Cleanup
    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_websocket_connection(websocket_server):
    """Test basic WebSocket connection."""
    async with websockets.connect(websocket_server) as websocket:
        # Should receive welcome message
        message = await websocket.recv()
        data = json.loads(message)
        
        assert data['type'] == 'welcome'
        assert 'timestamp' in data
        assert data['message'] == 'Connected to Brum Brum Tracker'


@pytest.mark.asyncio
async def test_get_config_endpoint(websocket_server):
    """Test get_config WebSocket endpoint."""
    async with websockets.connect(websocket_server) as websocket:
        # Skip welcome message
        await websocket.recv()
        
        # Send get_config request
        await websocket.send(json.dumps({'type': 'get_config'}))
        
        # Wait for response
        message = await websocket.recv()
        data = json.loads(message)
        
        assert data['type'] == 'config'
        assert 'config' in data
        assert 'home' in data['config']
        assert 'lat' in data['config']['home']
        assert 'lon' in data['config']['home']
        assert 'search' in data['config']
        assert 'radiusKm' in data['config']['search']


@pytest.mark.asyncio
async def test_get_logbook_endpoint(websocket_server):
    """Test get_logbook WebSocket endpoint."""
    # Mock the database function
    with patch('backend.server.get_logbook') as mock_get_logbook:
        mock_get_logbook.return_value = [
            {
                'id': 1,
                'spotted_at': '2025-06-26T12:00:00',
                'aircraft_type': 'Boeing 737',
                'image_url': 'https://example.com/image.jpg'
            }
        ]
        
        async with websockets.connect(websocket_server) as websocket:
            # Skip welcome message
            await websocket.recv()
            
            # Send get_logbook request
            await websocket.send(json.dumps({'type': 'get_logbook'}))
            
            # Wait for response
            message = await websocket.recv()
            data = json.loads(message)
            
            assert data['type'] == 'logbook_data'
            assert 'log' in data
            assert len(data['log']) == 1
            assert data['log'][0]['aircraft_type'] == 'Boeing 737'


@pytest.mark.asyncio
async def test_get_logbook_with_since_parameter(websocket_server):
    """Test get_logbook with since parameter."""
    with patch('backend.server.get_logbook') as mock_get_logbook:
        mock_get_logbook.return_value = []
        
        async with websockets.connect(websocket_server) as websocket:
            # Skip welcome message
            await websocket.recv()
            
            # Send get_logbook request with since parameter
            await websocket.send(json.dumps({
                'type': 'get_logbook',
                'since': '2025-06-26T00:00:00'
            }))
            
            # Wait for response
            message = await websocket.recv()
            data = json.loads(message)
            
            # Verify the function was called with since parameter
            mock_get_logbook.assert_called_once_with(since='2025-06-26T00:00:00')
            
            assert data['type'] == 'logbook_data'
            assert data['log'] == []


@pytest.mark.asyncio
async def test_invalid_message_type(websocket_server):
    """Test handling of invalid message types."""
    async with websockets.connect(websocket_server) as websocket:
        # Skip welcome message
        await websocket.recv()
        
        # Send invalid message type
        await websocket.send(json.dumps({'type': 'invalid_type'}))
        
        # Should not crash, just log debug message
        # Give it a moment to process
        await asyncio.sleep(0.1)
        
        # Connection should still be alive
        await websocket.ping()


@pytest.mark.asyncio
async def test_malformed_json(websocket_server):
    """Test handling of malformed JSON."""
    async with websockets.connect(websocket_server) as websocket:
        # Skip welcome message
        await websocket.recv()
        
        # Send malformed JSON
        await websocket.send('{"invalid json')
        
        # Should not crash
        await asyncio.sleep(0.1)
        
        # Connection should still be alive
        await websocket.ping()


@pytest.mark.asyncio
async def test_authentication_flow():
    """Test authentication flow when enabled."""
    # Set up environment for auth
    os.environ['AUTH_ENABLED'] = 'true'
    os.environ['AUTH_USERNAME'] = 'testuser'
    os.environ['AUTH_PASSWORD'] = 'testpass'
    
    try:
        # Need to import after setting env vars
        from backend.auth import AuthManager
        auth_manager = AuthManager()
        
        # Create a new tracker with auth enabled
        tracker = AircraftTracker()
        server = await websockets.serve(
            tracker.handle_client,
            'localhost',
            0
        )
        
        port = server.sockets[0].getsockname()[1]
        
        async with websockets.connect(f'ws://localhost:{port}') as websocket:
            # Should receive auth_required message
            message = await websocket.recv()
            data = json.loads(message)
            
            assert data['type'] == 'auth_required'
            
            # Send login credentials
            await websocket.send(json.dumps({
                'type': 'auth_login',
                'username': 'testuser',
                'password': 'testpass'
            }))
            
            # Should receive auth success
            message = await websocket.recv()
            data = json.loads(message)
            
            assert data['type'] == 'auth_response'
            assert data['success'] is True
            assert 'token' in data
            
            # Now should receive welcome message
            message = await websocket.recv()
            data = json.loads(message)
            assert data['type'] == 'welcome'
        
        server.close()
        await server.wait_closed()
        
    finally:
        # Clean up env vars
        os.environ['AUTH_ENABLED'] = 'false'


@pytest.mark.asyncio
async def test_multiple_clients(websocket_server):
    """Test multiple concurrent WebSocket connections."""
    clients = []
    
    # Connect 3 clients
    for i in range(3):
        client = await websockets.connect(websocket_server)
        clients.append(client)
        
        # Each should receive welcome message
        message = await client.recv()
        data = json.loads(message)
        assert data['type'] == 'welcome'
    
    # All clients should be able to send messages
    for i, client in enumerate(clients):
        await client.send(json.dumps({'type': 'get_config'}))
        message = await client.recv()
        data = json.loads(message)
        assert data['type'] == 'config'
    
    # Close all clients
    for client in clients:
        await client.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])