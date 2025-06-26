document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('logbook-grid');
    const loadingMessage = document.getElementById('loading-logbook');

    const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const WS_PORT = window.location.protocol === 'https:' ? '8001' : '8000';
    const WS_URL = `${WS_PROTOCOL}//${window.location.hostname}:${WS_PORT}/ws`;

    let websocket = null;

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

    function getCachedLogbook() {
        const cachedData = localStorage.getItem('logbook');
        return cachedData ? JSON.parse(cachedData) : null;
    }

    function setCachedLogbook(log) {
        localStorage.setItem('logbook', JSON.stringify(log));
        localStorage.setItem('logbookLastUpdate', new Date().toISOString());
    }

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


    function displayLogbook(log) {
        grid.innerHTML = ''; // Clear previous entries
        if (!log || log.length === 0) {
            grid.innerHTML = '<p>No brum brums spotted yet. Go find some!</p>';
            return;
        }

        log.forEach(entry => {
            const card = document.createElement('div');
            card.className = 'logbook-card';

            const planeImg = document.createElement('img');
            planeImg.src = entry.image_url || 'plane-placeholder.svg';
            planeImg.alt = entry.aircraft_type;

            const planeName = document.createElement('div');
            planeName.className = 'plane-name';
            planeName.textContent = entry.aircraft_type;

            const firstSpotted = document.createElement('div');
            firstSpotted.className = 'first-spotted';
            const date = new Date(entry.first_spotted);
            firstSpotted.textContent = `First spotted: ${date.toLocaleDateString()}`;

            card.appendChild(planeImg);
            card.appendChild(planeName);
            card.appendChild(firstSpotted);
            grid.appendChild(card);
        });
    }

    connect();
});