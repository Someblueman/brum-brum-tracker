/**
 * Logbook page for Brum Brum Tracker
 * Displays a visual collection of all spotted aircraft types
 */

import { LazyImageLoader } from './js/modules/lazy-loader.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize lazy loader
    const lazyLoader = new LazyImageLoader({
        rootMargin: '100px 0px',
        placeholder: 'assets/plane-placeholder.svg'
    });
    const grid = document.getElementById('logbook-grid');
    const loadingMessage = document.getElementById('loading-logbook');

    const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const WS_PORT = window.location.protocol === 'https:' ? '8001' : '8000';
    const WS_URL = `${WS_PROTOCOL}//${window.location.hostname}:${WS_PORT}/ws`;

    let websocket = null;

    /**
     * Connect to WebSocket server and request logbook data
     */
    function connect() {
        console.log('Connecting to WebSocket...');
        loadingMessage.classList.remove('hidden');

        // Load cached data immediately
        const cachedLog = getCachedLogbook();
        if (cachedLog) {
            console.log('Displaying cached logbook data.');
            displayLogbook(cachedLog);
            loadingMessage.classList.add('hidden');
        }

        websocket = new WebSocket(WS_URL);

        websocket.onopen = () => {
            console.log('Connected! Requesting logbook data...');
            // Provide a fallback to an empty string if 'logbookLastUpdate' is not set
            const lastUpdate = localStorage.getItem('logbookLastUpdate') || '';
            websocket.send(JSON.stringify({
                type: 'get_logbook',
                since: lastUpdate
            }));
        };

        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'logbook_data') {
                console.log('Received logbook data:', data.log);
                updateLogbook(data.log); // New function to update the logbook
                loadingMessage.classList.add('hidden');
            }
        };

        websocket.onerror = (error) => {
            console.error('WebSocket Error:', error);
            loadingMessage.textContent = 'Could not connect to the server.';
        };

        websocket.onclose = () => {
            console.log('WebSocket disconnected.');
        };
    }

    /**
     * Get cached logbook data from localStorage
     * @returns {Array|null} Cached logbook entries or null if none exist
     */
    function getCachedLogbook() {
        const cachedData = localStorage.getItem('logbook');
        return cachedData ? JSON.parse(cachedData) : null;
    }

    /**
     * Store logbook data in localStorage with timestamp
     * @param {Array} log - Array of logbook entries to cache
     */
    function setCachedLogbook(log) {
        localStorage.setItem('logbook', JSON.stringify(log));
        localStorage.setItem('logbookLastUpdate', new Date().toISOString());
    }

    /**
     * Update logbook with new entries, merging with cached data
     * @param {Array} newEntries - New logbook entries from server
     */
    function updateLogbook(newEntries) {
        let log = getCachedLogbook() || [];

        // Create a map for quick lookups
        const logMap = new Map(log.map(entry => [entry.aircraft_type, entry]));

        // Add or update entries
        newEntries.forEach(entry => {
            logMap.set(entry.aircraft_type, entry);
        });

        // Convert back to an array and sort by date
        const updatedLog = Array.from(logMap.values());
        updatedLog.sort((a, b) => new Date(b.first_spotted) - new Date(a.first_spotted));

        setCachedLogbook(updatedLog);
        displayLogbook(updatedLog);
    }


    /**
     * Display logbook entries in the grid UI
     * @param {Array} log - Array of logbook entries to display
     */
    function displayLogbook(log) {
        const grid = document.getElementById('logbook-grid');
        grid.innerHTML = ''; // Clear previous entries
        if (!log || log.length === 0) {
            grid.innerHTML = '<p>No brum brums spotted yet. Go find some!</p>';
            return;
        }

        log.forEach(entry => {
            const card = document.createElement('div');
            card.className = 'logbook-card';

            // Create lazy-loaded image
            const planeImg = lazyLoader.createLazyImage(
                entry.image_url || 'assets/plane-placeholder.svg',
                entry.aircraft_type,
                'logbook-image'
            );
            
            // Observe the image for lazy loading
            lazyLoader.observe(planeImg);

            const planeName = document.createElement('div');
            planeName.className = 'plane-name';
            planeName.textContent = entry.aircraft_type;

            // Container for the details
            const detailsDiv = document.createElement('div');
            detailsDiv.className = 'sighting-details';

            // Sighting count
            const sightingCount = document.createElement('div');
            sightingCount.className = 'sighting-count';
            sightingCount.textContent = `Spotted: ${entry.sighting_count} time${entry.sighting_count > 1 ? 's' : ''}`;

            // First spotted date
            const firstSpotted = document.createElement('div');
            firstSpotted.className = 'sighting-date';
            const firstDate = new Date(entry.first_spotted);
            firstSpotted.textContent = `First seen: ${firstDate.toLocaleDateString()}`;

            // Append count and first date
            detailsDiv.appendChild(sightingCount);
            detailsDiv.appendChild(firstSpotted);

            // Last spotted date (only if it exists and is different from first)
            if (entry.last_spotted) {
                const lastSpotted = document.createElement('div');
                lastSpotted.className = 'sighting-date';
                const lastDate = new Date(entry.last_spotted);

                // Only show if it's a different day
                if (lastDate.toDateString() !== firstDate.toDateString()) {
                    lastSpotted.textContent = `Last seen: ${lastDate.toLocaleDateString()}`;
                    detailsDiv.appendChild(lastSpotted);
                }
            }

            card.appendChild(planeImg);
            card.appendChild(planeName);
            card.appendChild(detailsDiv);
            grid.appendChild(card);
        });
    }

    connect();
});