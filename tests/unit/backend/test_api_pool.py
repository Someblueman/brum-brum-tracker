"""
Tests for API connection pooling.
"""

import time
import threading
from unittest.mock import patch, MagicMock
import requests

from backend.api_pool import APIConnectionPool, get_global_pool, close_global_pool


class TestAPIConnectionPool:
    """Test API connection pool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pool = APIConnectionPool(
            pool_connections=2,
            pool_maxsize=5,
            max_retries=2,
            backoff_factor=0.1,
            timeout=(1.0, 5.0)
        )
    
    def teardown_method(self):
        """Clean up after tests."""
        self.pool.close()
        close_global_pool()
    
    def test_initialization(self):
        """Test pool initialization."""
        assert self.pool.pool_connections == 2
        assert self.pool.pool_maxsize == 5
        assert self.pool.max_retries == 2
        assert self.pool.backoff_factor == 0.1
        assert self.pool.timeout == (1.0, 5.0)
        assert len(self.pool._sessions) == 0
    
    def test_create_session(self):
        """Test session creation."""
        session = self.pool._create_session("https://example.com")
        
        assert isinstance(session, requests.Session)
        assert session.headers['User-Agent'] == 'BrumBrumTracker/1.0'
        assert session.headers['Accept'] == 'application/json'
        assert session.headers['Connection'] == 'keep-alive'
    
    def test_get_session_creates_new(self):
        """Test that get_session creates a new session if none exists."""
        url = "https://example.com/api/test"
        session = self.pool.get_session(url)
        
        assert isinstance(session, requests.Session)
        assert "https://example.com" in self.pool._sessions
        assert len(self.pool._sessions) == 1
    
    def test_get_session_reuses_existing(self):
        """Test that get_session reuses existing sessions."""
        url1 = "https://example.com/api/test1"
        url2 = "https://example.com/api/test2"
        
        session1 = self.pool.get_session(url1)
        session2 = self.pool.get_session(url2)
        
        assert session1 is session2
        assert len(self.pool._sessions) == 1
    
    def test_get_session_different_hosts(self):
        """Test that different hosts get different sessions."""
        url1 = "https://example1.com/api/test"
        url2 = "https://example2.com/api/test"
        
        session1 = self.pool.get_session(url1)
        session2 = self.pool.get_session(url2)
        
        assert session1 is not session2
        assert len(self.pool._sessions) == 2
    
    def test_rate_limiting(self):
        """Test rate limiting enforcement."""
        self.pool.set_rate_limit("example.com", 0.5)  # 500ms between requests
        
        # First request should go through immediately
        start_time = time.time()
        self.pool._enforce_rate_limit("example.com")
        first_duration = time.time() - start_time
        
        # Second request should be delayed
        start_time = time.time()
        self.pool._enforce_rate_limit("example.com")
        second_duration = time.time() - start_time
        
        assert first_duration < 0.1  # First request is immediate
        assert second_duration >= 0.4  # Second request is delayed
    
    def test_rate_limiting_different_hosts(self):
        """Test that rate limiting is per-host."""
        self.pool.set_rate_limit("example1.com", 1.0)
        self.pool.set_rate_limit("example2.com", 0.5)
        
        # Requests to different hosts should not interfere
        self.pool._enforce_rate_limit("example1.com")
        
        start_time = time.time()
        self.pool._enforce_rate_limit("example2.com")
        duration = time.time() - start_time
        
        assert duration < 0.1  # No delay for different host
    
    @patch('requests.Session.request')
    def test_request_method(self, mock_request):
        """Test the request method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.123
        mock_request.return_value = mock_response
        
        response = self.pool.request('GET', 'https://example.com/api/test')
        
        assert response == mock_response
        mock_request.assert_called_once_with(
            'GET', 
            'https://example.com/api/test',
            timeout=(1.0, 5.0)
        )
    
    @patch('requests.Session.request')
    def test_get_method(self, mock_request):
        """Test the GET method."""
        mock_response = MagicMock()
        mock_request.return_value = mock_response
        
        response = self.pool.get('https://example.com/api/test', params={'q': 'test'})
        
        assert response == mock_response
        mock_request.assert_called_once_with(
            'GET',
            'https://example.com/api/test',
            params={'q': 'test'},
            timeout=(1.0, 5.0)
        )
    
    @patch('requests.Session.request')
    def test_post_method(self, mock_request):
        """Test the POST method."""
        mock_response = MagicMock()
        mock_request.return_value = mock_response
        
        response = self.pool.post('https://example.com/api/test', json={'data': 'test'})
        
        assert response == mock_response
        mock_request.assert_called_once_with(
            'POST',
            'https://example.com/api/test',
            json={'data': 'test'},
            timeout=(1.0, 5.0)
        )
    
    def test_close(self):
        """Test closing the pool."""
        # Create some sessions
        self.pool.get_session("https://example1.com")
        self.pool.get_session("https://example2.com")
        
        assert len(self.pool._sessions) == 2
        
        # Close the pool
        self.pool.close()
        
        assert len(self.pool._sessions) == 0
    
    def test_context_manager(self):
        """Test using pool as context manager."""
        with APIConnectionPool() as pool:
            session = pool.get_session("https://example.com")
            assert isinstance(session, requests.Session)
            assert len(pool._sessions) == 1
        
        # Pool should be closed after context
        assert len(pool._sessions) == 0
    
    def test_thread_safety(self):
        """Test thread safety of session management."""
        urls = [f"https://example{i}.com" for i in range(10)]
        sessions = []
        
        def get_session(url):
            session = self.pool.get_session(url)
            sessions.append(session)
        
        # Create threads
        threads = [threading.Thread(target=get_session, args=(url,)) for url in urls]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have 10 unique base URLs in sessions
        assert len(self.pool._sessions) == 10
        assert len(sessions) == 10


class TestGlobalPool:
    """Test global pool management."""
    
    def teardown_method(self):
        """Clean up after tests."""
        close_global_pool()
    
    def test_get_global_pool_creates_instance(self):
        """Test that get_global_pool creates a singleton instance."""
        pool1 = get_global_pool()
        pool2 = get_global_pool()
        
        assert pool1 is pool2
        assert isinstance(pool1, APIConnectionPool)
    
    def test_global_pool_has_rate_limits(self):
        """Test that global pool has default rate limits."""
        pool = get_global_pool()
        
        assert 'opensky-network.org' in pool._rate_limits
        assert pool._rate_limits['opensky-network.org'] == 5.0
        assert 'auth.opensky-network.org' in pool._rate_limits
        assert pool._rate_limits['auth.opensky-network.org'] == 1.0
    
    def test_close_global_pool(self):
        """Test closing the global pool."""
        pool1 = get_global_pool()
        close_global_pool()
        pool2 = get_global_pool()
        
        assert pool1 is not pool2  # New instance created after close