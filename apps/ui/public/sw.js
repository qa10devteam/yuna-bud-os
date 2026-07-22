const CACHE = 'budos-v1';
const STATIC = ['/', '/landing', '/pricing'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC).catch(() => {})));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => {
    const toDelete = [];
    for (const k of keys) { if (k !== CACHE) toDelete.push(caches.delete(k)); }
    return Promise.all(toDelete);
  }));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('/api/')) return; // never cache API
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
