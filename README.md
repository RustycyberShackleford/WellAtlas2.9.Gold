
# WellAtlas_2_9_9_BigSeed_Details_Share_GH
WellAtlas by Henry Suden — **Big Seed + Details + Share links**

- 40 customers × 10 sites each = ~400 jobs (25xxx numbers)
- Mining-terminology site names
- Rich job descriptions and multiple notes
- Interactive Leaflet map with search & filters
- Share-link endpoints (customer-wide and per-job)

## Deploy
- Env var: `MAPTILER_KEY`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
- Health: `/healthz`
