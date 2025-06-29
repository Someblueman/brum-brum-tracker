/**
 * Enhanced WebSocket reconnection module with additional features
 */

export class WebSocketReconnectionManager {
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            initialDelay: 1000,
            maxDelay: 30000,
            backoffFactor: 1.5,
            jitterFactor: 0.3,
            maxRetries: null,
            pingInterval: 30000,
            pongTimeout: 5000,
            reconnectOnUserActivity: true,
            ...options
        };
        
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.reconnectTimeout = null;
        this.pingInterval = null;
        this.pongTimeout = null;
        this.lastPongReceived = Date.now();
        this.isReconnecting = false;
        this.connectionLostTime = null;
        
        // Event handlers
        this.handlers = {
            open: [],
            message: [],
            close: [],
            error: [],
            reconnecting: [],
            reconnected: [],
            maxRetriesReached: []
        };
        
        // Network state monitoring
        this.setupNetworkMonitoring();
        
        // User activity monitoring
        if (this.options.reconnectOnUserActivity) {
            this.setupActivityMonitoring();
        }
    }
    
    /**
     * Connect to WebSocket server
     */
    connect() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }
        
        this.cleanup();
        
        try {
            this.websocket = new WebSocket(this.url);
            this.setupEventHandlers();
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.scheduleReconnect();
        }
    }
    
    /**
     * Set up WebSocket event handlers
     */
    setupEventHandlers() {
        this.websocket.onopen = (event) => {
            console.log('WebSocket connected');
            this.handleOpen(event);
        };
        
        this.websocket.onmessage = (event) => {
            this.handleMessage(event);
        };
        
        this.websocket.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            this.handleClose(event);
        };
        
        this.websocket.onerror = (event) => {
            console.error('WebSocket error:', event);
            this.handleError(event);
        };
    }
    
    /**
     * Handle WebSocket open event
     */
    handleOpen(event) {
        const wasReconnecting = this.isReconnecting;
        this.isReconnecting = false;
        this.reconnectAttempts = 0;
        this.connectionLostTime = null;
        
        // Start ping/pong heartbeat
        this.startHeartbeat();
        
        // Emit events
        this.emit('open', event);
        
        if (wasReconnecting) {
            this.emit('reconnected', {
                attempts: this.reconnectAttempts,
                timestamp: new Date()
            });
        }
    }
    
    /**
     * Handle WebSocket message
     */
    handleMessage(event) {
        // Handle ping/pong messages
        if (event.data === 'pong') {
            this.lastPongReceived = Date.now();
            clearTimeout(this.pongTimeout);
            return;
        }
        
        this.emit('message', event);
    }
    
    /**
     * Handle WebSocket close event
     */
    handleClose(event) {
        this.cleanup();
        this.emit('close', event);
        
        if (!this.connectionLostTime) {
            this.connectionLostTime = Date.now();
        }
        
        // Don't reconnect if close was clean (code 1000)
        if (event.code !== 1000) {
            this.scheduleReconnect();
        }
    }
    
    /**
     * Handle WebSocket error event
     */
    handleError(event) {
        this.emit('error', event);
    }
    
    /**
     * Schedule reconnection with exponential backoff
     */
    scheduleReconnect() {
        if (this.reconnectTimeout) {
            return; // Already scheduled
        }
        
        // Check max retries
        if (this.options.maxRetries && this.reconnectAttempts >= this.options.maxRetries) {
            console.error('Max reconnection attempts reached');
            this.emit('maxRetriesReached', {
                attempts: this.reconnectAttempts,
                connectionLostTime: this.connectionLostTime
            });
            return;
        }
        
        this.isReconnecting = true;
        const delay = this.calculateReconnectDelay();
        
        console.log(`Scheduling reconnection in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
        this.emit('reconnecting', {
            attempt: this.reconnectAttempts + 1,
            delay: delay
        });
        
        this.reconnectTimeout = setTimeout(() => {
            this.reconnectTimeout = null;
            this.reconnectAttempts++;
            this.connect();
        }, delay);
    }
    
    /**
     * Calculate reconnect delay with exponential backoff and jitter
     */
    calculateReconnectDelay() {
        const baseDelay = Math.min(
            this.options.initialDelay * Math.pow(this.options.backoffFactor, this.reconnectAttempts),
            this.options.maxDelay
        );
        
        const jitter = baseDelay * this.options.jitterFactor * (Math.random() - 0.5);
        return Math.floor(baseDelay + jitter);
    }
    
    /**
     * Start heartbeat mechanism
     */
    startHeartbeat() {
        this.stopHeartbeat();
        
        this.pingInterval = setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send('ping');
                
                // Set timeout for pong response
                this.pongTimeout = setTimeout(() => {
                    console.warn('Pong timeout - connection may be dead');
                    this.websocket.close();
                }, this.options.pongTimeout);
            }
        }, this.options.pingInterval);
    }
    
    /**
     * Stop heartbeat mechanism
     */
    stopHeartbeat() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        
        if (this.pongTimeout) {
            clearTimeout(this.pongTimeout);
            this.pongTimeout = null;
        }
    }
    
    /**
     * Set up network state monitoring
     */
    setupNetworkMonitoring() {
        // Monitor online/offline events
        window.addEventListener('online', () => {
            console.log('Network online - attempting reconnection');
            if (this.isReconnecting || !this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
                this.connect();
            }
        });
        
        window.addEventListener('offline', () => {
            console.log('Network offline');
        });
        
        // Monitor page visibility
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.isReconnecting) {
                console.log('Page visible - checking connection');
                this.connect();
            }
        });
    }
    
    /**
     * Set up user activity monitoring
     */
    setupActivityMonitoring() {
        let activityTimeout;
        const activityEvents = ['mousedown', 'keydown', 'touchstart', 'scroll'];
        
        const handleActivity = () => {
            clearTimeout(activityTimeout);
            
            // If disconnected and user is active, try to reconnect
            if (this.isReconnecting) {
                activityTimeout = setTimeout(() => {
                    console.log('User activity detected - attempting reconnection');
                    this.connect();
                }, 1000);
            }
        };
        
        activityEvents.forEach(event => {
            document.addEventListener(event, handleActivity, { passive: true });
        });
    }
    
    /**
     * Clean up resources
     */
    cleanup() {
        this.stopHeartbeat();
        
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
        
        if (this.websocket) {
            this.websocket.onopen = null;
            this.websocket.onmessage = null;
            this.websocket.onclose = null;
            this.websocket.onerror = null;
            
            if (this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.close(1000, 'Manual cleanup');
            }
            
            this.websocket = null;
        }
    }
    
    /**
     * Send message through WebSocket
     */
    send(data) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(typeof data === 'string' ? data : JSON.stringify(data));
            return true;
        }
        
        console.warn('WebSocket not connected - message not sent');
        return false;
    }
    
    /**
     * Close WebSocket connection
     */
    close(code = 1000, reason = 'Normal closure') {
        this.isReconnecting = false; // Prevent auto-reconnect
        this.cleanup();
    }
    
    /**
     * Register event handler
     */
    on(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event].push(handler);
        }
    }
    
    /**
     * Remove event handler
     */
    off(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event] = this.handlers[event].filter(h => h !== handler);
        }
    }
    
    /**
     * Emit event to handlers
     */
    emit(event, data) {
        if (this.handlers[event]) {
            this.handlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in ${event} handler:`, error);
                }
            });
        }
    }
    
    /**
     * Get connection state
     */
    get readyState() {
        return this.websocket ? this.websocket.readyState : WebSocket.CLOSED;
    }
    
    /**
     * Get connection statistics
     */
    getStats() {
        return {
            connected: this.websocket && this.websocket.readyState === WebSocket.OPEN,
            reconnecting: this.isReconnecting,
            reconnectAttempts: this.reconnectAttempts,
            connectionLostTime: this.connectionLostTime,
            lastPongReceived: this.lastPongReceived
        };
    }
}