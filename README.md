# brum-brum-tracker

## Project Guide: The "Brum Brum" Overhead Plane Tracker

This document outlines the concept, technical strategy, and deployment steps for creating a personalized, web-based plane spotter for a toddler. The goal is to create a simple, engaging display that shows when an airplane is about to pass overhead, complete with a directional arrow, a picture of the plane, a sound notification, and fun flight data like height and speed.

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

2. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
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

You need to run two servers:

1. **Backend (WebSocket Server)** - Terminal 1:
```bash
source .venv/bin/activate
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

### Adding Sound

The app expects a "brum brum" sound file. To add it:
1. Record or download an airplane sound effect
2. Save as `frontend/brum.mp3`
3. Keep it short (1-2 seconds) and child-friendly

### Current Features

- Real-time aircraft tracking via OpenSky Network API
- WebSocket streaming of aircraft data
- Direction arrow pointing to aircraft (requires device orientation)
- Aircraft information display (altitude, speed, distance)
- Visual notifications with glow effect
- Automatic reconnection on connection loss
- Smart polling (only when clients connected)

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

- **Connection refused**: Ensure both servers are running
- **No aircraft showing**: Check your coordinates in `.env`
- **Arrow not rotating**: Device orientation requires HTTPS or user permission
- **Sound not playing**: Add `brum.mp3` to frontend folder

### Development Status

- ✅ Backend core (flight tracking, WebSocket API)
- ✅ Frontend interface (display, animations, reconnection)
- ✅ PWA features (manifest.json, icons, mobile web app)
- ✅ Unit tests for geometry calculations
- ✅ Pre-commit hooks (black, isort, flake8)
- ⏳ Aircraft image scraping integration
- ⏳ Production deployment optimization

## Deployment

### Local Network Deployment (Mac Mini/Raspberry Pi)

1. **Set up the host machine**:
   ```bash
   # Clone and install as above
   git clone https://github.com/yourusername/brum-brum-tracker.git
   cd brum-brum-tracker
   python3 -m venv .venv
   source .venv/bin/activate
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
   source .venv/bin/activate
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

### HTTPS Setup (Optional, for device orientation)

For full device orientation support, you'll need HTTPS:

1. **Generate self-signed certificate**:
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
   ```

2. **Modify `serve.py` for HTTPS** (optional)

3. **Access via HTTPS**: `https://[your-ip]:8443`

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

### Code Quality

Pre-commit hooks are configured for:
- Black (code formatting)
- isort (import sorting)
- Flake8 (linting)

Run manually:
```bash
pre-commit run --all-files
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is for personal/educational use. See LICENSE file for details.