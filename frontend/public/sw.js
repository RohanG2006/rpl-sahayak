/*
  RPL-Sahayak service worker (registered in production builds only).
  - Navigations: network-first; on failure serve the cached copy of that page, else the cached worker dashboard.
  - /_next/static/* (content-hashed JS/CSS/fonts): cache-first.
  - Other same-origin GETs (icons, manifest): stale-while-revalidate.
  - Cross-origin requests (the API) are never intercepted: API data offline comes from IndexedDB (lib/offline).
*/
const VERSION = "rpl-v1";
const SHELL = ["/", "/login", "/worker/dashboard", "/worker/assessment", "/worker/evidence", "/worker/progress", "/worker/experience", "/manifest.webmanifest", "/icon-192.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => Promise.allSettled(SHELL.map((u) => c.add(u)))).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;

  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then((res) => { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(url.pathname, copy)); return res; })
        .catch(async () => (await caches.match(url.pathname)) || (await caches.match("/worker/dashboard")) || Response.error()),
    );
    return;
  }
  if (url.pathname.startsWith("/_next/static/")) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); return res; })));
    return;
  }
  e.respondWith(
    caches.match(req).then((hit) => {
      const net = fetch(req).then((res) => { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); return res; }).catch(() => hit);
      return hit || net;
    }),
  );
});
