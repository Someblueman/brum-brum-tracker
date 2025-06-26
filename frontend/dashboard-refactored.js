/**
 * Dashboard JavaScript for Brum Brum Tracker - Refactored
 * Uses shared modules for WebSocket and UI utilities
 */

import { WebSocketManager } from './js/modules/websocket-manager.js';
import { 
    updateConnectionStatus,
    formatDistance,
    formatAltitude,
    formatSpeed,
    formatDuration,
    formatTime,
    getCountryFlag
} from './js/modules/ui-utils.js';

// State
let aircraftData = [];

// DOM Elements
const elements = {
    connectionIndicator: document.getElementById('connection-indicator'),
    statusDot: document.querySelector('.status-dot'),
    statusText: document.querySelector('.status-text'),
    aircraftList: document.getElementById('aircraft-list'),
    noAircraft: document.getElementById('no-aircraft'),
    aircraftTable: document.getElementById('aircraft-table'),
    totalCount: document.getElementById('total-count'),
    nextArrival: document.getElementById('next-arrival'),
    lastUpdate: document.getElementById('last-update')
};

// Initialize WebSocket Manager
const wsManager = new WebSocketManager();

// Setup WebSocket event handlers
wsManager.on('statusChange', ({ connected, reconnecting }) => {
    updateConnectionStatus(elements.connectionIndicator, connected, reconnecting);
});

wsManager.on('message', handleMessage);

wsManager.on('open', () => {
    console.log('Dashboard connected to WebSocket server');
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    wsManager.connect();
    WebSocketManager.setupVisibilityHandling(wsManager);
});

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
    elements.aircraftList.innerHTML = '';
    
    if (aircraft.length === 0) {
        elements.noAircraft.style.display = 'block';
        elements.aircraftTable.style.display = 'none';
        return;
    }
    
    elements.noAircraft.style.display = 'none';
    elements.aircraftTable.style.display = 'table';
    
    // Sort by ETA
    aircraft.sort((a, b) => (a.eta_seconds || Infinity) - (b.eta_seconds || Infinity));
    
    // Create rows
    aircraft.forEach((plane, index) => {
        const row = createAircraftRow(plane, index + 1);
        elements.aircraftList.appendChild(row);
    });
}

/**
 * Create a table row for an aircraft
 */
function createAircraftRow(aircraft, position) {
    const row = document.createElement('tr');
    
    // Position
    const posCell = document.createElement('td');
    posCell.textContent = position;
    row.appendChild(posCell);
    
    // Callsign with flag
    const callsignCell = document.createElement('td');
    const flag = aircraft.origin_airport_country_code 
        ? getCountryFlag(aircraft.origin_airport_country_code) + ' '
        : '';
    callsignCell.textContent = flag + (aircraft.callsign || aircraft.icao24 || 'Unknown');
    row.appendChild(callsignCell);
    
    // Aircraft type
    const typeCell = document.createElement('td');
    typeCell.textContent = aircraft.aircraft_type || 'Unknown';
    row.appendChild(typeCell);
    
    // Distance
    const distanceCell = document.createElement('td');
    distanceCell.textContent = formatDistance(aircraft.distance);
    row.appendChild(distanceCell);
    
    // Altitude
    const altitudeCell = document.createElement('td');
    altitudeCell.textContent = formatAltitude(aircraft.altitude || 0);
    row.appendChild(altitudeCell);
    
    // Speed
    const speedCell = document.createElement('td');
    speedCell.textContent = formatSpeed(aircraft.velocity || 0);
    row.appendChild(speedCell);
    
    // Direction
    const directionCell = document.createElement('td');
    directionCell.textContent = getCompassDirection(aircraft.bearing);
    row.appendChild(directionCell);
    
    // ETA
    const etaCell = document.createElement('td');
    if (aircraft.eta_seconds && aircraft.eta_seconds > 0) {
        etaCell.textContent = formatDuration(aircraft.eta_seconds);
        // Highlight if arriving soon
        if (aircraft.eta_seconds < 60) {
            etaCell.classList.add('arriving-soon');
        }
    } else {
        etaCell.textContent = '—';
    }
    row.appendChild(etaCell);
    
    // Route
    const routeCell = document.createElement('td');
    const origin = aircraft.origin_airport_iata || '?';
    const dest = aircraft.destination_airport_iata || '?';
    routeCell.textContent = `${origin} → ${dest}`;
    routeCell.title = `${aircraft.origin_airport_name || 'Unknown'} → ${aircraft.destination_airport_name || 'Unknown'}`;
    row.appendChild(routeCell);
    
    // Add click handler
    row.addEventListener('click', () => {
        // Could implement aircraft detail view here
        console.log('Selected aircraft:', aircraft);
    });
    
    return row;
}

/**
 * Update statistics
 */
function updateStats(data) {
    // Total count
    if (elements.totalCount) {
        elements.totalCount.textContent = data.aircraft ? data.aircraft.length : 0;
    }
    
    // Next arrival
    if (elements.nextArrival && data.aircraft && data.aircraft.length > 0) {
        const nextPlane = data.aircraft.reduce((prev, curr) => 
            (curr.eta_seconds || Infinity) < (prev.eta_seconds || Infinity) ? curr : prev
        );
        
        if (nextPlane.eta_seconds) {
            const etaText = formatDuration(nextPlane.eta_seconds);
            elements.nextArrival.textContent = `${nextPlane.callsign || 'Aircraft'} in ${etaText}`;
        } else {
            elements.nextArrival.textContent = 'No ETA available';
        }
    }
    
    // Last update time
    if (elements.lastUpdate) {
        elements.lastUpdate.textContent = formatTime(new Date());
    }
}

/**
 * Convert bearing to compass direction
 */
function getCompassDirection(bearing) {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.round(bearing / 45) % 8;
    return directions[index];
}

// Auto-refresh every 5 seconds
setInterval(() => {
    if (wsManager.isConnected && elements.lastUpdate) {
        elements.lastUpdate.textContent = formatTime(new Date());
    }
}, 5000);