# TripWise

TripWise is a full stack travel planner for discovering places, checking the local forecast, and saving destinations to a personal itinerary.

## Chosen track

**Track 3 — Full-Stack Development**

## What it includes

- Find a city with the Open-Meteo Geocoding API, then discover nearby mapped places through OpenStreetMap Overpass, with Wikipedia geosearch as a fallback.
- Browse sights, culture, history, nature, and spiritual places within a 5 km, 15 km, or 30 km radius; sort by distance or name.
- Open a destination for location details and a live five-day weather forecast.
- Add places to a personal trip, view the saved list, and remove items.
- Save itinerary items in SQLite. A browser profile ID keeps each browser's list separate and the list survives refreshes and server restarts.
- Responsive Explore and My trip views, with loading, empty, validation, and request error feedback.

## Technology

- Python 3.10+ standard library HTTP server and `sqlite3`
- HTML, CSS, and vanilla JavaScript
- Open-Meteo Geocoding and Forecast APIs; OpenStreetMap Overpass and Wikipedia geosearch for places
- SQLite database (`tripwise.db` by default)

No API key or third-party Python package is required.

## Run locally

1. Install Python 3.10 or newer.
2. On Windows, double-click `Run TripWise.bat`. It starts a fresh server on port `8011` and opens the app. Keep its window open while using TripWise; API errors are printed there.
3. On other systems, from the project folder, run:

   ```bash
   python server.py
   ```

   Then open [http://localhost:8000](http://localhost:8000).

Set `PORT` to change the HTTP port. Set `TRIPWISE_DB` to choose a different SQLite file path. The database is created automatically on first run.

## API

The frontend and API are served from the same origin. Itinerary requests include the `X-TripWise-User` header, generated and stored by the browser.

### Find a city

`GET /api/destinations?q=Kyoto&kind=all&sort=relevance`

Returns city matches with coordinates. The app uses a selected match as the center for nearby place discovery.

Example response:

```json
{
  "results": [
    {
      "id": "1857910",
      "name": "Kyoto",
      "country": "Japan",
      "countryCode": "JP",
      "region": "Kyoto",
      "latitude": 35.02107,
      "longitude": 135.75385,
      "population": 1463723,
      "featureCode": "PPLA",
      "kind": "Major city",
      "timezone": "Asia/Tokyo"
    }
  ],
  "count": 1,
  "source": "Open-Meteo Geocoding API"
}
```

### Search nearby places

`GET /api/places?latitude=13.08&longitude=80.27&city=Chennai&radius=15000&category=all&sort=distance`

Radius is limited to 1–30 km. Categories: `all`, `sights`, `culture`, `history`, `nature`, `spiritual`. Sort: `distance` or `name`. Results include the place name, OSM feature type, coordinates, distance from the selected city centre, and an OpenStreetMap link.

### Place details and weather

`GET /api/destinations/{id}?name=Kyoto&latitude=35.02&longitude=135.75`

Returns the selected destination name and the current conditions plus five-day forecast from Open-Meteo.

### View itinerary

`GET /api/trips` with `X-TripWise-User: <browser-profile-id>`

Example response:

```json
{
  "items": [
    {
      "id": "<saved-item-id>",
      "destination_id": "1857910",
      "name": "Kyoto",
      "country": "Japan",
      "destination": { "id": "1857910", "name": "Kyoto", "country": "Japan" }
    }
  ]
}
```

### Add an itinerary item

`POST /api/trips` with `X-TripWise-User: <browser-profile-id>` and JSON body:

```json
{
  "destination": {
    "id": "1857910",
    "name": "Kyoto",
    "country": "Japan",
    "latitude": 35.02,
    "longitude": 135.75
  }
}
```

Returns `201` and the saved item. Re-adding the same destination for the same browser profile returns its existing saved item.

### Remove an itinerary item

`DELETE /api/trips/{saved-item-id}` with `X-TripWise-User: <browser-profile-id>`

Returns `200 {"deleted": true}` or `404` when the item does not exist in that profile.

Invalid or incomplete inputs return `400` with an `error` message. An unavailable upstream destination service returns `502` with a user-facing error.

## External data and attribution

- [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) supplies city search results.
- [Open-Meteo Forecast API](https://open-meteo.com/en/docs) supplies current conditions and forecast details.
- [OpenStreetMap data](https://www.openstreetmap.org/copyright), queried through the [Overpass API](https://dev.overpass-api.de/overpass-doc/en/), supplies nearby attractions, museums, historic places, parks, beaches, and places of worship. The app tries three public Overpass endpoints; if all are unavailable, it uses [Wikipedia's nearby-page search](https://www.mediawiki.org/wiki/API:Geosearch) to find notable landmarks.
- Wikipedia article titles and summaries are provided by Wikipedia contributors under [CC BY-SA](https://en.wikipedia.org/wiki/Wikipedia:Text_of_the_Creative_Commons_Attribution-ShareAlike_4.0_International_License); the app links each result to its article. This fallback contains notable article locations and may not include every mapped place.
- Open-Meteo data is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The app links to the data provider and identifies its API in the interface.
- OpenStreetMap data is licensed under the [ODbL](https://www.openstreetmap.org/copyright); attribution appears in the app. Nearby results are limited to a city-centred radius and depend on what contributors have mapped. The public Overpass service can throttle requests; the app caches each area for 30 minutes.
- The free Open-Meteo API is for non-commercial use and has rate limits. See the provider's current [terms](https://open-meteo.com/en/terms) before deploying or using this project beyond educational, non-commercial use.

## Deployment notes

Run `python server.py` as the web service start command and expose the configured `PORT`. Attach persistent storage and set `TRIPWISE_DB` to a file on that storage; otherwise SQLite data may be lost when a hosting instance is replaced. For a public deployment, configure the host's persistent disk before inviting users to save plans.

## Project structure

```text
server.py                     HTTP API, upstream API client, and SQLite persistence
Run TripWise.bat              Windows launcher (opens http://127.0.0.1:8011)
static/index.html             Explore and My trip views
static/app.js                 Search, place details, weather, and itinerary flow
static/styles.css             Base layout and responsive components
static/discovery.css          Search-first discovery layout and breakpoints
static/theme.css              Dark theme and coastal background treatment
static/nearby.css             Nearby-place controls and image cards
static/motion.css             Card depth and scroll reveal animations
static/motion.js              Motion behavior
static/mark.svg               Compass logo and browser favicon
static/images/tripwise-coast.png  Dashboard background image
```

## Submission checklist

- [ ] Publish this repository as public and add its link.
- [ ] Deploy the app and add the live link.
- [ ] Capture Explore, destination details, My trip, mobile, search/filter, populated trip, and empty states in a PDF.
- [ ] Rename the submission PDF to `<register no>_<Track>` as specified in the task brief.
