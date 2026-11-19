// Overheads offline cache. The page opens with no signal once it has been opened once with one.
// The page itself: network first (so updates arrive), falling back to the saved copy after 3 seconds or when offline.
// Everything else (icons, jsPDF, fonts): the saved copy first, refreshed in the background.
const VERSION = 'overheads-v1';
const SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'docs/apple-touch-icon.png'];
const EXTRA = ['https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'];

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(VERSION);
    await c.addAll(SHELL);
    // the PDF library lives on a CDN; if it can't be reached now, it's saved the first time the page loads it
    for (const u of EXTRA) { try { await c.add(new Request(u, { mode: 'no-cors' })) } catch (err) {} }
    self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== VERSION) await caches.delete(k);
    await self.clients.claim();
  })());
});

const timeout = (p, ms) => new Promise((ok, no) => { const t = setTimeout(() => no(new Error('slow')), ms); p.then(v => { clearTimeout(t); ok(v) }, err => { clearTimeout(t); no(err) }) });

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const sameSite = url.origin === self.location.origin;
  if (req.mode === 'navigate') {
    e.respondWith((async () => {
      const c = await caches.open(VERSION);
      try {
        const res = await timeout(fetch(req), 3000);
        if (res.ok) c.put('index.html', res.clone());
        return res;
      } catch (err) {
        return (await c.match('index.html')) || (await c.match('./')) || Response.error();
      }
    })());
    return;
  }
  const cacheable = sameSite || /^(cdnjs\.cloudflare\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)$/.test(url.hostname);
  if (!cacheable) return;
  e.respondWith((async () => {
    const c = await caches.open(VERSION);
    const hit = await c.match(req);
    const fresh = fetch(req).then(res => { if (res.ok || res.type === 'opaque') c.put(req, res.clone()); return res }).catch(() => null);
    if (hit) { e.waitUntil(fresh); return hit }
    return (await fresh) || Response.error();
  })());
});
