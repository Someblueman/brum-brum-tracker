/**
 * Device Orientation Module
 * Handles compass and device orientation across different platforms
 */

export class DeviceOrientationManager {
    constructor(options = {}) {
        // Configuration
        this.headingHistorySize = options.headingHistorySize || 5;
        this.updateThreshold = options.updateThreshold || 2;
        
        // State
        this.deviceHeading = 0;
        this.headingHistory = [];
        this.hasPermission = false;
        this.isSupported = false;
        this.isIOS = false;
        
        // Callbacks
        this.onHeadingUpdate = options.onHeadingUpdate || (() => {});
        this.onPermissionChange = options.onPermissionChange || (() => {});
        
        // Detect platform
        this._detectPlatform();
        
        // Bind methods
        this.requestPermission = this.requestPermission.bind(this);
        this._handleOrientation = this._handleOrientation.bind(this);
        this._handleMotion = this._handleMotion.bind(this);
    }
    
    /**
     * Detect platform and capabilities
     */
    _detectPlatform() {
        // Detect iOS
        this.isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
        
        // Check for orientation support
        if (window.DeviceOrientationEvent) {
            // Check if we need permission (iOS 13+)
            if (typeof DeviceOrientationEvent.requestPermission === 'function') {
                this.isSupported = true;
                this.needsPermission = true;
            } else {
                // Non-iOS or older iOS
                this.isSupported = true;
                this.needsPermission = false;
                this.hasPermission = true;
            }
        }
        
        console.log('Device orientation detection:', {
            isIOS: this.isIOS,
            isSupported: this.isSupported,
            needsPermission: this.needsPermission
        });
    }
    
    /**
     * Request permission for device orientation
     */
    async requestPermission() {
        if (!this.isSupported) {
            console.warn('Device orientation not supported');
            return false;
        }
        
        if (this.needsPermission) {
            try {
                const response = await DeviceOrientationEvent.requestPermission();
                this.hasPermission = response === 'granted';
                console.log('Device orientation permission:', response);
            } catch (error) {
                console.error('Error requesting device orientation permission:', error);
                this.hasPermission = false;
            }
        }
        
        if (this.hasPermission) {
            this.startListening();
        }
        
        this.onPermissionChange(this.hasPermission);
        return this.hasPermission;
    }
    
    /**
     * Start listening for orientation changes
     */
    startListening() {
        if (!this.hasPermission) {
            console.warn('No permission to access device orientation');
            return;
        }
        
        // Remove any existing listeners
        this.stopListening();
        
        if (this.isIOS) {
            // iOS uses webkitCompassHeading
            window.addEventListener('deviceorientation', this._handleOrientation);
        } else {
            // Android and others use alpha
            window.addEventListener('deviceorientationabsolute', this._handleOrientation);
            window.addEventListener('deviceorientation', this._handleOrientation);
        }
        
        // Also listen for device motion as a fallback
        if (window.DeviceMotionEvent) {
            window.addEventListener('devicemotion', this._handleMotion);
        }
        
        console.log('Started listening for device orientation');
    }
    
    /**
     * Stop listening for orientation changes
     */
    stopListening() {
        window.removeEventListener('deviceorientation', this._handleOrientation);
        window.removeEventListener('deviceorientationabsolute', this._handleOrientation);
        window.removeEventListener('devicemotion', this._handleMotion);
    }
    
    /**
     * Handle device orientation event
     */
    _handleOrientation(event) {
        let heading = 0;
        
        if (this.isIOS && event.webkitCompassHeading !== undefined) {
            // iOS provides webkitCompassHeading (0 = North)
            heading = event.webkitCompassHeading;
        } else if (event.alpha !== null) {
            // Android provides alpha (0 = device's current orientation)
            // Convert to compass heading (0 = North)
            heading = (360 - event.alpha) % 360;
        } else {
            return; // No valid heading data
        }
        
        this._updateHeading(heading);
    }
    
    /**
     * Handle device motion event (fallback)
     */
    _handleMotion(event) {
        // This is a basic fallback - not as accurate as orientation
        if (event.rotationRate && event.rotationRate.alpha !== null) {
            // Use rotation rate to estimate heading changes
            // This is less accurate but better than nothing
            const deltaHeading = event.rotationRate.alpha * 0.1;
            this._updateHeading((this.deviceHeading + deltaHeading) % 360);
        }
    }
    
    /**
     * Update heading with smoothing
     */
    _updateHeading(newHeading) {
        // Add to history
        this.headingHistory.push(newHeading);
        if (this.headingHistory.length > this.headingHistorySize) {
            this.headingHistory.shift();
        }
        
        // Calculate average heading (circular mean)
        const avgHeading = this._calculateCircularMean(this.headingHistory);
        
        // Check if change is significant
        const headingDiff = Math.abs(avgHeading - this.deviceHeading);
        const circularDiff = Math.min(headingDiff, 360 - headingDiff);
        
        if (circularDiff > this.updateThreshold) {
            this.deviceHeading = avgHeading;
            this.onHeadingUpdate(this.deviceHeading);
        }
    }
    
    /**
     * Calculate circular mean of angles
     */
    _calculateCircularMean(angles) {
        let sumSin = 0;
        let sumCos = 0;
        
        for (const angle of angles) {
            const rad = angle * Math.PI / 180;
            sumSin += Math.sin(rad);
            sumCos += Math.cos(rad);
        }
        
        const avgRad = Math.atan2(sumSin, sumCos);
        const avgDeg = avgRad * 180 / Math.PI;
        
        return (avgDeg + 360) % 360;
    }
    
    /**
     * Get current heading
     */
    getHeading() {
        return this.deviceHeading;
    }
    
    /**
     * Calculate relative bearing to target
     */
    calculateBearing(targetBearing) {
        let relativeBearing = targetBearing - this.deviceHeading;
        
        // Normalize to -180 to 180
        while (relativeBearing > 180) relativeBearing -= 360;
        while (relativeBearing < -180) relativeBearing += 360;
        
        return relativeBearing;
    }
}