/**
 * Enhanced Service Worker for Brum Brum Tracker
 * Implements multiple caching strategies for optimal performance
 */

// Cache version and names
const CACHE_VERSION = 'v4';
const CACHE_PREFIX = 'brum-brum';
const CACHE_NAMES = {
    STATIC: `${CACHE_PREFIX}-static-${CACHE_VERSION}`,
    DYNAMIC: `${CACHE_PREFIX}-dynamic-${CACHE_VERSION}`,
    IMAGES: `${CACHE_PREFIX}-images-${CACHE_VERSION}`,
    API: `${CACHE_PREFIX}-api-${CACHE_VERSION}`
};

// Maximum cache sizes
const MAX_CACHE_SIZES = {
    DYNAMIC: 50,
    IMAGES: 100,
    API: 30
};

// Cache durations (in seconds)
const CACHE_DURATIONS = {
    API: 300, // 5 minutes
    IMAGES: 86400, // 24 hours
    DYNAMIC: 3600 // 1 hour
};

// Static assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/dashboard.html',
    '/logbook.html',
    '/style.css',
    '/logbook.css',
    '/main.js',
    '/dashboard.js',
    '/logbook.js',
    '/manifest.json',
    '/assets/arrow.svg',
    '/assets/plane-placeholder.svg',
    '/assets/icon-192.png',
    '/assets/icon-512.png',
    '/assets/atc_1.mp3',
    '/assets/atc_2.mp3',
    '/assets/atc_3.mp3',
    '/assets/atc_4.mp3',
    '/assets/atc_5.mp3',
    '/js/modules/lazy-loader.js',
    '/js/modules/websocket-manager.js',
    '/js/modules/ui-utils.js',
    '/js/modules/device-orientation.js'
];

// Install event - cache static resources
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAMES.STATIC)
            .then(cache => {
                console.log('Service Worker: Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('Service Worker: Install complete');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('Service Worker: Install failed', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        Promise.all([
            // Delete old caches
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName.startsWith(CACHE_PREFIX) && 
                            !Object.values(CACHE_NAMES).includes(cacheName)) {
                            console.log('Service Worker: Deleting old cache', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            // Claim all clients
            self.clients.claim()
        ]).then(() => {
            console.log('Service Worker: Activated');
        })
    );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip WebSocket requests
    if (url.protocol === 'ws:' || url.protocol === 'wss:') {
        return;
    }
    
    // Determine caching strategy based on request
    if (isStaticAsset(url)) {
        event.respondWith(cacheFirst(request));
    } else if (isImageRequest(url)) {
        event.respondWith(cacheFirstWithRefresh(request, CACHE_NAMES.IMAGES));
    } else if (isApiRequest(url)) {
        event.respondWith(networkFirstWithCache(request, CACHE_NAMES.API));
    } else {
        event.respondWith(staleWhileRevalidate(request, CACHE_NAMES.DYNAMIC));
    }
});

// Helper functions to determine request type
function isStaticAsset(url) {
    return STATIC_ASSETS.some(asset => url.pathname.endsWith(asset));
}

function isImageRequest(url) {
    return /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(url.pathname) ||
           url.hostname.includes('jetphotos') ||
           url.hostname.includes('planespotters');
}

function isApiRequest(url) {
    return url.pathname.includes('/api/') || 
           url.pathname.includes('/logbook');
}

// Caching Strategies

/**
 * Cache First - for static assets
 * Try cache first, fallback to network
 */
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) {
        return cached;
    }
    
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAMES.STATIC);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.error('Service Worker: Fetch failed', error);
        throw error;
    }
}

/**
 * Cache First with Background Refresh - for images
 * Return from cache immediately, update cache in background
 */
async function cacheFirstWithRefresh(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    
    // Fetch in background to update cache
    const fetchPromise = fetch(request).then(response => {
        if (response.ok) {
            cache.put(request, response.clone());
            limitCacheSize(cacheName, MAX_CACHE_SIZES.IMAGES);
        }
        return response;
    }).catch(() => cached);
    
    // Return cached immediately if available
    return cached || fetchPromise;
}

/**
 * Network First with Cache Fallback - for API requests
 * Try network first with timeout, fallback to cache
 */
async function networkFirstWithCache(request, cacheName) {
    const cache = await caches.open(cacheName);
    
    try {
        const response = await fetch(request);
        
        if (response.ok) {
            cache.put(request, response.clone());
            limitCacheSize(cacheName, MAX_CACHE_SIZES.API);
        }
        
        return response;
    } catch (error) {
        console.log('Service Worker: Network failed, trying cache', error);
        const cached = await cache.match(request);
        
        if (cached) {
            return cached;
        }
        
        throw error;
    }
}

/**
 * Stale While Revalidate - for dynamic content
 * Return from cache immediately, update cache in background
 */
async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    
    const fetchPromise = fetch(request).then(response => {
        if (response.ok) {
            cache.put(request, response.clone());
            limitCacheSize(cacheName, MAX_CACHE_SIZES.DYNAMIC);
        }
        return response;
    });
    
    return cached || fetchPromise;
}

/**
 * Limit cache size by removing oldest entries
 */
async function limitCacheSize(cacheName, maxSize) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    
    if (keys.length > maxSize) {
        // Remove oldest entries
        const toDelete = keys.length - maxSize;
        for (let i = 0; i < toDelete; i++) {
            await cache.delete(keys[i]);
        }
    }
}

// Handle messages from the app
self.addEventListener('message', event => {
    if (!event.data) return;
    
    switch (event.data.type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;
            
        case 'CLEAR_CACHE':
            event.waitUntil(
                caches.keys().then(cacheNames => {
                    return Promise.all(
                        cacheNames.map(cacheName => {
                            if (cacheName.startsWith(CACHE_PREFIX)) {
                                return caches.delete(cacheName);
                            }
                        })
                    );
                })
            );
            break;
            
        case 'CACHE_URLS':
            if (event.data.urls && Array.isArray(event.data.urls)) {
                event.waitUntil(
                    caches.open(CACHE_NAMES.DYNAMIC).then(cache => {
                        return cache.addAll(event.data.urls);
                    })
                );
            }
            break;
    }
});