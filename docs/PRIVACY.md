# Brum Brum Tracker - Privacy Policy

**Last Updated: December 2024**

## Overview

Brum Brum Tracker is designed with privacy in mind. We believe in transparency about what data is used and how it's handled. This document explains our privacy practices in clear, simple terms.

## Core Privacy Principles

1. **No Personal Data Collection**: We don't collect names, emails, or any personal information
2. **No User Accounts**: No registration or login required
3. **No Tracking**: No analytics, cookies, or user tracking
4. **Local Storage Only**: Your data stays on your device
5. **No Ads**: No advertising networks or third-party trackers

## What Information Is Used

### Location Data

**What we use:**
- Your approximate location (latitude/longitude)
- Only while the app is open and active

**Why we need it:**
- To show aircraft near your location
- To calculate distances and directions to aircraft

**What we DON'T do:**
- Store your location on any server
- Track your location history
- Share your location with anyone
- Access location when app is closed

### Device Sensors

**What we use:**
- Compass/magnetometer (if you enable it)
- Device orientation (for arrow pointing)

**Why we need it:**
- To point the arrow in the right direction
- To show aircraft elevation angle

**Privacy note:**
- Sensor data never leaves your device
- Only used for real-time display
- No sensor data is stored

### Aircraft Data

**What we receive:**
- Public ADS-B transponder data from OpenSky Network
- Aircraft registration and type information
- Flight routes (when available)

**Important:**
- This is publicly broadcast data
- Same data anyone with ADS-B receiver can see
- We don't track specific flights over time

## Data Storage

### What's Stored Locally

On your device only:
- Captain's Logbook entries (aircraft types you've seen)
- Your chosen greeting preference
- Basic app settings

**How to clear this data:**
- Clear your browser's data/cache
- Or use private/incognito mode (nothing saved)

### What's NOT Stored

We never store:
- Your location history
- Personal information
- Device identifiers
- Usage patterns
- IP addresses (in application logs)

## Third-Party Services

### OpenSky Network API
- Provides real-time aircraft position data
- They receive: your approximate location area
- They don't receive: any personal information
- See their privacy policy at opensky-network.org

### Aircraft Image Services
- Images loaded from aircraft photo databases
- These services only see: aircraft registration requests
- No personal data is shared

### WebSocket Connection
- Real-time connection to our server
- Only transmits: aircraft data and app messages
- No personal information in connection

## Children's Privacy

Brum Brum Tracker is designed to be family-friendly:

- No personal information required
- No social features or communication
- No in-app purchases
- No external links (except aircraft images)
- Parental supervision recommended for young children

## Your Rights and Controls

### You can always:

1. **Use without location**
   - Deny location permission
   - App won't show aircraft (needs location to work)

2. **Clear stored data**
   - Clear browser cache/data
   - Removes logbook and settings

3. **Use privately**
   - Private/incognito mode
   - Nothing saved after closing

4. **Disable sensors**
   - Don't click "Enable Compass"
   - Arrow won't point to aircraft

## Security Measures

### How we protect privacy:

- **HTTPS encryption** (when using HTTPS version)
- **No databases** of user information
- **No authentication** requirements
- **Input validation** to prevent attacks
- **Rate limiting** to prevent abuse
- **No logs** of personal data

### Self-hosted option:
- You can run your own instance
- Complete control over your data
- See deployment documentation

## Changes to Privacy Practices

If privacy practices change:
- This document will be updated
- Date at top shows last update
- No changes will affect past data (we don't have any!)

## Open Source Transparency

- All code is open source
- You can verify our privacy claims
- Review code at: github.com/[repository]
- No hidden data collection

## Contact

For privacy questions or concerns:
- Open an issue on GitHub
- No need to provide personal info to contact us

## Summary for Parents

**What we DO:**
- Show planes near your location
- Save which planes your child has spotted
- Play fun airplane sounds

**What we DON'T:**
- Know who your child is
- Track where you've been
- Share data with anyone
- Show ads or collect marketing data

**Your child's privacy is protected by design.**

## Technical Details for Developers

### Local Storage

```javascript
// Only these items in localStorage:
- logbook_entries: Array of spotted aircraft types
- greeting_choice: "parents" or "grandparents"
- compass_enabled: true/false
```

### WebSocket Messages

No personal data in any WebSocket message:
```javascript
// Client sends:
{
  "type": "hello"  // No user identification
}

// Server sends:
{
  "type": "aircraft",
  "icao24": "...",  // Aircraft data only
  "distance_km": ... // Relative to provided location
}
```

### No Server-Side Storage

- No database of users
- No session tracking
- No IP address logging
- Memory-only rate limiting (not persisted)

## Legal Compliance

This privacy policy is designed to comply with:
- GDPR (General Data Protection Regulation)
- COPPA (Children's Online Privacy Protection Act)
- CCPA (California Consumer Privacy Act)
- Other privacy regulations

By not collecting personal data, we avoid most regulatory requirements while providing maximum privacy protection.

---

**Remember:** Brum Brum Tracker shows publicly available aircraft data based on your current location. We don't know who you are, and we like it that way!