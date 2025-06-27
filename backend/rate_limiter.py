"""
Rate limiting module for WebSocket connections.

This module provides comprehensive rate limiting functionality to prevent
abuse and ensure fair resource usage across all WebSocket clients. It implements
a token bucket algorithm with sliding windows for accurate rate tracking.

The rate limiter protects against:
- Connection flooding: Limits new connections per IP address
- Message flooding: Limits messages per connection
- Resource exhaustion: Limits concurrent connections per IP

Rate limiting is essential for production deployments to maintain service
stability and prevent denial-of-service attacks.
"""

import time
from collections import defaultdict, deque
from typing import Dict, Deque, Optional
import asyncio


class RateLimitExceeded(Exception):
    """
    Exception raised when rate limit is exceeded.
    
    This exception should be caught by WebSocket handlers to send
    appropriate error messages to clients and potentially close connections.
    """
    pass


class RateLimiter:
    """
    Token bucket rate limiter for WebSocket connections.
    
    Implements a sliding window algorithm to track and limit:
    - Connection attempts per IP address
    - Messages sent per connection
    - Concurrent connections per IP address
    
    The rate limiter automatically cleans up old tracking data to prevent
    memory leaks. All limits are configurable and can be adjusted based
    on server capacity and expected usage patterns.
    """
    
    def __init__(
        self,
        connection_limit: int = 5,
        connection_window: int = 60,
        message_limit: int = 100,
        message_window: int = 60,
        max_connections_per_ip: int = 3
    ):
        """
        Initialize rate limiter with configurable thresholds.
        
        Default values are suitable for a small to medium deployment.
        Adjust based on your server capacity and expected usage.
        
        Args:
            connection_limit: Maximum new connections allowed per IP within
                the connection window (default: 5 connections)
            connection_window: Time window in seconds for connection rate
                limiting (default: 60 seconds)
            message_limit: Maximum messages allowed per connection within
                the message window (default: 100 messages)
            message_window: Time window in seconds for message rate
                limiting (default: 60 seconds)
            max_connections_per_ip: Maximum concurrent WebSocket connections
                allowed from a single IP address (default: 3 connections)
                
        Example:
            >>> limiter = RateLimiter(
            ...     connection_limit=10,      # Allow 10 new connections
            ...     connection_window=300,    # Per 5 minutes
            ...     message_limit=1000,       # Allow 1000 messages
            ...     message_window=3600      # Per hour
            ... )
        """
        self.connection_limit = connection_limit
        self.connection_window = connection_window
        self.message_limit = message_limit
        self.message_window = message_window
        self.max_connections_per_ip = max_connections_per_ip
        
        # Track connection attempts per IP
        self.connection_attempts: Dict[str, Deque[float]] = defaultdict(deque)
        
        # Track messages per connection
        self.message_counts: Dict[str, Deque[float]] = defaultdict(deque)
        
        # Track active connections per IP
        self.active_connections: Dict[str, int] = defaultdict(int)
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop the cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        """Periodically clean up old tracking data."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                self._cleanup_old_data()
            except asyncio.CancelledError:
                break
    
    def _cleanup_old_data(self):
        """Remove old entries from tracking dictionaries."""
        current_time = time.time()
        
        # Clean connection attempts
        for ip in list(self.connection_attempts.keys()):
            attempts = self.connection_attempts[ip]
            cutoff = current_time - self.connection_window
            
            while attempts and attempts[0] < cutoff:
                attempts.popleft()
            
            if not attempts:
                del self.connection_attempts[ip]
        
        # Clean message counts
        for conn_id in list(self.message_counts.keys()):
            messages = self.message_counts[conn_id]
            cutoff = current_time - self.message_window
            
            while messages and messages[0] < cutoff:
                messages.popleft()
            
            if not messages:
                del self.message_counts[conn_id]
    
    def check_connection_allowed(self, client_ip: str) -> bool:
        """
        Check if a new connection is allowed from this IP.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if connection is allowed
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        current_time = time.time()
        attempts = self.connection_attempts[client_ip]
        
        # Remove old attempts outside the window
        cutoff = current_time - self.connection_window
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        
        # Check if limit exceeded
        if len(attempts) >= self.connection_limit:
            raise RateLimitExceeded(
                f"Connection rate limit exceeded: {self.connection_limit} per {self.connection_window}s"
            )
        
        # Check concurrent connections
        if self.active_connections[client_ip] >= self.max_connections_per_ip:
            raise RateLimitExceeded(
                f"Max concurrent connections exceeded: {self.max_connections_per_ip} per IP"
            )
        
        # Record this attempt
        attempts.append(current_time)
        self.active_connections[client_ip] += 1
        
        return True
    
    def check_message_allowed(self, connection_id: str) -> bool:
        """
        Check if a message is allowed from this connection.
        
        Args:
            connection_id: Unique connection identifier
            
        Returns:
            True if message is allowed
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        current_time = time.time()
        messages = self.message_counts[connection_id]
        
        # Remove old messages outside the window
        cutoff = current_time - self.message_window
        while messages and messages[0] < cutoff:
            messages.popleft()
        
        # Check if limit exceeded
        if len(messages) >= self.message_limit:
            raise RateLimitExceeded(
                f"Message rate limit exceeded: {self.message_limit} per {self.message_window}s"
            )
        
        # Record this message
        messages.append(current_time)
        
        return True
    
    def connection_closed(self, client_ip: str, connection_id: str):
        """
        Clean up when a connection is closed.
        
        Args:
            client_ip: Client IP address
            connection_id: Unique connection identifier
        """
        # Decrement active connections
        if client_ip in self.active_connections:
            self.active_connections[client_ip] = max(0, self.active_connections[client_ip] - 1)
            if self.active_connections[client_ip] == 0:
                del self.active_connections[client_ip]
        
        # Remove message tracking for this connection
        if connection_id in self.message_counts:
            del self.message_counts[connection_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics."""
        return {
            "active_ips": len(self.active_connections),
            "total_connections": sum(self.active_connections.values()),
            "tracked_connections": len(self.message_counts),
            "connection_attempts": {
                ip: len(attempts) 
                for ip, attempts in self.connection_attempts.items()
            },
            "active_connections_per_ip": dict(self.active_connections)
        }


class ConnectionThrottler:
    """
    Additional throttling for API requests to external services.
    Ensures we don't exceed external API rate limits.
    """
    
    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize API throttler.
        
        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_minute = requests_per_minute
        self.request_times: Deque[float] = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """
        Acquire permission to make an API request.
        This method will wait if rate limit would be exceeded.
        """
        async with self._lock:
            current_time = time.time()
            
            # Remove requests older than 1 minute
            cutoff = current_time - 60
            while self.request_times and self.request_times[0] < cutoff:
                self.request_times.popleft()
            
            # If at limit, calculate wait time
            if len(self.request_times) >= self.requests_per_minute:
                oldest_request = self.request_times[0]
                wait_time = 60 - (current_time - oldest_request)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # Recurse to clean up and check again
                    return await self.acquire()
            
            # Record this request
            self.request_times.append(current_time)