# Brum Brum Tracker API Documentation

## Overview

The Brum Brum Tracker uses WebSocket connections for real-time aircraft tracking data. This document describes all WebSocket message formats and REST endpoints.

## WebSocket Connection

### Connection URL
```
ws://[hostname]:8000/ws   # HTTP connection
wss://[hostname]:8001/ws  # HTTPS connection (required for iOS compass)
```

### Authentication
If authentication is enabled on the server, the first message after connection should be an authentication message.

## WebSocket Message Formats

All WebSocket messages are JSON-encoded with a `type` field indicating the message type.

### Client → Server Messages

#### 1. Authentication Token
```json
{
  "type": "auth_token",
  "token": "jwt_token_here"
}
```

#### 2. Authentication Credentials
```json
{
  "type": "auth_credentials",
  "username": "user",
  "password": "password"
}
```

#### 3. Get Configuration
```json
{
  "type": "get_config"
}
```
Response includes HOME_LAT and HOME_LON values from server configuration.

#### 4. Get Logbook
```json
{
  "type": "get_logbook",
  "since": "2025-06-26T10:00:00Z"  // Optional: ISO timestamp to get updates since
}
```

#### 5. Heartbeat/Ping
```json
{
  "type": "ping"
}
```

### Server → Client Messages

#### 1. Welcome Message
Sent immediately after successful connection.
```json
{
  "type": "welcome",
  "message": "Connected to Brum Brum Tracker",
  "timestamp": "2025-06-26T10:00:00Z"
}
```

#### 2. Authentication Required
```json
{
  "type": "auth_required",
  "message": "Authentication required"
}
```

#### 3. Authentication Response
```json
{
  "type": "auth_response",
  "success": true,
  "message": "Authentication successful",
  "token": "jwt_token_here"  // Only included on successful login
}
```

#### 4. Configuration Data
```json
{
  "type": "config",
  "data": {
    "HOME_LAT": 51.5074,
    "HOME_LON": -0.1278,
    "SEARCH_RADIUS_KM": 50,
    "MIN_ELEVATION_ANGLE": 20
  }
}
```

#### 5. Aircraft Update
Sent when a new aircraft is detected or existing aircraft data is updated.
```json
{
  "type": "aircraft",
  "icao24": "3474CB",
  "callsign": "BAW123",
  "distance_km": 12.5,
  "bearing": 270,
  "altitude_m": 11000,
  "velocity_ms": 230,
  "aircraft_type": "Boeing 737",
  "aircraft_type_raw": "B738",
  "origin_country": "United Kingdom",
  "image_url": "https://example.com/aircraft.jpg",
  "from_airport": "LHR",
  "to_airport": "JFK",
  "eta_seconds": 120,
  "is_approaching": true,
  "elevation_angle": 45.5,
  "true_track": 270,
  "timestamp": "2025-06-26T10:00:00Z"
}
```

#### 6. Aircraft Lost
Sent when an aircraft is no longer visible or trackable.
```json
{
  "type": "aircraft_lost",
  "icao24": "3474CB",
  "message": "Aircraft no longer visible"
}
```

#### 7. Multiple Aircraft List
Used by the dashboard view to show all approaching aircraft.
```json
{
  "type": "approaching_aircraft_list",
  "count": 3,
  "aircraft": [
    {
      "icao24": "3474CB",
      "callsign": "BAW123",
      "distance_km": 12.5,
      "bearing": 270,
      "altitude_m": 11000,
      "velocity_ms": 230,
      "aircraft_type": "Boeing 737",
      "eta_seconds": 120,
      "from_airport": "LHR",
      "to_airport": "JFK"
    }
    // ... more aircraft
  ],
  "next_arrival_seconds": 120,
  "timestamp": "2025-06-26T10:00:00Z"
}
```

#### 8. Logbook Data
```json
{
  "type": "logbook_data",
  "log": [
    {
      "aircraft_type": "Boeing 747",
      "image_url": "https://example.com/747.jpg",
      "first_spotted": "2025-06-26T09:00:00Z",
      "last_spotted": "2025-06-26T10:00:00Z",
      "sighting_count": 5
    }
    // ... more entries
  ]
}
```

#### 9. Error Message
```json
{
  "type": "error",
  "error": "Error description",
  "code": "ERROR_CODE",  // Optional error code
  "details": {}          // Optional additional details
}
```

#### 10. Pong Response
```json
{
  "type": "pong",
  "timestamp": "2025-06-26T10:00:00Z"
}
```

## Error Codes

| Code | Description |
|------|-------------|
| AUTH_REQUIRED | Authentication is required but not provided |
| AUTH_FAILED | Authentication credentials are invalid |
| INVALID_TOKEN | JWT token is invalid or expired |
| RATE_LIMIT | Rate limit exceeded |
| INVALID_MESSAGE | Message format is invalid |
| SERVER_ERROR | Internal server error |

## REST Endpoints

Currently, all functionality is handled through WebSocket connections. The logbook data persistence is managed internally by the server.

## Rate Limiting

- Maximum connections per IP: 10
- Maximum messages per minute: 60
- Maximum message size: 10KB

## Data Update Frequency

- Aircraft position updates: Every 5-10 seconds
- Dashboard list updates: Every 5 seconds
- Logbook updates: On demand

## Example Connection Flow

```javascript
// 1. Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// 2. Handle connection open
ws.onopen = () => {
    console.log('Connected');
    
    // 3. Request configuration
    ws.send(JSON.stringify({ type: 'get_config' }));
};

// 4. Handle messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'config':
            // Store configuration
            console.log('Home coordinates:', data.data.HOME_LAT, data.data.HOME_LON);
            break;
            
        case 'aircraft':
            // Update aircraft display
            console.log('Aircraft detected:', data.callsign);
            break;
            
        case 'auth_required':
            // Send authentication
            ws.send(JSON.stringify({
                type: 'auth_credentials',
                username: 'user',
                password: 'pass'
            }));
            break;
    }
};

// 5. Handle errors
ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

// 6. Handle close
ws.onclose = () => {
    console.log('Disconnected');
    // Implement reconnection logic
};
```

## Security Considerations

1. **Authentication**: Use JWT tokens for persistent authentication
2. **HTTPS/WSS**: Required for production deployments
3. **Input Validation**: All messages are validated server-side
4. **Rate Limiting**: Prevents abuse and DoS attacks
5. **CORS**: Configure appropriate CORS headers for your deployment

## Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support (HTTPS required for device orientation)
- Mobile browsers: Full support (HTTPS required for iOS compass)