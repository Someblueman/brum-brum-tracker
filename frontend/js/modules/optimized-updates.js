/**
 * Optimized update functions for the main tracker
 * Reduces unnecessary re-renders and DOM manipulations
 */

import { RenderOptimizer, debounce, throttle, memoize } from './render-optimizer.js';

// Create render optimizer instance
const optimizer = new RenderOptimizer();

// Cache for computed values
const computedCache = new Map();

/**
 * Create optimized display updaters
 * @param {Object} elements - DOM elements object
 * @returns {Object} Optimized updaters
 */
export function createOptimizedUpdaters(elements) {
    const updaters = {};
    
    // Distance updater with formatting
    updaters.updateDistance = optimizer.createUpdater(
        elements.distanceDisplay, 
        'textContent', 
        'distance'
    );
    
    // Callsign updater
    updaters.updateCallsign = optimizer.createUpdater(
        elements.callsignDisplay,
        'textContent',
        'callsign'
    );
    
    // Altitude updater with formatting
    updaters.updateAltitude = (altitude) => {
        const formatted = `${altitude.toLocaleString()} ft`;
        optimizer.scheduleUpdate('altitude', (val) => {
            if (elements.altitudeDisplay) {
                elements.altitudeDisplay.textContent = val;
            }
        }, formatted);
    };
    
    // Speed updater with rounding
    updaters.updateSpeed = (speed) => {
        const rounded = `${Math.round(speed)} km/h`;
        optimizer.scheduleUpdate('speed', (val) => {
            if (elements.speedDisplay) {
                elements.speedDisplay.textContent = val;
            }
        }, rounded);
    };
    
    // Type updater
    updaters.updateType = optimizer.createUpdater(
        elements.typeDisplay,
        'textContent',
        'type'
    );
    
    // Image updater with lazy loading
    updaters.updateImage = (imageUrl) => {
        optimizer.scheduleUpdate('image', (url) => {
            if (elements.planeImage && url) {
                // Only update if URL actually changed
                if (elements.planeImage.src !== url) {
                    elements.planeImage.src = url;
                }
            }
        }, imageUrl);
    };
    
    // Arrow rotation updater (high priority, no throttling)
    updaters.updateArrow = (bearing) => {
        optimizer.scheduleUpdate('bearing', (val) => {
            if (elements.arrow) {
                elements.arrow.style.transform = `rotate(${val}deg)`;
            }
        }, bearing, { immediate: true });
    };
    
    return updaters;
}

/**
 * Optimized aircraft update function
 * @param {Object} aircraft - Aircraft data
 * @param {Object} elements - DOM elements
 * @param {Object} updaters - Optimized updaters
 */
export function updateAircraftOptimized(aircraft, elements, updaters) {
    // Check if aircraft data has significantly changed
    const cacheKey = `${aircraft.icao24}_${aircraft.distance_km}_${aircraft.bearing}`;
    const lastCache = computedCache.get('lastAircraft');
    
    if (lastCache === cacheKey) {
        // Only update bearing for smooth rotation
        updaters.updateArrow(aircraft.bearing);
        return;
    }
    
    computedCache.set('lastAircraft', cacheKey);
    
    // Batch all updates together
    optimizer.batchUpdates([
        {
            key: 'distance',
            fn: () => updaters.updateDistance(`${aircraft.distance_km} km`),
            value: aircraft.distance_km
        },
        {
            key: 'callsign',
            fn: () => updaters.updateCallsign(aircraft.callsign || aircraft.icao24),
            value: aircraft.callsign || aircraft.icao24
        },
        {
            key: 'altitude',
            fn: () => updaters.updateAltitude(aircraft.altitude_ft),
            value: aircraft.altitude_ft
        },
        {
            key: 'speed',
            fn: () => updaters.updateSpeed(aircraft.speed_kmh),
            value: aircraft.speed_kmh
        },
        {
            key: 'type',
            fn: () => updaters.updateType(aircraft.aircraft_type || 'Unknown'),
            value: aircraft.aircraft_type
        }
    ]);
    
    // Update image only if changed
    if (aircraft.image_url) {
        updaters.updateImage(aircraft.image_url);
    }
    
    // Update arrow immediately for smooth rotation
    updaters.updateArrow(aircraft.bearing);
    
    // Show/hide elements efficiently
    if (elements.mainDisplay.classList.contains('hidden')) {
        elements.mainDisplay.classList.remove('hidden');
    }
    if (!elements.noAircraft.classList.contains('hidden')) {
        elements.noAircraft.classList.add('hidden');
    }
}

/**
 * Optimized route information update
 * @param {Object} origin - Origin data
 * @param {Object} destination - Destination data
 * @param {Object} elements - DOM elements
 */
export const updateRouteOptimized = memoize((origin, destination, elements) => {
    // Update origin
    if (origin && origin.country_code) {
        const originKey = `${origin.country_code}_${origin.airport}`;
        optimizer.scheduleUpdate(`route_origin_${originKey}`, () => {
            if (elements.originFlag) {
                elements.originFlag.textContent = getFlagEmoji(origin.country_code);
            }
            if (elements.originName) {
                const display = origin.airport !== 'Unknown' 
                    ? origin.airport 
                    : origin.region || origin.country_code;
                elements.originName.textContent = display;
            }
        }, originKey);
    }
    
    // Update destination
    if (destination && destination.country_code) {
        const destKey = `${destination.country_code}_${destination.airport}`;
        optimizer.scheduleUpdate(`route_dest_${destKey}`, () => {
            if (elements.destinationFlag) {
                elements.destinationFlag.textContent = getFlagEmoji(destination.country_code);
            }
            if (elements.destinationName) {
                const display = destination.airport !== 'Unknown'
                    ? destination.airport
                    : destination.region || destination.country_code;
                elements.destinationName.textContent = display;
            }
        }, destKey);
    }
}, (args) => `${args[0]?.country_code}_${args[1]?.country_code}`);

/**
 * Optimized aircraft stack update
 * @param {Array} aircraft - Array of aircraft
 * @param {HTMLElement} container - Stack container element
 */
export const updateAircraftStackOptimized = throttle((aircraft, container) => {
    if (!container || !aircraft || aircraft.length <= 1) {
        if (container) {
            container.style.display = 'none';
        }
        return;
    }
    
    // Only show up to 4 additional aircraft
    const stackAircraft = aircraft.slice(1, 5);
    const stackKey = stackAircraft.map(a => a.icao24).join('_');
    
    // Check if stack needs updating
    const lastStackKey = computedCache.get('lastStack');
    if (lastStackKey === stackKey) {
        return;
    }
    
    computedCache.set('lastStack', stackKey);
    
    // Update stack efficiently
    optimizer.scheduleUpdate('stack', () => {
        container.innerHTML = '';
        container.style.display = 'flex';
        
        stackAircraft.forEach((ac, index) => {
            const item = document.createElement('div');
            item.className = 'stack-item';
            item.style.opacity = 1 - (index * 0.2);
            
            const callsign = document.createElement('span');
            callsign.className = 'stack-callsign';
            callsign.textContent = ac.callsign || ac.icao24;
            
            const distance = document.createElement('span');
            distance.className = 'stack-distance';
            distance.textContent = `${ac.distance_km} km`;
            
            item.appendChild(callsign);
            item.appendChild(distance);
            container.appendChild(item);
        });
    }, stackKey);
}, 2000); // Update stack at most every 2 seconds

/**
 * Get flag emoji for country code (memoized)
 */
const getFlagEmoji = memoize((countryCode) => {
    if (!countryCode || countryCode.length !== 2) return '';
    
    const codePoints = countryCode
        .toUpperCase()
        .split('')
        .map(char => 127397 + char.charCodeAt());
    
    return String.fromCodePoint(...codePoints);
});

/**
 * Clear all optimization caches
 */
export function clearOptimizationCaches() {
    optimizer.clear();
    computedCache.clear();
}