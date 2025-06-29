// Get WebSocket URL based on current protocol
function getWebSocketUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsPort = window.location.protocol === 'https:' ? '8001' : '8000';
    return `${protocol}//${window.location.hostname}:${wsPort}`;
}

// Format timestamp for display
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) {
        return `${diffMins} minutes ago`;
    } else if (diffHours < 24) {
        return `${diffHours} hours ago`;
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else {
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }
}

// Show aircraft details in modal
function showDetails(aircraft) {
    const modal = document.getElementById('detailsModal');
    const content = document.getElementById('modalContent');
    
    let html = '<table style="width: 100%;">';
    
    // Basic info
    html += `<tr><td><strong>ICAO24:</strong></td><td>${aircraft.icao24}</td></tr>`;
    html += `<tr><td><strong>Logged At:</strong></td><td>${new Date(aircraft.logged_at).toLocaleString()}</td></tr>`;
    html += `<tr><td><strong>Data Source:</strong></td><td>${aircraft.data_source || 'N/A'}</td></tr>`;
    
    // Type info
    if (aircraft.simplified_type) {
        html += `<tr><td><strong>Simplified Type:</strong></td><td>${aircraft.simplified_type}</td></tr>`;
    }
    if (aircraft.raw_type) {
        html += `<tr><td><strong>Raw Type:</strong></td><td>${aircraft.raw_type}</td></tr>`;
    }
    if (aircraft.manufacturer) {
        html += `<tr><td><strong>Manufacturer:</strong></td><td>${aircraft.manufacturer}</td></tr>`;
    }
    if (aircraft.type_name) {
        html += `<tr><td><strong>Type Name:</strong></td><td>${aircraft.type_name}</td></tr>`;
    }
    
    // Additional info
    if (aircraft.callsign) {
        html += `<tr><td><strong>Callsign:</strong></td><td>${aircraft.callsign}</td></tr>`;
    }
    if (aircraft.registration) {
        html += `<tr><td><strong>Registration:</strong></td><td>${aircraft.registration}</td></tr>`;
    }
    if (aircraft.operator) {
        html += `<tr><td><strong>Operator:</strong></td><td>${aircraft.operator}</td></tr>`;
    }
    
    html += '</table>';
    
    // Raw API response if available
    if (aircraft.raw_api_response) {
        html += '<h3>Raw API Response:</h3>';
        try {
            const parsed = JSON.parse(aircraft.raw_api_response);
            html += `<pre>${JSON.stringify(parsed, null, 2)}</pre>`;
        } catch (e) {
            html += `<pre>${aircraft.raw_api_response}</pre>`;
        }
    }
    
    // Additional data if available
    if (aircraft.additional_data) {
        html += '<h3>Additional Data:</h3>';
        html += `<pre>${aircraft.additional_data}</pre>`;
    }
    
    content.innerHTML = html;
    modal.style.display = 'block';
}

// Close modal
function closeModal() {
    const modal = document.getElementById('detailsModal');
    modal.style.display = 'none';
}

// Load unidentified aircraft from backend
async function loadUnidentifiedAircraft() {
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const table = document.getElementById('aircraftTable');
    const tbody = document.getElementById('aircraftBody');
    const stats = document.getElementById('stats');
    
    loading.style.display = 'block';
    error.style.display = 'none';
    table.style.display = 'none';
    
    try {
        const wsUrl = getWebSocketUrl();
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            // Request unidentified aircraft log
            ws.send(JSON.stringify({
                type: 'get_unidentified_aircraft',
                limit: 200
            }));
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'unidentified_aircraft_log') {
                loading.style.display = 'none';
                
                if (!data.aircraft || data.aircraft.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No unidentified aircraft logged yet</td></tr>';
                    table.style.display = 'table';
                    stats.innerHTML = '<p>Total unidentified aircraft: 0</p>';
                    return;
                }
                
                // Update statistics
                const typeCount = {};
                const sourceCount = {};
                
                data.aircraft.forEach(aircraft => {
                    const type = aircraft.simplified_type || 'Unknown';
                    typeCount[type] = (typeCount[type] || 0) + 1;
                    
                    const source = aircraft.data_source || 'unknown';
                    sourceCount[source] = (sourceCount[source] || 0) + 1;
                });
                
                let statsHtml = `<p><strong>Total unidentified aircraft:</strong> ${data.aircraft.length}</p>`;
                statsHtml += '<p><strong>By Type:</strong> ';
                statsHtml += Object.entries(typeCount)
                    .sort((a, b) => b[1] - a[1])
                    .map(([type, count]) => `${type} (${count})`)
                    .join(', ');
                statsHtml += '</p>';
                statsHtml += '<p><strong>By Source:</strong> ';
                statsHtml += Object.entries(sourceCount)
                    .map(([source, count]) => `${source} (${count})`)
                    .join(', ');
                statsHtml += '</p>';
                
                stats.innerHTML = statsHtml;
                
                // Populate table
                tbody.innerHTML = '';
                data.aircraft.forEach(aircraft => {
                    const row = document.createElement('tr');
                    
                    // Determine type class
                    let typeClass = '';
                    if (aircraft.simplified_type === 'Unknown Aircraft') {
                        typeClass = 'unknown-type';
                    } else if (aircraft.simplified_type && 
                              (aircraft.simplified_type.includes('Aircraft') || 
                               aircraft.simplified_type.includes('Plane') ||
                               aircraft.simplified_type.includes('Jet'))) {
                        typeClass = 'generic-type';
                    }
                    
                    row.innerHTML = `
                        <td class="timestamp">${formatTimestamp(aircraft.logged_at)}</td>
                        <td class="icao24">${aircraft.icao24}</td>
                        <td><span class="${typeClass}">${aircraft.simplified_type || 'N/A'}</span></td>
                        <td>${aircraft.raw_type || 'N/A'}</td>
                        <td>${aircraft.manufacturer || 'N/A'}</td>
                        <td>${aircraft.type_name || 'N/A'}</td>
                        <td class="data-source">${aircraft.data_source || 'N/A'}</td>
                        <td>${aircraft.callsign || 'N/A'}</td>
                        <td>
                            <button class="details-btn" onclick='showDetails(${JSON.stringify(aircraft)})'>Details</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
                
                table.style.display = 'table';
            } else if (data.type === 'error') {
                loading.style.display = 'none';
                error.style.display = 'block';
                error.textContent = `Error: ${data.message}`;
            }
        };
        
        ws.onerror = (err) => {
            loading.style.display = 'none';
            error.style.display = 'block';
            error.textContent = 'Failed to connect to WebSocket server';
            console.error('WebSocket error:', err);
        };
        
    } catch (err) {
        loading.style.display = 'none';
        error.style.display = 'block';
        error.textContent = `Error: ${err.message}`;
        console.error('Error loading unidentified aircraft:', err);
    }
}

// Click outside modal to close
window.onclick = function(event) {
    const modal = document.getElementById('detailsModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Load on page load
document.addEventListener('DOMContentLoaded', loadUnidentifiedAircraft);