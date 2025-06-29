/**
 * Tests for main UI components and interactions
 */

// Mock DOM elements and UI functions
class MockMainUI {
    constructor() {
        this.elements = {
            arrow: { style: { transform: '' } },
            distance: { textContent: '' },
            callsign: { textContent: '' },
            aircraftType: { textContent: '' },
            altitude: { textContent: '' },
            compassStatus: { textContent: 'Compass: Off' },
            connectionStatus: { textContent: 'Disconnected', className: '' },
            familySelect: { value: 'mamma_pappa' }
        };
        
        this.audioPlayed = [];
        this.currentAircraft = null;
        this.compassEnabled = false;
    }
    
    updateAircraftDisplay(aircraft) {
        if (!aircraft) {
            this.clearDisplay();
            return;
        }
        
        this.currentAircraft = aircraft;
        this.elements.distance.textContent = this.formatDistance(aircraft.distance);
        this.elements.callsign.textContent = aircraft.callsign || 'Unknown';
        this.elements.aircraftType.textContent = aircraft.aircraft_type || 'Unknown';
        this.elements.altitude.textContent = `${Math.round(aircraft.altitude)}m`;
        
        // Update arrow rotation
        if (this.compassEnabled) {
            const rotation = aircraft.bearing - this.deviceHeading;
            this.elements.arrow.style.transform = `rotate(${rotation}deg)`;
        } else {
            this.elements.arrow.style.transform = `rotate(${aircraft.bearing}deg)`;
        }
    }
    
    clearDisplay() {
        this.currentAircraft = null;
        this.elements.distance.textContent = 'No aircraft';
        this.elements.callsign.textContent = '';
        this.elements.aircraftType.textContent = '';
        this.elements.altitude.textContent = '';
        this.elements.arrow.style.transform = 'rotate(0deg)';
    }
    
    formatDistance(km) {
        if (km < 1) {
            return `${Math.round(km * 1000)}m`;
        }
        return `${km.toFixed(1)}km`;
    }
    
    playAircraftSound(type) {
        this.audioPlayed.push({
            type: type,
            timestamp: new Date()
        });
    }
    
    updateConnectionStatus(connected) {
        if (connected) {
            this.elements.connectionStatus.textContent = 'Connected';
            this.elements.connectionStatus.className = 'connected';
        } else {
            this.elements.connectionStatus.textContent = 'Disconnected';
            this.elements.connectionStatus.className = 'disconnected';
        }
    }
    
    enableCompass() {
        this.compassEnabled = true;
        this.elements.compassStatus.textContent = 'Compass: On';
    }
    
    disableCompass() {
        this.compassEnabled = false;
        this.elements.compassStatus.textContent = 'Compass: Off';
        this.deviceHeading = 0;
    }
    
    updateDeviceHeading(heading) {
        this.deviceHeading = heading;
        if (this.currentAircraft && this.compassEnabled) {
            const rotation = this.currentAircraft.bearing - heading;
            this.elements.arrow.style.transform = `rotate(${rotation}deg)`;
        }
    }
    
    getSelectedFamily() {
        return this.elements.familySelect.value;
    }
    
    getAudioHistory() {
        return [...this.audioPlayed];
    }
}

describe('Main UI Tests', async (it) => {
    
    it('should display aircraft information correctly', () => {
        const ui = new MockMainUI();
        
        const aircraft = {
            callsign: 'BA123',
            aircraft_type: 'Boeing 747',
            distance: 5.2,
            bearing: 45,
            altitude: 10000
        };
        
        ui.updateAircraftDisplay(aircraft);
        
        assert.equal(ui.elements.distance.textContent, '5.2km');
        assert.equal(ui.elements.callsign.textContent, 'BA123');
        assert.equal(ui.elements.aircraftType.textContent, 'Boeing 747');
        assert.equal(ui.elements.altitude.textContent, '10000m');
        assert.equal(ui.elements.arrow.style.transform, 'rotate(45deg)');
    });
    
    it('should format short distances in meters', () => {
        const ui = new MockMainUI();
        
        const aircraft = {
            callsign: 'TEST',
            distance: 0.5,
            bearing: 0,
            altitude: 1000
        };
        
        ui.updateAircraftDisplay(aircraft);
        assert.equal(ui.elements.distance.textContent, '500m');
    });
    
    it('should clear display when no aircraft', () => {
        const ui = new MockMainUI();
        
        // First set some aircraft
        ui.updateAircraftDisplay({
            callsign: 'TEST',
            distance: 5,
            bearing: 90,
            altitude: 5000
        });
        
        // Then clear
        ui.updateAircraftDisplay(null);
        
        assert.equal(ui.elements.distance.textContent, 'No aircraft');
        assert.equal(ui.elements.callsign.textContent, '');
        assert.equal(ui.elements.aircraftType.textContent, '');
        assert.equal(ui.elements.altitude.textContent, '');
        assert.equal(ui.elements.arrow.style.transform, 'rotate(0deg)');
    });
    
    it('should update connection status', () => {
        const ui = new MockMainUI();
        
        ui.updateConnectionStatus(true);
        assert.equal(ui.elements.connectionStatus.textContent, 'Connected');
        assert.equal(ui.elements.connectionStatus.className, 'connected');
        
        ui.updateConnectionStatus(false);
        assert.equal(ui.elements.connectionStatus.textContent, 'Disconnected');
        assert.equal(ui.elements.connectionStatus.className, 'disconnected');
    });
    
    it('should handle compass functionality', () => {
        const ui = new MockMainUI();
        
        // Initially disabled
        assert.isFalse(ui.compassEnabled);
        assert.equal(ui.elements.compassStatus.textContent, 'Compass: Off');
        
        // Enable compass
        ui.enableCompass();
        assert.isTrue(ui.compassEnabled);
        assert.equal(ui.elements.compassStatus.textContent, 'Compass: On');
        
        // Update device heading
        ui.updateDeviceHeading(30);
        assert.equal(ui.deviceHeading, 30);
        
        // Display aircraft with compass enabled
        const aircraft = {
            callsign: 'TEST',
            distance: 5,
            bearing: 90,
            altitude: 5000
        };
        ui.updateAircraftDisplay(aircraft);
        
        // Arrow should point to relative bearing (90 - 30 = 60)
        assert.equal(ui.elements.arrow.style.transform, 'rotate(60deg)');
        
        // Disable compass
        ui.disableCompass();
        assert.isFalse(ui.compassEnabled);
        assert.equal(ui.deviceHeading, 0);
    });
    
    it('should track audio playback', () => {
        const ui = new MockMainUI();
        
        ui.playAircraftSound('new_aircraft');
        ui.playAircraftSound('aircraft_nearby');
        
        const history = ui.getAudioHistory();
        assert.equal(history.length, 2);
        assert.equal(history[0].type, 'new_aircraft');
        assert.equal(history[1].type, 'aircraft_nearby');
        assert.notNull(history[0].timestamp);
    });
    
    it('should get selected family from dropdown', () => {
        const ui = new MockMainUI();
        
        assert.equal(ui.getSelectedFamily(), 'mamma_pappa');
        
        ui.elements.familySelect.value = 'mormor_pops';
        assert.equal(ui.getSelectedFamily(), 'mormor_pops');
    });
    
    it('should handle missing aircraft properties gracefully', () => {
        const ui = new MockMainUI();
        
        const aircraft = {
            distance: 3.5,
            bearing: 180,
            altitude: 2000
            // Missing callsign and aircraft_type
        };
        
        ui.updateAircraftDisplay(aircraft);
        
        assert.equal(ui.elements.callsign.textContent, 'Unknown');
        assert.equal(ui.elements.aircraftType.textContent, 'Unknown');
        assert.equal(ui.elements.distance.textContent, '3.5km');
    });
});