/**
 * Tests for configuration management
 */

// Mock configuration module
class MockConfig {
    constructor() {
        this.config = {
            HOME_LAT: null,
            HOME_LON: null,
            WS_URL: 'ws://localhost:8000',
            WSS_URL: 'wss://localhost:8001',
            API_UPDATE_INTERVAL: 30000,
            RECONNECT_DELAY: 1000,
            MAX_RECONNECT_DELAY: 30000
        };
        this.loaded = false;
    }
    
    async load() {
        // Simulate loading config from backend
        return new Promise((resolve) => {
            setTimeout(() => {
                this.config.HOME_LAT = 51.5074;
                this.config.HOME_LON = -0.1278;
                this.loaded = true;
                resolve(this.config);
            }, 10);
        });
    }
    
    get(key) {
        return this.config[key];
    }
    
    set(key, value) {
        this.config[key] = value;
    }
    
    getAll() {
        return { ...this.config };
    }
    
    isLoaded() {
        return this.loaded;
    }
    
    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = protocol === 'wss:' ? 8001 : 8000;
        return `${protocol}//${host}:${port}`;
    }
}

describe('Configuration Tests', async (it) => {
    
    it('should have default values before loading', () => {
        const config = new MockConfig();
        assert.isFalse(config.isLoaded());
        assert.equal(config.get('HOME_LAT'), null);
        assert.equal(config.get('HOME_LON'), null);
        assert.equal(config.get('WS_URL'), 'ws://localhost:8000');
        assert.equal(config.get('API_UPDATE_INTERVAL'), 30000);
    });
    
    it('should load configuration from backend', async () => {
        const config = new MockConfig();
        const loadedConfig = await config.load();
        
        assert.isTrue(config.isLoaded());
        assert.equal(config.get('HOME_LAT'), 51.5074);
        assert.equal(config.get('HOME_LON'), -0.1278);
        assert.equal(loadedConfig.HOME_LAT, 51.5074);
        assert.equal(loadedConfig.HOME_LON, -0.1278);
    });
    
    it('should get and set configuration values', () => {
        const config = new MockConfig();
        
        config.set('TEST_VALUE', 'hello');
        assert.equal(config.get('TEST_VALUE'), 'hello');
        
        config.set('API_UPDATE_INTERVAL', 60000);
        assert.equal(config.get('API_UPDATE_INTERVAL'), 60000);
    });
    
    it('should return all configuration values', async () => {
        const config = new MockConfig();
        await config.load();
        
        const allConfig = config.getAll();
        assert.notNull(allConfig);
        assert.equal(allConfig.HOME_LAT, 51.5074);
        assert.equal(allConfig.HOME_LON, -0.1278);
        assert.equal(allConfig.WS_URL, 'ws://localhost:8000');
    });
    
    it('should generate correct WebSocket URL based on protocol', () => {
        const config = new MockConfig();
        
        // Mock window.location for HTTP
        const originalLocation = window.location;
        delete window.location;
        window.location = {
            protocol: 'http:',
            hostname: 'example.com'
        };
        
        assert.equal(config.getWebSocketUrl(), 'ws://example.com:8000');
        
        // Mock for HTTPS
        window.location.protocol = 'https:';
        assert.equal(config.getWebSocketUrl(), 'wss://example.com:8001');
        
        // Restore original location
        window.location = originalLocation;
    });
    
    it('should not modify original config when returning all values', () => {
        const config = new MockConfig();
        const allConfig = config.getAll();
        
        allConfig.HOME_LAT = 99.999;
        assert.equal(config.get('HOME_LAT'), null); // Original should be unchanged
    });
});