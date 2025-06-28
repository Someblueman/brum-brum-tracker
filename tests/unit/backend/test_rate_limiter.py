"""
Unit tests for rate limiting
"""

import unittest
import asyncio
import time

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.rate_limiter import RateLimiter, ConnectionThrottler


class TestRateLimiter(unittest.TestCase):
    """Test cases for RateLimiter"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.rate_limiter = RateLimiter(max_requests=5, window_seconds=1)
        
    def test_check_rate_limit_allowed(self):
        """Test rate limiting allows requests within limit"""
        client_id = '192.168.1.1'
        
        # First 5 requests should be allowed
        for i in range(5):
            allowed, remaining = self.rate_limiter.check_rate_limit(client_id)
            self.assertTrue(allowed)
            self.assertEqual(remaining, 4 - i)
            
    def test_check_rate_limit_blocked(self):
        """Test rate limiting blocks requests over limit"""
        client_id = '192.168.1.2'
        
        # Use up all requests
        for i in range(5):
            self.rate_limiter.check_rate_limit(client_id)
            
        # Next request should be blocked
        allowed, remaining = self.rate_limiter.check_rate_limit(client_id)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        
    def test_rate_limit_window_reset(self):
        """Test rate limit resets after window"""
        client_id = '192.168.1.3'
        
        # Use up all requests
        for i in range(5):
            self.rate_limiter.check_rate_limit(client_id)
            
        # Should be blocked
        allowed, _ = self.rate_limiter.check_rate_limit(client_id)
        self.assertFalse(allowed)
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be allowed again
        allowed, remaining = self.rate_limiter.check_rate_limit(client_id)
        self.assertTrue(allowed)
        self.assertEqual(remaining, 4)
        
    def test_cleanup_old_entries(self):
        """Test cleanup of old rate limit entries"""
        # Create entries for multiple clients
        for i in range(10):
            self.rate_limiter.check_rate_limit(f'192.168.1.{i}')
            
        # Should have 10 clients
        self.assertEqual(len(self.rate_limiter.requests), 10)
        
        # Wait for cleanup interval
        time.sleep(2)
        
        # Manually trigger cleanup
        self.rate_limiter.cleanup_old_entries()
        
        # Old entries should be removed
        self.assertEqual(len(self.rate_limiter.requests), 0)
        

class TestConnectionThrottler(unittest.TestCase):
    """Test cases for ConnectionThrottler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.throttler = ConnectionThrottler(
            max_connections_per_ip=3,
            global_max_connections=10
        )
        
    def test_can_connect_allowed(self):
        """Test connection throttling allows connections within limit"""
        # First 3 connections from same IP should be allowed
        for i in range(3):
            allowed = self.throttler.can_connect('192.168.1.1')
            self.assertTrue(allowed)
            
    def test_can_connect_blocked_per_ip(self):
        """Test connection throttling blocks over per-IP limit"""
        ip = '192.168.1.2'
        
        # Use up all connections for this IP
        for i in range(3):
            self.throttler.can_connect(ip)
            
        # Next connection should be blocked
        allowed = self.throttler.can_connect(ip)
        self.assertFalse(allowed)
        
        # Different IP should still be allowed
        allowed = self.throttler.can_connect('192.168.1.3')
        self.assertTrue(allowed)
        
    def test_can_connect_blocked_global(self):
        """Test connection throttling blocks over global limit"""
        # Create connections from different IPs up to global limit
        for i in range(10):
            # Use different IPs to avoid per-IP limit
            ip = f'192.168.1.{i // 3 + 1}'
            self.throttler.can_connect(ip)
            
        # Next connection should be blocked (global limit)
        allowed = self.throttler.can_connect('192.168.2.1')
        self.assertFalse(allowed)
        
    def test_disconnect(self):
        """Test connection removal on disconnect"""
        ip = '192.168.1.4'
        
        # Connect 3 times
        for i in range(3):
            self.throttler.can_connect(ip)
            
        # Should be blocked
        self.assertFalse(self.throttler.can_connect(ip))
        
        # Disconnect one
        self.throttler.disconnect(ip)
        
        # Should be allowed again
        self.assertTrue(self.throttler.can_connect(ip))
        
    def test_get_connection_count(self):
        """Test getting connection counts"""
        # No connections
        self.assertEqual(self.throttler.get_connection_count('192.168.1.5'), 0)
        
        # Add connections
        self.throttler.can_connect('192.168.1.5')
        self.throttler.can_connect('192.168.1.5')
        
        self.assertEqual(self.throttler.get_connection_count('192.168.1.5'), 2)
        

class TestAsyncRateLimiter(unittest.TestCase):
    """Test cases for async rate limiting decorator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.call_count = 0
        
    async def test_rate_limit_decorator(self):
        """Test rate limiting decorator on async function"""
        from backend.rate_limiter import rate_limit
        
        @rate_limit(max_calls=3, window=1)
        async def test_function():
            self.call_count += 1
            return self.call_count
            
        # First 3 calls should work
        for i in range(3):
            result = await test_function()
            self.assertEqual(result, i + 1)
            
        # 4th call should be rate limited (return None)
        result = await test_function()
        self.assertIsNone(result)
        
        # Wait for window to reset
        await asyncio.sleep(1.1)
        
        # Should work again
        result = await test_function()
        self.assertEqual(result, 4)
        

if __name__ == '__main__':
    unittest.main()