# TripWise

**A small travel companion for finding places worth a detour.** Search a city, explore nearby places, check the forecast, and save ideas to a personal trip.

**Built by:** Sri Saidhakshini Venkatesan  
**Chosen track:** Track 3 — Full-Stack Development

## What you can do

- Search for cities and neighbourhoods.
- Discover nearby attractions, cultural and historic places, parks, and places of worship.
- Filter places by interest, choose a search radius, and sort the results.
- Open a place for more details and a five-day local forecast.
- Save places to **My Trip** and remove them whenever plans change.
- Use the app on desktop or mobile. Your saved list stays in the local SQLite database.

## How it is built

| Part | Technology |
| --- | --- |
| Web app | HTML, CSS, and vanilla JavaScript |
| API and server | Python 3.10+ standard library |
| Database | SQLite (`tripwise.db` by default) |
| City search and weather | Open-Meteo Geocoding and Forecast APIs |
| Nearby places | OpenStreetMap Overpass API, with Wikipedia geosearch as a fallback |

No API key or third-party Python package is needed to run the project.

## Run it on your computer

### Windows

1. Install Python 3.10 or newer.
2. Double-click **Run TripWise.bat**.
3. The app opens at [http://127.0.0.1:8011](http://127.0.0.1:8011). Keep the terminal window open while using it; server and API messages appear there.

### Other systems

From the project folder, run:

```bash
python server.py
```

Then visit [http://localhost:8000](http://localhost:8000).

## Database and configuration

The server creates `tripwise.db` automatically the first time it runs. The browser gives each profile its own saved trip, so the list remains available after refreshes and server restarts.

- `PORT` changes the web server port. The default is `8000`; the Windows launcher uses `8011`.
- `TRIPWISE_DB` sets a different SQLite database file path.

For a hosted deployment, set `TRIPWISE_DB` to a file on persistent storage. Otherwise, saved trips may be lost when the hosting service replaces its instance.

## API guide

The web app and API are served from the same origin. Trip requests include an `X-TripWise-User` header so each browser profile has a separate itinerary.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/destinations?q=Kyoto` | Find matching cities and return their coordinates. Optional `kind` and `sort` filters are supported. |
| `GET /api/places?latitude=13.08&longitude=80.27&city=Chennai&radius=15000&category=all&sort=distance` | Find nearby mapped places. Radius is limited to 1–30 km. Categories: `all`, `sights`, `culture`, `history`, `nature`, `spiritual`; sort by `distance` or `name`. |
| `GET /api/destinations/{id}?name=Kyoto&latitude=35.02&longitude=135.75` | Get destination details and the current conditions plus five-day forecast. |
| `GET /api/trips` | View the current browser profile's saved places. Send `X-TripWise-User: <browser-profile-id>`. |
| `POST /api/trips` | Add a place. Send the same header and a JSON body containing a `destination` object with its id, name, country, latitude, and longitude. Returns `201`; adding a place twice returns the existing saved item. |
| `DELETE /api/trips/{saved-item-id}` | Remove a saved item from the current profile. Returns `200` when removed or `404` if it is not in that profile. |

Invalid inputs return `400` with an error message. If an upstream place service is unavailable, the API returns `502` with a user-facing message.

## Data sources and usage notes

- [Open-Meteo](https://open-meteo.com/) provides city search and weather forecasts. Its free API is for non-commercial use and has rate limits.
- [OpenStreetMap](https://www.openstreetmap.org/copyright) provides map data through public Overpass servers. The app credits contributors and caches nearby searches for 30 minutes. Public servers can be busy, so a search may occasionally need a retry.
- [Wikipedia](https://www.mediawiki.org/wiki/API:Geosearch) provides notable nearby landmarks when mapped place search is unavailable. Wikipedia content is linked to its articles and remains subject to the applicable attribution and reuse terms.

Please review each provider's current terms before using the app commercially or serving substantial traffic.

## Project files

```text
server.py                         Python server, API, and SQLite persistence
Run TripWise.bat                  Windows launcher
static/index.html                 Explore and My Trip views
static/app.js                     Search, place details, weather, and itinerary
static/styles.css                 Base layout and responsive components
static/discovery.css              Discovery layout and responsive breakpoints
static/theme.css                  Dark theme and coastal background styling
static/nearby.css                 Nearby-place controls and cards
static/motion.css, motion.js      Card depth and scroll animations
static/mark.svg                   Compass logo and browser favicon
static/images/tripwise-coast.png  Dashboard background image
```

## Submission checklist

- [ ] Add the public GitHub repository link.
- [ ] Add the live deployment link.
- [ ] Include a PDF with Explore, Destination Details, My Trip, mobile, search/filter, populated-trip, and empty-state screenshots.
- [ ] Name the PDF `<register no>_Track 3.pdf`.
