/**
 * Dashboard JavaScript for Brum Brum Tracker
 * Displays list of approaching aircraft with ETAs
 */

// Configuration
// Use WSS when page is served over HTTPS, WS otherwise
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_PORT = window.location.protocol === 'https:' ? '8001' : '8000';
const WS_URL = `${WS_PROTOCOL}//${window.location.hostname}:${WS_PORT}/ws`;
const RECONNECT_DELAY = 3000;

// State
let ws = null;
let reconnectTimeout = null;
let aircraftData = [];

// DOM Elements
const connectionIndicator = document.getElementById('connection-indicator');
const statusDot = connectionIndicator.querySelector('.status-dot');
const statusText = connectionIndicator.querySelector('.status-text');
const aircraftList = document.getElementById('aircraft-list');
const noAircraftDiv = document.getElementById('no-aircraft');
const aircraftTable = document.getElementById('aircraft-table');
const totalCount = document.getElementById('total-count');
const nextArrival = document.getElementById('next-arrival');
const lastUpdate = document.getElementById('last-update');

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
});

/**
 * Connect to WebSocket server
 */
function connectWebSocket() {
    console.log(`Connecting to WebSocket at ${WS_URL}`);
    
    ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
        console.log('Connected to WebSocket server');
        updateConnectionStatus(true);
        
        // Clear any pending reconnect
        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
        }
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleMessage(data);
        } catch (error) {
            console.error('Error parsing message:', error);
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus(false);
    };
    
    ws.onclose = () => {
        console.log('WebSocket connection closed');
        updateConnectionStatus(false);
        scheduleReconnect();
    };
}

/**
 * Handle incoming WebSocket messages
 */
function handleMessage(data) {
    switch (data.type) {
        case 'approaching_aircraft_list':
            updateAircraftList(data.aircraft);
            updateStats(data);
            break;
        case 'welcome':
            console.log('Received welcome message');
            break;
        default:
            // Ignore other message types (like single aircraft updates)
            break;
    }
}

/**
 * Update the aircraft list display
 */
function updateAircraftList(aircraft) {
    aircraftData = aircraft;
    
    // Clear existing rows
    aircraftList.innerHTML = '';
    
    if (!aircraft || aircraft.length === 0) {
        // Show no aircraft message
        noAircraftDiv.classList.remove('hidden');
        aircraftTable.classList.add('hidden');
        return;
    }
    
    // Hide no aircraft message
    noAircraftDiv.classList.add('hidden');
    aircraftTable.classList.remove('hidden');
    
    // Add rows for each aircraft
    aircraft.forEach((plane, index) => {
        const row = createAircraftRow(plane, index);
        aircraftList.appendChild(row);
    });
}

/**
 * Create a table row for an aircraft
 */
function createAircraftRow(plane, index) {
    const row = document.createElement('tr');
    
    // Determine ETA color class
    let etaClass = 'eta-far';
    if (plane.eta_minutes < 2) {
        etaClass = 'eta-imminent';
    } else if (plane.eta_minutes < 5) {
        etaClass = 'eta-soon';
    }
    
    row.className = etaClass;
    
    // Format ETA
    const etaText = formatETA(plane.eta_seconds);
    
    // Format bearing as compass direction
    const direction = bearingToCompass(plane.bearing);
    
    row.innerHTML = `
        <td class="flight-info">
            <div class="callsign">${plane.callsign || plane.icao24}</div>
            <div class="aircraft-type">${plane.aircraft_type || ''}</div>
        </td>
        <td>${plane.distance_km} km</td>
        <td class="eta-cell">${etaText}</td>
        <td>${plane.altitude_ft.toLocaleString()} ft</td>
        <td>${Math.round(plane.speed_kmh)} km/h</td>
        <td>${direction}</td>
    `;
    
    // Add animation for new aircraft
    if (index === 0) {
        row.classList.add('pulse');
    }
    
    return row;
}

/**
 * Format ETA in human-readable format
 */
function formatETA(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.round(seconds % 60);
        return `${minutes}m ${secs}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.round((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}

/**
 * Convert bearing to compass direction
 */
function bearingToCompass(bearing) {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.round(bearing / 45) % 8;
    return directions[index];
}

/**
 * Update statistics
 */
function updateStats(data) {
    // Update total count
    totalCount.textContent = data.aircraft_count || 0;
    
    // Update next arrival
    if (data.aircraft && data.aircraft.length > 0) {
        const nextETA = formatETA(data.aircraft[0].eta_seconds);
        nextArrival.textContent = nextETA;
    } else {
        nextArrival.textContent = '--:--';
    }
    
    // Update last update time
    const now = new Date();
    lastUpdate.textContent = now.toLocaleTimeString();
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(connected) {
    if (connected) {
        connectionIndicator.classList.remove('disconnected');
        connectionIndicator.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        connectionIndicator.classList.remove('connected');
        connectionIndicator.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }
}

/**
 * Schedule WebSocket reconnection
 */
function scheduleReconnect() {
    if (reconnectTimeout) return;
    
    console.log(`Reconnecting in ${RECONNECT_DELAY / 1000} seconds...`);
    reconnectTimeout = setTimeout(() => {
        reconnectTimeout = null;
        connectWebSocket();
    }, RECONNECT_DELAY);
}

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Page is hidden, close connection to save battery
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close();
        }
    } else {
        // Page is visible, reconnect if needed
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            connectWebSocket();
        }
    }
});