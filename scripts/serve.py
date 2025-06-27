#!/usr/bin/env python3
"""
Simple HTTP server for serving the frontend files.
Includes CORS headers for WebSocket compatibility.
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path
from typing import Any, Tuple

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from utils.config import Config


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Set the directory to serve
        super().__init__(*args, directory='frontend/src', **kwargs)
    
    def end_headers(self) -> None:
        """Add CORS headers to response."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()
    
    def do_OPTIONS(self) -> None:
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format: str, *args: Any) -> None:
        """Custom log format."""
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    """Start the HTTP server."""
    print(f"Starting frontend server on http://{Config.FRONTEND_HOST}:{Config.FRONTEND_PORT}")
    print(f"Serving files from: {os.path.abspath('frontend')}")
    print("\nMake sure the backend WebSocket server is also running!")
    print("Backend should be started with: python backend/app.py")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        with socketserver.TCPServer((Config.FRONTEND_HOST, Config.FRONTEND_PORT), CORSRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()