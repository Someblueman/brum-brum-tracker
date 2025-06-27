"""
Geometry utilities for calculating distances, bearings, and elevation angles.
"""

import math
from typing import Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.
    
    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees
        
    Returns:
        Distance in kilometers
    """
    # Earth's radius in kilometers
    R = 6371.0
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def bearing_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the bearing from point 1 to point 2.
    
    Args:
        lat1: Latitude of origin point in degrees
        lon1: Longitude of origin point in degrees
        lat2: Latitude of destination point in degrees
        lon2: Longitude of destination point in degrees
        
    Returns:
        Bearing in degrees (0-359), where 0 is North
    """
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    lon2_rad = math.radians(lon2)
    
    # Calculate difference in longitude
    dlon = lon2_rad - lon1_rad
    
    # Calculate bearing
    x = math.sin(dlon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon))
    
    # Convert to degrees and normalize to 0-359
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def elevation_angle(distance_km: float, altitude_m: float) -> float:
    """
    Calculate the elevation angle to an aircraft.
    
    Args:
        distance_km: Horizontal distance to aircraft in kilometers
        altitude_m: Aircraft altitude in meters
        
    Returns:
        Elevation angle in degrees
    """
    # Convert distance to meters for consistent units
    distance_m = distance_km * 1000
    
    # Avoid division by zero
    if distance_m == 0:
        return 90.0 if altitude_m > 0 else 0.0
    
    # Calculate angle using arctangent
    angle_rad = math.atan(altitude_m / distance_m)
    
    # Convert to degrees
    return math.degrees(angle_rad)


def is_plane_approaching(home_bearing: float, plane_bearing: float, 
                        true_track: float, threshold: float = 90.0) -> bool:
    """
    Determine if a plane is flying towards or away from home location.
    
    Args:
        home_bearing: Bearing from home to plane (degrees)
        plane_bearing: Bearing from plane to home (degrees)
        true_track: Plane's direction of travel (degrees)
        threshold: Maximum angle difference to consider approaching (degrees)
        
    Returns:
        True if plane is approaching, False if departing
    """
    # Calculate the difference between plane's track and bearing to home
    # If the plane is flying roughly towards us, this difference should be small
    angle_diff = abs((plane_bearing - true_track + 180) % 360 - 180)
    
    return angle_diff < threshold


def calculate_eta(distance_km: float, velocity_ms: float, 
                  elevation_angle: float = 0) -> float:
    """
    Calculate estimated time of arrival for an aircraft.
    
    Args:
        distance_km: Distance to aircraft in kilometers
        velocity_ms: Aircraft velocity in meters per second
        elevation_angle: Current elevation angle in degrees (optional)
        
    Returns:
        ETA in seconds, or float('inf') if aircraft is not approaching
    """
    if velocity_ms is None or velocity_ms <= 0:
        return float('inf')
    
    # Convert velocity to km/h for consistency
    velocity_kmh = velocity_ms * 3.6
    
    # Simple calculation: time = distance / speed
    # This assumes the aircraft maintains current speed and heading
    eta_hours = distance_km / velocity_kmh
    eta_seconds = eta_hours * 3600
    
    # If elevation angle is very low, aircraft might just be passing by
    # rather than flying overhead
    if elevation_angle < 5 and distance_km > 50:
        return float('inf')
    
    return eta_seconds


def calculate_eta(distance_km: float, velocity_ms: float, 
                  current_elevation: float = 0.0, 
                  target_elevation: float = 20.0) -> float:
    """
    Calculate estimated time of arrival for an aircraft.
    
    ETA is calculated as time until the aircraft reaches the target elevation angle
    (default 20° which is our visibility threshold).
    
    Args:
        distance_km: Current horizontal distance to aircraft in kilometers
        velocity_ms: Aircraft ground speed in meters per second
        current_elevation: Current elevation angle in degrees (default 0)
        target_elevation: Target elevation angle in degrees (default 20)
        
    Returns:
        Estimated time in seconds until aircraft reaches target elevation.
        Returns infinity if aircraft is stationary or moving away.
    """
    # Convert velocity to km/h for easier calculation
    velocity_kmh = velocity_ms * 3.6 if velocity_ms else 0
    
    # If aircraft is not moving or barely moving, return infinity
    if velocity_kmh < 10:  # Less than 10 km/h
        return float('inf')
    
    # If already above target elevation, aircraft is nearly overhead
    if current_elevation >= target_elevation:
        return 0
    
    # Simple linear approximation: time = distance / speed
    # This assumes straight-line approach at constant altitude
    eta_hours = distance_km / velocity_kmh
    eta_seconds = eta_hours * 3600
    
    # Adjust for elevation angle if needed
    # As plane gets closer, elevation increases non-linearly
    # This is a simplified adjustment factor
    if current_elevation > 10:
        # Reduce ETA as we're already at significant elevation
        adjustment_factor = 1 - (current_elevation / target_elevation) * 0.3
        eta_seconds *= adjustment_factor
    
    return max(0, eta_seconds)