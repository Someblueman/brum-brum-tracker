/**
 * WebSocket Manager Module
 * Shared WebSocket connection management with reconnection support and request debouncing
 */

import { createMessageBatcher, debounce } from './debouncer.js';

export class WebSocketManager {
    constructor(options = {}) {
        // Configuration
        this.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.port = window.location.protocol === 'https:' ? '8001' : '8000';
        this.hostname = options.hostname || window.location.hostname;
        this.path = options.path || '/ws';
        this.url = `${this.protocol}//${this.hostname}:${this.port}${this.path}`;
        
        // Reconnection config
        this.reconnectConfig = {
            initialDelay: 1000,
            maxDelay: 30000,
            decayFactor: 1.5,
            maxRetries: null,
            jitterFactor: 0.3,
            ...options.reconnectConfig
        };
        
        // State
        this.ws = null;
        this.reconnectTimeout = null;
        this.reconnectAttempts = 0;
        this.isReconnecting = false;
        
        // Debouncing
        this.enableDebouncing = options.enableDebouncing || false;
        this.debounceWait = options.debounceWait || 100;
        this.maxBatchSize = options.maxBatchSize || 10;
        
        // Create message batcher if debouncing is enabled
        if (this.enableDebouncing) {
            this.messageBatcher = createMessageBatcher(
                this._sendRaw.bind(this),
                this.debounceWait,
                this.maxBatchSize
            );
        }
        
        // Event handlers
        this.handlers = {
            open: [],
            message: [],
            error: [],
            close: [],
            statusChange: []
        };
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.disconnect = this.disconnect.bind(this);
        this.send = this.send.bind(this);
        this._handleOpen = this._handleOpen.bind(this);
        this._handleMessage = this._handleMessage.bind(this);
        this._handleError = this._handleError.bind(this);
        this._handleClose = this._handleClose.bind(this);
    }
    
    /**
     * Register event handler
     */
    on(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event].push(handler);
        }
        return () => this.off(event, handler); // Return unsubscribe function
    }
    
    /**
     * Unregister event handler
     */
    off(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event] = this.handlers[event].filter(h => h !== handler);
        }
    }
    
    /**
     * Emit event to all handlers
     */
    _emit(event, data) {
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
     * Connect to WebSocket server
     */
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }
        
        console.log(`Connecting to WebSocket at ${this.url}`);
        
        try {
            this.ws = new WebSocket(this.url);
            this.ws.onopen = this._handleOpen;
            this.ws.onmessage = this._handleMessage;
            this.ws.onerror = this._handleError;
            this.ws.onclose = this._handleClose;
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this._scheduleReconnect();
        }
    }
    
    /**
     * Disconnect WebSocket
     */
    disconnect() {
        this.isReconnecting = false;
        
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
        
        if (this.messageBatcher) {
            this.messageBatcher.cancel();
        }
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
    
    /**
     * Send message through WebSocket
     */
    send(data) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return false;
        }
        
        if (this.enableDebouncing && this.messageBatcher) {
            this.messageBatcher.send(data);
            return true;
        } else {
            return this._sendRaw(data);
        }
    }
    
    /**
     * Send message immediately without debouncing
     */
    sendImmediate(data) {
        return this._sendRaw(data);
    }
    
    /**
     * Internal send method
     */
    _sendRaw(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = typeof data === 'string' ? data : JSON.stringify(data);
            this.ws.send(message);
            return true;
        }
        return false;
    }
    
    /**
     * Flush any pending debounced messages
     */
    flush() {
        if (this.messageBatcher) {
            this.messageBatcher.flush();
        }
    }
    
    /**
     * Get connection state
     */
    get isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
    
    /**
     * Handle WebSocket open
     */
    _handleOpen() {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.isReconnecting = false;
        
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
        
        this._emit('statusChange', { connected: true, reconnecting: false });
        this._emit('open', {});
    }
    
    /**
     * Handle WebSocket message
     */
    _handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this._emit('message', data);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
            // Emit raw message if JSON parsing fails
            this._emit('message', { raw: event.data });
        }
    }
    
    /**
     * Handle WebSocket error
     */
    _handleError(error) {
        console.error('WebSocket error:', error);
        this._emit('error', error);
    }
    
    /**
     * Handle WebSocket close
     */
    _handleClose(event) {
        console.log('WebSocket closed:', event.code, event.reason);
        this._emit('close', { code: event.code, reason: event.reason });
        this._emit('statusChange', { connected: false, reconnecting: this.isReconnecting });
        
        if (!event.wasClean && this.isReconnecting !== false) {
            this._scheduleReconnect();
        }
    }
    
    /**
     * Schedule reconnection with exponential backoff and jitter
     */
    _scheduleReconnect() {
        if (!this.isReconnecting && this.reconnectConfig.maxRetries && 
            this.reconnectAttempts >= this.reconnectConfig.maxRetries) {
            console.log('Max reconnection attempts reached');
            return;
        }
        
        this.isReconnecting = true;
        
        // Calculate delay with exponential backoff
        let delay = Math.min(
            this.reconnectConfig.initialDelay * Math.pow(this.reconnectConfig.decayFactor, this.reconnectAttempts),
            this.reconnectConfig.maxDelay
        );
        
        // Add jitter to prevent thundering herd
        const jitter = delay * this.reconnectConfig.jitterFactor * (Math.random() - 0.5);
        delay = Math.round(delay + jitter);
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
        
        this.reconnectTimeout = setTimeout(() => {
            this.reconnectAttempts++;
            this.connect();
        }, delay);
        
        this._emit('statusChange', { connected: false, reconnecting: true });
    }
    
    /**
     * Handle visibility change for auto-reconnect
     */
    static setupVisibilityHandling(manager) {
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !manager.isConnected && !manager.isReconnecting) {
                console.log('Page became visible, reconnecting...');
                manager.connect();
            }
        });
    }
}