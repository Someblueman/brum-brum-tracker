#!/bin/bash

# Setup script for mkcert certificates
echo "Setting up mkcert for Brum Brum Tracker PWA..."

# Install root certificate (requires sudo)
echo "Installing mkcert root certificate..."
echo "You will be prompted for your password to trust the certificate."
mkcert -install

# Get local IP address
LOCAL_IP=$(ipconfig getifaddr en0)
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP=$(ipconfig getifaddr en1)
fi

echo "Local IP address: $LOCAL_IP"

# Generate certificates for all necessary domains
echo "Generating certificates..."
mkcert -cert-file cert.pem -key-file key.pem \
    localhost \
    127.0.0.1 \
    ::1 \
    $LOCAL_IP \
    "*.localhost" \
    "localhost.local"

echo "Certificates generated:"
echo "  - cert.pem"
echo "  - key.pem"

# Show certificate info
echo ""
echo "Certificate details:"
openssl x509 -in cert.pem -text -noout | grep -E "(Subject:|DNS:|IP Address:)"

echo ""
echo "Setup complete! The certificates are ready to use."
echo ""
echo "To trust these certificates on iOS devices:"
echo "1. Run: mkcert -CAROOT"
echo "2. Transfer the rootCA.pem file to your iOS device (AirDrop, email, etc.)"
echo "3. Open the file on iOS and install the profile"
echo "4. Go to Settings > General > About > Certificate Trust Settings"
echo "5. Enable trust for the mkcert certificate"