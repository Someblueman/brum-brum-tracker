#!/usr/bin/env python3
"""
HTTPS server for serving the frontend files with SSL support.
Required for device orientation API on iOS devices.
"""

import http.server
import ssl
import socketserver
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import Config
from backend.ssl_utils import create_ssl_context, SSLConfig, check_certificates_exist


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Set the directory to serve
        try:
            super().__init__(*args, directory='frontend', **kwargs)
        except (ConnectionResetError, BrokenPipeError, ssl.SSLError) as e:
            # Silently handle connection errors
            pass
    
    def end_headers(self):
        """Add CORS headers to response."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom log format."""
        print(f"{self.address_string()} - {format % args}")
    
    def handle(self):
        """Handle requests with connection error handling."""
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError, ssl.SSLError) as e:
            # These errors are common with HTTPS and service workers
            pass




def main():
    """Start the HTTPS server."""
    # Check for certificates
    if not check_certificates_exist():
        print("\nCertificate files not found!")
        print(SSLConfig.MKCERT_INSTRUCTIONS)
        sys.exit(1)
    
    print(f"\nStarting HTTPS frontend server on https://{Config.FRONTEND_HOST}:{Config.FRONTEND_HTTPS_PORT}")
    print(f"Serving files from: {os.path.abspath('frontend')}")
    
    print("\n📱 For PWA installation:")
    print("   1. Open https://[your-computer-ip]:8443 in Safari (iOS) or Chrome (Android)")
    print("   2. For iOS: Tap Share button → Add to Home Screen")
    print("   3. For Android: Tap menu → Install app")
    print("\nMake sure the backend WebSocket server is also running!")
    print("Backend should be started with: python backend/app.py")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        # Create SSL context using shared utility
        context = create_ssl_context()
        
        # Custom TCP server that handles SSL errors gracefully
        class QuietTCPServer(socketserver.TCPServer):
            def handle_error(self, request, client_address):
                # Get the error type
                exc_type = sys.exc_info()[0]
                if exc_type in (ConnectionResetError, BrokenPipeError, ssl.SSLError):
                    # Silently ignore SSL and connection errors
                    pass
                else:
                    # Let other errors bubble up
                    super().handle_error(request, client_address)
        
        # Create and start HTTPS server
        with QuietTCPServer((Config.FRONTEND_HOST, Config.FRONTEND_HTTPS_PORT), CORSRequestHandler) as httpd:
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()