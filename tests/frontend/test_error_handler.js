/**
 * Tests for error handling functionality
 */

// Mock error handler
class MockErrorHandler {
    constructor() {
        this.errors = [];
        this.handlers = {
            error: [],
            unhandledRejection: []
        };
        this.originalHandlers = {};
    }
    
    init() {
        // Store original handlers
        this.originalHandlers.error = window.onerror;
        this.originalHandlers.unhandledRejection = window.onunhandledrejection;
        
        // Set up global error handlers
        window.onerror = (message, source, lineno, colno, error) => {
            this.handleError({
                type: 'error',
                message,
                source,
                lineno,
                colno,
                error
            });
            return true; // Prevent default handling
        };
        
        window.onunhandledrejection = (event) => {
            this.handleError({
                type: 'unhandledRejection',
                reason: event.reason,
                promise: event.promise
            });
            event.preventDefault();
        };
    }
    
    destroy() {
        // Restore original handlers
        window.onerror = this.originalHandlers.error;
        window.onunhandledrejection = this.originalHandlers.unhandledRejection;
    }
    
    handleError(errorInfo) {
        this.errors.push(errorInfo);
        
        // Call registered handlers
        const handlers = this.handlers[errorInfo.type] || [];
        handlers.forEach(handler => {
            try {
                handler(errorInfo);
            } catch (e) {
                console.error('Error in error handler:', e);
            }
        });
    }
    
    on(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event].push(handler);
        }
    }
    
    off(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event] = this.handlers[event].filter(h => h !== handler);
        }
    }
    
    getErrors() {
        return [...this.errors];
    }
    
    clearErrors() {
        this.errors = [];
    }
    
    logError(message, error = null) {
        this.handleError({
            type: 'manual',
            message,
            error,
            timestamp: new Date().toISOString()
        });
    }
}

describe('Error Handler Tests', async (it) => {
    
    it('should initialize and capture global errors', () => {
        const errorHandler = new MockErrorHandler();
        errorHandler.init();
        
        // Simulate a global error
        window.onerror('Test error', 'test.js', 10, 5, new Error('Test'));
        
        const errors = errorHandler.getErrors();
        assert.equal(errors.length, 1);
        assert.equal(errors[0].type, 'error');
        assert.equal(errors[0].message, 'Test error');
        assert.equal(errors[0].source, 'test.js');
        assert.equal(errors[0].lineno, 10);
        
        errorHandler.destroy();
    });
    
    it('should capture unhandled promise rejections', () => {
        const errorHandler = new MockErrorHandler();
        errorHandler.init();
        
        // Simulate unhandled rejection
        const event = {
            reason: 'Promise rejected',
            promise: Promise.reject('test'),
            preventDefault: () => {}
        };
        window.onunhandledrejection(event);
        
        const errors = errorHandler.getErrors();
        assert.equal(errors.length, 1);
        assert.equal(errors[0].type, 'unhandledRejection');
        assert.equal(errors[0].reason, 'Promise rejected');
        
        errorHandler.destroy();
    });
    
    it('should register and call error handlers', () => {
        const errorHandler = new MockErrorHandler();
        let handlerCalled = false;
        let receivedError = null;
        
        const handler = (error) => {
            handlerCalled = true;
            receivedError = error;
        };
        
        errorHandler.on('error', handler);
        errorHandler.handleError({
            type: 'error',
            message: 'Test error'
        });
        
        assert.isTrue(handlerCalled);
        assert.equal(receivedError.message, 'Test error');
    });
    
    it('should remove error handlers', () => {
        const errorHandler = new MockErrorHandler();
        let callCount = 0;
        
        const handler = () => {
            callCount++;
        };
        
        errorHandler.on('error', handler);
        errorHandler.handleError({ type: 'error' });
        assert.equal(callCount, 1);
        
        errorHandler.off('error', handler);
        errorHandler.handleError({ type: 'error' });
        assert.equal(callCount, 1); // Should not increase
    });
    
    it('should log manual errors', () => {
        const errorHandler = new MockErrorHandler();
        
        errorHandler.logError('Manual error message', new Error('Test error'));
        
        const errors = errorHandler.getErrors();
        assert.equal(errors.length, 1);
        assert.equal(errors[0].type, 'manual');
        assert.equal(errors[0].message, 'Manual error message');
        assert.notNull(errors[0].timestamp);
    });
    
    it('should clear error history', () => {
        const errorHandler = new MockErrorHandler();
        
        errorHandler.logError('Error 1');
        errorHandler.logError('Error 2');
        assert.equal(errorHandler.getErrors().length, 2);
        
        errorHandler.clearErrors();
        assert.equal(errorHandler.getErrors().length, 0);
    });
    
    it('should handle errors in error handlers gracefully', () => {
        const errorHandler = new MockErrorHandler();
        
        // Add a handler that throws
        errorHandler.on('error', () => {
            throw new Error('Handler error');
        });
        
        // This should not throw
        errorHandler.handleError({ type: 'error', message: 'Test' });
        
        // Original error should still be recorded
        const errors = errorHandler.getErrors();
        assert.equal(errors.length, 1);
        assert.equal(errors[0].message, 'Test');
    });
});