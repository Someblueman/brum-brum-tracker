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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.constants import FRONTEND_HOST

# HTTPS configuration
HTTPS_PORT = 8443
CERT_FILE = 'cert.pem'
KEY_FILE = 'key.pem'


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers."""
    
    def __init__(self, *args, **kwargs):
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


def check_mkcert_certificates():
    """Check if mkcert certificates exist, provide instructions if not."""
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        print("\n⚠️  Certificate files not found!")
        print("\nTo generate certificates using mkcert:")
        print("1. Install mkcert:")
        print("   - macOS: brew install mkcert")
        print("   - Linux: Check your package manager or download from GitHub")
        print("   - Windows: Use Chocolatey or Scoop")
        print("\n2. Install the root certificate (optional but recommended):")
        print("   mkcert -install")
        print("\n3. Generate certificates:")
        print("   mkcert -cert-file cert.pem -key-file key.pem localhost 127.0.0.1 ::1 [your-local-ip]")
        print("\n4. Or run the provided setup script:")
        print("   ./setup_mkcert.sh")
        print("\nAlternatively, you can generate a self-signed certificate with:")
        print("openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes")
        sys.exit(1)


def main():
    """Start the HTTPS server."""
    # Check for certificates
    check_mkcert_certificates()
    
    print(f"\nStarting HTTPS frontend server on https://{FRONTEND_HOST}:{HTTPS_PORT}")
    print(f"Serving files from: {os.path.abspath('frontend')}")
    
    # Check if using mkcert certificates
    try:
        with open(CERT_FILE, 'r') as f:
            cert_content = f.read()
            if 'mkcert' in cert_content:
                print("\n✅ Using mkcert certificates - should be trusted automatically!")
                print("   (If you haven't run 'mkcert -install', you may still see warnings)")
            else:
                print("\n⚠️  Using self-signed certificates - you will see security warnings.")
                print("   Click 'Advanced' and 'Proceed' to continue.")
    except:
        pass
    
    print("\n📱 For PWA installation:")
    print("   1. Open https://[your-computer-ip]:8443 in Safari (iOS) or Chrome (Android)")
    print("   2. For iOS: Tap Share button → Add to Home Screen")
    print("   3. For Android: Tap menu → Install app")
    print("\nMake sure the backend WebSocket server is also running!")
    print("Backend should be started with: python backend/app.py")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(CERT_FILE, KEY_FILE)
        
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
        with QuietTCPServer((FRONTEND_HOST, HTTPS_PORT), CORSRequestHandler) as httpd:
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