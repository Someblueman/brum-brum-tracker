/**
 * Brum Brum Tracker - Frontend JavaScript
 * Handles WebSocket connection, device orientation, and UI updates
 */

// Register Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
            .then(registration => {
                console.log('Service Worker registered:', registration);
                
                // Handle updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'activated') {
                            console.log('Service Worker updated');
                        }
                    });
                });
            })
            .catch(error => {
                console.error('Service Worker registration failed:', error);
            });
    });
}

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
let allAircraft = [];  // Track all nearby aircraft
let glowTimeout = null;
let reconnectTimeout = null;
let reconnectAttempts = 0;
let hasOrientationPermission = false;
let isIOS = false;
let compassSupported = false;
let seenAircraft = new Set(); // Track aircraft that have already played sound

// Smoothing for compass readings
const headingHistory = [];
const HEADING_HISTORY_SIZE = 5; // Keep last 5 readings
const HEADING_UPDATE_THRESHOLD = 2; // Only update if change > 2 degrees

// DOM Elements
const elements = {
    connectionStatus: document.getElementById('connection-status'),
    statusText: document.querySelector('.status-text'),
    mainDisplay: document.getElementById('main-display'),
    noAircraft: document.getElementById('no-aircraft'),
    arrowAnimator: document.getElementById('arrow-animator'), // Add this line
    directionArrow: document.getElementById('direction-arrow'),
    planeImage: document.getElementById('plane-image'),
    aircraftStack: document.getElementById('aircraft-stack'),
    aircraftCount: document.getElementById('aircraft-count'),
    countNumber: document.getElementById('count-number'),
    distanceDisplay: document.getElementById('distance-display'),
    callsignDisplay: document.getElementById('callsign-display'),
    altitudeDisplay: document.getElementById('altitude-display'),
    speedDisplay: document.getElementById('speed-display'),
    typeDisplay: document.getElementById('type-display'),
    atcSounds: [
        document.getElementById('atc-sound-1'),
        document.getElementById('atc-sound-2'),
        document.getElementById('atc-sound-3'),
        document.getElementById('atc-sound-4'),
        document.getElementById('atc-sound-5')
    ],
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
            handleAircraftUpdate(data);
            break;
            
        case 'no_aircraft':
            showNoAircraft();
            break;
            
        default:
            console.log('Unknown message type:', data.type);
    }
}

/**
 * Handle aircraft update message
 */
function handleAircraftUpdate(data) {
    // Store all aircraft data
    if (data.all_aircraft) {
        allAircraft = data.all_aircraft;
    } else {
        // Fallback for backward compatibility
        allAircraft = [data];
    }
    
    // Display the closest aircraft
    const closestAircraft = data.closest || data;
    updateAircraftDisplay(closestAircraft);
    
    // Update stack display
    updateAircraftStack();
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
    
    // Check if this is a new aircraft (not seen before)
    const aircraftId = aircraft.icao24;
    if (!seenAircraft.has(aircraftId)) {
        // First time seeing this aircraft - play sound and add glow effect
        seenAircraft.add(aircraftId);
        playNotification();
        console.log(`New aircraft detected: ${aircraftId} - playing sound`);
    } else {
        console.log(`Aircraft ${aircraftId} already seen - not playing sound`);
    }
}

/**
 * Update the stacked aircraft display
 */
function updateAircraftStack() {
    const stackContainer = elements.aircraftStack;
    
    // Clear existing stack images (except the main one)
    const existingStacks = stackContainer.querySelectorAll('.stacked-aircraft');
    existingStacks.forEach(img => img.remove());
    
    // Update aircraft count
    if (allAircraft.length > 1) {
        elements.aircraftCount.classList.remove('hidden');
        elements.countNumber.textContent = allAircraft.length;
        
        // Add stacked images for other aircraft (up to 3 more)
        const maxStacked = Math.min(allAircraft.length - 1, 3);
        for (let i = 1; i <= maxStacked; i++) {
            const aircraft = allAircraft[i];
            if (aircraft && aircraft.image_url) {
                const stackImg = document.createElement('img');
                stackImg.className = 'stacked-aircraft';
                stackImg.src = aircraft.image_url;
                stackImg.alt = `Aircraft ${i + 1}`;
                stackImg.style.zIndex = 5 - i;
                stackContainer.appendChild(stackImg);
            }
        }
    } else {
        elements.aircraftCount.classList.add('hidden');
    }
}

/**
 * Show no aircraft message
 * */
function showNoAircraft(connecting = false) {
    currentAircraft = null;
    allAircraft = [];
    elements.mainDisplay.classList.add('hidden');
    elements.noAircraft.classList.remove('hidden');
    
    // Clear seen aircraft when no aircraft are visible
    // This allows sound to play again when aircraft return
    if (seenAircraft.size > 0) {
        console.log(`Clearing ${seenAircraft.size} seen aircraft from memory`);
        seenAircraft.clear();
    }
    
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
 * */
function showSearching() {
    currentAircraft = null;
    allAircraft = [];
    elements.mainDisplay.classList.add('hidden');
    elements.noAircraft.classList.remove('hidden');
    
    // Clear seen aircraft when searching
    if (seenAircraft.size > 0) {
        console.log(`Clearing ${seenAircraft.size} seen aircraft from memory`);
        seenAircraft.clear();
    }
    
    const titleElement = document.getElementById('no-aircraft-title');
    const subtitleElement = document.getElementById('no-aircraft-subtitle');
    
    titleElement.textContent = 'Scanning the skies...';
    subtitleElement.textContent = 'Looking for aircraft overhead';
    
    // Remove glow effect
    clearTimeout(glowTimeout);
    elements.directionArrow.classList.remove('glow');
}

/**
 * Update arrow rotation to point TOWARD the aircraft location
 * This helps users (especially children) know where to look in the sky
 */
function updateArrowRotation(planeBearing) {
    let rotation;
    
    if (hasOrientationPermission && deviceHeading !== 0) {
        // Calculate final rotation: plane bearing - device heading
        // planeBearing is already FROM home TO aircraft, so no need to add 180
        rotation = (planeBearing - deviceHeading + 360) % 360;
        console.log(`Arrow rotation: bearing(${planeBearing}) - heading(${deviceHeading}) = ${rotation}`);
    } else {
        // No device orientation available, just show bearing from north
        // planeBearing already points TO the aircraft
        rotation = planeBearing;
        console.log(`No device orientation, showing bearing: ${rotation}`);
    }

    elements.directionArrow.style.transform = `rotate(${rotation}deg)`;
}

/**
 * Play notification sound and add glow effect
 */
function playNotification() {
    // Play random ATC sound
    const randomIndex = Math.floor(Math.random() * elements.atcSounds.length);
    const selectedSound = elements.atcSounds[randomIndex];
    
    selectedSound.play().catch(error => {
        console.log('Could not play sound:', error);
    });
    
    // Add glow effect TO THE WRAPPER
    elements.arrowAnimator.classList.add('glow'); // Change this line
    
    // Remove glow after duration
    clearTimeout(glowTimeout);
    glowTimeout = setTimeout(() => {
        elements.arrowAnimator.classList.remove('glow'); // and this line
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
 * Smooth compass heading using moving average
 */
function smoothHeading(newHeading) {
    // Add to history
    headingHistory.push(newHeading);
    
    // Keep only recent readings
    if (headingHistory.length > HEADING_HISTORY_SIZE) {
        headingHistory.shift();
    }
    
    // Calculate circular mean (handles 359->0 wrap-around)
    let sinSum = 0;
    let cosSum = 0;
    
    headingHistory.forEach(heading => {
        const rad = heading * Math.PI / 180;
        sinSum += Math.sin(rad);
        cosSum += Math.cos(rad);
    });
    
    let avgHeading = Math.atan2(sinSum, cosSum) * 180 / Math.PI;
    if (avgHeading < 0) avgHeading += 360;
    
    return avgHeading;
}

/**
 * Handle device orientation changes
 */
function handleOrientation(event) {
    let rawHeading;
    
    // More robust handling for different devices
    if (event.webkitCompassHeading !== undefined && event.webkitCompassHeading !== null) {
        // iOS devices with compass - webkitCompassHeading gives absolute heading
        rawHeading = event.webkitCompassHeading;
        
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
        rawHeading = (360 - event.alpha) % 360;
        
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
    
    // Apply smoothing
    const smoothedHeading = smoothHeading(rawHeading);
    
    // Only update if change is significant
    const headingChange = Math.abs(smoothedHeading - deviceHeading);
    const minChange = Math.min(headingChange, 360 - headingChange); // Handle wrap-around
    
    if (minChange > HEADING_UPDATE_THRESHOLD || deviceHeading === 0) {
        deviceHeading = smoothedHeading;
        console.log(`Heading updated: raw=${rawHeading.toFixed(1)}°, smoothed=${smoothedHeading.toFixed(1)}°`);
        
        // Update arrow if we have current aircraft
        if (currentAircraft) {
            updateArrowRotation(currentAircraft.bearing);
        }
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