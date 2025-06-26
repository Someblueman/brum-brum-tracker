/**
 * Enhanced WebSocket client with automatic reconnection and error handling
 */

class WebSocketClient extends EventTarget {
    constructor(url = null) {
        super();
        
        this.url = url || Config.getWebSocketUrl();
        this.ws = null;
        this.reconnectAttempts = 0;
        this.reconnectDelay = Config.WS_RECONNECT_INITIAL_DELAY;
        this.reconnectTimer = null;
        this.heartbeatTimer = null;
        this.messageHandlers = new Map();
        this.isIntentionallyClosed = false;
        this.connectionId = null;
        
        // Performance monitoring
        this.stats = {
            messagesSent: 0,
            messagesReceived: 0,
            errorsCount: 0,
            reconnectCount: 0,
            lastConnectedAt: null,
            lastDisconnectedAt: null
        };
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.disconnect = this.disconnect.bind(this);
        this.send = this.send.bind(this);
        this.handleOpen = this.handleOpen.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
        this.handleError = this.handleError.bind(this);
        this.handleClose = this.handleClose.bind(this);
        
        // Listen for page visibility changes
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
        
        // Listen for online/offline events
        window.addEventListener('online', this.handleOnline.bind(this));
        window.addEventListener('offline', this.handleOffline.bind(this));
    }
    
    /**
     * Connect to WebSocket server
     */
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return Promise.resolve();
        }
        
        this.isIntentionallyClosed = false;
        
        return new Promise((resolve, reject) => {
            try {
                console.log(`Connecting to WebSocket: ${this.url}`);
                this.ws = new WebSocket(this.url);
                
                // Set up event handlers
                this.ws.onopen = (event) => {
                    this.handleOpen(event);
                    resolve();
                };
                
                this.ws.onmessage = this.handleMessage;
                this.ws.onerror = this.handleError;
                this.ws.onclose = this.handleClose;
                
                // Set connection timeout
                const timeout = setTimeout(() => {
                    if (this.ws.readyState !== WebSocket.OPEN) {
                        this.ws.close();
                        reject(new Error('Connection timeout'));
                    }
                }, Config.WS_MESSAGE_TIMEOUT);
                
                this.ws.addEventListener('open', () => {
                    clearTimeout(timeout);
                });
                
            } catch (error) {
                console.error('Failed to create WebSocket:', error);
                reject(error);
            }
        });
    }
    
    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        this.isIntentionallyClosed = true;
        this.clearTimers();
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
    
    /**
     * Send message to server with validation
     */
    send(message) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('WebSocket is not connected');
            return Promise.reject(new Error('WebSocket is not connected'));
        }
        
        return new Promise((resolve, reject) => {
            try {
                // Validate message
                if (typeof message !== 'object') {
                    throw new Error('Message must be an object');
                }
                
                if (!message.type) {
                    throw new Error('Message must have a type');
                }
                
                // Convert to JSON
                const jsonMessage = JSON.stringify(message);
                
                // Check message size
                if (jsonMessage.length > Config.MAX_MESSAGE_SIZE) {
                    throw new Error(`Message too large: ${jsonMessage.length} bytes`);
                }
                
                // Send message
                this.ws.send(jsonMessage);
                this.stats.messagesSent++;
                
                if (Config.DEBUG) {
                    console.log('Sent message:', message);
                }
                
                resolve();
                
            } catch (error) {
                console.error('Failed to send message:', error);
                this.stats.errorsCount++;
                reject(error);
            }
        });
    }
    
    /**
     * Handle WebSocket open event
     */
    handleOpen(event) {
        console.log('WebSocket connected');
        
        this.reconnectAttempts = 0;
        this.reconnectDelay = Config.WS_RECONNECT_INITIAL_DELAY;
        this.stats.lastConnectedAt = new Date();
        
        // Start heartbeat
        this.startHeartbeat();
        
        // Send hello message
        this.send({ type: 'hello' }).catch(console.error);
        
        // Emit connected event
        this.dispatchEvent(new CustomEvent('connected', { detail: { event } }));
    }
    
    /**
     * Handle incoming messages with validation
     */
    handleMessage(event) {
        try {
            // Validate message size
            if (event.data.length > Config.MAX_MESSAGE_SIZE) {
                throw new Error(`Message too large: ${event.data.length} bytes`);
            }
            
            // Parse message
            const message = JSON.parse(event.data);
            
            // Validate message structure
            if (!message || typeof message !== 'object') {
                throw new Error('Invalid message format');
            }
            
            if (!message.type) {
                throw new Error('Message missing type');
            }
            
            // Check if message type is allowed
            if (Config.ALLOWED_MESSAGE_TYPES.indexOf(message.type) === -1) {
                throw new Error(`Unknown message type: ${message.type}`);
            }
            
            this.stats.messagesReceived++;
            
            if (Config.DEBUG) {
                console.log('Received message:', message);
            }
            
            // Emit message event
            this.dispatchEvent(new CustomEvent('message', { 
                detail: { message, raw: event.data } 
            }));
            
            // Emit specific message type event
            this.dispatchEvent(new CustomEvent(message.type, { 
                detail: message 
            }));
            
        } catch (error) {
            console.error('Failed to handle message:', error);
            this.stats.errorsCount++;
            
            this.dispatchEvent(new CustomEvent('error', { 
                detail: { error, raw: event.data } 
            }));
        }
    }
    
    /**
     * Handle WebSocket errors
     */
    handleError(event) {
        console.error('WebSocket error:', event);
        this.stats.errorsCount++;
        
        this.dispatchEvent(new CustomEvent('error', { 
            detail: { error: event } 
        }));
    }
    
    /**
     * Handle WebSocket close event
     */
    handleClose(event) {
        console.log('WebSocket closed:', event.code, event.reason);
        
        this.ws = null;
        this.stats.lastDisconnectedAt = new Date();
        this.clearTimers();
        
        this.dispatchEvent(new CustomEvent('disconnected', { 
            detail: { event } 
        }));
        
        // Attempt reconnection if not intentionally closed
        if (!this.isIntentionallyClosed && 
            this.reconnectAttempts < Config.WS_RECONNECT_MAX_ATTEMPTS) {
            this.scheduleReconnect();
        }
    }
    
    /**
     * Schedule reconnection with exponential backoff
     */
    scheduleReconnect() {
        // Clear existing timer
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        
        // Calculate delay with exponential backoff and jitter
        const jitter = Math.random() * 1000; // 0-1 second jitter
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts) + jitter,
            Config.WS_RECONNECT_MAX_DELAY
        );
        
        console.log(`Reconnecting in ${Math.round(delay / 1000)}s (attempt ${this.reconnectAttempts + 1})`);
        
        this.reconnectTimer = setTimeout(() => {
            this.reconnectAttempts++;
            this.stats.reconnectCount++;
            
            this.connect().catch((error) => {
                console.error('Reconnection failed:', error);
            });
        }, delay);
    }
    
    /**
     * Start heartbeat to keep connection alive
     */
    startHeartbeat() {
        this.clearHeartbeat();
        
        this.heartbeatTimer = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.send({ type: 'ping' }).catch((error) => {
                    console.error('Heartbeat failed:', error);
                });
            }
        }, Config.WS_HEARTBEAT_INTERVAL);
    }
    
    /**
     * Clear heartbeat timer
     */
    clearHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    /**
     * Clear all timers
     */
    clearTimers() {
        this.clearHeartbeat();
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }
    
    /**
     * Handle page visibility change
     */
    handleVisibilityChange() {
        if (!document.hidden && !this.isIntentionallyClosed && 
            (!this.ws || this.ws.readyState !== WebSocket.OPEN)) {
            console.log('Page became visible, attempting reconnection');
            this.connect().catch(console.error);
        }
    }
    
    /**
     * Handle online event
     */
    handleOnline() {
        console.log('Network came online');
        if (!this.isIntentionallyClosed && 
            (!this.ws || this.ws.readyState !== WebSocket.OPEN)) {
            this.connect().catch(console.error);
        }
    }
    
    /**
     * Handle offline event
     */
    handleOffline() {
        console.log('Network went offline');
    }
    
    /**
     * Get connection state
     */
    get readyState() {
        return this.ws ? this.ws.readyState : WebSocket.CLOSED;
    }
    
    /**
     * Check if connected
     */
    get isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
    
    /**
     * Get connection statistics
     */
    getStats() {
        return {
            ...this.stats,
            isConnected: this.isConnected,
            reconnectAttempts: this.reconnectAttempts,
            uptime: this.stats.lastConnectedAt ? 
                (Date.now() - this.stats.lastConnectedAt.getTime()) : 0
        };
    }
    
    /**
     * Reset statistics
     */
    resetStats() {
        this.stats = {
            messagesSent: 0,
            messagesReceived: 0,
            errorsCount: 0,
            reconnectCount: 0,
            lastConnectedAt: null,
            lastDisconnectedAt: null
        };
    }
}