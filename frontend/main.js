/**
 * Brum Brum Tracker - Frontend JavaScript
 * Handles WebSocket connection, device orientation, and UI updates
 */

// Map configuration - matches backend constants
const HOME_LAT = 51.2792;
const HOME_LON = 1.2836;

// Initialize map
let map = null;

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
let aircraftLastSeen = new Map(); // Track when each aircraft was last seen
let sessionSpottedCount = 0; // New state for the session counter

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
    arrowAnimator: document.getElementById('arrow-animator'),
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
    compassIndicator: document.getElementById('compass-indicator'),
    startButton: document.getElementById('start-button'),
    startOverlay: document.getElementById('start-overlay'),
    appContainer: document.getElementById('app'),
    unlockSound: document.getElementById('unlock-sound'),
    startButtonMammaPappa: document.getElementById('start-button-mamma-pappa'),
    startButtonMormorPops: document.getElementById('start-button-mormor-pops'),
    startOverlay: document.getElementById('start-overlay'),
    sessionTracker: document.getElementById('session-tracker'),
    sessionCountNumber: document.getElementById('session-count-number'),
    originInfo: document.getElementById('origin-info'),
    originFlag: document.getElementById('origin-flag'),
    originCountry: document.getElementById('origin-country'),
    destinationInfo: document.getElementById('destination-info'),
    destinationFlag: document.getElementById('destination-flag'),
    destinationCountry: document.getElementById('destination-country'),
};

// Audio Configuration
const audioConfig = {
    'mamma_pappa': [
        'assets/mamma_brum.wav',
        'assets/pappa_swedish_brum.wav',
        'assets/bbc_voice_brum.wav',
        'assets/brum.wav',
        'assets/brum_brum.wav',
        'assets/get_ready_brum.wav',
        'assets/look_sky_brum.wav',
        'assets/sky_brum_brum.wav',
        'assets/wwe_brum.wav',
    ],
    'mormor_pops': [
        'assets/mormor_brum.wav',
        'assets/pops_brum.wav',
        'assets/bbc_voice_brum.wav',
        'assets/brum.wav',
        'assets/brum_brum.wav',
        'assets/get_ready_brum.wav',
        'assets/look_sky_brum.wav',
        'assets/sky_brum_brum.wav',
        'assets/wwe_brum.wav',
    ],
    'atc_sounds': [
        'assets/atc_1.mp3',
        'assets/atc_2.mp3',
        'assets/atc_3.mp3',
        'assets/atc_4.mp3',
        'assets/atc_5.mp3',
    ]
};

let activeBrumSet = [];
let atcAudioSet = [];
const ATC_SOUND_CHANCE = 0.2; // 20% chance to play an ATC sound

function getFlagEmoji(countryCode) {
    if (!countryCode || countryCode.length !== 2) return '';
    const codePoints = countryCode.toUpperCase().split('').map(char => 127397 + char.charCodeAt());
    return String.fromCodePoint(...codePoints);
}

function resetUI() {
    console.log('Resetting UI to its initial start screen state.');

    // Ensure start overlay is visible and main app is hidden
    if (elements.startOverlay) elements.startOverlay.style.display = 'flex';
    if (elements.appContainer) elements.appContainer.classList.add('hidden');

    // Close any existing WebSocket connection cleanly.
    if (websocket) {
        console.log('Closing WebSocket connection during UI reset.');
        // Remove the onclose handler to prevent automatic reconnection attempts during a manual reset.
        websocket.onclose = () => { };
        websocket.close(1000, "User navigating back to start screen");
        websocket = null;
    }

    // Explicitly reset the connection status indicator
    updateConnectionStatus('disconnected');

    // Stop any animations or pending timeouts
    if (glowTimeout) clearTimeout(glowTimeout);
    if (elements.arrowAnimator) elements.arrowAnimator.classList.remove('glow');

    // Reset and hide the session tracker
    sessionSpottedCount = 0;
    if (elements.sessionCountNumber) elements.sessionCountNumber.textContent = sessionSpottedCount;
    if (elements.sessionTracker) elements.sessionTracker.classList.add('hidden');



    // Ensure the start buttons are ready to be used again by re-binding them.
    rebindStartButtons();
}


/**
 * Re-creates the start buttons and attaches fresh event listeners.
 * This is a robust way to solve issues with the back-forward cache (bfcache).
 */
function rebindStartButtons() {
    console.log('Re-binding event listeners to start buttons.');

    const rebind = (buttonId, audioSetKey) => {
        const oldButton = document.getElementById(buttonId);
        const startButtonsContainer = document.getElementById('start-buttons');
        if (!oldButton || !startButtonsContainer) return;

        // Create a new button from scratch to ensure no old listeners are carried over.
        const newButton = document.createElement('button');
        newButton.id = oldButton.id;
        newButton.textContent = oldButton.textContent;
        newButton.className = oldButton.className;
        // Copy any other necessary attributes from the old button if needed.

        // Replace the old button with the new one in the DOM.
        startButtonsContainer.replaceChild(newButton, oldButton);

        // Add the click listener to the new button.
        newButton.addEventListener('click', () => startTracking(audioSetKey), { once: true });
    };

    rebind('start-button-mamma-pappa', 'mamma_pappa');
    rebind('start-button-mormor-pops', 'mormor_pops');
}


/**
 * Initialize the application
 */
function init() {
    console.log("Application initializing...");
    initializeMap();

    isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;

    document.addEventListener('visibilitychange', handleVisibilityChange);

    window.addEventListener('pageshow', function (event) {
        // event.persisted is true if the page was loaded from the bfcache.
        if (event.persisted) {
            console.log('Page has been restored from the bfcache. Resetting UI.');
            resetUI();
        }
    });

    // Initial UI state setup, in case pageshow doesn't fire on first load.
    resetUI();
}


/**
 * Start the tracking experience
 * @param {string} audioSetKey - The key for the selected audio set
 */
function startTracking(audioSetKey) {
    elements.startOverlay.style.display = 'none';
    elements.appContainer.classList.remove('hidden');

    sessionSpottedCount = 0;
    elements.sessionCountNumber.textContent = sessionSpottedCount;
    elements.sessionTracker.classList.add('hidden'); // Start hidden

    // Set the active audio files
    activeBrumSet = audioConfig[audioSetKey].map(src => {
        const audio = new Audio(src);
        audio.preload = 'auto';
        return audio;
    });

    // Load the ATC sounds
    atcAudioSet = audioConfig['atc_sounds'].map(src => {
        const audio = new Audio(src);
        audio.preload = 'auto';
        return audio;
    });


    // Unlock audio
    elements.unlockSound.play().catch(e => console.error("Could not play unlock sound:", e));

    // Start the main app logic
    showSearching();
    setupWebSocket();
    setupOrientationHandling();
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
            const timestamp = new Date().toISOString();
            console.log(`WEBSOCKET CONNECTED: ${timestamp} (attempt #${reconnectAttempts + 1})`);
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
            const timestamp = new Date().toISOString();
            console.log(`WEBSOCKET DISCONNECTED: ${timestamp} - Code: ${event.code}, Reason: ${event.reason || 'none'}`);
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

        // Add this new case to explicitly ignore the dashboard's message type
        case 'approaching_aircraft_list':
            // This message is for the dashboard, so the main tracker ignores it.
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
    // The backend now sends a single, reliable list sorted by distance
    if (data.all_aircraft && data.all_aircraft.length > 0) {
        allAircraft = data.all_aircraft;

        // The main aircraft to display is ALWAYS the first one in the list (the closest)
        const mainAircraft = allAircraft[0];

        updateAircraftDisplay(mainAircraft);
        updateAircraftStack(); // This will show the others
    } else {
        // This can happen if the message is malformed, treat as no aircraft
        showNoAircraft();
    }
}

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

    // Update Route Information
    if (aircraft.origin && aircraft.origin.country_code) {
        elements.originFlag.textContent = getFlagEmoji(aircraft.origin.country_code);
        // Display airport name, or region, or country code as fallback
        const originDisplay = aircraft.origin.airport !== 'Unknown' 
            ? aircraft.origin.airport 
            : (aircraft.origin.region_name || aircraft.origin.country_code || 'Unknown');
        elements.originCountry.textContent = originDisplay;
        elements.originInfo.classList.remove('hidden');
    } else {
        elements.originInfo.classList.add('hidden');
    }

    if (aircraft.destination && aircraft.destination.country_code) {
        elements.destinationFlag.textContent = getFlagEmoji(aircraft.destination.country_code);
        // Display airport name, or region, or country code as fallback
        const destDisplay = aircraft.destination.airport !== 'Unknown' 
            ? aircraft.destination.airport 
            : (aircraft.destination.region_name || aircraft.destination.country_code || 'Unknown');
        elements.destinationCountry.textContent = destDisplay;
        elements.destinationInfo.classList.remove('hidden');
    } else {
        elements.destinationInfo.classList.add('hidden');
    }

    // Check if this is a new aircraft (not seen before) or hasn't been seen in 5 minutes
    const aircraftId = aircraft.icao24;
    const now = Date.now();
    const lastSeen = aircraftLastSeen.get(aircraftId);
    const fiveMinutes = 5 * 60 * 1000; // 5 minutes in milliseconds

    // Only increment the session counter for planes we haven't seen yet in this session.
    if (!seenAircraft.has(aircraftId)) {
        sessionSpottedCount++;
        elements.sessionCountNumber.textContent = sessionSpottedCount;
        // Show the tracker and keep it visible for the rest of the session
        if (elements.sessionTracker.classList.contains('hidden')) {
            elements.sessionTracker.classList.remove('hidden');
        }
    }

    if (!seenAircraft.has(aircraftId) || (lastSeen && now - lastSeen > fiveMinutes)) {
        // First time seeing this aircraft OR hasn't been seen in 5 minutes
        seenAircraft.add(aircraftId);
        const reason = !lastSeen ? 'FIRST TIME' : 'RETURNED (>5min)';
        console.log(`AIRCRAFT EVENT: ${reason} - ${aircraftId} (${aircraft.callsign || 'no callsign'}) ` +
            `at ${aircraft.distance_km}km, ${aircraft.elevation_angle}° elevation`);
        playNotification();
    } else {
        const timeSince = Math.round((now - lastSeen) / 1000);
        console.log(`AIRCRAFT UPDATE: ${aircraftId} seen ${timeSince}s ago - no sound`);
    }

    // Update last seen time
    aircraftLastSeen.set(aircraftId, now);
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

    // Don't clear seen aircraft here - we want to remember them
    // to prevent repeated audio when they briefly disappear

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

    // Don't clear seen aircraft here - we want to remember them
    // to prevent repeated audio when they briefly disappear

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

    // When aircraft is very close/overhead, use flight track instead of bearing
    if (currentAircraft && currentAircraft.distance_km < 3.0 && currentAircraft.elevation_angle > 60) {
        // Aircraft is nearly overhead - arrow becomes less useful
        // Could show flight direction instead, but for now just point up
        console.log(`Aircraft overhead (${currentAircraft.distance_km}km, ${currentAircraft.elevation_angle}°) - arrow pointing up`);
        rotation = 0; // Point north/up when overhead
    } else if (hasOrientationPermission && deviceHeading !== 0) {
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
    let soundToPlay = null;

    // Decide whether to play a regular sound or an ATC sound
    if (Math.random() < ATC_SOUND_CHANCE && atcAudioSet.length > 0) {
        // Play an ATC sound
        const randomIndex = Math.floor(Math.random() * atcAudioSet.length);
        soundToPlay = atcAudioSet[randomIndex];
        console.log('Decided to play an ATC sound.');
    } else if (activeBrumSet.length > 0) {
        // Play a regular "brum" sound
        const randomIndex = Math.floor(Math.random() * activeBrumSet.length);
        soundToPlay = activeBrumSet[randomIndex];
        console.log('Decided to play a Brum sound.');
    }

    if (soundToPlay) {
        const soundFile = soundToPlay.src.split('/').pop();
        console.log(`AUDIO: Attempting to play sound: ${soundFile}`);

        soundToPlay.play()
            .then(() => {
                console.log(`AUDIO: Successfully played ${soundFile}`);
            })
            .catch(error => {
                console.error(`AUDIO: Failed to play ${soundFile} - ${error.name}: ${error.message}`);
            });
    }

    // Add glow effect TO THE WRAPPER
    elements.arrowAnimator.classList.add('glow');
    console.log('UI: Added glow effect to arrow');

    // Remove glow after duration
    clearTimeout(glowTimeout);
    glowTimeout = setTimeout(() => {
        elements.arrowAnimator.classList.remove('glow');
        console.log('UI: Removed glow effect from arrow');
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

/**
 * Initialize the Leaflet map
 */
function initializeMap() {
    try {
        // Create map with all interactions disabled
        map = L.map('map', {
            center: [HOME_LAT, HOME_LON],
            zoom: 9,
            zoomControl: false,
            dragging: false,
            touchZoom: false,
            scrollWheelZoom: false,
            doubleClickZoom: false,
            boxZoom: false,
            keyboard: false,
            tap: false,
            attributionControl: false
        });

        // Add a simple, clean tile layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
            maxZoom: 19
        }).addTo(map);

    } catch (error) {
        console.error('Error initializing map:', error);
        document.getElementById('map').style.display = 'none'; // Hide map on error
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}