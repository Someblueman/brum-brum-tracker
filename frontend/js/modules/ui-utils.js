/**
 * UI Utilities Module
 * Shared UI helper functions and utilities
 */

/**
 * Update connection status indicator
 */
export function updateConnectionStatus(element, connected, reconnecting = false) {
    if (!element) return;
    
    const statusText = element.querySelector('.status-text');
    const statusDot = element.querySelector('.status-dot');
    
    if (connected) {
        element.className = 'connection-status connected';
        if (statusText) statusText.textContent = 'Connected';
        if (statusDot) statusDot.className = 'status-dot connected';
    } else if (reconnecting) {
        element.className = 'connection-status reconnecting';
        if (statusText) statusText.textContent = 'Reconnecting...';
        if (statusDot) statusDot.className = 'status-dot reconnecting';
    } else {
        element.className = 'connection-status disconnected';
        if (statusText) statusText.textContent = 'Disconnected';
        if (statusDot) statusDot.className = 'status-dot disconnected';
    }
}

/**
 * Format distance for display
 */
export function formatDistance(km) {
    if (km < 1) {
        return `${Math.round(km * 1000)}m`;
    } else if (km < 10) {
        return `${km.toFixed(1)}km`;
    } else {
        return `${Math.round(km)}km`;
    }
}

/**
 * Format altitude for display
 */
export function formatAltitude(meters) {
    const feet = Math.round(meters * 3.28084);
    return `${feet.toLocaleString()}ft`;
}

/**
 * Format speed for display
 */
export function formatSpeed(kmh) {
    const mph = Math.round(kmh * 0.621371);
    return `${mph}mph`;
}

/**
 * Format time duration
 */
export function formatDuration(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.round(seconds % 60);
        return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
    }
}

/**
 * Format timestamp
 */
export function formatTime(date) {
    return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
    });
}

/**
 * Get country flag emoji from country code
 */
export function getCountryFlag(countryCode) {
    if (!countryCode || countryCode.length !== 2) return '';
    
    const codePoints = countryCode
        .toUpperCase()
        .split('')
        .map(char => 127397 + char.charCodeAt());
    
    return String.fromCodePoint(...codePoints);
}

/**
 * Show/hide element with animation
 */
export function toggleElement(element, show, animationClass = 'fade') {
    if (!element) return;
    
    if (show) {
        element.style.display = '';
        element.classList.add(animationClass);
        // Force reflow
        element.offsetHeight;
        element.classList.add('show');
    } else {
        element.classList.remove('show');
        setTimeout(() => {
            element.style.display = 'none';
            element.classList.remove(animationClass);
        }, 300);
    }
}

/**
 * Smooth value update with animation
 */
export function updateValueWithAnimation(element, newValue, duration = 300) {
    if (!element) return;
    
    const oldValue = parseFloat(element.textContent) || 0;
    const startTime = performance.now();
    
    function animate(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        
        const currentValue = oldValue + (newValue - oldValue) * easeOut;
        element.textContent = Math.round(currentValue);
        
        if (progress < 1) {
            requestAnimationFrame(animate);
        }
    }
    
    requestAnimationFrame(animate);
}

/**
 * Create and show notification
 */
export function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Trigger animation
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Remove after duration
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

/**
 * Debounce function
 */
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function
 */
export function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}