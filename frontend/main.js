/**
 * Brum Brum Tracker - Frontend JavaScript
 * Handles WebSocket connection, device orientation, and UI updates
 */

// Configuration
const WEBSOCKET_URL = `ws://${window.location.hostname}:8000/ws`;
const GLOW_DURATION = 15000; // 15 seconds

// State
let websocket = null;
let deviceHeading = 0;
let currentAircraft = null;
let glowTimeout = null;
let reconnectTimeout = null;
let hasOrientationPermission = false;

// DOM Elements
const elements = {
    connectionStatus: document.getElementById('connection-status'),
    statusText: document.querySelector('.status-text'),
    mainDisplay: document.getElementById('main-display'),
    noAircraft: document.getElementById('no-aircraft'),
    directionArrow: document.getElementById('direction-arrow'),
    planeImage: document.getElementById('plane-image'),
    distanceDisplay: document.getElementById('distance-display'),
    callsignDisplay: document.getElementById('callsign-display'),
    altitudeDisplay: document.getElementById('altitude-display'),
    speedDisplay: document.getElementById('speed-display'),
    typeDisplay: document.getElementById('type-display'),
    brumSound: document.getElementById('brum-sound')
};

/**
 * Initialize the application
 */
function init() {
    // Initialize UI state
    showNoAircraft();
    
    setupWebSocket();
    setupOrientationHandling();
    
    // Handle visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);
}

/**
 * Set up WebSocket connection
 */
function setupWebSocket() {
    updateConnectionStatus('connecting');
    showNoAircraft(true);  // Show connecting message
    
    try {
        websocket = new WebSocket(WEBSOCKET_URL);
        
        websocket.onopen = () => {
            console.log('WebSocket connected');
            updateConnectionStatus('connected');
            clearTimeout(reconnectTimeout);
        };
        
        websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };
        
        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateConnectionStatus('error');
        };
        
        websocket.onclose = () => {
            console.log('WebSocket disconnected');
            updateConnectionStatus('disconnected');
            scheduleReconnect();
        };
        
    } catch (error) {
        console.error('Failed to create WebSocket:', error);
        updateConnectionStatus('error');
        scheduleReconnect();
    }
}

/**
 * Schedule WebSocket reconnection
 */
function scheduleReconnect() {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = setTimeout(() => {
        console.log('Attempting to reconnect...');
        setupWebSocket();
    }, 5000);
}

/**
 * Handle incoming WebSocket messages
 */
function handleMessage(data) {
    switch (data.type) {
        case 'welcome':
            console.log('Received welcome message');
            break;
            
        case 'searching':
            showSearching();
            break;
            
        case 'aircraft_update':
            updateAircraftDisplay(data);
            break;
            
        case 'no_aircraft':
            showNoAircraft();
            break;
            
        default:
            console.log('Unknown message type:', data.type);
    }
}

/**
 * Update aircraft display with new data
 */
function updateAircraftDisplay(aircraft) {
    currentAircraft = aircraft;

    
    // Show main display, hide no aircraft message
    elements.mainDisplay.classList.remove('hidden');
    elements.noAircraft.classList.add('hidden');
    
    // Update aircraft information
    elements.distanceDisplay.textContent = `${aircraft.distance_km} km`;
    elements.callsignDisplay.textContent = aircraft.callsign || aircraft.icao24;
    elements.altitudeDisplay.textContent = `${aircraft.altitude_ft.toLocaleString()} ft`;
    elements.speedDisplay.textContent = `${Math.round(aircraft.speed_kmh)} km/h`;
    elements.typeDisplay.textContent = aircraft.aircraft_type || 'Unknown';
    
    // Update aircraft image
    if (aircraft.image_url) {
        elements.planeImage.src = aircraft.image_url;
    }
    
    // Update arrow rotation
    updateArrowRotation(aircraft.bearing);
    
    // Play sound and add glow effect
    playNotification();
}

/**
 * Show no aircraft message
 */
function showNoAircraft(connecting = false) {
    currentAircraft = null;
    elements.mainDisplay.classList.add('hidden');
    elements.noAircraft.classList.remove('hidden');
    
    // Update message based on connection state
    const titleElement = document.getElementById('no-aircraft-title');
    const subtitleElement = document.getElementById('no-aircraft-subtitle');
    
    if (connecting) {
        titleElement.textContent = 'Connecting...';
        subtitleElement.textContent = 'Establishing connection to aircraft tracker';
    } else {
        titleElement.textContent = 'Clear skies';
        subtitleElement.textContent = 'No aircraft visible overhead right now';
    }
    
    // Remove glow effect
    clearTimeout(glowTimeout);
    elements.directionArrow.classList.remove('glow');
}

/**
 * Show searching message
 */
function showSearching() {
    currentAircraft = null;
    elements.mainDisplay.classList.add('hidden');
    elements.noAircraft.classList.remove('hidden');
    
    const titleElement = document.getElementById('no-aircraft-title');
    const subtitleElement = document.getElementById('no-aircraft-subtitle');
    
    titleElement.textContent = 'Scanning the skies...';
    subtitleElement.textContent = 'Looking for aircraft overhead';
    
    // Remove glow effect
    clearTimeout(glowTimeout);
    elements.directionArrow.classList.remove('glow');
}

/**
 * Update arrow rotation based on bearing and device heading
 */
function updateArrowRotation(planeBearing) {
    // Calculate final rotation: plane bearing - device heading
    const rotation = planeBearing - deviceHeading;

    elements.directionArrow.style.transform = `rotate(${rotation}deg)`;
}

/**
 * Play notification sound and add glow effect
 */
function playNotification() {
    // Play sound
    elements.brumSound.play().catch(error => {
        console.log('Could not play sound:', error);
    });
    
    // Add glow effect
    elements.directionArrow.classList.add('glow');
    
    // Remove glow after duration
    clearTimeout(glowTimeout);
    glowTimeout = setTimeout(() => {
        elements.directionArrow.classList.remove('glow');
    }, GLOW_DURATION);
}

/**
 * Set up device orientation handling
 */
function setupOrientationHandling() {
    // Check if we need to request permission (iOS 13+)
    if (typeof DeviceOrientationEvent !== 'undefined' && 
        typeof DeviceOrientationEvent.requestPermission === 'function') {
        
        // Add click handler to request permission
        document.addEventListener('click', requestOrientationPermission, { once: true });
    } else {
        // No permission needed, just add the listener
        window.addEventListener('deviceorientation', handleOrientation);
        hasOrientationPermission = true;
    }
}

/**
 * Request device orientation permission (iOS 13+)
 */
async function requestOrientationPermission() {
    try {
        const permission = await DeviceOrientationEvent.requestPermission();
        if (permission === 'granted') {
            window.addEventListener('deviceorientation', handleOrientation);
            hasOrientationPermission = true;
            console.log('Device orientation permission granted');
        }
    } catch (error) {
        console.error('Failed to get orientation permission:', error);
    }
}

/**
 * Handle device orientation changes
 */
function handleOrientation(event) {
    if (event.webkitCompassHeading) {
        // iOS devices
        deviceHeading = event.webkitCompassHeading;
    } else if (event.alpha) {
        // Android devices (convert alpha to compass heading)
        deviceHeading = 360 - event.alpha;
    }
    
    // Update arrow if we have current aircraft
    if (currentAircraft) {
        updateArrowRotation(currentAircraft.bearing);
    }
}

/**
 * Update connection status display
 */
function updateConnectionStatus(status) {
    elements.connectionStatus.className = status;
    
    switch (status) {
        case 'connecting':
            elements.statusText.textContent = 'Connecting...';
            break;
        case 'connected':
            elements.statusText.textContent = 'Connected';
            break;
        case 'disconnected':
            elements.statusText.textContent = 'Disconnected';
            break;
        case 'error':
            elements.statusText.textContent = 'Connection Error';
            break;
    }
}

/**
 * Handle page visibility changes
 */
function handleVisibilityChange() {
    if (document.hidden) {
        // Page is hidden, close WebSocket to save resources
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.close();
        }
    } else {
        // Page is visible, reconnect if needed
        if (!websocket || websocket.readyState !== WebSocket.OPEN) {
            setupWebSocket();
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}