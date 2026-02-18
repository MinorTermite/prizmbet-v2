// Service Worker for PrizmBet PWA  
  
const CACHE_NAME = 'prizmbet-v2';  
const urlsToCache = [  
  '/index.html',  
  '/matches.json',  
  '/prizmbet-logo.gif'  
];  
  
// Install  
self.addEventListener('install', event = 
  event.waitUntil(  
    caches.open(CACHE_NAME)  
      .then(cache = 
  );  
});  
  
// Fetch  
self.addEventListener('fetch', event = 
  event.respondWith(  
    caches.match(event.request)  
      .then(response = 
        if (response) {  
          return response;  
        }  
        return fetch(event.request);  
      })  
  );  
});  
  
// Activate  
self.addEventListener('activate', event = 
  event.waitUntil(  
    caches.keys().then(cacheNames = 
      return Promise.all(  
        cacheNames.map(cacheName = 
          if (cacheName !== CACHE_NAME) {  
            return caches.delete(cacheName);  
          }  
        })  
      );  
    })  
  );  
}); 
