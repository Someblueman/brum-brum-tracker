"""
Shared SSL utilities for certificate management and SSL context creation.
"""

import ssl
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SSLConfig:
    """SSL configuration constants."""
    # SSL certificates are now in config/ssl directory
    SSL_DIR = Path(__file__).parent.parent.parent / "config" / "ssl"
    CERT_FILE = str(SSL_DIR / "cert.pem")
    KEY_FILE = str(SSL_DIR / "key.pem")
    
    # Instructions for certificate generation
    MKCERT_INSTRUCTIONS = """
To generate certificates using mkcert:
1. Install mkcert:
   - macOS: brew install mkcert
   - Linux: Check your package manager or download from GitHub
   - Windows: Use Chocolatey or Scoop

2. Install the root certificate (optional but recommended):
   mkcert -install

3. Generate certificates:
   mkcert -cert-file config/ssl/cert.pem -key-file config/ssl/key.pem localhost 127.0.0.1 ::1 [your-local-ip]

4. Or run the provided setup script:
   ./scripts/setup_mkcert.sh

Alternatively, generate a self-signed certificate with:
   openssl req -x509 -newkey rsa:4096 -keyout config/ssl/key.pem -out config/ssl/cert.pem -days 365 -nodes
"""


def check_certificates_exist(cert_file: str = SSLConfig.CERT_FILE, 
                           key_file: str = SSLConfig.KEY_FILE) -> bool:
    """Check if SSL certificate files exist."""
    cert_path = Path(cert_file)
    key_path = Path(key_file)
    return cert_path.exists() and key_path.exists()


def is_mkcert_certificate(cert_file: str = SSLConfig.CERT_FILE) -> bool:
    """Check if the certificate was generated by mkcert."""
    try:
        with open(cert_file, 'r') as f:
            cert_content = f.read()
            return 'mkcert' in cert_content
    except Exception:
        return False


def get_certificate_info(cert_file: str = SSLConfig.CERT_FILE) -> Tuple[bool, str]:
    """
    Get information about the certificate.
    
    Returns:
        Tuple of (exists, info_message)
    """
    if not check_certificates_exist(cert_file):
        return False, "Certificate files not found"
    
    if is_mkcert_certificate(cert_file):
        return True, "Using mkcert certificates - should be trusted automatically!"
    
    return True, "Using self-signed certificates"


def create_ssl_context(cert_file: Optional[str] = None, 
                      key_file: Optional[str] = None,
                      protocol: int = ssl.PROTOCOL_TLS_SERVER) -> ssl.SSLContext:
    """
    Create and configure an SSL context.
    
    Args:
        cert_file: Path to certificate file (default: cert.pem)
        key_file: Path to key file (default: key.pem)
        protocol: SSL protocol to use
        
    Returns:
        Configured SSL context
        
    Raises:
        RuntimeError: If certificate files don't exist
        ssl.SSLError: If certificates are invalid
    """
    cert_file = cert_file or SSLConfig.CERT_FILE
    key_file = key_file or SSLConfig.KEY_FILE
    
    # Check if certificates exist
    if not check_certificates_exist(cert_file, key_file):
        logger.error("SSL certificate files not found!")
        logger.error(SSLConfig.MKCERT_INSTRUCTIONS)
        raise RuntimeError("SSL certificate files not found")
    
    # Create SSL context
    ssl_context = ssl.SSLContext(protocol)
    
    try:
        ssl_context.load_cert_chain(cert_file, key_file)
    except ssl.SSLError as e:
        logger.error(f"Failed to load SSL certificates: {e}")
        logger.error("Please check that your certificate files are valid")
        raise
    
    # Log certificate info
    exists, info = get_certificate_info(cert_file)
    logger.info(info)
    
    return ssl_context


def log_ssl_instructions(service_name: str = "SSL Server"):
    """Log SSL setup instructions and warnings."""
    exists, info = get_certificate_info()
    
    if not exists:
        logger.error(f"\n{service_name} - Certificate Setup Required")
        logger.error(SSLConfig.MKCERT_INSTRUCTIONS)
    else:
        logger.info(f"\n{service_name} - {info}")
        if not is_mkcert_certificate():
            logger.info("You will see a certificate warning in your browser.")
            logger.info("This is normal for self-signed certificates.")