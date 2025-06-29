/**
 * Tests for dashboard UI functionality
 */

// Mock dashboard UI
class MockDashboardUI {
    constructor() {
        this.container = {
            innerHTML: '',
            children: []
        };
        this.aircraft = new Map();
        this.updateInterval = null;
        this.lastUpdate = null;
    }
    
    addOrUpdateAircraft(data) {
        this.aircraft.set(data.icao24, {
            ...data,
            lastSeen: new Date()
        });
        this.render();
    }
    
    removeAircraft(icao24) {
        this.aircraft.delete(icao24);
        this.render();
    }
    
    render() {
        const sortedAircraft = Array.from(this.aircraft.values())
            .sort((a, b) => a.distance - b.distance);
        
        this.container.children = sortedAircraft.map(aircraft => ({
            className: 'aircraft-card',
            dataset: { icao24: aircraft.icao24 },
            innerHTML: this.createAircraftCardHTML(aircraft)
        }));
        
        this.container.innerHTML = this.container.children
            .map(child => `<div class="${child.className}" data-icao24="${child.dataset.icao24}">${child.innerHTML}</div>`)
            .join('');
            
        this.lastUpdate = new Date();
    }
    
    createAircraftCardHTML(aircraft) {
        const distance = aircraft.distance < 1 
            ? `${Math.round(aircraft.distance * 1000)}m` 
            : `${aircraft.distance.toFixed(1)}km`;
            
        const bearing = this.formatBearing(aircraft.bearing);
        const altitude = `${Math.round(aircraft.altitude)}m`;
        
        return `
            <div class="aircraft-image">
                <img src="${aircraft.image_url || 'assets/plane-placeholder.svg'}" alt="${aircraft.aircraft_type}">
            </div>
            <div class="aircraft-info">
                <h3>${aircraft.callsign || 'Unknown'}</h3>
                <p class="aircraft-type">${aircraft.aircraft_type || 'Unknown'}</p>
                <p class="distance">${distance} ${bearing}</p>
                <p class="altitude">Alt: ${altitude}</p>
            </div>
        `;
    }
    
    formatBearing(bearing) {
        const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
        const index = Math.round(bearing / 45) % 8;
        return directions[index];
    }
    
    startAutoUpdate(interval = 1000) {
        this.stopAutoUpdate();
        this.updateInterval = setInterval(() => {
            this.removeStaleAircraft();
        }, interval);
    }
    
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    removeStaleAircraft(maxAge = 60000) {
        const now = new Date();
        const stale = [];
        
        this.aircraft.forEach((aircraft, icao24) => {
            if (now - aircraft.lastSeen > maxAge) {
                stale.push(icao24);
            }
        });
        
        stale.forEach(icao24 => this.removeAircraft(icao24));
    }
    
    getAircraftCount() {
        return this.aircraft.size;
    }
    
    getAircraft(icao24) {
        return this.aircraft.get(icao24);
    }
    
    getAllAircraft() {
        return Array.from(this.aircraft.values());
    }
    
    clear() {
        this.aircraft.clear();
        this.render();
    }
    
    getClosestAircraft() {
        let closest = null;
        let minDistance = Infinity;
        
        this.aircraft.forEach(aircraft => {
            if (aircraft.distance < minDistance) {
                minDistance = aircraft.distance;
                closest = aircraft;
            }
        });
        
        return closest;
    }
}

describe('Dashboard UI Tests', async (it) => {
    
    it('should add and display aircraft', () => {
        const dashboard = new MockDashboardUI();
        
        dashboard.addOrUpdateAircraft({
            icao24: 'ABC123',
            callsign: 'BA123',
            aircraft_type: 'Boeing 737',
            distance: 5.2,
            bearing: 45,
            altitude: 10000,
            image_url: 'https://example.com/b737.jpg'
        });
        
        assert.equal(dashboard.getAircraftCount(), 1);
        assert.equal(dashboard.container.children.length, 1);
        
        const html = dashboard.container.innerHTML;
        assert.isTrue(html.includes('BA123'));
        assert.isTrue(html.includes('Boeing 737'));
        assert.isTrue(html.includes('5.2km'));
    });
    
    it('should update existing aircraft', () => {
        const dashboard = new MockDashboardUI();
        
        // Add aircraft
        dashboard.addOrUpdateAircraft({
            icao24: 'ABC123',
            callsign: 'BA123',
            distance: 5.2,
            bearing: 45,
            altitude: 10000
        });
        
        // Update same aircraft
        dashboard.addOrUpdateAircraft({
            icao24: 'ABC123',
            callsign: 'BA123',
            distance: 4.8,
            bearing: 50,
            altitude: 9500
        });
        
        assert.equal(dashboard.getAircraftCount(), 1); // Still only one
        
        const aircraft = dashboard.getAircraft('ABC123');
        assert.equal(aircraft.distance, 4.8);
        assert.equal(aircraft.bearing, 50);
        assert.equal(aircraft.altitude, 9500);
    });
    
    it('should sort aircraft by distance', () => {
        const dashboard = new MockDashboardUI();
        
        dashboard.addOrUpdateAircraft({
            icao24: 'FAR',
            callsign: 'FAR123',
            distance: 10
        });
        
        dashboard.addOrUpdateAircraft({
            icao24: 'NEAR',
            callsign: 'NEAR123',
            distance: 2
        });
        
        dashboard.addOrUpdateAircraft({
            icao24: 'MID',
            callsign: 'MID123',
            distance: 5
        });
        
        const children = dashboard.container.children;
        assert.equal(children[0].dataset.icao24, 'NEAR');
        assert.equal(children[1].dataset.icao24, 'MID');
        assert.equal(children[2].dataset.icao24, 'FAR');
    });
    
    it('should format distances correctly', () => {
        const dashboard = new MockDashboardUI();
        
        // Distance in meters
        dashboard.addOrUpdateAircraft({
            icao24: 'CLOSE',
            distance: 0.5,
            bearing: 0,
            altitude: 1000
        });
        
        let html = dashboard.container.innerHTML;
        assert.isTrue(html.includes('500m'));
        
        // Distance in kilometers
        dashboard.addOrUpdateAircraft({
            icao24: 'FAR',
            distance: 15.7,
            bearing: 180,
            altitude: 5000
        });
        
        html = dashboard.container.innerHTML;
        assert.isTrue(html.includes('15.7km'));
    });
    
    it('should format bearings to compass directions', () => {
        const dashboard = new MockDashboardUI();
        
        const testCases = [
            { bearing: 0, expected: 'N' },
            { bearing: 45, expected: 'NE' },
            { bearing: 90, expected: 'E' },
            { bearing: 180, expected: 'S' },
            { bearing: 270, expected: 'W' }
        ];
        
        testCases.forEach((test, index) => {
            dashboard.addOrUpdateAircraft({
                icao24: `TEST${index}`,
                distance: 5,
                bearing: test.bearing,
                altitude: 5000
            });
            
            const html = dashboard.container.innerHTML;
            assert.isTrue(html.includes(test.expected), 
                `Expected bearing ${test.bearing} to show ${test.expected}`);
        });
    });
    
    it('should remove aircraft', () => {
        const dashboard = new MockDashboardUI();
        
        dashboard.addOrUpdateAircraft({
            icao24: 'ABC123',
            callsign: 'BA123'
        });
        
        dashboard.addOrUpdateAircraft({
            icao24: 'DEF456',
            callsign: 'LH456'
        });
        
        assert.equal(dashboard.getAircraftCount(), 2);
        
        dashboard.removeAircraft('ABC123');
        
        assert.equal(dashboard.getAircraftCount(), 1);
        assert.equal(dashboard.getAircraft('ABC123'), undefined);
        assert.notNull(dashboard.getAircraft('DEF456'));
    });
    
    it('should remove stale aircraft', async () => {
        const dashboard = new MockDashboardUI();
        
        // Add aircraft with old timestamp
        const oldAircraft = {
            icao24: 'OLD',
            callsign: 'OLD123',
            lastSeen: new Date(Date.now() - 70000) // 70 seconds ago
        };
        dashboard.aircraft.set('OLD', oldAircraft);
        
        // Add recent aircraft
        dashboard.addOrUpdateAircraft({
            icao24: 'NEW',
            callsign: 'NEW123'
        });
        
        assert.equal(dashboard.getAircraftCount(), 2);
        
        // Remove stale aircraft (older than 60 seconds)
        dashboard.removeStaleAircraft(60000);
        
        assert.equal(dashboard.getAircraftCount(), 1);
        assert.equal(dashboard.getAircraft('OLD'), undefined);
        assert.notNull(dashboard.getAircraft('NEW'));
    });
    
    it('should find closest aircraft', () => {
        const dashboard = new MockDashboardUI();
        
        dashboard.addOrUpdateAircraft({
            icao24: 'FAR',
            distance: 10
        });
        
        dashboard.addOrUpdateAircraft({
            icao24: 'CLOSEST',
            distance: 1.5
        });
        
        dashboard.addOrUpdateAircraft({
            icao24: 'MID',
            distance: 5
        });
        
        const closest = dashboard.getClosestAircraft();
        assert.equal(closest.icao24, 'CLOSEST');
        assert.equal(closest.distance, 1.5);
    });
    
    it('should clear all aircraft', () => {
        const dashboard = new MockDashboardUI();
        
        // Add multiple aircraft
        for (let i = 0; i < 5; i++) {
            dashboard.addOrUpdateAircraft({
                icao24: `TEST${i}`,
                distance: i + 1
            });
        }
        
        assert.equal(dashboard.getAircraftCount(), 5);
        
        dashboard.clear();
        
        assert.equal(dashboard.getAircraftCount(), 0);
        assert.equal(dashboard.container.children.length, 0);
    });
    
    it('should handle missing aircraft properties', () => {
        const dashboard = new MockDashboardUI();
        
        dashboard.addOrUpdateAircraft({
            icao24: 'PARTIAL',
            distance: 3,
            bearing: 90,
            altitude: 5000
            // Missing callsign, aircraft_type, image_url
        });
        
        const html = dashboard.container.innerHTML;
        assert.isTrue(html.includes('Unknown')); // For callsign
        assert.isTrue(html.includes('plane-placeholder.svg')); // Default image
    });
});