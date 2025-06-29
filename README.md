# Brum Brum Tracker

A real-time aircraft tracker designed for toddlers that shows planes overhead with directional arrows, images, and sound notifications.

## Background

My son Teddy is turning 2 soon, and **ABSOLUTELY** loves machines of all sorts (or as he referes to them, "brum brums"), and since we live in a part of the UK that see quite a few flights arriving and departing the London area airports, I thought I would build a small tracker that alerts him that there's about to be an airplane flying overhead. It was also an opportunity to play around with some of the recent agentic AI models

## Features

- **Real-time tracking** of aircraft within 50km radius
- **Directional arrow** pointing to aircraft (compass support on mobile)
- **Aircraft photos** and kid-friendly plane type names
- **Sound alerts** with family voice greetings
- **Captain's Logbook** to track spotted planes
- **Dashboard view** showing all approaching aircraft
- **PWA support** for installation on phones/tablets

## Screenshots

<div align="center">

### Start Screen
<img src="docs/screenshots/start_screen.png" alt="Start screen with family voice selection" width="300">

### Main Tracker View
<img src="docs/screenshots/brum-brum-tracker.png" alt="Main tracker showing aircraft with directional arrow" width="300">

### Captain's Logbook
<img src="docs/screenshots/logbook.png" alt="Captain's logbook showing spotted aircraft history" width="300">

</div>

## Quick Start

### Prerequisites
- Python 3.11+
- Modern web browser
- Location with overhead air traffic

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/brum-brum-tracker.git
cd brum-brum-tracker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your location:
```bash
cp .env.example .env
# Edit .env with your coordinates
```

### Running the App

Choose either HTTP (simple) or HTTPS (for iOS compass) mode:

#### HTTP Mode (Desktop/Android)
```bash
# Terminal 1: Backend
python backend/app.py

# Terminal 2: Frontend  
python serve.py
```
Access at: http://localhost:8080

#### HTTPS Mode (Required for iOS Compass)
```bash
# Terminal 1: Backend with SSL
python backend/app_ssl.py

# Terminal 2: Frontend with HTTPS
python serve_https.py
```
Access at: https://localhost:8443

### iPad/iPhone Setup

1. Find your computer's IP: `ifconfig | grep inet`
2. On device, navigate to `http://[your-ip]:8080`
3. Add to Home Screen via Share button
4. For compass support, use HTTPS mode and tap "Enable Compass"

## Progressive Web App (PWA) Setup

### Installing with Trusted Certificates

For the best PWA experience with trusted HTTPS:

```bash
# Install mkcert
brew install mkcert  # macOS
# Or see https://github.com/FiloSottile/mkcert for other platforms

# Run setup script
./setup_mkcert.sh

# Start HTTPS servers
python backend/app_ssl.py
python serve_https.py
```

### Installing as PWA

**iOS:** Safari → Share → Add to Home Screen  
**Android:** Chrome → Menu → Install app  
**Desktop:** Look for install icon in address bar

## Documentation

- [User Guide](docs/USER_GUIDE.md) - For parents and kids using the app
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Architecture](docs/ARCHITECTURE.md) - Technical implementation details

## Project Structure

```
brum-brum-tracker/
├── backend/          # Python WebSocket server
│   ├── app.py        # HTTP server
│   ├── app_ssl.py    # HTTPS server
│   └── server.py     # Core logic
├── frontend/         # Web interface
│   ├── index.html    # Main tracker
│   ├── dashboard.html
│   ├── logbook.html
│   └── assets/       # Audio files
├── serve.py          # HTTP frontend server
└── serve_https.py    # HTTPS frontend server
```

## Troubleshooting

### No Aircraft Showing?
- Check backend logs for "Received X aircraft from API"
- Verify .env has correct HOME_LAT and HOME_LON
- Try during busier times (morning/evening)

### Compass Not Working on iOS?
- Must use HTTPS mode
- Enable Motion & Orientation in Safari settings
- Tap "Enable Compass" button when prompted

### Connection Issues?
- Ensure both backend and frontend servers are running
- Check firewall isn't blocking ports 8000/8080
- Try refreshing the page

See [full troubleshooting guide](docs/TROUBLESHOOTING.md) for more help.

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
- Black for formatting
- Type hints throughout
- Comprehensive error handling

## License

MIT License - See LICENSE file for details
