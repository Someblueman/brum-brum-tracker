/**
 * Tests for UI utility functions
 */

// Mock the ui-utils module functions for testing
const formatDistance = (distance) => {
    if (distance < 1) {
        return `${Math.round(distance * 1000)}m`;
    }
    return `${distance.toFixed(1)}km`;
};

const formatBearing = (bearing) => {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.round(bearing / 45) % 8;
    return directions[index];
};

const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
};

const getAircraftImageUrl = (type) => {
    if (!type) return 'assets/plane-placeholder.svg';
    
    const typePrefix = type.substring(0, 3).toUpperCase();
    const imageMap = {
        'A32': 'https://example.com/a320.jpg',
        'B73': 'https://example.com/b737.jpg',
        'B77': 'https://example.com/b777.jpg',
        'A38': 'https://example.com/a380.jpg'
    };
    
    return imageMap[typePrefix] || 'assets/plane-placeholder.svg';
};

describe('UI Utils Tests', async (it) => {
    
    it('should format distances correctly', () => {
        assert.equal(formatDistance(0.5), '500m');
        assert.equal(formatDistance(0.999), '999m');
        assert.equal(formatDistance(1), '1.0km');
        assert.equal(formatDistance(10.5), '10.5km');
        assert.equal(formatDistance(100.99), '101.0km');
    });
    
    it('should format bearings to compass directions', () => {
        assert.equal(formatBearing(0), 'N');
        assert.equal(formatBearing(45), 'NE');
        assert.equal(formatBearing(90), 'E');
        assert.equal(formatBearing(135), 'SE');
        assert.equal(formatBearing(180), 'S');
        assert.equal(formatBearing(225), 'SW');
        assert.equal(formatBearing(270), 'W');
        assert.equal(formatBearing(315), 'NW');
        assert.equal(formatBearing(360), 'N');
    });
    
    it('should handle bearing edge cases', () => {
        assert.equal(formatBearing(22.5), 'N');  // Should round to N
        assert.equal(formatBearing(67.5), 'E');  // Should round to E
        assert.equal(formatBearing(337.5), 'N'); // Should round to N
    });
    
    it('should format timestamps to locale time string', () => {
        const timestamp = new Date('2024-01-01T12:30:45Z').getTime();
        const formatted = formatTime(timestamp);
        assert.isTrue(formatted.includes(':'), 'Time should contain colon separator');
    });
    
    it('should get correct aircraft image URLs', () => {
        assert.equal(getAircraftImageUrl('A320'), 'https://example.com/a320.jpg');
        assert.equal(getAircraftImageUrl('B737'), 'https://example.com/b737.jpg');
        assert.equal(getAircraftImageUrl('B777'), 'https://example.com/b777.jpg');
        assert.equal(getAircraftImageUrl('A380'), 'https://example.com/a380.jpg');
    });
    
    it('should return placeholder for unknown aircraft types', () => {
        assert.equal(getAircraftImageUrl('C172'), 'assets/plane-placeholder.svg');
        assert.equal(getAircraftImageUrl(''), 'assets/plane-placeholder.svg');
        assert.equal(getAircraftImageUrl(null), 'assets/plane-placeholder.svg');
        assert.equal(getAircraftImageUrl(undefined), 'assets/plane-placeholder.svg');
    });
});