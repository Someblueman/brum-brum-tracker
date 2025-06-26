#!/usr/bin/env python3
"""
Run the refactored WebSocket server.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.server_refactored import main
import asyncio

if __name__ == "__main__":
    try:
        print("Starting refactored Brum Brum Tracker WebSocket server...")
        print("Using service layer architecture")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)