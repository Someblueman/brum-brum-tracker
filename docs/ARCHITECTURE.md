# Brum Brum Tracker Architecture

## Overview

Brum Brum Tracker is a real-time aircraft tracking application designed for toddlers. It shows aircraft overhead with directional arrows, images, and sound notifications. The system consists of a Python backend that fetches aircraft data and a JavaScript frontend that displays the information in a child-friendly interface.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Browser                          │
│ ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌────────────┐ │
│ │   Main UI   │ │  Dashboard   │ │  Logbook   │ │   Assets   │ │
│ │ (index.html)│ │(dashboard.   │ │(logbook.   │ │  (audio,   │ │
│ │             │ │    html)     │ │   html)    │ │  images)   │ │
│ └──────┬──────┘ └──────┬───────┘ └─────┬──────┘ └────────────┘ │
│        │                │               │                        │
│ ┌──────┴────────────────┴───────────────┴──────────────────────┐│
│ │                    WebSocket Connection                       ││
│ │                  (websocket-manager.js)                       ││
│ └───────────────────────────┬───────────────────────────────────┘│
└─────────────────────────────┼───────────────────────────────────┘
                              │ WebSocket (ws://)
                              │ or WSS (wss://)
┌─────────────────────────────┼───────────────────────────────────┐
│                        Backend Server                            │
│ ┌───────────────────────────┴───────────────────────────────────┐│
│ │                    WebSocket Server                           ││
│ │                     (server.py)                               ││
│ └─────────┬─────────────────┬─────────────────┬────────────────┘│
│           │                 │                 │                  │
│ ┌─────────┴──────┐ ┌───────┴──────┐ ┌───────┴──────┐          │
│ │Aircraft Service│ │Logbook Service│ │  Auth Module │          │
│ │                │ │              │ │              │          │
│ └────────┬───────┘ └───────┬──────┘ └──────────────┘          │
│          │                 │                                    │
│ ┌────────┴───────┐ ┌──────┴───────┐ ┌────────────────┐       │
│ │  OpenSky API   │ │SQLite Database│ │ Configuration  │       │
│ │   Client       │ │    (db.py)    │ │  (.env file)   │       │
│ └────────────────┘ └──────────────┘ └────────────────┘       │
└────────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend Components

#### 1. Main Tracker UI (`index.html`, `main.js`)
- **Purpose**: Primary interface showing nearby aircraft with directional arrows
- **Key Features**:
  - Real-time aircraft position updates
  - Compass/directional arrow pointing to aircraft
  - Distance display
  - Sound notifications for new aircraft
  - Family voice greetings

#### 2. Dashboard (`dashboard.html`, `dashboard.js`)
- **Purpose**: Shows all aircraft in the vicinity
- **Key Features**:
  - Grid view of all tracked aircraft
  - Real-time updates
  - Aircraft images and details

#### 3. Logbook (`logbook.html`, `logbook.js`)
- **Purpose**: Captain's logbook showing spotted aircraft history
- **Key Features**:
  - Persistent storage of spotted aircraft
  - Grid display with aircraft types and images
  - Historical tracking

#### 4. WebSocket Manager (`websocket-manager.js`)
- **Purpose**: Handles WebSocket connection and reconnection
- **Key Features**:
  - Automatic reconnection with exponential backoff
  - Message queuing during disconnection
  - Connection state management

### Backend Components

#### 1. WebSocket Server (`server.py`)
- **Purpose**: Main server handling WebSocket connections
- **Responsibilities**:
  - Client connection management
  - Message routing
  - Broadcasting updates
  - Configuration serving

#### 2. Aircraft Service (`aircraft_service.py`)
- **Purpose**: Fetches and processes aircraft data
- **Key Features**:
  - OpenSky API integration
  - Distance/bearing calculations
  - Aircraft filtering by proximity
  - Data formatting

#### 3. Logbook Service (`logbook_service.py`)
- **Purpose**: Manages aircraft spotting history
- **Features**:
  - Database operations
  - REST API endpoints
  - Data persistence

#### 4. Database Layer (`db.py`, `db_secure.py`)
- **Purpose**: SQLite database management
- **Schema**:
  ```sql
  CREATE TABLE logbook (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      spotted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      aircraft_type TEXT NOT NULL,
      image_url TEXT
  )
  ```

## Data Flow

### 1. Aircraft Tracking Flow

```
OpenSky API → Aircraft Service → WebSocket Server → Frontend UI
     ↑                                    ↓
     └──── Polling (30s interval) ────────┘
```

1. Aircraft Service polls OpenSky API every 30 seconds
2. Filters aircraft within configured radius
3. Calculates distance and bearing from home location
4. Broadcasts updates to all connected clients
5. Frontend updates UI with new aircraft data

### 2. Logbook Flow

```
Aircraft Spotted → WebSocket Message → Logbook Service → SQLite DB
                                              ↓
Frontend Request ← REST API Response ← Database Query
```

1. When aircraft enters "spotted" range
2. Frontend sends logbook entry via WebSocket
3. Backend stores in SQLite database
4. Frontend can query logbook via REST endpoints

### 3. Configuration Flow

```
.env file → Backend Config → WebSocket Message → Frontend Config
```

1. Backend reads configuration from .env file
2. Frontend requests config via WebSocket
3. Backend sends HOME_LAT, HOME_LON to frontend
4. Frontend uses config for calculations

## Security Architecture

### Authentication
- JWT-based authentication for production
- Token validation on WebSocket connection
- Session management

### Rate Limiting
- Connection rate limiting per IP
- Message rate limiting per connection
- API call throttling

### Input Validation
- WebSocket message schema validation
- Coordinate validation
- SQL injection prevention

## Deployment Architecture

### Development Mode
```
Frontend HTTP Server (8080) ←→ Backend WS Server (8000)
```

### Production Mode (HTTPS)
```
Frontend HTTPS Server (8443) ←→ Backend WSS Server (8001)
         ↓                              ↓
    SSL Certificate              Shared SSL Certificate
```

## Performance Considerations

### Frontend
- Efficient DOM updates
- Image lazy loading
- WebSocket message batching
- Service Worker caching

### Backend
- Connection pooling
- Database query optimization
- Memory leak prevention
- Efficient broadcast mechanisms

## Scalability

### Current Limitations
- Single server instance
- Local SQLite database
- In-memory connection tracking

### Future Improvements
- Redis for session management
- PostgreSQL for production database
- Load balancing support
- Horizontal scaling capability

## Technology Stack

### Frontend
- Vanilla JavaScript (ES6+)
- HTML5/CSS3
- Service Workers
- Web Audio API
- Device Orientation API

### Backend
- Python 3.8+
- AsyncIO/Websockets
- SQLite
- OpenSky API

### Development Tools
- pytest for testing
- ESLint for JavaScript linting
- GitHub Actions for CI/CD

## Error Handling

### Frontend
- Global error handler
- WebSocket reconnection logic
- Graceful degradation
- User-friendly error messages

### Backend
- Try-catch blocks for all operations
- Proper error logging
- Client disconnection handling
- API failure recovery

## Monitoring and Logging

### Metrics Tracked
- Active connections
- Message throughput
- API response times
- Error rates

### Logging Strategy
- Structured logging format
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Rotating log files
- Performance metrics