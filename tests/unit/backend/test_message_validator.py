"""
Unit tests for message validation
"""

import unittest
from unittest.mock import Mock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.message_validator import MessageValidator, ValidationError


class TestMessageValidator(unittest.TestCase):
    """Test cases for MessageValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = MessageValidator()
        
    def test_validate_coordinates_valid(self):
        """Test validation of valid coordinates"""
        # Valid coordinates
        data = {
            'lat': 51.5074,
            'lon': -0.1278
        }
        
        result = self.validator.validate_coordinates(data)
        self.assertTrue(result)
        
        # Edge cases - poles
        data = {'lat': 90, 'lon': 0}
        self.assertTrue(self.validator.validate_coordinates(data))
        
        data = {'lat': -90, 'lon': 180}
        self.assertTrue(self.validator.validate_coordinates(data))
        
    def test_validate_coordinates_invalid(self):
        """Test validation of invalid coordinates"""
        # Missing fields
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinates({})
            
        # Invalid latitude
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinates({'lat': 91, 'lon': 0})
            
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinates({'lat': -91, 'lon': 0})
            
        # Invalid longitude
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinates({'lat': 0, 'lon': 181})
            
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinates({'lat': 0, 'lon': -181})
            
        # Invalid types
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinates({'lat': 'fifty', 'lon': 0})
            
    def test_validate_search_parameters_valid(self):
        """Test validation of valid search parameters"""
        # Valid search
        data = {
            'radius': 50,
            'min_elevation': 20,
            'max_altitude': 12000
        }
        
        result = self.validator.validate_search_parameters(data)
        self.assertEqual(result['radius'], 50)
        self.assertEqual(result['min_elevation'], 20)
        self.assertEqual(result['max_altitude'], 12000)
        
        # With defaults
        result = self.validator.validate_search_parameters({})
        self.assertIn('radius', result)
        self.assertIn('min_elevation', result)
        
    def test_validate_search_parameters_invalid(self):
        """Test validation of invalid search parameters"""
        # Negative radius
        with self.assertRaises(ValidationError):
            self.validator.validate_search_parameters({'radius': -10})
            
        # Radius too large
        with self.assertRaises(ValidationError):
            self.validator.validate_search_parameters({'radius': 1000})
            
        # Invalid elevation
        with self.assertRaises(ValidationError):
            self.validator.validate_search_parameters({'min_elevation': -10})
            
        with self.assertRaises(ValidationError):
            self.validator.validate_search_parameters({'min_elevation': 100})
            
    def test_validate_websocket_message_valid(self):
        """Test validation of valid WebSocket messages"""
        # Valid get_aircraft message
        message = {
            'type': 'get_aircraft',
            'data': {
                'lat': 51.5,
                'lon': -0.1,
                'radius': 30
            }
        }
        
        result = self.validator.validate_websocket_message(message)
        self.assertEqual(result['type'], 'get_aircraft')
        self.assertIn('data', result)
        
        # Valid update_location message
        message = {
            'type': 'update_location',
            'data': {
                'lat': 48.8566,
                'lon': 2.3522
            }
        }
        
        result = self.validator.validate_websocket_message(message)
        self.assertEqual(result['type'], 'update_location')
        
    def test_validate_websocket_message_invalid(self):
        """Test validation of invalid WebSocket messages"""
        # Missing type
        with self.assertRaises(ValidationError):
            self.validator.validate_websocket_message({'data': {}})
            
        # Invalid type
        with self.assertRaises(ValidationError):
            self.validator.validate_websocket_message({
                'type': 'hack_system',
                'data': {}
            })
            
        # Missing data
        with self.assertRaises(ValidationError):
            self.validator.validate_websocket_message({'type': 'get_aircraft'})
            
        # Invalid data structure
        with self.assertRaises(ValidationError):
            self.validator.validate_websocket_message({
                'type': 'get_aircraft',
                'data': 'not a dict'
            })
            
    def test_sanitize_aircraft_data(self):
        """Test aircraft data sanitization"""
        # Valid aircraft data
        aircraft = {
            'icao24': 'abc123',
            'callsign': 'TEST123',
            'latitude': 51.5,
            'longitude': -0.1,
            'altitude': 10000,
            'velocity': 250,
            'bearing': 45,
            'distance': 15.5,
            'extra_field': 'should be removed'
        }
        
        sanitized = self.validator.sanitize_aircraft_data(aircraft)
        
        # Check allowed fields are present
        self.assertEqual(sanitized['icao24'], 'abc123')
        self.assertEqual(sanitized['callsign'], 'TEST123')
        self.assertEqual(sanitized['altitude'], 10000)
        
        # Check extra field is removed
        self.assertNotIn('extra_field', sanitized)
        
        # Test with missing optional fields
        aircraft = {
            'icao24': 'def456',
            'latitude': 52.0,
            'longitude': 0.0
        }
        
        sanitized = self.validator.sanitize_aircraft_data(aircraft)
        self.assertEqual(sanitized['icao24'], 'def456')
        self.assertIsNone(sanitized.get('callsign'))
        
    def test_validate_message_size(self):
        """Test message size validation"""
        # Valid size
        small_message = {'type': 'test', 'data': 'x' * 100}
        self.assertTrue(self.validator.validate_message_size(small_message))
        
        # Too large
        large_message = {'type': 'test', 'data': 'x' * 100000}
        with self.assertRaises(ValidationError):
            self.validator.validate_message_size(large_message)
            

if __name__ == '__main__':
    unittest.main()