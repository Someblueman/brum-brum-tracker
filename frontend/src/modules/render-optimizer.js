/**
 * Render optimization module to reduce unnecessary DOM updates
 * Uses dirty checking and batching to minimize reflows and repaints
 */

export class RenderOptimizer {
    constructor() {
        this.pendingUpdates = new Map();
        this.frameId = null;
        this.lastValues = new Map();
        this.updateThrottles = new Map();
        this.batchTimeout = null;
        
        // Configuration
        this.config = {
            batchDelay: 16, // ~60fps
            throttleDefaults: {
                distance: 1000, // Update distance every second
                altitude: 2000, // Update altitude every 2 seconds
                speed: 1500,    // Update speed every 1.5 seconds
                bearing: 100,   // Update bearing frequently for smooth rotation
                default: 500    // Default throttle for other fields
            }
        };
    }
    
    /**
     * Check if value has actually changed
     * @param {string} key - The property key
     * @param {*} newValue - The new value
     * @returns {boolean} True if value changed
     */
    hasChanged(key, newValue) {
        const lastValue = this.lastValues.get(key);
        
        // Handle different types appropriately
        if (typeof newValue === 'object' && newValue !== null) {
            return JSON.stringify(newValue) !== JSON.stringify(lastValue);
        }
        
        return newValue !== lastValue;
    }
    
    /**
     * Check if update is throttled
     * @param {string} key - The property key
     * @returns {boolean} True if throttled
     */
    isThrottled(key) {
        const lastUpdate = this.updateThrottles.get(key);
        if (!lastUpdate) return false;
        
        const throttleTime = this.config.throttleDefaults[key] || 
                           this.config.throttleDefaults.default;
        
        return Date.now() - lastUpdate < throttleTime;
    }
    
    /**
     * Schedule a DOM update
     * @param {string} key - The property key
     * @param {Function} updateFn - The update function
     * @param {*} value - The new value
     * @param {Object} options - Update options
     */
    scheduleUpdate(key, updateFn, value, options = {}) {
        // Skip if value hasn't changed
        if (!options.force && !this.hasChanged(key, value)) {
            return;
        }
        
        // Skip if throttled
        if (!options.immediate && this.isThrottled(key)) {
            return;
        }
        
        // Store the update
        this.pendingUpdates.set(key, {
            fn: updateFn,
            value: value,
            timestamp: Date.now()
        });
        
        // Schedule batch update
        if (options.immediate) {
            this.flushUpdates();
        } else {
            this.scheduleBatch();
        }
    }
    
    /**
     * Schedule a batch update
     */
    scheduleBatch() {
        if (this.batchTimeout) return;
        
        this.batchTimeout = setTimeout(() => {
            this.batchTimeout = null;
            this.flushUpdates();
        }, this.config.batchDelay);
    }
    
    /**
     * Flush all pending updates
     */
    flushUpdates() {
        if (this.pendingUpdates.size === 0) return;
        
        // Cancel any pending animation frame
        if (this.frameId) {
            cancelAnimationFrame(this.frameId);
        }
        
        // Schedule updates in next animation frame
        this.frameId = requestAnimationFrame(() => {
            // Sort updates by priority (bearing first for smooth rotation)
            const sortedUpdates = Array.from(this.pendingUpdates.entries())
                .sort(([keyA], [keyB]) => {
                    if (keyA === 'bearing') return -1;
                    if (keyB === 'bearing') return 1;
                    return 0;
                });
            
            // Execute updates
            sortedUpdates.forEach(([key, update]) => {
                try {
                    update.fn(update.value);
                    this.lastValues.set(key, update.value);
                    this.updateThrottles.set(key, update.timestamp);
                } catch (error) {
                    console.error(`Error updating ${key}:`, error);
                }
            });
            
            // Clear pending updates
            this.pendingUpdates.clear();
            this.frameId = null;
        });
    }
    
    /**
     * Create an optimized updater function
     * @param {HTMLElement} element - The DOM element to update
     * @param {string} property - The property to update (textContent, src, etc.)
     * @param {string} key - The cache key
     * @returns {Function} Optimized update function
     */
    createUpdater(element, property, key) {
        return (value) => {
            this.scheduleUpdate(key, (val) => {
                if (element && element[property] !== undefined) {
                    element[property] = val;
                }
            }, value);
        };
    }
    
    /**
     * Create an optimized style updater
     * @param {HTMLElement} element - The DOM element to update
     * @param {string} styleProperty - The style property to update
     * @param {string} key - The cache key
     * @returns {Function} Optimized style update function
     */
    createStyleUpdater(element, styleProperty, key) {
        return (value) => {
            this.scheduleUpdate(key, (val) => {
                if (element && element.style) {
                    element.style[styleProperty] = val;
                }
            }, value);
        };
    }
    
    /**
     * Batch multiple updates together
     * @param {Array} updates - Array of {key, fn, value} objects
     */
    batchUpdates(updates) {
        updates.forEach(({key, fn, value, options}) => {
            this.scheduleUpdate(key, fn, value, options);
        });
    }
    
    /**
     * Clear all caches and pending updates
     */
    clear() {
        if (this.frameId) {
            cancelAnimationFrame(this.frameId);
            this.frameId = null;
        }
        
        if (this.batchTimeout) {
            clearTimeout(this.batchTimeout);
            this.batchTimeout = null;
        }
        
        this.pendingUpdates.clear();
        this.lastValues.clear();
        this.updateThrottles.clear();
    }
}

/**
 * Create a debounced function
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(fn, delay) {
    let timeout;
    
    return function debounced(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), delay);
    };
}

/**
 * Create a throttled function
 * @param {Function} fn - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
export function throttle(fn, limit) {
    let inThrottle;
    
    return function throttled(...args) {
        if (!inThrottle) {
            fn.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Memoize a function's results
 * @param {Function} fn - Function to memoize
 * @param {Function} keyFn - Function to generate cache key
 * @returns {Function} Memoized function
 */
export function memoize(fn, keyFn = JSON.stringify) {
    const cache = new Map();
    
    return function memoized(...args) {
        const key = keyFn(args);
        
        if (cache.has(key)) {
            return cache.get(key);
        }
        
        const result = fn.apply(this, args);
        cache.set(key, result);
        
        // Limit cache size
        if (cache.size > 100) {
            const firstKey = cache.keys().next().value;
            cache.delete(firstKey);
        }
        
        return result;
    };
}

// Create default instance
export const renderOptimizer = new RenderOptimizer();