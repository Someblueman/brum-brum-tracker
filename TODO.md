 ‑Each task is phrased as a single, clear action.
 ‑Where a task logically depends on another, it is indented under its parent.

 pip install --upgrade pip).
1.2 Add a requirements.txt with: requests, websockets, beautifulsoup4.
1.3 Commit an empty backend/ folder and an entry‑point file backend/app.py.
1.4 Create .env.example with placeholders for HOME_LAT, HOME_LON, and OpenSky credentials.

2 · Backend — Data Layer
2.1 Create backend/db.py and initialise SQLite connection.
 2.1.1 Write create_tables() that runs
  CREATE TABLE IF NOT EXISTS aircraft (icao24 TEXT PRIMARY KEY, image_url TEXT, type TEXT);
2.2 Write get_aircraft_from_cache(icao24) that returns record or None.
2.3 Write save_aircraft_to_cache(record) that inserts/updates row.

3 · Backend — Location & Geometry Helpers
3.1 Add utils/constants.py with HOME_LAT and HOME_LON.
3.2 Implement haversine_distance(lat1, lon1, lat2, lon2) (km output).
3.3 Implement bearing_between(lat1, lon1, lat2, lon2) (0‑359°).
3.4 Implement elevation_angle(distance_km, altitude_m) (degrees).

4 · Backend — Flight Polling
4.1 Add opensky_client.py with function fetch_state_vectors(bbox) returning JSON list.
4.2 Implement build_bounding_box(home_lat, home_lon, radius_km=100).
4.3 Write filter_aircraft(raw_list) that drops
 ‑ planes on ground (baro_altitude ≤ 0)
 ‑ planes outside radius_km
 ‑ planes moving away (use true_track vs bearing).
4.4 Write is_visible(plane) using elevation threshold ≥ 20°.
4.5 Write select_best_plane(visible_planes) (highest elevation‑angle).

5 · Backend — Image Scraper & Cache
5.1 Write scrape_planespotters_image(icao24) → (image_url, aircraft_type) using BeautifulSoup.
5.2 Wrap into get_plane_media(icao24):
 ‑ try cache → return if hit
 ‑ else scrape and cache.

6 · Backend — WebSocket API & Message Format
6.1 Create server.py with WebSocket endpoint /ws.
6.2 Define JSON schema {bearing, image_url, altitude_ft, speed_kmh, aircraft_type}.
6.3 Implement periodic task: every 5 s run pipeline → send message when select_best_plane returns data.
6.4 Add structured logging (events.log, one line per push).

7 · Frontend — Static Assets
7.1 Create frontend/index.html with:
 ‑ <img id="direction‑arrow" src="arrow.png">
 ‑ <img id="plane-image">
 ‑ <audio id="brum-sound" src="brum.mp3"></audio>
 ‑ <p>Height: <span id="altitude-display"></span></p>
 ‑ same for speed & type.
7.2 Add frontend/style.css and pulse animation.
7.3 Add frontend/arrow.png and a placeholder plane‑placeholder.jpg.

8 · Frontend — JavaScript Logic
8.1 Create frontend/main.js.
 8.1.1 Implement requestOrientationPermission() + handleOrientation().
 8.1.2 Open WebSocket ws://<BACKEND_IP>:8000/ws.
 8.1.3 On message, parse JSON and:
  ‑ compute finalRotation = planeBearing – deviceHeading
  ‑ rotate arrow
  ‑ swap plane image
  ‑ update text fields
  ‑ play audio and trigger glow class (setTimeout 15 s).
8.2 Link JS & CSS in index.html.

9 · PWA Enhancements
9.1 Add manifest.json (as per guide).
9.2 Create icon.png 192×192.
9.3 Insert <meta name="apple-mobile-web-app-capable" content="yes">.

10 · Local Hosting & HTTPS
10.1 Add serve.py (simple http.server) to serve frontend/.
10.2 Expose both WebSocket (8000) and static (8080) ports on Mac Mini / Pi.
10.3 (Optional) Generate self‑signed cert and test wss://.

11 · iPad Setup (USER TESTING)
11.1 Open http://<BACKEND_IP>:8080 in Safari → “Add to Home Screen.”
11.2 Enable Guided Access (Settings → Accessibility).
11.3 Start Guided Access session and disable touch.

12 · Testing & QA
12.1 Unit‑test geometry helpers (pytest).
12.2 Simulate fake plane data to confirm frontend reaction.
12.3 Run end‑to‑end for 24 h; review events.log for errors.
12.4 Document known issues in README.

13 · Finishing Touches
13.1 Add .pre‑commit‑config.yaml (black, isort, flake8).
13.2 Write a brief “How to run” section in README.
13.3 Tag v0.1 release.
