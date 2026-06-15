const CACHE_NAME = 'songstory-v4';
const OFFLINE_URL = '/offline/';

const PRECACHE = [
    '/',
    '/static/core/css/tokens.css',
    '/static/core/css/styles.css',
    '/static/core/js/main.js',
    '/static/core/js/forms.js',
    '/static/core/js/likes.js',
    '/static/core/js/player.js',
    '/static/core/js/rating.js',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => Promise.all(
                PRECACHE.map(url => cache.add(url).catch(() => {}))
            ))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(k => k !== CACHE_NAME)
                    .map(k => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    if (request.method !== 'GET') return;
    if (url.origin !== location.origin) return;

    if (url.pathname.startsWith('/static/') || url.pathname.startsWith('/media/')) {
        event.respondWith(
            caches.match(request).then(cached => {
                if (cached) return cached;
                return fetch(request).then(response => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
                    }
                    return response;
                });
            })
        );
        return;
    }

    event.respondWith(
        fetch(request)
            .then(response => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
                }
                return response;
            })
            .catch(() => {
                return caches.match(request)
                    .then(cached => cached || caches.match('/'));
            })
    );
});
