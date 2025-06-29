# Brum Brum Tracker Architecture

## Overview

Brum Brum Tracker is a real-time aircraft tracking application designed for toddlers. It consists of a Python backend that fetches aircraft data from the OpenSky Network API and a JavaScript frontend that displays the information in a child-friendly interface.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Browser                          │
│ ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌────────────┐ │
│ │   Main UI   │ │  Dashboard   │ │  Logbook   │ │   Assets   │ │
│ │ (index.html)│ │(dashboard.   │ │(logbook.   │ │  (audio,   │ │
│ └──────┬──────┘ └──────┬───────┘ └─────┬──────┘ └────────────┘ │
│        │                │               │                        │
│        └────────────────┴───────────────┴───────────────────────┤
│                     WebSocket Connection (ws://)                 │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────┐
│                        Backend Server                            │
│                                 │                                │
│          ┌──────────────────────┴──────────────────────┐        │
│          │          WebSocket Server (server.py)       │        │
│          └───────┬──────────────┬──────────────────────┘        │
│                  │              │                                │
│        ┌─────────▼──────┐ ┌────▼──────────┐                    │
│        │ OpenSky API    │ │ SQLite DB     │                    │
│        │ Integration    │ │ (logbook)     │                    │
│        └────────────────┘ └───────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend Components

**Main Tracker UI** (`index.html`, `main.js`)
- Real-time aircraft position updates via WebSocket
- Compass/directional arrow using Device Orientation API
- Distance and bearing calculations
- Sound notifications and family voice greetings

**Dashboard** (`dashboard.html`, `dashboard.js`)
- Grid view of all aircraft within range
- Shows ETA for approaching aircraft
- Real-time updates every 5 seconds

**Logbook** (`logbook.html`, `logbook.js`)
- Displays history of spotted aircraft
- Grid layout with aircraft images
- Persistent storage in SQLite database

**WebSocket Manager** (`websocket-manager.js`)
- Handles connection lifecycle
- Automatic reconnection with exponential backoff
- Message queuing during disconnection

### Backend Components

**WebSocket Server** (`server.py`)
- Manages client connections
- Routes messages between components
- Broadcasts aircraft updates to all clients
- Serves configuration data from .env

**Aircraft Tracking**
- Polls OpenSky Network API every 30 seconds
- Filters aircraft within configured radius
- Calculates distance and bearing from home location
- Simplifies aircraft types to kid-friendly names

**Database** (`db.py`)
- SQLite for logbook persistence
- Simple schema with aircraft type and timestamp
- REST-style endpoints for querying history

## Data Flow

### Aircraft Tracking
1. Backend polls OpenSky API every 30 seconds when clients connected
2. Filters aircraft within 50km radius and above minimum elevation
3. Calculates distance/bearing for each aircraft
4. Broadcasts updates to all connected clients
5. Frontend updates UI with new positions

### Logbook Recording
1. When aircraft enters "spotted" range (<10km)
2. Frontend sends logbook entry via WebSocket
3. Backend stores in SQLite with timestamp
4. Frontend can query history via `/logbook` endpoint

### Configuration
1. Backend reads HOME_LAT/HOME_LON from .env file
2. Frontend requests config on connection
3. Used for all distance/bearing calculations

## Key Technical Decisions

### Why WebSockets?
- Real-time updates without polling
- Bi-directional communication
- Lower latency than HTTP polling
- Automatic reconnection handling

### Why SQLite?
- Simple, file-based database
- No separate database server needed
- Perfect for single-user deployments
- Easy backup (just copy the file)

### Why Vanilla JavaScript?
- No build process required
- Easy to understand and modify
- Fast loading times
- Works on older devices

## Deployment Modes

### HTTP Mode
- Simple setup for local network
- Works on all devices except iOS compass
- Ports: 8000 (WebSocket), 8080 (HTTP)

### HTTPS Mode
- Required for iOS device orientation
- Self-signed certificates auto-generated
- Ports: 8000/8001 (WebSocket/WSS), 8443 (HTTPS)

## Performance Considerations

- Smart polling: Only active when clients connected
- Efficient DOM updates in frontend
- WebSocket message batching
- Image lazy loading for aircraft photos
- Service Worker for offline capability

## Technology Stack

**Frontend**: HTML5, CSS3, Vanilla JavaScript, Service Workers
**Backend**: Python 3.11+, AsyncIO, Websockets, SQLite
**APIs**: OpenSky Network, Wikimedia Commons (images)