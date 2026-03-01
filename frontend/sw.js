const CACHE_NAME = 'prizmbet-v13';
const ASSETS = [
    './',
    './index.html',
    './live_index.html',
    './manifest.json',
    './prizmbet-logo.webp'
];

self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS).catch(err => {
                console.warn('SW Install - some assets failed to cache:', err);
            });
        })
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            );
        })
    );
});

self.addEventListener('fetch', (event) => {
    // Не кешируем matches.json (он должен быть всегда свежим), но можем отдавать fallback
    if (event.request.url.includes('matches.json')) {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then((cached) => {
            return cached || fetch(event.request).then((response) => {
                // Если хотим динамически кешировать:
                // if (response && response.status === 200 && response.type === 'basic') {
                //     const responseClone = response.clone();
                //     caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
                // }
                return response;
            });
        }).catch(() => {
            return caches.match('./index.html');
        })
    );
});
