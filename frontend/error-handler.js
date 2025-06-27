/**
 * Global error handling for the frontend application
 * Catches and logs errors, prevents app crashes
 */

class ErrorHandler {
    constructor() {
        this.errors = [];
        this.maxErrors = 50;
        this.errorListeners = new Set();
        
        // Set up global error handlers
        this.setupGlobalHandlers();
        
        // Error reporting endpoint (if configured)
        this.errorReportingUrl = null;
    }
    
    /**
     * Set up global error handlers
     */
    setupGlobalHandlers() {
        // Handle unhandled errors
        window.addEventListener('error', (event) => {
            this.handleError({
                type: 'unhandled-error',
                message: event.message,
                filename: event.filename,
                line: event.lineno,
                column: event.colno,
                error: event.error,
                timestamp: new Date()
            });
            
            // Prevent default error handling in production
            if (Config.ENV === 'production') {
                event.preventDefault();
            }
        });
        
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError({
                type: 'unhandled-rejection',
                reason: event.reason,
                promise: event.promise,
                timestamp: new Date()
            });
            
            // Prevent default rejection handling in production
            if (Config.ENV === 'production') {
                event.preventDefault();
            }
        });
        
        // Override console.error to capture all errors
        const originalConsoleError = console.error;
        console.error = (...args) => {
            this.handleError({
                type: 'console-error',
                message: args.join(' '),
                args: args,
                timestamp: new Date()
            });
            
            // Call original console.error
            originalConsoleError.apply(console, args);
        };
    }
    
    /**
     * Handle an error
     */
    handleError(errorInfo) {
        // Store error
        this.errors.push(errorInfo);
        
        // Limit stored errors
        if (this.errors.length > this.maxErrors) {
            this.errors.shift();
        }
        
        // Log error details in development
        if (Config.DEBUG) {
            console.log('Error captured:', errorInfo);
        }
        
        // Notify listeners
        this.notifyListeners(errorInfo);
        
        // Report critical errors
        if (this.isCriticalError(errorInfo)) {
            this.reportError(errorInfo);
        }
        
        // Show user-friendly error message for critical errors
        if (this.shouldShowErrorToUser(errorInfo)) {
            this.showErrorNotification(errorInfo);
        }
    }
    
    /**
     * Check if error is critical
     */
    isCriticalError(errorInfo) {
        // WebSocket connection errors
        if (errorInfo.message && errorInfo.message.includes('WebSocket')) {
            return true;
        }
        
        // API errors
        if (errorInfo.message && errorInfo.message.includes('Failed to fetch')) {
            return true;
        }
        
        // Memory errors
        if (errorInfo.message && errorInfo.message.includes('out of memory')) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Check if error should be shown to user
     */
    shouldShowErrorToUser(errorInfo) {
        // Don't show errors in production unless critical
        if (Config.ENV === 'production' && !this.isCriticalError(errorInfo)) {
            return false;
        }
        
        // Don't show network errors repeatedly
        if (errorInfo.type === 'network-error') {
            const recentNetworkErrors = this.errors.filter(e => 
                e.type === 'network-error' && 
                (Date.now() - e.timestamp.getTime()) < 60000
            );
            return recentNetworkErrors.length <= 1;
        }
        
        return true;
    }
    
    /**
     * Show error notification to user
     */
    showErrorNotification(errorInfo) {
        // Check if notification element exists
        let notification = document.getElementById('error-notification');
        
        if (!notification) {
            // Create notification element
            notification = document.createElement('div');
            notification.id = 'error-notification';
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                max-width: 300px;
                padding: 15px;
                background: #ef4444;
                color: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                z-index: 10000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 14px;
                display: none;
            `;
            document.body.appendChild(notification);
        }
        
        // Set error message
        let message = 'An error occurred';
        
        if (errorInfo.type === 'network-error' || 
            (errorInfo.message && errorInfo.message.includes('WebSocket'))) {
            message = 'Connection error. Please check your network.';
        } else if (errorInfo.message && errorInfo.message.includes('Failed to fetch')) {
            message = 'Unable to load data. Please try again.';
        }
        
        notification.textContent = message;
        notification.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            notification.style.display = 'none';
        }, 5000);
    }
    
    /**
     * Report error to backend (if configured)
     */
    async reportError(errorInfo) {
        if (!this.errorReportingUrl) {
            return;
        }
        
        try {
            const response = await fetch(this.errorReportingUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ...errorInfo,
                    userAgent: navigator.userAgent,
                    url: window.location.href,
                    timestamp: errorInfo.timestamp.toISOString()
                })
            });
            
            if (!response.ok) {
                console.warn('Failed to report error:', response.status);
            }
        } catch (error) {
            // Silently fail - don't create error loop
            console.warn('Error reporting failed:', error);
        }
    }
    
    /**
     * Add error listener
     */
    addListener(callback) {
        this.errorListeners.add(callback);
    }
    
    /**
     * Remove error listener
     */
    removeListener(callback) {
        this.errorListeners.delete(callback);
    }
    
    /**
     * Notify all listeners
     */
    notifyListeners(errorInfo) {
        this.errorListeners.forEach(callback => {
            try {
                callback(errorInfo);
            } catch (error) {
                console.warn('Error listener failed:', error);
            }
        });
    }
    
    /**
     * Get recent errors
     */
    getRecentErrors(count = 10) {
        return this.errors.slice(-count);
    }
    
    /**
     * Clear all errors
     */
    clearErrors() {
        this.errors = [];
    }
    
    /**
     * Get error statistics
     */
    getStats() {
        const now = Date.now();
        const last5Min = now - 5 * 60 * 1000;
        const last1Hour = now - 60 * 60 * 1000;
        
        return {
            total: this.errors.length,
            last5Minutes: this.errors.filter(e => e.timestamp.getTime() > last5Min).length,
            lastHour: this.errors.filter(e => e.timestamp.getTime() > last1Hour).length,
            byType: this.errors.reduce((acc, error) => {
                acc[error.type] = (acc[error.type] || 0) + 1;
                return acc;
            }, {})
        };
    }
}

// Create global error handler instance
const errorHandler = new ErrorHandler();

// Wrap common async operations
function safeAsync(asyncFn, errorContext = {}) {
    return async (...args) => {
        try {
            return await asyncFn(...args);
        } catch (error) {
            errorHandler.handleError({
                type: 'async-error',
                error: error,
                context: errorContext,
                timestamp: new Date()
            });
            throw error;
        }
    };
}

// Wrap setTimeout to catch errors
const originalSetTimeout = window.setTimeout;
window.setTimeout = function(callback, delay, ...args) {
    const wrappedCallback = function() {
        try {
            callback(...args);
        } catch (error) {
            errorHandler.handleError({
                type: 'timeout-error',
                error: error,
                timestamp: new Date()
            });
        }
    };
    
    return originalSetTimeout(wrappedCallback, delay);
};

// Wrap setInterval to catch errors
const originalSetInterval = window.setInterval;
window.setInterval = function(callback, delay, ...args) {
    const wrappedCallback = function() {
        try {
            callback(...args);
        } catch (error) {
            errorHandler.handleError({
                type: 'interval-error',
                error: error,
                timestamp: new Date()
            });
        }
    };
    
    return originalSetInterval(wrappedCallback, delay);
};

// Export for use in other modules
window.errorHandler = errorHandler;
window.safeAsync = safeAsync;