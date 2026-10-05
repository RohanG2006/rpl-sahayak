# RPL-Sahayak AI — frontend

Next.js 16 (App Router) PWA for workers, assessors and administrators. Setup, environment variables and the demo
workflow are in the [root README](../README.md); the offline layer is described in
[docs/offline-sync.md](../docs/offline-sync.md).

```bash
npm install
npm run dev      # http://localhost:3000 (expects the API at NEXT_PUBLIC_API_BASE, default http://localhost:8000/api/v1)
npm test         # Vitest
npm run lint
```
