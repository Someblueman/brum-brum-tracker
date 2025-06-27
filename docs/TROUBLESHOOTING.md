# Brum Brum Tracker - Troubleshooting FAQ

## Frequently Asked Questions

### General Issues

#### Q: The app won't load at all
**A:** Try these steps:
1. Check your internet connection
2. Clear your browser cache and cookies
3. Try a different browser (Chrome, Firefox, Safari, Edge)
4. Disable browser extensions that might interfere
5. Make sure JavaScript is enabled in your browser

#### Q: I see an error message about WebSocket connection
**A:** This usually means:
- The server might be temporarily down
- Your firewall or network might be blocking WebSocket connections
- You're using an outdated browser

**Solution:**
1. Wait a few minutes and refresh the page
2. Try accessing from a different network
3. Update your browser to the latest version

#### Q: The page is loading very slowly
**A:** 
- Check your internet speed
- Close other browser tabs that might be using resources
- The aviation image database might be slow - images will load eventually
- Try the HTTP version instead of HTTPS if you don't need compass features

### Location and Tracking Issues

#### Q: No aircraft are showing up
**A:** Several things to check:

1. **Location Services**
   - Make sure location services are enabled for your browser
   - On iPhone: Settings > Privacy > Location Services > Safari > While Using App
   - On Android: Settings > Location > App permissions > Chrome > Allow

2. **Time and Location**
   - You might be in an area with less air traffic
   - Try during busier times (morning 6-10 AM, evening 4-8 PM)
   - Aircraft only show within 50km radius and above minimum elevation

3. **API Issues**
   - The OpenSky Network API might be temporarily unavailable
   - Check the browser console for error messages

#### Q: Aircraft positions seem wrong or delayed
**A:** 
- Aircraft positions update every 5-10 seconds
- There's a natural delay in ADS-B data transmission
- Weather can affect signal quality
- This is normal and expected behavior

#### Q: The app thinks I'm in the wrong location
**A:**
- Browser location can be inaccurate, especially on desktop computers
- VPNs can affect location detection
- Try on a mobile device for better GPS accuracy

### Compass and Arrow Issues

#### Q: The arrow isn't pointing to the aircraft (iOS)
**A:** This is the most common issue on iPhones and iPads:

1. **Enable Compass Permission**
   - Click the "Enable Compass" button when it appears
   - If you missed it, refresh the page

2. **Check Safari Settings**
   - Go to Settings > Safari > Advanced
   - Turn ON "Motion & Orientation Access"
   - Restart Safari after changing this setting

3. **HTTPS Required**
   - Make sure you're using the HTTPS version of the site
   - The compass won't work on HTTP connections

4. **Device Orientation**
   - Hold your device relatively flat
   - Move away from magnetic interference (speakers, metal objects)
   - Try calibrating your compass in the Compass app first

#### Q: The arrow spins randomly or points wrong direction
**A:**
- Magnetic interference from nearby objects
- Device compass needs calibration
- Try the figure-8 motion to calibrate: move your device in a figure-8 pattern
- Move away from metal objects, speakers, or other electronics

#### Q: Compass shows "Off" status
**A:**
- You haven't enabled compass permissions yet
- Your device doesn't support device orientation API
- You're using HTTP instead of HTTPS

### Audio Issues

#### Q: No sounds are playing
**A:**
1. Check your device volume and mute switches
2. Some browsers block autoplay - click anywhere on the page
3. Check browser permissions for audio
4. iOS devices require user interaction before playing audio

#### Q: "Brum Brum" sound plays too often
**A:**
- This is normal in busy airspace
- The sound plays for each new aircraft detected
- You can mute your device if it's too frequent

#### Q: Family greeting didn't play
**A:**
- Make sure you clicked one of the start buttons
- Check browser audio permissions
- Some browsers require clicking "Allow" for audio

### Display Issues

#### Q: Aircraft images aren't loading
**A:**
- Some aircraft don't have photos in the database
- Images can take time to load from external sources
- This is normal, especially for private or military aircraft
- The plane will still be tracked without an image

#### Q: The display looks broken or overlapped
**A:**
- Try refreshing the page (Ctrl+R or Cmd+R)
- Clear browser cache
- Make sure browser zoom is at 100%
- Try landscape orientation on mobile devices
- Update to the latest browser version

#### Q: Can't see the logbook button
**A:**
- It might be outside the viewport on small screens
- Try scrolling or zooming out
- Rotate to landscape mode on mobile
- Use a device with a larger screen

### Logbook Issues

#### Q: My logbook is empty
**A:**
- You need to spot aircraft first - they're automatically added
- Only known aircraft types are logged (not "Unknown Aircraft")
- The logbook persists between sessions on the same device

#### Q: Lost my logbook entries
**A:**
- Logbook is stored in your browser's local storage
- Clearing browser data will delete the logbook
- Use the same browser and device to keep your collection
- Private/incognito mode won't save the logbook

#### Q: Same aircraft appears multiple times
**A:**
- This shouldn't happen in the same session
- After restarting the app, previously seen aircraft can be logged again
- This is by design to allow collecting over multiple days

### Connection Issues

#### Q: "WebSocket disconnected" message
**A:**
- Temporary network interruption
- The app will try to reconnect automatically
- If it doesn't reconnect, refresh the page
- Check your internet connection

#### Q: Getting rate limit errors
**A:**
- Too many connection attempts in a short time
- Too many messages being sent
- Wait 60 seconds before trying again
- This protects the server from overload

### Browser-Specific Issues

#### Q: Safari on Mac issues
**A:**
- Enable developer menu: Safari > Preferences > Advanced > Show Develop menu
- Check Develop > Disable Cross-Origin Restrictions if having CORS issues
- Make sure JavaScript is enabled

#### Q: Chrome security warnings
**A:**
- HTTPS version uses self-signed certificates
- Click "Advanced" then "Proceed to site"
- This is safe for the Brum Brum Tracker

#### Q: Firefox tracking protection
**A:**
- Firefox's tracking protection might block some features
- Click the shield icon in the address bar
- Turn off Enhanced Tracking Protection for this site

### Mobile-Specific Issues

#### Q: Battery draining quickly
**A:**
- Continuous GPS and compass use consumes battery
- Screen staying on draws power
- Close the app when not actively watching
- Reduce screen brightness

#### Q: App stops working when screen locks
**A:**
- This is normal browser behavior
- The app will resume when you unlock
- Keep screen on if continuous tracking needed

### Development/Technical Issues

#### Q: How do I check for errors?
**A:** Open browser developer console:
- Chrome/Edge: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)
- Firefox: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)
- Safari: Enable Develop menu first, then Cmd+Option+I

Look for red error messages that might indicate the problem.

#### Q: WebSocket won't connect on corporate network
**A:**
- Corporate firewalls often block WebSocket connections
- Try using a personal network or mobile hotspot
- Contact IT to whitelist WebSocket protocols
- Port 8000 (WS) or 8001 (WSS) need to be open

#### Q: Running locally but can't connect
**A:** Make sure:
- Backend is running (`python backend/app.py`)
- Using correct URL (http://localhost:8080)
- No other service is using ports 8000, 8080, 8443
- .env file has correct HOME_LAT and HOME_LON values

### Still Having Issues?

If none of these solutions work:

1. **Collect Information**
   - What browser and version?
   - What device and OS?
   - What exact error message?
   - Browser console errors (F12 > Console)

2. **Report the Issue**
   - Create an issue on GitHub
   - Include all information from step 1
   - Describe what you expected vs what happened

3. **Temporary Workarounds**
   - Try the HTTP version if HTTPS isn't working
   - Use a different device
   - Try during different times of day
   - Check if others are experiencing the same issue

Remember: The app depends on real-time data from aircraft transponders. Sometimes issues are temporary and resolve themselves!