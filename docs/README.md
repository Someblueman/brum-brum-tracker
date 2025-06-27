# Brum Brum Tracker

## A Real-Time Aircraft Tracker for Toddlers

Brum Brum Tracker is a delightful web application designed to help young children spot airplanes flying overhead. When an aircraft approaches, the app displays a directional arrow, shows a real photo of the plane, announces it with fun sounds, and presents flight information in kid-friendly language.

### The Concept & High-Level Strategy

The core idea is to build a small website that tracks flights in real-time near a specific location (your home).

This project is divided into two main components:
 -The Backend (The Brains): A program running on a home computer (like a Mac Mini or Raspberry Pi) that constantly fetches live flight data from a public API. It will do the "heavy lifting" of figuring out which planes are nearby and likely visible.
 -The Frontend (The Display): A simple, visual webpage displayed on an old iPad. This will show the fun stuff: an arrow pointing to the plane, a picture of the plane, its altitude and speed, and it will play a sound alert.

How It Works: The Workflow
 -Start Backend: You run the backend script on your home computer. It starts a local server and begins polling for flight data.
 -Open Frontend: You open the webpage on the iPad. It connects to the backend script.
 -Plane Approaches: The backend script identifies a plane that is getting close and is high enough in the sky to be visible.
 -Data is Sent: The backend fetches a picture and key flight details (altitude, speed, etc.) for that specific plane and sends all the relevant information to the iPad in real-time.
 -"Brum Brum!": The iPad's webpage receives the data, plays a "brum brum" sound, points an arrow towards the plane, and displays its picture and other fun facts.

## Getting Started

### Prerequisites
- Python 3.11 or higher
- Git
- A location with overhead air traffic

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/brum-brum-tracker.git
cd brum-brum-tracker
```

2. Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Configure your location:
```bash
cp .env.example .env
# Edit .env with your coordinates:
# HOME_LAT=your_latitude
# HOME_LON=your_longitude
```

### Running the Application

You need to run two servers. Choose either HTTP or HTTPS mode:

#### Option A: HTTPS Mode (Recommended for iPad/iPhone with compass)

1. **Backend (SSL WebSocket Server)** - Terminal 1:
```bash
python backend/app_ssl.py
```
This starts the secure WebSocket server on ports 8000 (ws) and 8001 (wss).

2. **Frontend (HTTPS Server)** - Terminal 2:
```bash
python serve_https.py
```
This serves the frontend on https://localhost:8443

3. **Access the Application**:
   - Open https://localhost:8443 in your browser
   - Accept the certificate warning
   - Or on iPad: https://[your-computer-ip]:8443
   - Click "Enable Compass" when prompted (iOS devices)

#### Option B: HTTP Mode (Simple setup, no compass on iOS)

1. **Backend (WebSocket Server)** - Terminal 1:
```bash
python backend/app.py
```
This starts the WebSocket server on port 8000.

2. **Frontend (HTTP Server)** - Terminal 2:
```bash
python serve.py
```
This serves the frontend on http://localhost:8080

3. **Access the Application**:
   - Open http://localhost:8080 in your browser
   - Or on iPad: http://[your-computer-ip]:8080

### iPad Setup

1. Find your computer's IP address:
   - Mac: `ifconfig | grep inet`
   - Windows: `ipconfig`

2. On iPad Safari, navigate to `http://[your-ip]:8080`

3. Add to Home Screen:
   - Tap the Share button
   - Select "Add to Home Screen"

4. Enable Guided Access (for child safety):
   - Settings → Accessibility → Guided Access
   - Start session and disable screen areas

### Audio Features

The app includes multiple audio options:
- **ATC sounds**: 5 realistic air traffic control clips (atc_1.mp3 through atc_5.mp3)
- **Family voices**: Custom greetings from different family members
- **Start buttons**: Choose between "Mamma & Pappa" or "Mormor & Pops" greeting sets

Audio files are located in `frontend/assets/`

### Current Features

- **Real-time aircraft tracking** via OpenSky Network API
- **WebSocket streaming** with automatic reconnection
- **Direction arrow** pointing to aircraft (compass support on iOS/Android)
- **Aircraft information** with simplified, kid-friendly plane types
- **Visual notifications** with animated clouds and glow effects
- **Captain's Logbook** - Track all planes spotted over time
- **Dashboard view** - See all approaching aircraft with ETAs
- **Smart polling** - Only active when clients connected
- **PWA support** - Install as app on phones/tablets
- **Dual language support** - Swedish/English family greetings

### Architecture

```
┌─────────────┐     WebSocket      ┌─────────────┐     HTTP        ┌─────────────┐
│   Backend   │ ◄─────────────────► │  Frontend   │ ◄──────────────► │    iPad     │
│  Port 8000  │                     │  Port 8080  │                  │   Browser   │
└─────────────┘                     └─────────────┘                  └─────────────┘
      │                                                                      │
      │                                                                      │
      ▼                                                                      ▼
┌─────────────┐                                                      ┌─────────────┐
│  OpenSky    │                                                      │   Device    │
│     API     │                                                      │ Orientation │
└─────────────┘                                                      └─────────────┘
```

### Troubleshooting

#### Connection Issues
- **"Connection refused" or "WebSocket error"**:
  - Ensure both backend and frontend servers are running
  - Check the browser console for specific error messages
  - Verify ports are not blocked by firewall
  
- **"Address already in use" error**:
  ```bash
  # Find what's using the port
  lsof -i :PORT_NUMBER
  # Kill the process
  kill PID
  ```

#### No Aircraft Showing
- **Check backend logs**: Look for "Received X aircraft from API"
- **Verify location**: Ensure `.env` has correct HOME_LAT and HOME_LON
- **API credentials**: Confirm OpenSky credentials are valid
- **Coverage area**: Not all areas have aircraft coverage

#### Compass/Arrow Issues
- **Arrow not rotating on iPad/iPhone**:
  1. Must use HTTPS mode (not HTTP)
  2. Tap "Enable Compass" button when it appears
  3. Grant permission when prompted
  4. If denied: Settings → Safari → Motion & Orientation Access
  
- **"Compass: HTTPS Required"**: Switch to HTTPS mode
- **"Compass: Not Available"**: Device may not have compass sensor

#### HTTPS/Certificate Issues
- **Certificate warnings**: Normal for self-signed certs, click "Advanced" → "Proceed"
- **WSS connection fails**:
  1. Open https://[your-ip]:8001 in a new tab
  2. Accept the certificate warning
  3. Return to main app
  
- **Mixed content blocked**: Use the SSL backend (`app_ssl.py`)

#### Audio Issues
- **No sound playing**:
  - Add `brum.mp3` to frontend folder
  - Browser may block autoplay - tap screen first
  - Check device volume and mute switch

#### Performance Issues
- **Slow updates**: OpenSky API has rate limits
- **High CPU usage**: Check if multiple server instances are running

### Recent Updates (June 2025)

- ✅ **Captain's Logbook** - Persistent tracking of all spotted planes
- ✅ **Simplified aircraft types** - Kid-friendly names like "Boeing 747 'Jumbo Jet'"
- ✅ **Family voice greetings** - Personalized audio from family members
- ✅ **Dual start buttons** - Choose your greeting preference
- ✅ **Enhanced audio** - Simplified filenames (atc_1.mp3, etc.)
- ✅ **Debug support** - Both raw and simplified aircraft types sent
- ✅ **Improved compass** - Better iOS device orientation handling
- ✅ **WebSocket reconnection** - Exponential backoff with jitter

## Deployment

### Local Network Deployment (Mac Mini/Raspberry Pi)

1. **Set up the host machine**:
   ```bash
   # Clone and install as above
   git clone https://github.com/yourusername/brum-brum-tracker.git
   cd brum-brum-tracker
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your exact coordinates
   ```

3. **Create startup scripts**:
   
   Create `start-backend.sh`:
   ```bash
   #!/bin/bash
   cd /path/to/brum-brum-tracker
   python backend/app.py
   ```
   
   Create `start-frontend.sh`:
   ```bash
   #!/bin/bash
   cd /path/to/brum-brum-tracker
   python serve.py
   ```

4. **Set up auto-start (macOS)**:
   - Use LaunchAgents or screen/tmux sessions
   - Or use PM2: `npm install -g pm2`
   ```bash
   pm2 start start-backend.sh --name brum-backend
   pm2 start start-frontend.sh --name brum-frontend
   pm2 save
   pm2 startup
   ```

5. **Set up auto-start (Raspberry Pi)**:
   - Add to `/etc/rc.local` or create systemd services

### HTTPS Setup (For iPad/iPhone Compass)

The application now fully supports HTTPS with secure WebSocket (WSS) connections. This enables:
- ✅ Device orientation (compass) on iOS devices
- ✅ Real-time plane tracking over secure connection
- ✅ No mixed content warnings

To use HTTPS mode:
1. Run the SSL backend: `python backend/app_ssl.py`
2. Run the HTTPS frontend: `python serve_https.py`
3. Accept the certificate warning when accessing the site
4. Enable compass by tapping the "Enable Compass" button on iOS

The SSL backend automatically generates self-signed certificates on first run.

### Network Configuration

1. **Find your local IP**:
   ```bash
   # macOS/Linux
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # Or use hostname
   hostname -I  # Linux
   ```

2. **Configure firewall** (if needed):
   - Allow ports 8000 (WebSocket) and 8080 (HTTP)
   - macOS: System Preferences → Security & Privacy → Firewall
   - Linux: `sudo ufw allow 8000 && sudo ufw allow 8080`

### Performance Optimization

- **Reduce polling frequency** during quiet hours
- **Enable caching** for aircraft images
- **Use nginx** as reverse proxy for production
- **Monitor logs**: Check `events.log` for errors

### Security Considerations

- Keep the service on local network only
- Don't expose to internet without proper authentication
- Regularly update dependencies: `pip install --upgrade -r requirements.txt`

## Development

### Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

### Testing

```bash
# Run unit tests
python -m pytest tests/ -v

# Test geometry calculations
python -m pytest tests/test_geometry.py -v
```

### Code Quality

The project uses:
- Black for code formatting
- isort for import sorting  
- Flake8 for linting
- Type hints for better code clarity

### Future Enhancements

- **Performance**: Service worker for offline support
- **Features**: Flight history statistics, weather integration
- **Production**: Docker containers, proper SSL certificates
- **Monitoring**: Add telemetry and alerting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Project Structure

```
brum-brum-tracker/
├── backend/          # Python WebSocket server
│   ├── server.py     # Main WebSocket logic
│   ├── app.py        # HTTP server entry
│   └── app_ssl.py    # HTTPS server entry
├── frontend/         # Web interface
│   ├── index.html    # Main tracker view
│   ├── dashboard.html # All planes view
│   ├── logbook.html  # Captain's logbook
│   └── assets/       # Audio and images
├── utils/            # Helper functions
├── tests/            # Unit tests
└── serve*.py         # Frontend servers
```

## License

MIT License - This project is open source for personal and educational use. See LICENSE file for details.