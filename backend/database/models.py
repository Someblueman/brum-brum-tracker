"""
Data models for the Brum Brum Tracker backend.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Airport:
    """Airport information model."""
    code: str
    name: str
    country_code: Optional[str] = None
    region_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'airport': self.name,
            'country_code': self.country_code,
            'region_name': self.region_name,
        }


@dataclass
class FlightRoute:
    """Flight route information model."""
    origin: Optional[Airport] = None
    destination: Optional[Airport] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'origin': self.origin.to_dict() if self.origin else None,
            'destination': self.destination.to_dict() if self.destination else None,
        }


@dataclass
class AircraftDetails:
    """Detailed aircraft information model."""
    icao24: str
    registration: Optional[str] = None
    manufacturer: Optional[str] = None
    type_name: Optional[str] = None
    operator: Optional[str] = None
    image_url: Optional[str] = None
    
    def get_simplified_type(self) -> str:
        """Get simplified aircraft type for display."""
        # This would use the simplify_aircraft_type logic
        return f"{self.manufacturer} {self.type_name}" if self.manufacturer and self.type_name else "Unknown Aircraft"


@dataclass
class AircraftState:
    """Current aircraft state model."""
    icao24: str
    callsign: Optional[str]
    latitude: float
    longitude: float
    baro_altitude: Optional[float]
    velocity: Optional[float]
    true_track: Optional[float]
    distance_km: float
    bearing_from_home: float
    elevation_angle: float
    
    @property
    def altitude_ft(self) -> Optional[float]:
        """Get altitude in feet."""
        return round(self.baro_altitude * 3.28084) if self.baro_altitude else None
    
    @property
    def speed_kmh(self) -> Optional[float]:
        """Get speed in km/h."""
        return round(self.velocity * 3.6) if self.velocity else None


@dataclass
class LogbookEntry:
    """Logbook entry model."""
    id: int
    spotted_at: datetime
    aircraft_type: str
    image_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'spotted_at': self.spotted_at.isoformat(),
            'aircraft_type': self.aircraft_type,
            'image_url': self.image_url,
        }


@dataclass
class WebSocketMessage:
    """Base WebSocket message model."""
    type: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'type': self.type,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class AircraftUpdateMessage(WebSocketMessage):
    """Aircraft update message model."""
    aircraft: AircraftState
    details: Optional[AircraftDetails] = None
    route: Optional[FlightRoute] = None
    
    def __post_init__(self):
        self.type = 'aircraft_update'
        if not hasattr(self, 'timestamp'):
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = super().to_dict()
        
        # Add aircraft state
        data.update({
            'icao24': self.aircraft.icao24,
            'callsign': self.aircraft.callsign.strip() if self.aircraft.callsign else '',
            'latitude': self.aircraft.latitude,
            'longitude': self.aircraft.longitude,
            'altitude': self.aircraft.baro_altitude,
            'altitude_ft': self.aircraft.altitude_ft,
            'velocity': self.aircraft.velocity,
            'true_track': self.aircraft.true_track,
            'distance_km': round(self.aircraft.distance_km, 1),
            'bearing_from_home': round(self.aircraft.bearing_from_home, 1),
            'elevation_angle': round(self.aircraft.elevation_angle, 1),
        })
        
        # Add details if available
        if self.details:
            data.update({
                'registration': self.details.registration,
                'image_url': self.details.image_url,
                'aircraft_type': self.details.get_simplified_type(),
                'aircraft_type_raw': self.details.type_name or 'Unknown',
                'operator': self.details.operator or 'Unknown',
            })
        
        # Add route if available
        if self.route:
            route_data = self.route.to_dict()
            data.update(route_data)
        
        return data