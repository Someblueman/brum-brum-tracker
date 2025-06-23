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
        super().__init__(*args, directory='frontend', **kwargs)
    
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


def generate_self_signed_cert():
    """Generate a self-signed certificate if it doesn't exist."""
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        print("\nGenerating self-signed certificate...")
        import subprocess
        
        # Generate self-signed certificate
        cmd = [
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
            '-keyout', KEY_FILE, '-out', CERT_FILE,
            '-days', '365', '-nodes',
            '-subj', '/CN=localhost'
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"Certificate generated: {CERT_FILE}")
            print(f"Private key generated: {KEY_FILE}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to generate certificate: {e}")
            print("Please install OpenSSL or generate certificate manually:")
            print("openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes")
            sys.exit(1)
        except FileNotFoundError:
            print("OpenSSL not found. Please install it or generate certificate manually:")
            print("openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes")
            sys.exit(1)


def main():
    """Start the HTTPS server."""
    # Generate certificate if needed
    generate_self_signed_cert()
    
    print(f"\nStarting HTTPS frontend server on https://{FRONTEND_HOST}:{HTTPS_PORT}")
    print(f"Serving files from: {os.path.abspath('frontend')}")
    print("\n⚠️  IMPORTANT: You will see a certificate warning in your browser.")
    print("   This is normal for self-signed certificates.")
    print("   Click 'Advanced' and 'Proceed' to continue.")
    print("\n📱 For iPad/iPhone:")
    print("   1. Open https://[your-computer-ip]:8443 in Safari")
    print("   2. Accept the certificate warning")
    print("   3. The compass should work after granting permission")
    print("\nMake sure the backend WebSocket server is also running!")
    print("Backend should be started with: python backend/app.py")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(CERT_FILE, KEY_FILE)
        
        # Create and start HTTPS server
        with socketserver.TCPServer((FRONTEND_HOST, HTTPS_PORT), CORSRequestHandler) as httpd:
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