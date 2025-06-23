/**
 * Brum Brum Tracker - Frontend JavaScript
 * Handles WebSocket connection, device orientation, and UI updates
 */

// Configuration
// Use WSS when page is served over HTTPS, WS otherwise
const WEBSOCKET_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WEBSOCKET_PORT = window.location.protocol === 'https:' ? '8001' : '8000';
const WEBSOCKET_URL = `${WEBSOCKET_PROTOCOL}//${window.location.hostname}:${WEBSOCKET_PORT}/ws`;
const GLOW_DURATION = 15000; // 15 seconds

// WebSocket reconnection configuration
const RECONNECT_CONFIG = {
    initialDelay: 1000,      // Start with 1 second
    maxDelay: 30000,         // Max 30 seconds
    decayFactor: 1.5,        // Exponential backoff factor
    maxRetries: null,        // Unlimited retries
    jitterFactor: 0.3        // Add randomness to prevent thundering herd
};

// State
let websocket = null;
let deviceHeading = 0;
let currentAircraft = null;
let glowTimeout = null;
let reconnectTimeout = null;
let reconnectAttempts = 0;
let hasOrientationPermission = false;
let isIOS = false;
let compassSupported = false;

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
    brumSound: document.getElementById('brum-sound'),
    compassIndicator: document.getElementById('compass-indicator')
};

/**
 * Initialize the application
 */
function init() {
    // Detect iOS
    isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    
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
    
    console.log(`Protocol: ${window.location.protocol}`);
    console.log(`WebSocket URL: ${WEBSOCKET_URL}`);
    console.log(`Connection attempt #${reconnectAttempts + 1}`);
    
    try {
        websocket = new WebSocket(WEBSOCKET_URL);
        
        websocket.onopen = () => {
            console.log('✅ WebSocket connected successfully!');
            updateConnectionStatus('connected');
            clearTimeout(reconnectTimeout);
            reconnectAttempts = 0; // Reset attempts on successful connection
        };
        
        websocket.onmessage = (event) => {
            console.log('📨 Received message:', event.data);
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };
        
        websocket.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            console.error('Check if backend is running on port', WEBSOCKET_PORT);
            updateConnectionStatus('error');
        };
        
        websocket.onclose = (event) => {
            console.log(`🔌 WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason}`);
            updateConnectionStatus('disconnected');
            
            // Clean up the WebSocket reference
            websocket = null;
            
            // Schedule reconnection
            scheduleReconnect();
        };
        
    } catch (error) {
        console.error('❌ Failed to create WebSocket:', error);
        updateConnectionStatus('error');
        scheduleReconnect();
    }
}

/**
 * Calculate reconnection delay with exponential backoff and jitter
 */
function calculateReconnectDelay() {
    const baseDelay = Math.min(
        RECONNECT_CONFIG.initialDelay * Math.pow(RECONNECT_CONFIG.decayFactor, reconnectAttempts),
        RECONNECT_CONFIG.maxDelay
    );
    
    // Add jitter to prevent thundering herd
    const jitter = baseDelay * RECONNECT_CONFIG.jitterFactor * (Math.random() - 0.5);
    return Math.floor(baseDelay + jitter);
}

/**
 * Schedule WebSocket reconnection
 */
function scheduleReconnect() {
    clearTimeout(reconnectTimeout);
    
    // Check if we've hit max retries (if configured)
    if (RECONNECT_CONFIG.maxRetries && reconnectAttempts >= RECONNECT_CONFIG.maxRetries) {
        console.error('Max reconnection attempts reached');
        updateConnectionStatus('error');
        return;
    }
    
    const delay = calculateReconnectDelay();
    console.log(`Scheduling reconnection in ${delay}ms (attempt ${reconnectAttempts + 1})`);
    
    reconnectTimeout = setTimeout(() => {
        reconnectAttempts++;
        setupWebSocket();
    }, delay);
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
    let rotation;
    
    if (hasOrientationPermission && deviceHeading !== 0) {
        // Calculate final rotation: plane bearing - device heading
        rotation = planeBearing - deviceHeading;
        console.log(`Arrow rotation: bearing(${planeBearing}) - heading(${deviceHeading}) = ${rotation}`);
    } else {
        // No device orientation available, just show bearing from north
        rotation = planeBearing;
        console.log(`No device orientation, showing bearing: ${rotation}`);
    }

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
        
        // Create a button to request permission
        createOrientationButton();
    } else {
        // No permission needed, but check if HTTPS is required
        if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
            console.warn('Device orientation may require HTTPS.');
            if (elements.compassIndicator) {
                elements.compassIndicator.textContent = 'Compass: HTTPS May Be Required';
                elements.compassIndicator.style.color = '#ff9800';
            }
        }
        
        // Try to add the listener
        window.addEventListener('deviceorientation', handleOrientation);
        
        // Check if we're actually getting data after a delay
        setTimeout(() => {
            if (deviceHeading === 0) {
                hasOrientationPermission = false;
                if (elements.compassIndicator) {
                    elements.compassIndicator.textContent = 'Compass: Not Available';
                    elements.compassIndicator.style.color = '#ff9800';
                }
                console.log('No orientation data received. Compass may not be available.');
            } else {
                hasOrientationPermission = true;
                if (elements.compassIndicator) {
                    elements.compassIndicator.textContent = 'Compass: On';
                    elements.compassIndicator.style.color = '#4CAF50';
                }
            }
        }, 2000);
    }
}

/**
 * Create orientation permission button for iOS
 */
function createOrientationButton() {
    // Check if we're on HTTPS
    if (window.location.protocol !== 'https:') {
        console.warn('Device orientation requires HTTPS. Compass will not work on HTTP.');
        if (elements.compassIndicator) {
            elements.compassIndicator.textContent = 'Compass: HTTPS Required';
            elements.compassIndicator.style.color = '#ff9800';
        }
        return;
    }
    
    const button = document.createElement('button');
    button.id = 'orientation-button';
    button.textContent = 'Enable Compass';
    button.style.cssText = `
        position: absolute;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        padding: 12px 24px;
        background: rgba(59, 130, 246, 0.9);
        color: white;
        border: none;
        border-radius: 12px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        z-index: 1000;
    `;
    
    button.addEventListener('click', requestOrientationPermission);
    document.body.appendChild(button);
}

/**
 * Request device orientation permission (iOS 13+)
 */
async function requestOrientationPermission() {
    try {
        console.log('Requesting device orientation permission...');
        const permission = await DeviceOrientationEvent.requestPermission();
        console.log('Permission response:', permission);
        
        if (permission === 'granted') {
            window.addEventListener('deviceorientation', handleOrientation);
            hasOrientationPermission = true;
            console.log('Device orientation permission granted');
            
            // Remove the button
            const button = document.getElementById('orientation-button');
            if (button) {
                button.remove();
            }
            
            // Update compass indicator
            if (elements.compassIndicator) {
                elements.compassIndicator.textContent = 'Compass: On';
                elements.compassIndicator.style.color = '#4CAF50';
            }
            
            // Update arrow if we have current aircraft
            if (currentAircraft) {
                updateArrowRotation(currentAircraft.bearing);
            }
        } else {
            console.log('Permission denied:', permission);
            if (elements.compassIndicator) {
                elements.compassIndicator.textContent = 'Compass: Permission Denied';
                elements.compassIndicator.style.color = '#f44336';
            }
            alert('Compass permission denied. Please enable in Settings > Safari > Motion & Orientation Access.');
        }
    } catch (error) {
        console.error('Failed to get orientation permission:', error);
        // Try to add event listener anyway - some devices don't need permission
        window.addEventListener('deviceorientation', handleOrientation);
        
        // Wait a bit to see if we get orientation data
        setTimeout(() => {
            if (deviceHeading === 0) {
                if (elements.compassIndicator) {
                    elements.compassIndicator.textContent = 'Compass: Not Available';
                    elements.compassIndicator.style.color = '#ff9800';
                }
                alert('Compass not available. Please ensure:\n1. You are using HTTPS\n2. Motion & Orientation Access is enabled in Safari settings\n3. Your device has a compass');
            }
        }, 2000);
    }
}

/**
 * Handle device orientation changes
 */
function handleOrientation(event) {
    // More robust handling for different devices
    if (event.webkitCompassHeading !== undefined && event.webkitCompassHeading !== null) {
        // iOS devices with compass - webkitCompassHeading gives absolute heading
        deviceHeading = event.webkitCompassHeading;
        console.log('iOS compass heading:', deviceHeading);
        
        if (!compassSupported) {
            compassSupported = true;
            hasOrientationPermission = true;
            if (elements.compassIndicator) {
                elements.compassIndicator.textContent = 'Compass: On';
                elements.compassIndicator.style.color = '#4CAF50';
            }
        }
    } else if (event.alpha !== null && event.alpha !== undefined) {
        // Android devices or iOS without compass
        // Alpha is rotation around Z-axis (0-360)
        deviceHeading = (360 - event.alpha) % 360;
        console.log('Device alpha:', event.alpha, 'Calculated heading:', deviceHeading);
        
        if (!compassSupported) {
            compassSupported = true;
            hasOrientationPermission = true;
            if (elements.compassIndicator) {
                elements.compassIndicator.textContent = 'Compass: On';
                elements.compassIndicator.style.color = '#4CAF50';
            }
        }
    } else {
        console.log('No orientation data available');
        return;
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
            console.log('Page hidden, closing WebSocket');
            websocket.close(1000, 'Page hidden');
        }
    } else {
        // Page is visible, reconnect if needed
        if (!websocket || websocket.readyState !== WebSocket.OPEN) {
            console.log('Page visible, reconnecting WebSocket');
            reconnectAttempts = 0; // Reset attempts for immediate reconnection
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