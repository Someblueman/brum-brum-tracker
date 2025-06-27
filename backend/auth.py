"""
Authentication module for Brum Brum Tracker.

Provides basic authentication for production deployment using
environment-based credentials and JWT tokens.
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
    """Manages authentication for the application."""
    
    def __init__(self):
        self.auth_enabled = os.getenv('AUTH_ENABLED', 'false').lower() == 'true'
        self.auth_username = os.getenv('AUTH_USERNAME', '')
        self.auth_password_hash = self._hash_password(os.getenv('AUTH_PASSWORD', ''))
        self.auth_secret = os.getenv('AUTH_SECRET', secrets.token_urlsafe(32))
        self.token_expiry = int(os.getenv('AUTH_TOKEN_EXPIRY', '3600'))  # 1 hour default
        self.valid_tokens = {}  # Store valid tokens in memory
        
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        if not password:
            return ''
        return hashlib.sha256(password.encode()).hexdigest()
    
    def is_enabled(self) -> bool:
        """Check if authentication is enabled."""
        return self.auth_enabled and self.auth_username and self.auth_password_hash
    
    def verify_credentials(self, username: str, password: str) -> bool:
        """Verify username and password."""
        if not self.is_enabled():
            return True
        
        password_hash = self._hash_password(password)
        return (username == self.auth_username and 
                password_hash == self.auth_password_hash)
    
    def generate_token(self, username: str) -> str:
        """Generate a simple authentication token."""
        token_data = {
            'username': username,
            'timestamp': time.time(),
            'nonce': secrets.token_urlsafe(16)
        }
        
        # Create token signature
        token_json = json.dumps(token_data, sort_keys=True)
        signature = hmac.new(
            self.auth_secret.encode(),
            token_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Combine data and signature
        token = f"{token_json}:{signature}"
        token_encoded = secrets.token_urlsafe(32)  # Simple token ID
        
        # Store token with expiry
        self.valid_tokens[token_encoded] = {
            'data': token_data,
            'expires': time.time() + self.token_expiry
        }
        
        # Clean up expired tokens
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