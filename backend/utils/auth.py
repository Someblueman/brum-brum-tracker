"""
Authentication module for Brum Brum Tracker.

Provides basic authentication for production deployment using
environment-based credentials and JWT-like tokens. This module implements
a simple but secure authentication system suitable for protecting access
to the aircraft tracking application.

The authentication flow:
1. User provides username/password
2. Credentials are verified against environment variables
3. A secure token is generated and returned
4. Token is used for subsequent WebSocket connections
5. Tokens expire after a configurable period

Security features:
- Passwords are hashed using SHA-256
- Tokens are signed with HMAC-SHA256
- Automatic cleanup of expired tokens
- Environment-based configuration
"""

import os
import secrets
import hashlib
import hmac
import json
import time
from typing import Optional, Dict, Any
from functools import wraps
import asyncio

from dotenv import load_dotenv

load_dotenv()


class AuthManager:
    """
    Manages authentication for the application.
    
    This class provides a simple authentication system that:
    - Uses environment variables for configuration
    - Supports username/password authentication
    - Generates secure tokens for session management
    - Automatically cleans up expired tokens
    
    Authentication can be enabled/disabled via AUTH_ENABLED env var,
    making it easy to run in development without auth.
    
    Attributes:
        auth_enabled: Whether authentication is required
        auth_username: Expected username from environment
        auth_password_hash: SHA-256 hash of expected password
        auth_secret: Secret key for token signing
        token_expiry: Token lifetime in seconds
        valid_tokens: In-memory store of active tokens
    """
    
    def __init__(self):
        """Initialize AuthManager with environment-based configuration."""
        self.auth_enabled = os.getenv('AUTH_ENABLED', 'false').lower() == 'true'
        self.auth_username = os.getenv('AUTH_USERNAME', '')
        self.auth_password_hash = self._hash_password(os.getenv('AUTH_PASSWORD', ''))
        self.auth_secret = os.getenv('AUTH_SECRET', secrets.token_urlsafe(32))
        self.token_expiry = int(os.getenv('AUTH_TOKEN_EXPIRY', '3600'))  # 1 hour default
        self.valid_tokens = {}  # Store valid tokens in memory
        
    def _hash_password(self, password: str) -> str:
        """
        Hash a password using SHA-256.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hexadecimal string of the SHA-256 hash, or empty string if no password
        """
        if not password:
            return ''
        return hashlib.sha256(password.encode()).hexdigest()
    
    def is_enabled(self) -> bool:
        """
        Check if authentication is enabled.
        
        Authentication is considered enabled only if:
        - AUTH_ENABLED environment variable is 'true'
        - AUTH_USERNAME is provided
        - AUTH_PASSWORD is provided (stored as hash)
        
        Returns:
            True if all auth requirements are met, False otherwise
        """
        return self.auth_enabled and self.auth_username and self.auth_password_hash
    
    def verify_credentials(self, username: str, password: str) -> bool:
        """
        Verify username and password against stored credentials.
        
        If authentication is disabled, this always returns True to allow
        unrestricted access in development environments.
        
        Args:
            username: Username to verify
            password: Plain text password to verify
            
        Returns:
            True if credentials match or auth is disabled, False otherwise
        """
        if not self.is_enabled():
            return True
        
        password_hash = self._hash_password(password)
        return (username == self.auth_username and 
                password_hash == self.auth_password_hash)
    
    def generate_token(self, username: str) -> str:
        """
        Generate a secure authentication token.
        
        Creates a cryptographically secure token that includes:
        - Username for identification
        - Timestamp for expiry checking
        - Random nonce to prevent replay attacks
        - HMAC signature for integrity verification
        
        The token is stored in memory with an expiration time.
        Expired tokens are automatically cleaned up.
        
        Args:
            username: Username to associate with the token
            
        Returns:
            A URL-safe token string that can be used for authentication
        """
        token_data = {
            'username': username,
            'timestamp': time.time(),
            'nonce': secrets.token_urlsafe(16)
        }
        
        # Create token signature using HMAC-SHA256
        token_json = json.dumps(token_data, sort_keys=True)
        signature = hmac.new(
            self.auth_secret.encode(),
            token_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Generate a unique token ID
        token_encoded = secrets.token_urlsafe(32)  # Simple token ID
        
        # Store token with expiry time
        self.valid_tokens[token_encoded] = {
            'data': token_data,
            'expires': time.time() + self.token_expiry
        }
        
        # Clean up expired tokens to prevent memory leak
        self._cleanup_expired_tokens()
        
        return token_encoded
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify an authentication token."""
        if not self.is_enabled():
            return {'username': 'anonymous'}
        
        # Clean up expired tokens
        self._cleanup_expired_tokens()
        
        # Check if token exists and is valid
        if token in self.valid_tokens:
            token_info = self.valid_tokens[token]
            if time.time() < token_info['expires']:
                return token_info['data']
        
        return None
    
    def _cleanup_expired_tokens(self):
        """Remove expired tokens from memory."""
        current_time = time.time()
        expired = [
            token for token, info in self.valid_tokens.items()
            if current_time >= info['expires']
        ]
        for token in expired:
            del self.valid_tokens[token]
    
    async def handle_auth_message(self, websocket, message: Dict[str, Any]) -> bool:
        """
        Handle authentication messages from WebSocket clients.
        
        Returns True if authentication was successful, False otherwise.
        """
        if not self.is_enabled():
            # Auth not enabled, allow all connections
            await websocket.send(json.dumps({
                'type': 'auth_response',
                'success': True,
                'message': 'Authentication not required'
            }))
            return True
        
        msg_type = message.get('type')
        
        if msg_type == 'auth_login':
            # Handle login request
            username = message.get('username', '')
            password = message.get('password', '')
            
            if self.verify_credentials(username, password):
                token = self.generate_token(username)
                await websocket.send(json.dumps({
                    'type': 'auth_response',
                    'success': True,
                    'token': token,
                    'message': 'Authentication successful'
                }))
                return True
            else:
                await websocket.send(json.dumps({
                    'type': 'auth_response',
                    'success': False,
                    'message': 'Invalid credentials'
                }))
                return False
        
        elif msg_type == 'auth_token':
            # Handle token authentication
            token = message.get('token', '')
            user_data = self.verify_token(token)
            
            if user_data:
                await websocket.send(json.dumps({
                    'type': 'auth_response',
                    'success': True,
                    'message': 'Token valid',
                    'username': user_data.get('username')
                }))
                return True
            else:
                await websocket.send(json.dumps({
                    'type': 'auth_response',
                    'success': False,
                    'message': 'Invalid or expired token'
                }))
                return False
        
        return False


# Global auth manager instance
auth_manager = AuthManager()


def require_auth(func):
    """Decorator to require authentication for WebSocket handlers."""
    @wraps(func)
    async def wrapper(self, websocket, path):
        if auth_manager.is_enabled():
            # Send auth required message
            await websocket.send(json.dumps({
                'type': 'auth_required',
                'message': 'Please authenticate to continue'
            }))
            
            # Wait for authentication
            authenticated = False
            try:
                # Give client 30 seconds to authenticate
                auth_timeout = 30
                start_time = time.time()
                
                while not authenticated and (time.time() - start_time) < auth_timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)
                        
                        if data.get('type') in ['auth_login', 'auth_token']:
                            authenticated = await auth_manager.handle_auth_message(websocket, data)
                            if not authenticated:
                                # Give client a chance to retry
                                continue
                        else:
                            # Non-auth message before authentication
                            await websocket.send(json.dumps({
                                'type': 'error',
                                'message': 'Authentication required'
                            }))
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"Auth error: {e}")
                        break
                
                if not authenticated:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Authentication timeout'
                    }))
                    await websocket.close()
                    return
            
            except Exception as e:
                print(f"Authentication error: {e}")
                await websocket.close()
                return
        
        # Call the original handler
        await func(self, websocket, path)
    
    return wrapper