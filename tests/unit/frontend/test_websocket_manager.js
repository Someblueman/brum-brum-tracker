/**
 * Unit tests for WebSocket Manager
 */

import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import { WebSocketManager } from '../../../frontend/js/modules/websocket-manager.js';

// Mock WebSocket
global.WebSocket = jest.fn();

describe('WebSocketManager', () => {
    let manager;
    let mockWebSocket;
    
    beforeEach(() => {
        // Reset mocks
        jest.clearAllMocks();
        jest.useFakeTimers();
        
        // Create mock WebSocket instance
        mockWebSocket = {
            send: jest.fn(),
            close: jest.fn(),
            readyState: WebSocket.CONNECTING,
            onopen: null,
            onclose: null,
            onerror: null,
            onmessage: null
        };
        
        global.WebSocket.mockImplementation(() => mockWebSocket);
        
        // Create manager instance
        manager = new WebSocketManager({
            hostname: 'localhost',
            reconnectConfig: {
                initialDelay: 1000,
                maxDelay: 5000,
                decayFactor: 2,
                jitterFactor: 0.1
            }
        });
    });
    
    afterEach(() => {
        jest.useRealTimers();
    });
    
    describe('connect()', () => {
        it('should create WebSocket connection with correct URL', () => {
            manager.connect();
            
            expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws');
            expect(mockWebSocket.onopen).toBeDefined();
            expect(mockWebSocket.onclose).toBeDefined();
            expect(mockWebSocket.onerror).toBeDefined();
            expect(mockWebSocket.onmessage).toBeDefined();
        });
        
        it('should not create multiple connections if already connected', () => {
            mockWebSocket.readyState = WebSocket.OPEN;
            manager.ws = mockWebSocket;
            
            manager.connect();
            
            expect(global.WebSocket).not.toHaveBeenCalled();
        });
        
        it('should use WSS protocol for HTTPS pages', () => {
            // Mock HTTPS
            delete global.window.location;
            global.window = { location: { protocol: 'https:' } };
            
            const httpsManager = new WebSocketManager();
            httpsManager.connect();
            
            expect(global.WebSocket).toHaveBeenCalledWith('wss://undefined:8001/ws');
        });
    });
    
    describe('disconnect()', () => {
        it('should close WebSocket connection', () => {
            manager.ws = mockWebSocket;
            manager.disconnect();
            
            expect(mockWebSocket.close).toHaveBeenCalled();
            expect(manager.ws).toBeNull();
        });
        
        it('should clear reconnect timeout', () => {
            manager.reconnectTimeout = setTimeout(() => {}, 1000);
            manager.disconnect();
            
            // Timer should not fire
            jest.runAllTimers();
            expect(manager.isReconnecting).toBe(false);
        });
    });
    
    describe('send()', () => {
        it('should send JSON data when connected', () => {
            mockWebSocket.readyState = WebSocket.OPEN;
            manager.ws = mockWebSocket;
            
            const data = { type: 'test', value: 123 };
            const result = manager.send(data);
            
            expect(result).toBe(true);
            expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify(data));
        });
        
        it('should send string data directly', () => {
            mockWebSocket.readyState = WebSocket.OPEN;
            manager.ws = mockWebSocket;
            
            const data = 'test message';
            manager.send(data);
            
            expect(mockWebSocket.send).toHaveBeenCalledWith(data);
        });
        
        it('should return false when not connected', () => {
            mockWebSocket.readyState = WebSocket.CLOSED;
            manager.ws = mockWebSocket;
            
            const result = manager.send({ type: 'test' });
            
            expect(result).toBe(false);
            expect(mockWebSocket.send).not.toHaveBeenCalled();
        });
    });
    
    describe('event handling', () => {
        it('should emit open event when connected', () => {
            const openHandler = jest.fn();
            manager.on('open', openHandler);
            
            manager.connect();
            mockWebSocket.onopen();
            
            expect(openHandler).toHaveBeenCalled();
        });
        
        it('should emit message event with parsed JSON', () => {
            const messageHandler = jest.fn();
            manager.on('message', messageHandler);
            
            manager.connect();
            const testData = { type: 'aircraft', data: {} };
            mockWebSocket.onmessage({ data: JSON.stringify(testData) });
            
            expect(messageHandler).toHaveBeenCalledWith(testData);
        });
        
        it('should emit raw message on JSON parse error', () => {
            const messageHandler = jest.fn();
            manager.on('message', messageHandler);
            
            manager.connect();
            mockWebSocket.onmessage({ data: 'invalid json' });
            
            expect(messageHandler).toHaveBeenCalledWith({ raw: 'invalid json' });
        });
        
        it('should emit status change events', () => {
            const statusHandler = jest.fn();
            manager.on('statusChange', statusHandler);
            
            manager.connect();
            mockWebSocket.onopen();
            
            expect(statusHandler).toHaveBeenCalledWith({
                connected: true,
                reconnecting: false
            });
            
            mockWebSocket.onclose({ wasClean: false });
            
            expect(statusHandler).toHaveBeenCalledWith({
                connected: false,
                reconnecting: true
            });
        });
    });
    
    describe('reconnection', () => {
        it('should attempt reconnect on unclean close', () => {
            manager.connect();
            mockWebSocket.onclose({ wasClean: false });
            
            expect(manager.isReconnecting).toBe(true);
            expect(manager.reconnectAttempts).toBe(0);
            
            // Fast-forward timer
            jest.advanceTimersByTime(1100); // Initial delay + jitter
            
            expect(global.WebSocket).toHaveBeenCalledTimes(2);
            expect(manager.reconnectAttempts).toBe(1);
        });
        
        it('should use exponential backoff for reconnection', () => {
            manager.connect();
            
            // First reconnect - 1000ms
            mockWebSocket.onclose({ wasClean: false });
            jest.advanceTimersByTime(1100);
            
            // Second reconnect - 2000ms
            mockWebSocket.onclose({ wasClean: false });
            jest.advanceTimersByTime(2200);
            
            // Third reconnect - 4000ms
            mockWebSocket.onclose({ wasClean: false });
            jest.advanceTimersByTime(4400);
            
            expect(manager.reconnectAttempts).toBe(3);
        });
        
        it('should cap reconnect delay at max delay', () => {
            manager.reconnectAttempts = 10; // High attempt count
            manager._scheduleReconnect();
            
            // Should not exceed maxDelay (5000ms in test config)
            jest.advanceTimersByTime(5500);
            
            expect(global.WebSocket).toHaveBeenCalled();
        });
        
        it('should not reconnect on clean close', () => {
            manager.connect();
            mockWebSocket.onclose({ wasClean: true });
            
            jest.runAllTimers();
            
            expect(manager.isReconnecting).toBe(false);
            expect(global.WebSocket).toHaveBeenCalledTimes(1);
        });
    });
    
    describe('event subscription', () => {
        it('should return unsubscribe function', () => {
            const handler = jest.fn();
            const unsubscribe = manager.on('message', handler);
            
            // Handler should be registered
            manager._emit('message', { test: true });
            expect(handler).toHaveBeenCalledTimes(1);
            
            // Unsubscribe
            unsubscribe();
            
            // Handler should not be called
            manager._emit('message', { test: true });
            expect(handler).toHaveBeenCalledTimes(1);
        });
        
        it('should handle errors in event handlers gracefully', () => {
            const errorHandler = jest.fn(() => {
                throw new Error('Handler error');
            });
            const goodHandler = jest.fn();
            
            manager.on('message', errorHandler);
            manager.on('message', goodHandler);
            
            // Should not throw
            expect(() => {
                manager._emit('message', { test: true });
            }).not.toThrow();
            
            // Good handler should still be called
            expect(goodHandler).toHaveBeenCalled();
        });
    });
    
    describe('visibility handling', () => {
        it('should reconnect when page becomes visible', () => {
            // Mock document visibility
            Object.defineProperty(document, 'hidden', {
                configurable: true,
                get: jest.fn(() => false)
            });
            
            const visibilityHandler = jest.fn();
            WebSocketManager.setupVisibilityHandling(manager);
            
            // Simulate disconnection
            manager.ws = null;
            manager.isReconnecting = false;
            
            // Trigger visibility change
            document.dispatchEvent(new Event('visibilitychange'));
            
            // Should attempt to connect
            expect(global.WebSocket).toHaveBeenCalled();
        });
    });
});