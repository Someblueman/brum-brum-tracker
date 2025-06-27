# Deployment Guide for Brum Brum Tracker

This guide covers deploying Brum Brum Tracker to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Deployment Options](#deployment-options)
- [Security Configuration](#security-configuration)
- [SSL Certificate Setup](#ssl-certificate-setup)
- [Systemd Service Setup](#systemd-service-setup)
- [Nginx Configuration](#nginx-configuration)
- [Docker Deployment](#docker-deployment)
- [Monitoring](#monitoring)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- Ubuntu 20.04+ or similar Linux distribution
- Python 3.8 or higher
- 1GB RAM minimum (2GB recommended)
- 10GB disk space
- Static IP address or domain name

### Required Software
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx certbot python3-certbot-nginx -y

# Install Node.js (for building frontend if needed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y
```

## Environment Setup

### 1. Create Application User
```bash
# Create dedicated user for the application
sudo useradd -m -s /bin/bash brumbrum
sudo usermod -aG www-data brumbrum
```

### 2. Clone Repository
```bash
# Switch to application user
sudo su - brumbrum

# Clone the repository
git clone https://github.com/yourusername/brum-brum-tracker.git
cd brum-brum-tracker
```

### 3. Create Virtual Environment
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
# Copy example environment file
cp .env.example .env

# Edit with your configuration
nano .env
```

Required environment variables:
```env
# Location Configuration
HOME_LAT=51.5074  # Your latitude
HOME_LON=-0.1278  # Your longitude
SEARCH_RADIUS_KM=50

# OpenSky API Credentials
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password

# Security
JWT_SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
ALLOWED_ORIGINS=https://yourdomain.com

# Database
DATABASE_PATH=/home/brumbrum/brum-brum-tracker/database/brumbrum.db

# Server Configuration
WS_HOST=0.0.0.0
WS_PORT=8000
WSS_PORT=8001
ENABLE_AUTH=true
```

## Deployment Options

### Option 1: Systemd Services (Recommended)

Create service files for backend and frontend:

#### Backend Service
```bash
sudo nano /etc/systemd/system/brumbrum-backend.service
```

```ini
[Unit]
Description=Brum Brum Tracker Backend
After=network.target

[Service]
Type=simple
User=brumbrum
Group=brumbrum
WorkingDirectory=/home/brumbrum/brum-brum-tracker
Environment="PATH=/home/brumbrum/brum-brum-tracker/venv/bin"
ExecStart=/home/brumbrum/brum-brum-tracker/venv/bin/python backend/app_ssl.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Frontend Service
```bash
sudo nano /etc/systemd/system/brumbrum-frontend.service
```

```ini
[Unit]
Description=Brum Brum Tracker Frontend
After=network.target

[Service]
Type=simple
User=brumbrum
Group=brumbrum
WorkingDirectory=/home/brumbrum/brum-brum-tracker
Environment="PATH=/home/brumbrum/brum-brum-tracker/venv/bin"
ExecStart=/home/brumbrum/brum-brum-tracker/venv/bin/python serve_https.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable brumbrum-backend brumbrum-frontend
sudo systemctl start brumbrum-backend brumbrum-frontend
```

### Option 2: Docker Deployment

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create non-root user
RUN useradd -m -u 1000 brumbrum && \
    chown -R brumbrum:brumbrum /app

USER brumbrum

# Expose ports
EXPOSE 8000 8001 8443

# Start script
CMD ["python", "backend/app_ssl.py"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  backend:
    build: .
    command: python backend/app_ssl.py
    volumes:
      - ./database:/app/database
      - ./certs:/app/certs
    environment:
      - HOME_LAT=${HOME_LAT}
      - HOME_LON=${HOME_LON}
      - OPENSKY_USERNAME=${OPENSKY_USERNAME}
      - OPENSKY_PASSWORD=${OPENSKY_PASSWORD}
    ports:
      - "8000:8000"
      - "8001:8001"
    restart: unless-stopped

  frontend:
    build: .
    command: python serve_https.py
    volumes:
      - ./certs:/app/certs
    ports:
      - "8443:8443"
    depends_on:
      - backend
    restart: unless-stopped
```

## Security Configuration

### 1. Firewall Setup
```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw allow 8001/tcp # WSS
sudo ufw enable
```

### 2. SSL Certificate Setup

#### Using Let's Encrypt (Production)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

#### Self-Signed Certificate (Development)
```bash
cd /home/brumbrum/brum-brum-tracker
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes
```

## Nginx Configuration

Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/brumbrum
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Frontend
    location / {
        proxy_pass https://localhost:8443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket
    location /ws {
        proxy_pass https://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' wss: https:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;" always;
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/brumbrum /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Monitoring

### 1. Application Logs
```bash
# View backend logs
sudo journalctl -u brumbrum-backend -f

# View frontend logs
sudo journalctl -u brumbrum-frontend -f

# View Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### 2. System Monitoring
```bash
# Install monitoring tools
sudo apt install htop iotop nethogs -y

# Monitor resource usage
htop  # CPU and memory
iotop  # Disk I/O
nethogs  # Network usage
```

### 3. Health Check Endpoint
Create a simple health check:
```python
# Add to backend/server.py
@app.route('/health')
async def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
```

### 4. Uptime Monitoring
Use services like:
- UptimeRobot
- Pingdom
- StatusCake

## Backup and Recovery

### 1. Database Backup Script
```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/home/brumbrum/backups"
DB_PATH="/home/brumbrum/brum-brum-tracker/database/brumbrum.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp $DB_PATH $BACKUP_DIR/brumbrum_$DATE.db

# Keep only last 30 days of backups
find $BACKUP_DIR -name "brumbrum_*.db" -mtime +30 -delete
```

### 2. Automated Backups
```bash
# Add to crontab
crontab -e

# Daily backup at 3 AM
0 3 * * * /home/brumbrum/backup.sh
```

### 3. Recovery Process
```bash
# Stop services
sudo systemctl stop brumbrum-backend

# Restore database
cp /home/brumbrum/backups/brumbrum_YYYYMMDD_HHMMSS.db /home/brumbrum/brum-brum-tracker/database/brumbrum.db

# Restart services
sudo systemctl start brumbrum-backend
```

## Troubleshooting

### Common Issues

#### 1. WebSocket Connection Failed
- Check firewall rules
- Verify SSL certificates
- Check Nginx proxy configuration
- Review backend logs

#### 2. High Memory Usage
- Check for memory leaks
- Monitor active connections
- Review tracking set cleanup
- Restart services if needed

#### 3. Database Locked
- Check for long-running queries
- Ensure proper connection closing
- Consider WAL mode for SQLite

#### 4. SSL Certificate Issues
- Verify certificate paths
- Check certificate expiration
- Ensure proper file permissions

### Debug Commands
```bash
# Check service status
sudo systemctl status brumbrum-backend

# Check port usage
sudo netstat -tlnp | grep -E '8000|8001|8443'

# Test WebSocket connection
wscat -c wss://yourdomain.com/ws

# Check SSL certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Database integrity check
sqlite3 /path/to/brumbrum.db "PRAGMA integrity_check;"
```

## Performance Tuning

### 1. Nginx Optimization
```nginx
# Add to nginx.conf
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}
```

### 2. Python Optimization
```bash
# Use production WSGI server
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.app:app
```

### 3. Database Optimization
```sql
-- Add indexes
CREATE INDEX idx_spotted_at ON logbook(spotted_at);
CREATE INDEX idx_aircraft_type ON logbook(aircraft_type);

-- Enable WAL mode
PRAGMA journal_mode=WAL;
```

## Security Checklist

- [ ] Change default passwords
- [ ] Enable firewall
- [ ] Configure SSL certificates
- [ ] Set up authentication
- [ ] Enable rate limiting
- [ ] Configure CORS properly
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Backup strategy in place
- [ ] Incident response plan

## Maintenance

### Regular Tasks
- Weekly: Check logs for errors
- Monthly: Update system packages
- Monthly: Review resource usage
- Quarterly: Update dependencies
- Yearly: Renew SSL certificates

### Update Process
```bash
# Backup first
./backup.sh

# Pull updates
cd /home/brumbrum/brum-brum-tracker
git pull

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart services
sudo systemctl restart brumbrum-backend brumbrum-frontend
```