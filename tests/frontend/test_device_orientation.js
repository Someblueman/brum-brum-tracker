/**
 * Tests for device orientation functionality
 */

// Mock device orientation module
class MockDeviceOrientation {
    constructor() {
        this.enabled = false;
        this.heading = 0;
        this.listeners = [];
        this.permissionGranted = false;
    }
    
    async requestPermission() {
        // Simulate permission request
        this.permissionGranted = true;
        return 'granted';
    }
    
    async enable() {
        if (!this.permissionGranted) {
            throw new Error('Permission not granted');
        }
        this.enabled = true;
        return true;
    }
    
    disable() {
        this.enabled = false;
        this.heading = 0;
    }
    
    getHeading() {
        return this.heading;
    }
    
    isEnabled() {
        return this.enabled;
    }
    
    addEventListener(event, handler) {
        this.listeners.push({ event, handler });
    }
    
    removeEventListener(event, handler) {
        this.listeners = this.listeners.filter(
            l => !(l.event === event && l.handler === handler)
        );
    }
    
    // Test helper to simulate orientation change
    simulateOrientationChange(heading) {
        this.heading = heading;
        this.listeners
            .filter(l => l.event === 'heading')
            .forEach(l => l.handler(heading));
    }
}

describe('Device Orientation Tests', async (it) => {
    
    it('should initialize with disabled state', () => {
        const orientation = new MockDeviceOrientation();
        assert.isFalse(orientation.isEnabled());
        assert.equal(orientation.getHeading(), 0);
    });
    
    it('should request permission before enabling', async () => {
        const orientation = new MockDeviceOrientation();
        
        // Should fail without permission
        try {
            await orientation.enable();
            assert.isTrue(false, 'Should have thrown error');
        } catch (error) {
            assert.equal(error.message, 'Permission not granted');
        }
        
        // Request permission and try again
        const permission = await orientation.requestPermission();
        assert.equal(permission, 'granted');
        
        const enabled = await orientation.enable();
        assert.isTrue(enabled);
        assert.isTrue(orientation.isEnabled());
    });
    
    it('should handle orientation changes', async () => {
        const orientation = new MockDeviceOrientation();
        await orientation.requestPermission();
        await orientation.enable();
        
        let receivedHeading = null;
        const handler = (heading) => {
            receivedHeading = heading;
        };
        
        orientation.addEventListener('heading', handler);
        
        // Simulate orientation changes
        orientation.simulateOrientationChange(45);
        assert.equal(receivedHeading, 45);
        assert.equal(orientation.getHeading(), 45);
        
        orientation.simulateOrientationChange(180);
        assert.equal(receivedHeading, 180);
        assert.equal(orientation.getHeading(), 180);
    });
    
    it('should remove event listeners', async () => {
        const orientation = new MockDeviceOrientation();
        await orientation.requestPermission();
        await orientation.enable();
        
        let callCount = 0;
        const handler = () => {
            callCount++;
        };
        
        orientation.addEventListener('heading', handler);
        orientation.simulateOrientationChange(90);
        assert.equal(callCount, 1);
        
        orientation.removeEventListener('heading', handler);
        orientation.simulateOrientationChange(180);
        assert.equal(callCount, 1); // Should not increase
    });
    
    it('should disable orientation tracking', async () => {
        const orientation = new MockDeviceOrientation();
        await orientation.requestPermission();
        await orientation.enable();
        
        orientation.simulateOrientationChange(90);
        assert.equal(orientation.getHeading(), 90);
        
        orientation.disable();
        assert.isFalse(orientation.isEnabled());
        assert.equal(orientation.getHeading(), 0);
    });
    
    it('should handle multiple listeners', async () => {
        const orientation = new MockDeviceOrientation();
        await orientation.requestPermission();
        await orientation.enable();
        
        const results = [];
        const handler1 = (h) => results.push(`handler1: ${h}`);
        const handler2 = (h) => results.push(`handler2: ${h}`);
        
        orientation.addEventListener('heading', handler1);
        orientation.addEventListener('heading', handler2);
        
        orientation.simulateOrientationChange(45);
        
        assert.equal(results.length, 2);
        assert.equal(results[0], 'handler1: 45');
        assert.equal(results[1], 'handler2: 45');
    });
});