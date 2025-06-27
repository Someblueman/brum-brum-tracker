/**
 * Brum Brum Tracker - Refactored Frontend JavaScript
 * Uses modular architecture with shared components
 */

import { WebSocketManager } from './js/modules/websocket-manager.js';
import { DeviceOrientationManager } from './js/modules/device-orientation.js';
import { 
    updateConnectionStatus, 
    formatDistance, 
    formatAltitude, 
    formatSpeed,
    toggleElement,
    updateValueWithAnimation
} from './js/modules/ui-utils.js';

// Map configuration - will be loaded from backend
let HOME_LAT = null;
let HOME_LON = null;

// Configuration
const GLOW_DURATION = 15000; // 15 seconds

// Initialize map
let map = null;

// State
let currentAircraft = null;
let allAircraft = [];  // Track all nearby aircraft
let glowTimeout = null;
let seenAircraft = new Set(); // Track aircraft that have already played sound
let aircraftLastSeen = new Map(); // Track when each aircraft was last seen
let sessionSpottedCount = 0; // Session counter
let familyVoicePreference = 'mamma-pappa'; // Default voice preference

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
    sessionTracker: document.getElementById('session-tracker'),
    sessionCountNumber: document.getElementById('session-count-number'),
    originInfo: document.getElementById('origin-info'),
    originFlag: document.getElementById('origin-flag'),
    originCountry: document.getElementById('origin-country'),
    destinationInfo: document.getElementById('destination-info'),
    destinationFlag: document.getElementById('destination-flag'),
    destinationCountry: document.getElementById('destination-country'),
    enableCompassBtn: document.getElementById('enable-compass-btn'),
    compassStatus: document.getElementById('compass-status'),
    dashboardLink: document.getElementById('dashboard-link'),
    atcSound: document.getElementById('atc-sound'),
    aircraftSound: document.getElementById('aircraft-sound'),
    logbookButton: document.getElementById('logbook-button')
};

// Initialize WebSocket Manager
const wsManager = new WebSocketManager({
    reconnectConfig: {
        jitterFactor: 0.3
    }
});

// Initialize Device Orientation Manager
const orientationManager = new DeviceOrientationManager({
    onHeadingUpdate: (heading) => {
        updateArrowRotation();
    },
    onPermissionChange: (hasPermission) => {
        updateCompassStatus(hasPermission);
    }
});

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

/**
 * Initialize the application
 */
function init() {
    // Setup WebSocket event handlers
    wsManager.on('statusChange', ({ connected, reconnecting }) => {
        updateConnectionStatus(elements.connectionStatus, connected, reconnecting);
    });
    
    wsManager.on('message', handleMessage);
    
    wsManager.on('open', () => {
        console.log('WebSocket connected');
    });
    
    // Setup visibility handling for auto-reconnect
    WebSocketManager.setupVisibilityHandling(wsManager);
    
    // Setup UI event handlers
    setupEventHandlers();
    
    // Initialize map
    initializeMap();
    
    // Clean up old aircraft periodically
    setInterval(cleanupOldAircraft, 10000); // Every 10 seconds
}

/**
 * Setup UI event handlers
 */
function setupEventHandlers() {
    // Enable compass button
    if (elements.enableCompassBtn) {
        elements.enableCompassBtn.addEventListener('click', async () => {
            const hasPermission = await orientationManager.requestPermission();
            elements.enableCompassBtn.style.display = 'none';
        });
    }
    
    // Start buttons
    if (elements.startButtonMammaPappa) {
        elements.startButtonMammaPappa.addEventListener('click', () => {
            familyVoicePreference = 'mamma-pappa';
            startApp();
        });
    }
    
    if (elements.startButtonMormorPops) {
        elements.startButtonMormorPops.addEventListener('click', () => {
            familyVoicePreference = 'mormor-pops';
            startApp();
        });
    }
    
    // Dashboard link
    if (elements.dashboardLink) {
        elements.dashboardLink.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = '/dashboard.html';
        });
    }
}

/**
 * Start the app after user interaction
 */
async function startApp() {
    // Hide start overlay
    if (elements.startOverlay) {
        elements.startOverlay.style.display = 'none';
    }
    
    // Show app container
    if (elements.appContainer) {
        elements.appContainer.style.display = 'flex';
    }
    
    // Play unlock sound
    playSound(elements.unlockSound);
    
    // Connect WebSocket
    wsManager.connect();
    
    // Show compass button on iOS
    if (orientationManager.needsPermission && elements.enableCompassBtn) {
        elements.enableCompassBtn.style.display = 'block';
    } else {
        // Automatically request permission if not needed (non-iOS)
        orientationManager.requestPermission();
    }
}

/**
 * Handle WebSocket messages
 */
function handleMessage(data) {
    switch (data.type) {
        case 'aircraft_update':
            handleAircraftUpdate(data);
            break;
        case 'aircraft_list':
            allAircraft = data.aircraft || [];
            if (allAircraft.length > 0 && !currentAircraft) {
                selectAircraft(allAircraft[0]);
            }
            updateAircraftStack();
            break;
        case 'aircraft_spotted':
            handleAircraftSpotted(data);
            break;
        case 'welcome':
            console.log('Connected to server');
            break;
        default:
            console.log('Unknown message type:', data.type);
    }
}

/**
 * Handle aircraft update
 */
function handleAircraftUpdate(data) {
    // Update last seen time
    aircraftLastSeen.set(data.icao24, Date.now());
    
    // Update current aircraft if it matches
    if (currentAircraft && currentAircraft.icao24 === data.icao24) {
        currentAircraft = data;
        updateDisplay(data);
    }
    
    // Update aircraft in the list
    const index = allAircraft.findIndex(a => a.icao24 === data.icao24);
    if (index !== -1) {
        allAircraft[index] = data;
    } else {
        allAircraft.push(data);
    }
    
    updateAircraftStack();
    
    // Handle visibility changes
    if (data.is_visible && !seenAircraft.has(data.icao24)) {
        seenAircraft.add(data.icao24);
        playAircraftSound();
        
        // Start glow effect
        if (elements.arrowAnimator) {
            elements.arrowAnimator.classList.add('glow');
            
            if (glowTimeout) clearTimeout(glowTimeout);
            glowTimeout = setTimeout(() => {
                elements.arrowAnimator.classList.remove('glow');
            }, GLOW_DURATION);
        }
    }
}

/**
 * Handle aircraft spotted event
 */
function handleAircraftSpotted(data) {
    console.log('Aircraft spotted and logged:', data);
    
    // Increment session counter
    sessionSpottedCount++;
    updateSessionTracker();
    
    // Play special sound for spotted aircraft
    playSound(elements.atcSound);
}

/**
 * Update the main display
 */
function updateDisplay(aircraft) {
    if (!aircraft) {
        toggleElement(elements.noAircraft, true);
        toggleElement(elements.mainDisplay, false);
        return;
    }
    
    toggleElement(elements.noAircraft, false);
    toggleElement(elements.mainDisplay, true);
    
    // Update aircraft info
    if (elements.callsignDisplay) {
        elements.callsignDisplay.textContent = aircraft.callsign || aircraft.icao24 || 'Unknown';
    }
    
    if (elements.distanceDisplay) {
        elements.distanceDisplay.textContent = formatDistance(aircraft.distance);
    }
    
    if (elements.altitudeDisplay) {
        elements.altitudeDisplay.textContent = formatAltitude(aircraft.altitude || 0);
    }
    
    if (elements.speedDisplay) {
        elements.speedDisplay.textContent = formatSpeed(aircraft.velocity || 0);
    }
    
    if (elements.typeDisplay && aircraft.aircraft_type) {
        elements.typeDisplay.textContent = aircraft.aircraft_type;
        elements.typeDisplay.style.display = 'block';
    }
    
    // Update plane image
    if (elements.planeImage && aircraft.photo_url) {
        elements.planeImage.src = aircraft.photo_url;
        elements.planeImage.style.display = 'block';
    } else if (elements.planeImage) {
        elements.planeImage.style.display = 'none';
    }
    
    // Update origin/destination
    updateRouteInfo(aircraft);
    
    // Update arrow rotation
    updateArrowRotation();
}

/**
 * Update arrow rotation based on bearing and device heading
 */
function updateArrowRotation() {
    if (!currentAircraft || !elements.directionArrow) return;
    
    const bearing = currentAircraft.bearing || 0;
    const relativeBearing = orientationManager.calculateBearing(bearing);
    
    elements.directionArrow.style.transform = `rotate(${relativeBearing}deg)`;
}

/**
 * Update compass status indicator
 */
function updateCompassStatus(enabled) {
    if (elements.compassIndicator) {
        elements.compassIndicator.textContent = enabled ? 'Compass: On' : 'Compass: Off';
        elements.compassIndicator.className = enabled ? 'compass-on' : 'compass-off';
    }
}

/**
 * Update route information
 */
function updateRouteInfo(aircraft) {
    // Origin
    if (aircraft.origin_airport_name) {
        if (elements.originCountry) {
            elements.originCountry.textContent = aircraft.origin_airport_name;
        }
        if (elements.originFlag) {
            elements.originFlag.textContent = aircraft.origin_airport_country_flag || '';
        }
        toggleElement(elements.originInfo, true);
    } else {
        toggleElement(elements.originInfo, false);
    }
    
    // Destination
    if (aircraft.destination_airport_name) {
        if (elements.destinationCountry) {
            elements.destinationCountry.textContent = aircraft.destination_airport_name;
        }
        if (elements.destinationFlag) {
            elements.destinationFlag.textContent = aircraft.destination_airport_country_flag || '';
        }
        toggleElement(elements.destinationInfo, true);
    } else {
        toggleElement(elements.destinationInfo, false);
    }
}

/**
 * Update aircraft stack display
 */
function updateAircraftStack() {
    if (elements.countNumber) {
        updateValueWithAnimation(elements.countNumber, allAircraft.length);
    }
    
    // Update stack visibility
    if (allAircraft.length > 1) {
        toggleElement(elements.aircraftStack, true);
    } else {
        toggleElement(elements.aircraftStack, false);
    }
}

/**
 * Update session tracker
 */
function updateSessionTracker() {
    if (elements.sessionCountNumber) {
        updateValueWithAnimation(elements.sessionCountNumber, sessionSpottedCount);
    }
    
    if (sessionSpottedCount > 0) {
        toggleElement(elements.sessionTracker, true);
    }
}

/**
 * Select an aircraft to track
 */
function selectAircraft(aircraft) {
    currentAircraft = aircraft;
    updateDisplay(aircraft);
}

/**
 * Play sound
 */
function playSound(audioElement) {
    if (audioElement) {
        audioElement.currentTime = 0;
        audioElement.play().catch(e => console.log('Audio play failed:', e));
    }
}

/**
 * Play aircraft sound based on family preference
 */
function playAircraftSound() {
    const sounds = familyVoicePreference === 'mormor-pops' 
        ? ['mormor_1.wav', 'mormor_2.wav', 'pops_1.wav', 'pops_2.wav']
        : ['mamma_1.wav', 'mamma_2.wav', 'pappa_1.wav', 'pappa_2.wav', 'pappa_3.wav'];
    
    const randomSound = sounds[Math.floor(Math.random() * sounds.length)];
    
    // Create temporary audio element
    const audio = new Audio(`/assets/${randomSound}`);
    audio.play().catch(e => console.log('Audio play failed:', e));
}

/**
 * Clean up old aircraft
 */
function cleanupOldAircraft() {
    const now = Date.now();
    const timeout = 30000; // 30 seconds
    
    // Remove aircraft we haven't seen recently
    allAircraft = allAircraft.filter(aircraft => {
        const lastSeen = aircraftLastSeen.get(aircraft.icao24) || 0;
        return (now - lastSeen) < timeout;
    });
    
    // Clean up the lastSeen map
    for (const [icao24, lastSeen] of aircraftLastSeen.entries()) {
        if ((now - lastSeen) > timeout) {
            aircraftLastSeen.delete(icao24);
            seenAircraft.delete(icao24);
        }
    }
    
    // Update display if current aircraft was removed
    if (currentAircraft && !allAircraft.find(a => a.icao24 === currentAircraft.icao24)) {
        currentAircraft = allAircraft[0] || null;
        updateDisplay(currentAircraft);
    }
    
    updateAircraftStack();
}

/**
 * Initialize map
 */
function initializeMap() {
    if (!document.getElementById('map')) return;
    
    // Initialize Leaflet map
    map = L.map('map').setView([HOME_LAT, HOME_LON], 10);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Add home marker
    L.marker([HOME_LAT, HOME_LON]).addTo(map)
        .bindPopup('Home')
        .openPopup();
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);