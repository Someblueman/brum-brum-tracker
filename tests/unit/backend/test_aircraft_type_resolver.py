"""
Tests for aircraft type resolver.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.aircraft_type_resolver import (
    simplify_aircraft_type,
    resolve_aircraft_type,
    get_aircraft_info_with_fallbacks
)


class TestSimplifyAircraftType:
    """Test aircraft type simplification."""
    
    def test_boeing_types(self):
        """Test Boeing aircraft type simplification."""
        assert simplify_aircraft_type('Boeing', '737-800') == 'Boeing 737'
        assert simplify_aircraft_type('Boeing', '747-400') == 'Boeing 747 Jumbo Jet'
        assert simplify_aircraft_type('Boeing', '777-300ER') == 'Boeing 777'
        assert simplify_aircraft_type('Boeing', '787-9') == 'Boeing 787 Dreamliner'
        assert simplify_aircraft_type('BOEING', 'Unknown') == 'Boeing Unknown'
        assert simplify_aircraft_type('Boeing', '') == 'Boeing Aircraft'
    
    def test_airbus_types(self):
        """Test Airbus aircraft type simplification."""
        assert simplify_aircraft_type('Airbus', 'A320-200') == 'Airbus A320'
        assert simplify_aircraft_type('Airbus', 'A330-300') == 'Airbus A330'
        assert simplify_aircraft_type('Airbus', 'A380-800') == 'Airbus A380 Super Jumbo'
        assert simplify_aircraft_type('AIRBUS', 'Unknown') == 'Airbus Unknown'
        assert simplify_aircraft_type('Airbus', '') == 'Airbus Aircraft'
    
    def test_regional_aircraft(self):
        """Test regional aircraft type simplification."""
        assert simplify_aircraft_type('Embraer', 'E175') == 'Embraer E175'
        assert simplify_aircraft_type('Embraer', 'ERJ-145') == 'Embraer Regional Jet'
        assert simplify_aircraft_type('Bombardier', 'CRJ900') == 'Bombardier CRJ'
        assert simplify_aircraft_type('Bombardier', 'Q400') == 'Bombardier Dash 8'
        assert simplify_aircraft_type('ATR', 'ATR 72-600') == 'ATR 72 Propeller'
    
    def test_small_aircraft(self):
        """Test small aircraft type simplification."""
        assert simplify_aircraft_type('Cessna', '172') == 'Cessna Small Plane'
        assert simplify_aircraft_type('CESSNA', 'Citation') == 'Cessna Citation Jet'
        assert simplify_aircraft_type('Piper', 'PA-28') == 'Piper Small Plane'
        assert simplify_aircraft_type('Beechcraft', 'King Air') == 'Beechcraft Small Plane'
        assert simplify_aircraft_type('Gulfstream', 'G650') == 'Gulfstream Private Jet'
    
    def test_generic_handling(self):
        """Test generic manufacturer and type handling."""
        assert simplify_aircraft_type('Unknown Mfr', 'Some Type') == 'Unknown Mfr Some Type'
        assert simplify_aircraft_type('SomeMfr', '') == 'SomeMfr Aircraft'
        assert simplify_aircraft_type('', 'SomeType') == 'SomeType'
        assert simplify_aircraft_type('', '') is None
        assert simplify_aircraft_type(None, None) is None


class TestResolveAircraftType:
    """Test aircraft type resolution with fallbacks."""
    
    @patch('backend.aircraft_type_resolver.get_aircraft_from_cache')
    def test_cache_hit(self, mock_get_cache):
        """Test resolution when type is in cache."""
        mock_get_cache.return_value = {
            'icao24': 'ABC123',
            'type': 'Boeing 737-800',
            'image_url': 'https://example.com/image.jpg'
        }
        
        result = resolve_aircraft_type('abc123')
        assert result == 'Boeing 737-800'
        mock_get_cache.assert_called_once_with('abc123')
    
    @patch('backend.aircraft_type_resolver.get_aircraft_from_cache')
    def test_cache_skip_placeholder(self, mock_get_cache):
        """Test that placeholder types are skipped."""
        mock_get_cache.return_value = {
            'icao24': 'ABC123',
            'type': 'Boeing 737 (placeholder)',
            'image_url': ''
        }
        
        with patch('backend.aircraft_type_resolver.fetch_aircraft_details_from_hexdb') as mock_hexdb:
            mock_hexdb.return_value = None
            with patch('backend.aircraft_type_resolver.get_aircraft_type_string') as mock_planespotters:
                mock_planespotters.return_value = None
                
                result = resolve_aircraft_type('abc123')
                assert result == 'Unknown Aircraft'
    
    @patch('backend.aircraft_type_resolver.get_aircraft_from_cache')
    @patch('backend.aircraft_type_resolver.fetch_aircraft_details_from_hexdb')
    @patch('backend.aircraft_type_resolver.save_aircraft_to_cache')
    def test_hexdb_fallback(self, mock_save_cache, mock_hexdb, mock_get_cache):
        """Test fallback to hexdb when cache misses."""
        mock_get_cache.return_value = None
        mock_hexdb.return_value = {
            'Manufacturer': 'Airbus',
            'Type': 'A320-214'
        }
        
        result = resolve_aircraft_type('def456')
        assert result == 'Airbus A320'
        
        # Verify cache was updated
        mock_save_cache.assert_called_once()
        saved_data = mock_save_cache.call_args[0][0]
        assert saved_data['icao24'] == 'def456'
        assert saved_data['type'] == 'Airbus A320'
    
    @patch('backend.aircraft_type_resolver.get_aircraft_from_cache')
    @patch('backend.aircraft_type_resolver.fetch_aircraft_details_from_hexdb')
    @patch('backend.aircraft_type_resolver.get_aircraft_type_string')
    @patch('backend.aircraft_type_resolver.save_aircraft_to_cache')
    def test_planespotters_fallback(self, mock_save_cache, mock_planespotters, mock_hexdb, mock_get_cache):
        """Test fallback to Planespotters when hexdb fails."""
        mock_get_cache.return_value = None
        mock_hexdb.return_value = None
        mock_planespotters.return_value = 'Boeing 777-300ER'
        
        result = resolve_aircraft_type('ghi789')
        assert result == 'Boeing 777'
        
        # Verify cache was updated
        mock_save_cache.assert_called_once()
        saved_data = mock_save_cache.call_args[0][0]
        assert saved_data['icao24'] == 'ghi789'
        assert saved_data['type'] == 'Boeing 777'
    
    @patch('backend.aircraft_type_resolver.get_aircraft_from_cache')
    @patch('backend.aircraft_type_resolver.fetch_aircraft_details_from_hexdb')
    @patch('backend.aircraft_type_resolver.get_aircraft_type_string')
    def test_all_fallbacks_fail(self, mock_planespotters, mock_hexdb, mock_get_cache):
        """Test when all data sources fail."""
        mock_get_cache.return_value = None
        mock_hexdb.return_value = None
        mock_planespotters.return_value = None
        
        result = resolve_aircraft_type('xyz999')
        assert result == 'Unknown Aircraft'
    
    @patch('backend.aircraft_type_resolver.get_aircraft_from_cache')
    @patch('backend.aircraft_type_resolver.fetch_aircraft_details_from_hexdb')
    def test_hexdb_error_handling(self, mock_hexdb, mock_get_cache):
        """Test error handling when hexdb throws exception."""
        mock_get_cache.return_value = None
        mock_hexdb.side_effect = Exception("Database error")
        
        with patch('backend.aircraft_type_resolver.get_aircraft_type_string') as mock_planespotters:
            mock_planespotters.return_value = 'Cessna Citation X'
            
            result = resolve_aircraft_type('error123')
            assert result == 'Cessna Citation Jet'
            
            # Should have tried Planespotters after hexdb failed
            mock_planespotters.assert_called_once_with('error123')


class TestGetAircraftInfoWithFallbacks:
    """Test comprehensive aircraft info retrieval."""
    
    @patch('backend.aircraft_type_resolver.resolve_aircraft_type')
    @patch('backend.aircraft_type_resolver.get_aircraft_from_cache')
    def test_with_cached_data(self, mock_get_cache, mock_resolve):
        """Test getting info when cache has data."""
        mock_resolve.return_value = 'Boeing 737'
        mock_get_cache.return_value = {
            'icao24': 'ABC123',
            'type': 'Boeing 737',
            'image_url': 'https://example.com/737.jpg',
            'last_updated': '2024-01-01 12:00:00'
        }
        
        result = get_aircraft_info_with_fallbacks('abc123')
        
        assert result['icao24'] == 'abc123'
        assert result['type'] == 'Boeing 737'
        assert result['image_url'] == 'https://example.com/737.jpg'
        assert result['last_updated'] == '2024-01-01 12:00:00'
    
    @patch('backend.aircraft_type_resolver.resolve_aircraft_type')
    @patch('backend.aircraft_type_resolver.get_aircraft_from_cache')
    def test_without_cached_data(self, mock_get_cache, mock_resolve):
        """Test getting info when cache is empty."""
        mock_resolve.return_value = 'Airbus A320'
        mock_get_cache.return_value = None
        
        result = get_aircraft_info_with_fallbacks('new123')
        
        assert result['icao24'] == 'new123'
        assert result['type'] == 'Airbus A320'
        assert result['image_url'] == ''
        assert result['last_updated'] is None