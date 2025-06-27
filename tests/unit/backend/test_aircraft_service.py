"""
Unit tests for aircraft service
"""

import unittest
from unittest.mock import Mock, patch
import math
from datetime import datetime

# Import the functions we're testing
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.aircraft_service import AircraftService
from backend.models import AircraftData, VisibilityStatus


class TestAircraftService(unittest.TestCase):
    """Test cases for AircraftService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = AircraftService()
        # Set home location (Hawkinge, UK)
        self.home_lat = 51.2792
        self.home_lon = 1.2836
        
    def test_calculate_distance(self):
        """Test distance calculation between two points"""
        # Test known distance: Hawkinge to London (~100km)
        london_lat = 51.5074
        london_lon = -0.1278
        
        distance = self.service.calculate_distance(
            self.home_lat, self.home_lon,
            london_lat, london_lon
        )
        
        # Should be approximately 100km
        self.assertAlmostEqual(distance, 100, delta=10)
        
    def test_calculate_bearing(self):
        """Test bearing calculation"""
        # North
        bearing = self.service.calculate_bearing(
            self.home_lat, self.home_lon,
            self.home_lat + 1, self.home_lon
        )
        self.assertAlmostEqual(bearing, 0, delta=1)
        
        # East
        bearing = self.service.calculate_bearing(
            self.home_lat, self.home_lon,
            self.home_lat, self.home_lon + 1
        )
        self.assertAlmostEqual(bearing, 90, delta=10)
        
        # South
        bearing = self.service.calculate_bearing(
            self.home_lat, self.home_lon,
            self.home_lat - 1, self.home_lon
        )
        self.assertAlmostEqual(bearing, 180, delta=1)
        
        # West
        bearing = self.service.calculate_bearing(
            self.home_lat, self.home_lon,
            self.home_lat, self.home_lon - 1
        )
        self.assertAlmostEqual(bearing, 270, delta=10)
    
    def test_calculate_elevation_angle(self):
        """Test elevation angle calculation"""
        # Aircraft directly overhead
        elevation = self.service.calculate_elevation_angle(0, 10000)
        self.assertEqual(elevation, 90)
        
        # Aircraft at 45 degree angle
        # altitude = distance for 45 degrees
        elevation = self.service.calculate_elevation_angle(10, 10000)
        self.assertAlmostEqual(elevation, 45, delta=1)
        
        # Aircraft on horizon
        elevation = self.service.calculate_elevation_angle(100, 0)
        self.assertEqual(elevation, 0)
        
    def test_is_aircraft_visible(self):
        """Test aircraft visibility determination"""
        # Visible aircraft (high elevation, close distance)
        status = self.service.is_aircraft_visible(5, 10000, min_elevation=20)
        self.assertEqual(status, VisibilityStatus.VISIBLE)
        
        # Too far away
        status = self.service.is_aircraft_visible(35, 10000, max_distance=30)
        self.assertEqual(status, VisibilityStatus.TOO_FAR)
        
        # Too low elevation
        status = self.service.is_aircraft_visible(50, 5000, min_elevation=20)
        self.assertEqual(status, VisibilityStatus.TOO_LOW)
        
        # No altitude data
        status = self.service.is_aircraft_visible(10, None)
        self.assertEqual(status, VisibilityStatus.NO_ALTITUDE)
        
    def test_process_aircraft_states(self):
        """Test processing of raw aircraft states"""
        # Mock aircraft states from API
        states = [
            [
                'abc123',  # icao24
                'TEST123',  # callsign
                'UK',       # origin_country
                None,       # time_position
                None,       # last_contact
                1.3,        # longitude
                51.3,       # latitude
                10000,      # baro_altitude
                False,      # on_ground
                250,        # velocity
                45,         # true_track
                0,          # vertical_rate
                None,       # sensors
                10000,      # geo_altitude
                None,       # squawk
                False,      # spi
                0           # position_source
            ],
            [
                'def456',   # Too far away
                'FAR456',
                'FR',
                None, None,
                2.5,        # Far longitude
                52.5,       # Far latitude
                10000,
                False,
                300,
                90,
                0,
                None,
                10000,
                None,
                False,
                0
            ]
        ]
        
        aircraft_list = self.service.process_aircraft_states(
            states, self.home_lat, self.home_lon
        )
        
        # Should have processed 2 aircraft
        self.assertEqual(len(aircraft_list), 2)
        
        # First aircraft should be close
        self.assertEqual(aircraft_list[0].icao24, 'abc123')
        self.assertEqual(aircraft_list[0].callsign, 'TEST123')
        self.assertLess(aircraft_list[0].distance, 20)  # Should be close
        
        # Second aircraft should be far
        self.assertEqual(aircraft_list[1].icao24, 'def456')
        self.assertGreater(aircraft_list[1].distance, 100)  # Should be far
        
    def test_get_aircraft_in_range(self):
        """Test filtering aircraft by range"""
        aircraft_list = [
            AircraftData(
                icao24='close1',
                distance=10,
                bearing=0,
                altitude=10000,
                callsign='CLOSE1'
            ),
            AircraftData(
                icao24='close2',
                distance=20,
                bearing=90,
                altitude=8000,
                callsign='CLOSE2'
            ),
            AircraftData(
                icao24='far1',
                distance=40,
                bearing=180,
                altitude=10000,
                callsign='FAR1'
            )
        ]
        
        # Get aircraft within 30km
        in_range = self.service.get_aircraft_in_range(aircraft_list, max_distance=30)
        
        self.assertEqual(len(in_range), 2)
        self.assertEqual(in_range[0].icao24, 'close1')
        self.assertEqual(in_range[1].icao24, 'close2')
        

if __name__ == '__main__':
    unittest.main()