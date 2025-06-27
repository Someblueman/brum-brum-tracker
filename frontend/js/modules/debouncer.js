/**
 * Request debouncing utility for optimizing frequent requests.
 * 
 * This module provides debouncing functionality to prevent excessive
 * requests to the backend, improving performance and reducing load.
 */

/**
 * Creates a debounced function that delays invoking func until after
 * wait milliseconds have elapsed since the last time it was invoked.
 * 
 * @param {Function} func - The function to debounce
 * @param {number} wait - The number of milliseconds to delay
 * @param {Object} options - Options object
 * @param {boolean} options.leading - Invoke on the leading edge of the timeout
 * @param {boolean} options.trailing - Invoke on the trailing edge of the timeout
 * @param {number} options.maxWait - Maximum time func is allowed to be delayed
 * @returns {Function} The debounced function
 */
export function debounce(func, wait, options = {}) {
    let timeout;
    let lastCallTime;
    let lastInvokeTime = 0;
    let lastArgs;
    let lastThis;
    let result;
    
    const {
        leading = false,
        trailing = true,
        maxWait
    } = options;
    
    const hasMaxWait = maxWait !== undefined;
    
    function invokeFunc(time) {
        const args = lastArgs;
        const thisArg = lastThis;
        
        lastArgs = lastThis = undefined;
        lastInvokeTime = time;
        result = func.apply(thisArg, args);
        return result;
    }
    
    function leadingEdge(time) {
        lastInvokeTime = time;
        timeout = setTimeout(timerExpired, wait);
        return leading ? invokeFunc(time) : result;
    }
    
    function remainingWait(time) {
        const timeSinceLastCall = time - lastCallTime;
        const timeSinceLastInvoke = time - lastInvokeTime;
        const timeWaiting = wait - timeSinceLastCall;
        
        return hasMaxWait
            ? Math.min(timeWaiting, maxWait - timeSinceLastInvoke)
            : timeWaiting;
    }
    
    function shouldInvoke(time) {
        const timeSinceLastCall = time - lastCallTime;
        const timeSinceLastInvoke = time - lastInvokeTime;
        
        return (lastCallTime === undefined || 
                timeSinceLastCall >= wait ||
                timeSinceLastCall < 0 ||
                (hasMaxWait && timeSinceLastInvoke >= maxWait));
    }
    
    function timerExpired() {
        const time = Date.now();
        if (shouldInvoke(time)) {
            return trailingEdge(time);
        }
        timeout = setTimeout(timerExpired, remainingWait(time));
    }
    
    function trailingEdge(time) {
        timeout = undefined;
        
        if (trailing && lastArgs) {
            return invokeFunc(time);
        }
        lastArgs = lastThis = undefined;
        return result;
    }
    
    function cancel() {
        if (timeout !== undefined) {
            clearTimeout(timeout);
        }
        lastInvokeTime = 0;
        lastArgs = lastCallTime = lastThis = timeout = undefined;
    }
    
    function flush() {
        return timeout === undefined ? result : trailingEdge(Date.now());
    }
    
    function pending() {
        return timeout !== undefined;
    }
    
    function debounced(...args) {
        const time = Date.now();
        const isInvoking = shouldInvoke(time);
        
        lastArgs = args;
        lastThis = this;
        lastCallTime = time;
        
        if (isInvoking) {
            if (timeout === undefined) {
                return leadingEdge(lastCallTime);
            }
            if (hasMaxWait) {
                timeout = setTimeout(timerExpired, wait);
                return invokeFunc(lastCallTime);
            }
        }
        if (timeout === undefined) {
            timeout = setTimeout(timerExpired, wait);
        }
        return result;
    }
    
    debounced.cancel = cancel;
    debounced.flush = flush;
    debounced.pending = pending;
    
    return debounced;
}

/**
 * Creates a throttled function that only invokes func at most once
 * per every wait milliseconds.
 * 
 * @param {Function} func - The function to throttle
 * @param {number} wait - The number of milliseconds to throttle invocations to
 * @param {Object} options - Options object
 * @param {boolean} options.leading - Invoke on the leading edge of the timeout
 * @param {boolean} options.trailing - Invoke on the trailing edge of the timeout
 * @returns {Function} The throttled function
 */
export function throttle(func, wait, options = {}) {
    const { leading = true, trailing = true } = options;
    
    return debounce(func, wait, {
        leading,
        trailing,
        maxWait: wait
    });
}

/**
 * WebSocket-specific debouncer that batches multiple messages
 * into a single request.
 * 
 * @param {Function} sendFunc - The WebSocket send function
 * @param {number} wait - Milliseconds to wait before sending
 * @param {number} maxBatchSize - Maximum number of messages to batch
 * @returns {Object} Debounced sender with send and flush methods
 */
export function createMessageBatcher(sendFunc, wait = 100, maxBatchSize = 10) {
    let messageQueue = [];
    
    const flushMessages = () => {
        if (messageQueue.length === 0) return;
        
        const messages = [...messageQueue];
        messageQueue = [];
        
        // Send as batch if multiple messages, otherwise send single
        if (messages.length === 1) {
            sendFunc(messages[0]);
        } else {
            sendFunc({
                type: 'batch',
                messages: messages
            });
        }
    };
    
    const debouncedFlush = debounce(flushMessages, wait, {
        trailing: true,
        maxWait: wait * 2
    });
    
    return {
        send(message) {
            messageQueue.push(message);
            
            if (messageQueue.length >= maxBatchSize) {
                debouncedFlush.cancel();
                flushMessages();
            } else {
                debouncedFlush();
            }
        },
        
        flush() {
            debouncedFlush.cancel();
            flushMessages();
        },
        
        cancel() {
            debouncedFlush.cancel();
            messageQueue = [];
        },
        
        pending() {
            return messageQueue.length > 0 || debouncedFlush.pending();
        }
    };
}

/**
 * Creates a debounced search function with automatic cancellation
 * of previous searches.
 * 
 * @param {Function} searchFunc - The search function to debounce
 * @param {number} wait - Milliseconds to wait before searching
 * @returns {Function} Debounced search function
 */
export function createSearchDebouncer(searchFunc, wait = 300) {
    let currentSearchId = 0;
    
    const debouncedSearch = debounce(async (query, searchId) => {
        // Only process if this is still the current search
        if (searchId === currentSearchId) {
            return await searchFunc(query);
        }
    }, wait);
    
    return (query) => {
        currentSearchId++;
        return debouncedSearch(query, currentSearchId);
    };
}