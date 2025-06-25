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

        websocket = new WebSocket(WS_URL);

        websocket.onopen = () => {
            console.log('Connected! Requesting logbook data...');
            websocket.send(JSON.stringify({ type: 'get_logbook' }));
        };

        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'logbook_data') {
                console.log('Received logbook data:', data.log);
                displayLogbook(data.log);
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