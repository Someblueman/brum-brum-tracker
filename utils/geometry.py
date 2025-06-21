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