#!/usr/bin/env python3
"""
Simple HTTP server to run frontend tests
"""

import os
import sys
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread

class TestHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set directory to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        super().__init__(*args, directory=project_root, **kwargs)
    
    def log_message(self, format, *args):
        # Suppress normal HTTP logging
        pass

def run_test_server(port=8888):
    """Run HTTP server for frontend tests"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, TestHTTPRequestHandler)
    
    print(f"Frontend test server running on http://localhost:{port}")
    print(f"Open http://localhost:{port}/tests/frontend/test-runner.html to run tests")
    print("Press Ctrl+C to stop the server")
    
    # Open browser automatically
    test_url = f"http://localhost:{port}/tests/frontend/test-runner.html"
    
    def open_browser():
        time.sleep(1)  # Give server time to start
        webbrowser.open(test_url)
    
    browser_thread = Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down test server...")
        httpd.shutdown()

if __name__ == '__main__':
    # Check if port is provided as argument
    port = 8888
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)
    
    run_test_server(port)