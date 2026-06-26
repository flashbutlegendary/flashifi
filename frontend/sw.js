/**
 * FlashiFi Service Worker for PWA Offline Caching
 */

const CACHE_NAME = "flashifi-v1";
const ASSETS_TO_CACHE = [
  "./",
  "index.html",
  "assets/css/styles.css",
  "assets/js/app.js",
  "assets/js/messages.js",
  "manifest.json"
];

// Install event - caching static shell assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[Service Worker] Caching app shell assets");
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

// Activate event - cleaning old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log("[Service Worker] Removing old cache:", name);
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - cache-first with network fallback for assets, network-only for API requests
self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);

  // Bypass cache completely for API calls to the backend running locally or in prod
  if (
    requestUrl.pathname.startsWith("/metadata") ||
    requestUrl.pathname.startsWith("/download") ||
    requestUrl.pathname.startsWith("/progress") ||
    requestUrl.pathname.startsWith("/health") ||
    requestUrl.port === "8000" // Backend port
  ) {
    return event.respondWith(fetch(event.request));
  }

  // Cache-first strategy for static assets
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).then((networkResponse) => {
        // Cache dynamic assets that load successfully
        if (
          networkResponse &&
          networkResponse.status === 200 &&
          networkResponse.type === "basic" &&
          // Skip caching files on different domains (like formspree or clarity)
          requestUrl.origin === self.location.origin
        ) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      }).catch(() => {
        // Fallback for offline usage
        if (event.request.mode === "navigate") {
          return caches.match("/index.html");
        }
      });
    })
  );
});
