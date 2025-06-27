# Brum Brum Tracker PWA Setup Guide

This guide will help you set up the Brum Brum Tracker as a Progressive Web App (PWA) with proper HTTPS certificates.

## Prerequisites

- Node.js or Python (for running servers)
- mkcert (for trusted certificates)
- A modern browser (Chrome, Safari, Edge)

## Quick Start

1. **Install mkcert** (if not already installed):
   ```bash
   # macOS
   brew install mkcert
   
   # Linux
   # Check your package manager or download from GitHub
   
   # Windows
   # Use Chocolatey: choco install mkcert
   # Or Scoop: scoop install mkcert
   ```

2. **Run the setup script**:
   ```bash
   ./setup_mkcert.sh
   ```
   
   This script will:
   - Install the mkcert root certificate (requires sudo)
   - Generate certificates for localhost and your local IP
   - Display certificate details

3. **Start the servers**:
   ```bash
   # Terminal 1: Backend WebSocket server
   python backend/app_ssl.py
   
   # Terminal 2: Frontend HTTPS server
   python serve_https.py
   ```

4. **Access the app**:
   - Open https://localhost:8443 or https://[your-ip]:8443
   - The certificate should be trusted automatically if you ran `mkcert -install`

## Installing as a PWA

### iOS (iPhone/iPad)
1. Open the app in Safari (must be Safari, not Chrome)
2. Tap the Share button (square with arrow)
3. Scroll down and tap "Add to Home Screen"
4. Give it a name and tap "Add"

### Android
1. Open the app in Chrome
2. Tap the three-dot menu
3. Tap "Install app" or "Add to Home Screen"
4. Follow the prompts

### Desktop (Chrome/Edge)
1. Look for the install icon in the address bar
2. Or go to the three-dot menu → "Install Brum Brum Tracker"

## Troubleshooting

### Certificate not trusted
If you see certificate warnings:

1. **Make sure you installed the root certificate**:
   ```bash
   mkcert -install
   ```

2. **For iOS devices**, you need to:
   - Get the root certificate:
     ```bash
     mkcert -CAROOT
     # This shows the directory containing rootCA.pem
     ```
   - Transfer rootCA.pem to your iOS device (AirDrop, email, etc.)
   - Open the file on iOS and install the profile
   - Go to Settings → General → About → Certificate Trust Settings
   - Enable trust for the mkcert certificate

### Service Worker not registering
1. Check the browser console for errors
2. Ensure you're using HTTPS (not HTTP)
3. Try clearing browser cache and cookies
4. In Chrome DevTools → Application → Service Workers, try "Unregister" and reload

### PWA not installable
1. Ensure all PWA requirements are met:
   - Valid manifest.json
   - Service worker registered
   - HTTPS connection
   - Icons provided
2. Check Chrome DevTools → Application → Manifest for issues

### WebSocket connection fails
1. Make sure the backend SSL server is running
2. Accept the certificate at https://localhost:8001 directly
3. Check that ports 8001 (backend) and 8443 (frontend) are not blocked

## Manual Certificate Generation

If the setup script doesn't work, generate certificates manually:

```bash
# With mkcert (recommended)
mkcert -cert-file cert.pem -key-file key.pem localhost 127.0.0.1 ::1 192.168.1.100

# With OpenSSL (self-signed, will show warnings)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

## Development Tips

1. **Test offline functionality**:
   - Install the PWA
   - Turn on airplane mode
   - The app should still load (though live data won't update)

2. **Update the service worker**:
   - Change the `CACHE_NAME` version in service-worker.js
   - Reload the page twice (once to install, once to activate)

3. **Debug on mobile**:
   - iOS: Use Safari on Mac with iPhone connected
   - Android: Use Chrome DevTools with USB debugging

## Security Notes

- The mkcert root certificate is only for development
- Never share your rootCA-key.pem file
- For production, use real certificates from Let's Encrypt or similar

## Features

When properly installed as a PWA:
- Works offline (shows cached content)
- Installable to home screen
- Full-screen experience
- Push notifications (if implemented)
- Background sync (if implemented)
- Device orientation access for compass feature