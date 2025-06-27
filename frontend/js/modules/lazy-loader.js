/**
 * Lazy loading module for images
 * Provides intersection observer-based lazy loading with progressive enhancement
 */

export class LazyImageLoader {
    constructor(options = {}) {
        this.options = {
            rootMargin: options.rootMargin || '50px 0px',
            threshold: options.threshold || 0.01,
            loadingClass: options.loadingClass || 'loading',
            loadedClass: options.loadedClass || 'loaded',
            errorClass: options.errorClass || 'error',
            placeholder: options.placeholder || 'assets/plane-placeholder.svg',
            retryAttempts: options.retryAttempts || 2,
            retryDelay: options.retryDelay || 1000
        };
        
        this.observer = null;
        this.loadingImages = new Set();
        this.failedImages = new Map(); // Track retry attempts
        
        this._initializeObserver();
    }
    
    /**
     * Initialize the intersection observer
     */
    _initializeObserver() {
        // Check if IntersectionObserver is supported
        if (!('IntersectionObserver' in window)) {
            console.warn('IntersectionObserver not supported, falling back to immediate loading');
            this.observer = null;
            return;
        }
        
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this._loadImage(entry.target);
                }
            });
        }, {
            rootMargin: this.options.rootMargin,
            threshold: this.options.threshold
        });
    }
    
    /**
     * Create a lazy-loaded image element
     * @param {string} src - The image source URL
     * @param {string} alt - Alt text for the image
     * @param {string} className - Additional CSS classes
     * @returns {HTMLImageElement} The image element
     */
    createLazyImage(src, alt = '', className = '') {
        const img = document.createElement('img');
        
        // Set placeholder and store real src
        img.src = this.options.placeholder;
        img.dataset.src = src;
        img.alt = alt;
        
        if (className) {
            img.className = className;
        }
        
        img.classList.add(this.options.loadingClass);
        
        // Handle error fallback
        img.onerror = () => this._handleImageError(img);
        
        return img;
    }
    
    /**
     * Observe an image for lazy loading
     * @param {HTMLImageElement} img - Image element to observe
     */
    observe(img) {
        if (this.observer) {
            this.observer.observe(img);
        } else {
            // Fallback for browsers without IntersectionObserver
            this._loadImage(img);
        }
    }
    
    /**
     * Observe multiple images
     * @param {NodeList|Array} images - Images to observe
     */
    observeAll(images) {
        images.forEach(img => this.observe(img));
    }
    
    /**
     * Load an image
     * @param {HTMLImageElement} img - Image element to load
     */
    _loadImage(img) {
        const src = img.dataset.src;
        
        if (!src || this.loadingImages.has(img)) {
            return;
        }
        
        this.loadingImages.add(img);
        
        // Create a new image to test loading
        const tempImg = new Image();
        
        tempImg.onload = () => {
            img.src = src;
            img.classList.remove(this.options.loadingClass);
            img.classList.add(this.options.loadedClass);
            
            // Stop observing this image
            if (this.observer) {
                this.observer.unobserve(img);
            }
            
            this.loadingImages.delete(img);
            this.failedImages.delete(img);
            
            // Trigger custom event
            img.dispatchEvent(new CustomEvent('lazyloaded', {
                detail: { src }
            }));
        };
        
        tempImg.onerror = () => {
            this.loadingImages.delete(img);
            this._handleImageError(img);
        };
        
        tempImg.src = src;
    }
    
    /**
     * Handle image loading errors with retry logic
     * @param {HTMLImageElement} img - Image that failed to load
     */
    _handleImageError(img) {
        const attempts = this.failedImages.get(img) || 0;
        
        if (attempts < this.options.retryAttempts && img.dataset.src) {
            // Increment retry counter
            this.failedImages.set(img, attempts + 1);
            
            // Retry after delay
            setTimeout(() => {
                console.log(`Retrying image load (attempt ${attempts + 1}): ${img.dataset.src}`);
                this._loadImage(img);
            }, this.options.retryDelay * (attempts + 1));
        } else {
            // Max retries reached or no data-src
            img.classList.remove(this.options.loadingClass);
            img.classList.add(this.options.errorClass);
            
            // Ensure placeholder is shown
            if (img.src !== this.options.placeholder) {
                img.src = this.options.placeholder;
            }
            
            // Stop observing
            if (this.observer) {
                this.observer.unobserve(img);
            }
            
            this.failedImages.delete(img);
            
            // Trigger error event
            img.dispatchEvent(new CustomEvent('lazyerror', {
                detail: { 
                    src: img.dataset.src,
                    attempts: attempts + 1
                }
            }));
        }
    }
    
    /**
     * Load all images immediately (useful for print or offline)
     */
    loadAll() {
        const lazyImages = document.querySelectorAll(`img[data-src]`);
        lazyImages.forEach(img => this._loadImage(img));
    }
    
    /**
     * Refresh observations (useful after dynamic content updates)
     */
    refresh() {
        const lazyImages = document.querySelectorAll(`img[data-src]:not(.${this.options.loadedClass})`);
        this.observeAll(lazyImages);
    }
    
    /**
     * Disconnect the observer and cleanup
     */
    disconnect() {
        if (this.observer) {
            this.observer.disconnect();
        }
        this.loadingImages.clear();
        this.failedImages.clear();
    }
}

// Create a default instance
export const lazyLoader = new LazyImageLoader();

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        lazyLoader.refresh();
    });
} else {
    lazyLoader.refresh();
}