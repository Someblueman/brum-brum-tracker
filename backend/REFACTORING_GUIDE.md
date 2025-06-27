# Backend Refactoring Guide

## Overview
This guide explains the backend refactoring from a monolithic `server.py` to a service-layer architecture.

## New Structure

### Service Layer
- **`aircraft_service.py`**: Handles all aircraft-related business logic
  - Aircraft data fetching
  - Type simplification
  - Message formatting
  
- **`logbook_service.py`**: Manages logbook operations
  - Tracking spotted aircraft
  - Adding entries to logbook
  - Retrieving logbook data

### Data Models (`models.py`)
- `Airport`: Airport information
- `FlightRoute`: Flight origin/destination
- `AircraftDetails`: Detailed aircraft info
- `AircraftState`: Current aircraft position/state
- `LogbookEntry`: Logbook record
- `WebSocketMessage`: Base message class
- `AircraftUpdateMessage`: Aircraft update message

### Refactored Server (`server_refactored.py`)
- Cleaner separation of concerns
- Uses service layer for business logic
- Simplified message handling
- Better error handling

## Key Benefits

1. **Separation of Concerns**
   - WebSocket handling separated from business logic
   - Each service has a single responsibility
   
2. **Testability**
   - Services can be unit tested independently
   - Mock services for integration testing
   
3. **Maintainability**
   - Easier to locate and modify specific functionality
   - Clear boundaries between components
   
4. **Extensibility**
   - Easy to add new services
   - Can swap implementations without affecting other components

## Migration Steps

1. **Test Current Functionality**
   ```bash
   # Start current server
   python backend/app.py
   # Test with frontend
   ```

2. **Switch to Refactored Server**
   ```bash
   # Update app.py to import from server_refactored
   # Or create new app_refactored.py
   ```

3. **Update Imports**
   - Change `from backend.server import` to appropriate service imports
   - Update any direct function calls to use service methods

4. **Test Refactored Version**
   - Verify aircraft tracking works
   - Check logbook functionality
   - Test WebSocket connections

## Example Usage

### Before (in server.py):
```python
# Everything mixed together
class AircraftTracker:
    def format_aircraft_message(self, aircraft):
        # Business logic mixed with formatting
        # Database calls mixed with message handling
        # ...
```

### After (service layer):
```python
# In aircraft_service.py
class AircraftService:
    def format_aircraft_message(self, aircraft):
        # Only aircraft-related logic
        
# In server_refactored.py
class AircraftTracker:
    def __init__(self):
        self.aircraft_service = AircraftService()
        self.logbook_service = LogbookService()
    
    async def polling_loop(self):
        # Delegates to services
        visible_aircraft = await self.aircraft_service.fetch_aircraft_data()
```

## Next Steps

1. Add comprehensive unit tests for services
2. Add integration tests for the refactored server
3. Update app.py and app_ssl.py to use refactored server
4. Consider adding dependency injection
5. Add API documentation using the new structure