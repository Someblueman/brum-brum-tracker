#!/usr/bin/env python3
"""
Brum Brum Tracker - SSL Backend Application
Entry point for the SSL-enabled plane tracking service
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from server_ssl import main


if __name__ == "__main__":
    print("Brum Brum Tracker Backend (SSL) - Starting...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)