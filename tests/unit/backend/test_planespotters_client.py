"""
Tests for Planespotters API client.
"""

from unittest.mock import patch, MagicMock
import time

from backend.planespotters_client import (
    fetch_aircraft_details,
    get_aircraft_type_string,
    get_airline_info,
    get_aircraft_type_fallback,
    clear_cache,
    _aircraft_details_cache,
    _cache_timestamps
)


class TestPlanespottersClient:
    """Test Planespotters API client functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear cache before each test
        clear_cache()
    
    def teardown_method(self):
        """Clean up after tests."""
        clear_cache()
    
    @patch('backend.planespotters_client.get_global_pool')
    def test_fetch_aircraft_details_success(self, mock_get_pool):
        """Test successful aircraft details fetch."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'registration': 'N12345',
            'aircraft_type': 'B738',
            'aircraft_type_text': 'Boeing 737-800',
            'model': '737-800',
            'manufacturer': 'Boeing',
            'serial_number': '12345',
            'airline_name': 'Test Airlines',
            'airline_iata': 'TA',
            'airline_icao': 'TST',
            'country': 'United States',
            'built': '2010',
            'engines': 2,
            'age': 13
        }
        
        mock_pool = MagicMock()
        mock_pool.get.return_value = mock_response
        mock_get_pool.return_value = mock_pool
        
        # Test
        result = fetch_aircraft_details('abc123')
        
        assert result is not None
        assert result['icao24'] == 'ABC123'
        assert result['registration'] == 'N12345'
        assert result['manufacturer'] == 'Boeing'
        assert result['model'] == '737-800'
        assert result['airline_name'] == 'Test Airlines'
        
        # Verify API was called correctly
        mock_pool.get.assert_called_once()
        call_args = mock_pool.get.call_args
        assert 'ABC123' in call_args[0][0]
    
    @patch('backend.planespotters_client.get_global_pool')
    def test_fetch_aircraft_details_not_found(self, mock_get_pool):
        """Test aircraft details fetch when not found."""
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_pool = MagicMock()
        mock_pool.get.return_value = mock_response
        mock_get_pool.return_value = mock_pool
        
        # Test
        result = fetch_aircraft_details('xyz999')
        
        assert result is None
        
        # Verify result is cached
        assert 'XYZ999' in _aircraft_details_cache
        assert _aircraft_details_cache['XYZ999'] is None
    
    @patch('backend.planespotters_client.get_global_pool')
    def test_fetch_aircraft_details_error(self, mock_get_pool):
        """Test aircraft details fetch with error."""
        # Mock error
        mock_pool = MagicMock()
        mock_pool.get.side_effect = Exception("Network error")
        mock_get_pool.return_value = mock_pool
        
        # Test
        result = fetch_aircraft_details('error123')
        
        assert result is None
    
    def test_fetch_aircraft_details_cache(self):
        """Test that cached results are used."""
        # Pre-populate cache
        test_data = {
            'icao24': 'TEST123',
            'manufacturer': 'Boeing',
            'model': '777-300ER'
        }
        _aircraft_details_cache['TEST123'] = test_data
        _cache_timestamps['TEST123'] = time.time()
        
        # Mock pool should not be called
        with patch('backend.planespotters_client.get_global_pool') as mock_get_pool:
            result = fetch_aircraft_details('test123')
            
            assert result == test_data
            mock_get_pool.assert_not_called()
    
    def test_fetch_aircraft_details_cache_expired(self):
        """Test that expired cache is not used."""
        # Pre-populate cache with old timestamp
        test_data = {'icao24': 'OLD123'}
        _aircraft_details_cache['OLD123'] = test_data
        _cache_timestamps['OLD123'] = time.time() - 100000  # Very old
        
        with patch('backend.planespotters_client.get_global_pool') as mock_get_pool:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_pool = MagicMock()
            mock_pool.get.return_value = mock_response
            mock_get_pool.return_value = mock_pool
            
            result = fetch_aircraft_details('old123')
            
            # Should have made API call
            mock_get_pool.assert_called_once()
    
    def test_get_aircraft_type_string(self):
        """Test aircraft type string formatting."""
        # Test with full data
        with patch('backend.planespotters_client.fetch_aircraft_details') as mock_fetch:
            mock_fetch.return_value = {
                'manufacturer': 'Airbus',
                'model': 'A320-214'
            }
            
            result = get_aircraft_type_string('test123')
            assert result == 'Airbus A320-214'
        
        # Test with only aircraft_type_text
        with patch('backend.planespotters_client.fetch_aircraft_details') as mock_fetch:
            mock_fetch.return_value = {
                'aircraft_type_text': 'Boeing 747-400'
            }
            
            result = get_aircraft_type_string('test456')
            assert result == 'Boeing 747-400'
        
        # Test with no data
        with patch('backend.planespotters_client.fetch_aircraft_details') as mock_fetch:
            mock_fetch.return_value = None
            
            result = get_aircraft_type_string('nodata')
            assert result is None
    
    def test_get_airline_info(self):
        """Test airline info extraction."""
        with patch('backend.planespotters_client.fetch_aircraft_details') as mock_fetch:
            mock_fetch.return_value = {
                'airline_name': 'United Airlines',
                'airline_iata': 'UA',
                'airline_icao': 'UAL'
            }
            
            result = get_airline_info('test123')
            assert result == {
                'name': 'United Airlines',
                'iata': 'UA',
                'icao': 'UAL'
            }
        
        # Test with no airline data
        with patch('backend.planespotters_client.fetch_aircraft_details') as mock_fetch:
            mock_fetch.return_value = {
                'manufacturer': 'Boeing'
            }
            
            result = get_airline_info('test456')
            assert result is None
    
    def test_get_aircraft_type_fallback(self):
        """Test aircraft type fallback logic."""
        # Test with good existing type
        result = get_aircraft_type_fallback('test123', 'Boeing 737-800')
        assert result == 'Boeing 737-800'
        
        # Test with Unknown Aircraft - should try fallback
        with patch('backend.planespotters_client.get_aircraft_type_string') as mock_get_type:
            mock_get_type.return_value = 'Airbus A320-200'
            
            result = get_aircraft_type_fallback('test123', 'Unknown Aircraft')
            assert result == 'Airbus A320-200'
            mock_get_type.assert_called_once_with('test123')
        
        # Test with no current type
        with patch('backend.planespotters_client.get_aircraft_type_string') as mock_get_type:
            mock_get_type.return_value = 'Boeing 777-300ER'
            
            result = get_aircraft_type_fallback('test456', None)
            assert result == 'Boeing 777-300ER'
        
        # Test when fallback also fails
        with patch('backend.planespotters_client.get_aircraft_type_string') as mock_get_type:
            mock_get_type.return_value = None
            
            result = get_aircraft_type_fallback('test789', 'Unknown Aircraft')
            assert result == 'Unknown Aircraft'
    
    def test_clear_cache(self):
        """Test cache clearing."""
        # Add some data to cache
        _aircraft_details_cache['TEST1'] = {'data': 'test1'}
        _aircraft_details_cache['TEST2'] = {'data': 'test2'}
        _cache_timestamps['TEST1'] = time.time()
        _cache_timestamps['TEST2'] = time.time()
        
        assert len(_aircraft_details_cache) == 2
        assert len(_cache_timestamps) == 2
        
        # Clear cache
        clear_cache()
        
        assert len(_aircraft_details_cache) == 0
        assert len(_cache_timestamps) == 0