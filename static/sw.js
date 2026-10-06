const CACHE_VERSION = 'v1';
const STATIC_CACHE = `songstery-static-${CACHE_VERSION}`;
const PAGE_CACHE = `songstery-pages-${CACHE_VERSION}`;
const OFFLINE_URL = '/offline/';
const STATIC_PREFIX = '/static/';
const PRECACHE_URLS = [OFFLINE_URL, '/static/icons/icon-192.png', '/static/icons/icon-512.png'];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches
            .open(PAGE_CACHE)
            .then((cache) => Promise.all(PRECACHE_URLS.map((url) => cache.add(url).catch(() => undefined))))
            .then(() => self.skipWaiting()),
    );
});

self.addEventListener('activate', (event) => {
    const keep = new Set([STATIC_CACHE, PAGE_CACHE]);
    event.waitUntil(
        caches
            .keys()
            .then((keys) => Promise.all(keys.filter((key) => !keep.has(key)).map((key) => caches.delete(key))))
            .then(() => self.clients.claim()),
    );
});

async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok) {
        const cache = await caches.open(STATIC_CACHE);
        cache.put(request, response.clone());
    }
    return response;
}

async function networkWithOfflineFallback(request) {
    try {
        return await fetch(request);
    } catch (error) {
        const offline = await caches.match(OFFLINE_URL);
        return offline || Response.error();
    }
}

self.addEventListener('fetch', (event) => {
    const {request} = event;
    if (request.method !== 'GET') return;

    const url = new URL(request.url);
    if (url.origin !== self.location.origin) return;

    if (url.pathname.startsWith(STATIC_PREFIX)) {
        event.respondWith(cacheFirst(request));
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith(networkWithOfflineFallback(request));
    }
});
