/**
 * Frontend configuration module
 * Centralizes all configuration values for the frontend
 */

const Config = {
    // Environment
    ENV: window.location.hostname === 'localhost' ? 'development' : 'production',
    DEBUG: window.location.hostname === 'localhost',
    
    // WebSocket configuration
    WS_RECONNECT_INITIAL_DELAY: 1000,    // Initial reconnect delay in ms
    WS_RECONNECT_MAX_DELAY: 30000,       // Max reconnect delay in ms
    WS_RECONNECT_MAX_ATTEMPTS: 10,       // Max reconnection attempts
    WS_HEARTBEAT_INTERVAL: 30000,        // Heartbeat interval in ms
    WS_MESSAGE_TIMEOUT: 5000,             // Message response timeout in ms
    
    // UI Update intervals
    ARROW_UPDATE_INTERVAL: 100,           // Arrow rotation update interval in ms
    DISTANCE_UPDATE_INTERVAL: 1000,       // Distance update interval in ms
    UI_ANIMATION_DURATION: 300,           // UI animation duration in ms
    
    // Audio configuration
    AUDIO_ENABLED: true,
    AUDIO_VOLUME: 0.7,
    AUDIO_DELAY_MS: 500,                  // Delay before playing audio
    
    // Map configuration
    DEFAULT_ZOOM: 10,
    MAX_TRACKING_DISTANCE_KM: 50,
    MIN_ELEVATION_ANGLE: 20,
    
    // API endpoints
    API_TIMEOUT: 10000,                   // API request timeout in ms
    MAX_RETRIES: 3,
    
    // Security
    MAX_MESSAGE_SIZE: 10240,              // Max WebSocket message size (10KB)
    ALLOWED_MESSAGE_TYPES: [
        'aircraft',
        'aircraft_lost',
        'logbook',
        'error'
    ],
    
    // Performance
    DEBOUNCE_DELAY: 250,                  // Debounce delay for UI updates
    THROTTLE_DELAY: 100,                  // Throttle delay for frequent updates
    MAX_LOG_ENTRIES: 100,                 // Max console log entries to keep
    
    // Feature flags
    ENABLE_COMPASS: true,
    ENABLE_LOGBOOK: true,
    ENABLE_DEBUG_INFO: window.location.hostname === 'localhost',
    ENABLE_PERFORMANCE_MONITORING: false,
    
    // Get WebSocket URL based on current protocol
    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        
        // Determine port based on protocol
        let port;
        if (this.ENV === 'development') {
            port = protocol === 'wss:' ? '8001' : '8000';
        } else {
            // In production, might use standard ports or reverse proxy
            port = protocol === 'wss:' ? '8001' : '8000';
        }
        
        return `${protocol}//${host}:${port}`;
    },
    
    // Validate configuration
    validate() {
        const errors = [];
        
        if (this.WS_RECONNECT_MAX_DELAY < this.WS_RECONNECT_INITIAL_DELAY) {
            errors.push('WS_RECONNECT_MAX_DELAY must be greater than WS_RECONNECT_INITIAL_DELAY');
        }
        
        if (this.AUDIO_VOLUME < 0 || this.AUDIO_VOLUME > 1) {
            errors.push('AUDIO_VOLUME must be between 0 and 1');
        }
        
        if (this.MAX_MESSAGE_SIZE < 1024) {
            errors.push('MAX_MESSAGE_SIZE must be at least 1024 bytes');
        }
        
        return errors;
    },
    
    // Log configuration (only in debug mode)
    logConfig() {
        if (this.DEBUG) {
            console.log('Frontend Configuration:', {
                ENV: this.ENV,
                DEBUG: this.DEBUG,
                WebSocketURL: this.getWebSocketUrl(),
                Features: {
                    compass: this.ENABLE_COMPASS,
                    logbook: this.ENABLE_LOGBOOK,
                    debug: this.ENABLE_DEBUG_INFO
                }
            });
        }
    }
};

// Validate configuration on load
const configErrors = Config.validate();
if (configErrors.length > 0) {
    console.error('Configuration errors:', configErrors);
}

// Log configuration in debug mode
Config.logConfig();

// Make config immutable
Object.freeze(Config);