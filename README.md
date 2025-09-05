# WellAtlas 2.9.2 — GOLD Demo

**Deploy**
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
- Env: `MAPTILER_KEY` (MapTiler key for tiles)

**Features**
- Header: title + controls (Customers, Sites, Job #, global search, filters)
- Map (Leaflet) with pins; job/customer filters; full-text search (incl. notes)
- Quick Add modal on Home (customer + site + job) with **Use My Location** and **Center on Me**
- Add forms on Customers, Sites, Jobs pages
- Share links: per-customer and per-job view-only pages
- Seeded demo: 10 customers, 100 sites (mining terms), 100 jobs (#25001..25100) with random categories
