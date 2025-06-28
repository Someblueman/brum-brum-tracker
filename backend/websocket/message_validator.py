"""
WebSocket message validation module.

This module provides comprehensive schema validation for all WebSocket messages
exchanged between clients and the server. It ensures data integrity, prevents
injection attacks, and maintains protocol consistency.

The validator enforces:
- Message structure and type safety
- Field presence and data types
- Value ranges and constraints
- Protection against malformed data

All messages must pass validation before being processed, providing a secure
communication layer for the real-time aircraft tracking system.
"""

import json
from typing import Dict, Any
from enum import Enum


class MessageType(Enum):
    """
    Valid WebSocket message types.
    
    Defines all allowed message types in the protocol, separated by
    direction (client-to-server vs server-to-client) for clarity.
    """
    # Client to Server messages
    CLIENT_HELLO = "hello"          # Initial connection handshake
    GET_LOGBOOK = "get_logbook"     # Request logbook entries
    
    # Server to Client messages
    AIRCRAFT_UPDATE = "aircraft"     # Real-time aircraft position update
    AIRCRAFT_LOST = "aircraft_lost"  # Aircraft no longer visible
    LOGBOOK_DATA = "logbook"        # Logbook entries response
    ERROR = "error"                 # Error notification


class ValidationError(Exception):
    """
    Custom exception for message validation errors.
    
    Raised when a message fails validation. The error message should
    be safe to send back to the client without exposing internal details.
    """
    pass


class MessageValidator:
    """
    Validates WebSocket messages between client and server.
    
    This class provides static methods to validate all message types,
    ensuring they conform to the expected schema. It acts as a security
    barrier, preventing malformed or malicious messages from being processed.
    
    The validator checks:
    - JSON structure validity
    - Required fields presence
    - Data type correctness
    - Value range constraints
    - Message type validity
    """
    
    @staticmethod
    def validate_client_message(message: str) -> Dict[str, Any]:
        """
        Validate messages from client to server.
        
        Args:
            message: Raw message string from client
            
        Returns:
            Validated message dictionary
            
        Raises:
            ValidationError: If message is invalid
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
        
        if not isinstance(data, dict):
            raise ValidationError("Message must be a JSON object")
        
        # Check for required fields
        if "type" not in data:
            raise ValidationError("Message must have a 'type' field")
        
        msg_type = data["type"]
        
        # Validate based on message type
        if msg_type == MessageType.CLIENT_HELLO.value:
            return MessageValidator._validate_hello(data)
        elif msg_type == MessageType.GET_LOGBOOK.value:
            return MessageValidator._validate_get_logbook(data)
        else:
            raise ValidationError(f"Unknown message type: {msg_type}")
    
    @staticmethod
    def _validate_hello(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hello message from client."""
        # Hello message currently has no additional fields
        return data
    
    @staticmethod
    def _validate_get_logbook(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate get_logbook request."""
        # Optional limit parameter
        if "limit" in data:
            if not isinstance(data["limit"], int) or data["limit"] < 1:
                raise ValidationError("Limit must be a positive integer")
            if data["limit"] > 1000:
                raise ValidationError("Limit cannot exceed 1000")
        
        return data
    
    @staticmethod
    def validate_server_message(message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate messages from server to client.
        
        Args:
            message: Message dictionary to send
            
        Returns:
            Validated message dictionary
            
        Raises:
            ValidationError: If message is invalid
        """
        if not isinstance(message, dict):
            raise ValidationError("Message must be a dictionary")
        
        if "type" not in message:
            raise ValidationError("Message must have a 'type' field")
        
        msg_type = message["type"]
        
        # Validate based on message type
        if msg_type == MessageType.AIRCRAFT_UPDATE.value:
            return MessageValidator._validate_aircraft_update(message)
        elif msg_type == MessageType.AIRCRAFT_LOST.value:
            return MessageValidator._validate_aircraft_lost(message)
        elif msg_type == MessageType.LOGBOOK_DATA.value:
            return MessageValidator._validate_logbook_data(message)
        elif msg_type == MessageType.ERROR.value:
            return MessageValidator._validate_error(message)
        else:
            raise ValidationError(f"Unknown message type: {msg_type}")
    
    @staticmethod
    def _validate_aircraft_update(message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate aircraft update message."""
        required_fields = [
            "callsign", "distance", "altitude", "speed", 
            "bearing", "elevation", "track", "aircraft_type"
        ]
        
        for field in required_fields:
            if field not in message:
                raise ValidationError(f"Aircraft update missing required field: {field}")
        
        # Validate numeric fields
        numeric_fields = ["distance", "altitude", "speed", "bearing", "elevation", "track"]
        for field in numeric_fields:
            if not isinstance(message[field], (int, float)):
                raise ValidationError(f"{field} must be numeric")
        
        # Validate ranges
        if not 0 <= message["bearing"] <= 360:
            raise ValidationError("Bearing must be between 0 and 360")
        
        if not -90 <= message["elevation"] <= 90:
            raise ValidationError("Elevation must be between -90 and 90")
        
        if message["altitude"] < 0:
            raise ValidationError("Altitude cannot be negative")
        
        if message["speed"] < 0:
            raise ValidationError("Speed cannot be negative")
        
        return message
    
    @staticmethod
    def _validate_aircraft_lost(message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate aircraft lost message."""
        # No additional validation needed
        return message
    
    @staticmethod
    def _validate_logbook_data(message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate logbook data message."""
        if "entries" not in message:
            raise ValidationError("Logbook data must have 'entries' field")
        
        if not isinstance(message["entries"], list):
            raise ValidationError("Entries must be a list")
        
        for entry in message["entries"]:
            if not isinstance(entry, dict):
                raise ValidationError("Each entry must be a dictionary")
            
            required_fields = ["id", "spotted_at", "aircraft_type"]
            for field in required_fields:
                if field not in entry:
                    raise ValidationError(f"Logbook entry missing field: {field}")
        
        return message
    
    @staticmethod
    def _validate_error(message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate error message."""
        if "error" not in message:
            raise ValidationError("Error message must have 'error' field")
        
        if not isinstance(message["error"], str):
            raise ValidationError("Error field must be a string")
        
        return message
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 100) -> str:
        """
        Sanitize string input to prevent XSS and injection attacks.
        
        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return ""
        
        # Strip whitespace
        value = value.strip()
        
        # Limit length
        value = value[:max_length]
        
        # Remove potentially dangerous characters
        dangerous_chars = ["<", ">", "&", '"', "'", "/", "\\"]
        for char in dangerous_chars:
            value = value.replace(char, "")
        
        return value
    
    @staticmethod
    def sanitize_aircraft_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize aircraft data before sending to frontend.
        
        Args:
            data: Aircraft data dictionary
            
        Returns:
            Sanitized data
        """
        if "callsign" in data and data["callsign"]:
            data["callsign"] = MessageValidator.sanitize_string(str(data["callsign"]), 20)
        
        if "aircraft_type" in data and data["aircraft_type"]:
            data["aircraft_type"] = MessageValidator.sanitize_string(str(data["aircraft_type"]), 50)
        
        if "image_url" in data and data["image_url"]:
            # Basic URL validation
            url = str(data["image_url"])
            if not url.startswith(("http://", "https://")):
                data["image_url"] = None
        
        return data