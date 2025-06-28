"""
WebSocket server with SSL support for secure real-time aircraft data streaming.
"""

import asyncio
import logging
from server import websocket_handler
from backend.utils.ssl_utils import create_ssl_context, log_ssl_instructions
from backend.utils.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main server entry point with SSL support."""
    import websockets

    # Create SSL context
    try:
        ssl_context = create_ssl_context()
        log_ssl_instructions("WebSocket SSL Server")
    except Exception as e:
        logger.error(f"Failed to create SSL context: {e}")
        return

    logger.info(f"Starting WebSocket SSL server on {Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_SSL_PORT}")

    # Start WebSocket server with SSL
    async with websockets.serve(
        websocket_handler,
        Config.WEBSOCKET_HOST,
        Config.WEBSOCKET_SSL_PORT,
        ssl=ssl_context,
        # Additional parameters for better compatibility
        compression=None,  # Disable compression for better compatibility
        max_size=10 * 1024 * 1024,  # 10MB max message size
        ping_interval=20,  # Send ping every 20 seconds
        ping_timeout=10,  # Wait 10 seconds for pong
        close_timeout=10,  # Wait 10 seconds for close
    ):
        logger.info(f"SSL Server running at wss://{Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_SSL_PORT}/ws")
        logger.info(
            "WebSocket parameters: SSL enabled, compression=None, ping_interval=20s"
        )

        # Also run the non-SSL server on the original port for backward compatibility
        try:
            async with websockets.serve(
                websocket_handler,
                Config.WEBSOCKET_HOST,
                Config.WEBSOCKET_PORT,
                compression=None,
                max_size=10 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
            ):
                logger.info(
                    f"Also running non-SSL server at ws://{Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_PORT}/ws"
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
