"""
WebSocket server with SSL support for secure real-time aircraft data streaming.
"""

import asyncio
import json
import logging
import ssl
import os
import subprocess
from pathlib import Path
from backend.server import AircraftTracker, websocket_handler
from utils.constants import WEBSOCKET_HOST, WEBSOCKET_PORT

# SSL configuration
SSL_CERT_FILE = "cert.pem"
SSL_KEY_FILE = "key.pem"
WSS_PORT = 8001  # Use 8001 for WSS (8443 is used by frontend HTTPS)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_mkcert_certificates():
    """Check if mkcert certificates exist."""
    cert_path = Path(SSL_CERT_FILE)
    key_path = Path(SSL_KEY_FILE)

    if cert_path.exists() and key_path.exists():
        logger.info("Using existing SSL certificate")
        
        # Check if using mkcert certificates
        try:
            with open(cert_path, 'r') as f:
                cert_content = f.read()
                if 'mkcert' in cert_content:
                    logger.info("✅ Using mkcert certificates - should be trusted automatically!")
                else:
                    logger.info("⚠️  Using self-signed certificates")
        except:
            pass
        
        return True

    logger.error("\n⚠️  Certificate files not found!")
    logger.error("\nTo generate certificates using mkcert:")
    logger.error("1. Install mkcert:")
    logger.error("   - macOS: brew install mkcert")
    logger.error("   - Linux: Check your package manager")
    logger.error("   - Windows: Use Chocolatey or Scoop")
    logger.error("\n2. Install the root certificate (optional but recommended):")
    logger.error("   mkcert -install")
    logger.error("\n3. Generate certificates:")
    logger.error("   mkcert -cert-file cert.pem -key-file key.pem localhost 127.0.0.1 ::1 [your-local-ip]")
    logger.error("\n4. Or run the provided setup script:")
    logger.error("   ./setup_mkcert.sh")
    logger.error("\nAlternatively, generate a self-signed certificate with:")
    logger.error("   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes")
    return False


def create_ssl_context():
    """Create SSL context for WSS."""
    # Check for certificates
    if not check_mkcert_certificates():
        raise RuntimeError("SSL certificate files not found")

    # Create SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(SSL_CERT_FILE, SSL_KEY_FILE)

    return ssl_context


async def main():
    """Main server entry point with SSL support."""
    import websockets

    # Create SSL context
    try:
        ssl_context = create_ssl_context()
    except Exception as e:
        logger.error(f"Failed to create SSL context: {e}")
        return

    logger.info(f"Starting WebSocket SSL server on {WEBSOCKET_HOST}:{WSS_PORT}")

    # Start WebSocket server with SSL
    async with websockets.serve(
        websocket_handler,
        WEBSOCKET_HOST,
        WSS_PORT,
        ssl=ssl_context,
        # Additional parameters for better compatibility
        compression=None,  # Disable compression for better compatibility
        max_size=10 * 1024 * 1024,  # 10MB max message size
        ping_interval=20,  # Send ping every 20 seconds
        ping_timeout=10,  # Wait 10 seconds for pong
        close_timeout=10,  # Wait 10 seconds for close
    ):
        logger.info(f"SSL Server running at wss://{WEBSOCKET_HOST}:{WSS_PORT}/ws")
        logger.info(
            "WebSocket parameters: SSL enabled, compression=None, ping_interval=20s"
        )
        logger.info(
            "\n⚠️  IMPORTANT: You will see a certificate warning in your browser."
        )
        logger.info("   This is normal for self-signed certificates.")

        # Also run the non-SSL server on the original port for backward compatibility
        try:
            async with websockets.serve(
                websocket_handler,
                WEBSOCKET_HOST,
                WEBSOCKET_PORT,
                compression=None,
                max_size=10 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
            ):
                logger.info(
                    f"Also running non-SSL server at ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}/ws"
                )
                await asyncio.Future()  # Run forever
        except Exception as e:
            logger.warning(f"Could not start non-SSL server: {e}")
            logger.info("Running SSL-only mode")
            await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
