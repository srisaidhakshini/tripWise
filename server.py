"""TripWise: small, dependency-free API and static app server."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = Path(os.environ.get("TRIPWISE_DB", ROOT / "tripwise.db"))
PORT = int(os.environ.get("PORT", "8000"))
UA = "TripWiseStudentProject/1.0 (educational travel planner)"
PLACE_CACHE = {}
CACHE_LOCK = threading.Lock()


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS itinerary (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, destination_id TEXT NOT NULL,
        name TEXT NOT NULL, country TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(owner, destination_id))""")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def nominatim_cities(query, count):
    """Fallback city search when the Open-Meteo geocoder is unreachable."""
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": query, "format": "jsonv2", "addressdetails": 1, "limit": min(count, 20), "featureType": "settlement", "accept-language": "en"})
    results = []
    for item in external_json(url, timeout=8):
        addr = item.get("address", {})
        results.append(destination({
            "id": f"osm{item.get('place_id')}", "name": item.get("name") or item.get("display_name", "").split(",")[0],
            "country": addr.get("country", ""), "country_code": addr.get("country_code", ""),
            "admin1": addr.get("state") or addr.get("region") or "",
            "latitude": float(item["lat"]), "longitude": float(item["lon"]),
            "population": 0, "feature_code": "PPLC" if item.get("addresstype") == "capital" else "",
            "timezone": ""}))
    return results


def external_json(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def osm_category(tags):
    tourism = tags.get("tourism", "")
    if tourism in ("museum", "gallery"):
        return "Culture"
    if tags.get("historic"):
        return "History"
    if tags.get("natural") in ("beach", "waterfall", "cave_entrance") or tags.get("leisure") in ("park", "garden"):
        return "Nature"
    if tags.get("amenity") == "place_of_worship":
        return "Spiritual"
    return "Sights"


WIKI_KINDS = (
    ("Museum", "Culture", ("museum", "gallery")),
    ("Temple", "Spiritual", ("temple", "church", "cathedral", "mosque", "basilica", "shrine", "gurdwara", "synagogue")),
    ("Beach", "Nature", ("beach",)),
    ("Park", "Nature", ("park", "garden", "zoo", "lake", "waterfall", "sanctuary", "reserve")),
    ("Monument", "History", ("fort", "castle", "palace", "monument", "memorial", "tomb", "ruins", "heritage", "historic", "lighthouse", "tower")),
    ("Attraction", "Sights", ("tourist", "attraction", "landmark", "market", "bridge", "square", "stadium", "aquarium", "theme")),
)


def wikipedia_places(lat, lon, radius):
    """Fallback when every Overpass server is busy: notable nearby Wikipedia articles."""
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "geosearch", "ggscoord": f"{lat}|{lon}",
        "ggsradius": min(radius, 10000), "ggslimit": 100, "prop": "coordinates|description|pageimages", "colimit": 100,
        "piprop": "thumbnail", "pithumbsize": 640})
    data = external_json(url, timeout=7)
    places = []
    for page in (data.get("query", {}).get("pages", {})).values():
        coords = (page.get("coordinates") or [{}])[0]
        desc = page.get("description", "")
        low = f"{page.get('title', '')} {desc}".lower()
        match = next(((k, c) for k, c, words in WIKI_KINDS if any(w in low for w in words)), None)
        if "coordinates" not in page:
            continue
        if not match:
            match = ("Notable place", "Sights")
        places.append({
            "id": f"wiki/{page['pageid']}", "name": page["title"], "kind": match[0], "category": match[1],
            "latitude": coords["lat"], "longitude": coords["lon"], "region": "", "country": "", "population": 0,
            "timezone": "", "description": desc[:1].upper() + desc[1:], "website": "", "wikipedia": f"en:{page['title']}",
            "osmUrl": "https://en.wikipedia.org/?curid=" + str(page["pageid"]), "dataSource": "wikipedia", "tags": {},
            "image": page.get("thumbnail", {}).get("source", "")})
    return places


def attach_images(places):
    """Add a Wikipedia thumbnail (`image`) to places that have a matching article."""
    wanted = {}
    for place in places:
        if place.get("image"):
            continue
        tag = place.get("wikipedia", "")
        title = tag[3:] if tag.startswith("en:") else ("" if ":" in tag else place["name"])
        if title:
            wanted.setdefault(title.replace("_", " "), []).append(place)
    titles = list(wanted)

    def fetch(batch):
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "redirects": 1, "prop": "pageimages",
            "piprop": "thumbnail", "pithumbsize": 640, "titles": "|".join(batch)})
        try:
            data = external_json(url, timeout=6).get("query", {})
        except Exception as error:
            print(f"Image lookup failed: {type(error).__name__}: {error}")
            return
        alias = {}
        for item in data.get("normalized", []) + data.get("redirects", []):
            alias[item["to"]] = item["from"]
        for page in data.get("pages", {}).values():
            thumb = page.get("thumbnail", {}).get("source")
            if not thumb:
                continue
            origin = page["title"]
            while origin in alias:
                origin = alias[origin]
            for place in wanted.get(origin, []) + wanted.get(page["title"], []):
                place["image"] = thumb

    batches = [titles[i:i + 40] for i in range(0, len(titles), 40)]
    threads = [threading.Thread(target=fetch, args=(b,)) for b in batches]
    for t in threads:
        t.start()
    for t in threads:
        t.join(8)


def nearby_places(lat, lon, radius):
    key = (round(lat, 3), round(lon, 3), radius)
    with CACHE_LOCK:
        cached = PLACE_CACHE.get(key)
        if cached and cached[0] > time.time():
            return cached[1]
    query = f'''[out:json][timeout:5][maxsize:30000000];
(
  nwr(around:{radius},{lat},{lon})["name"]["tourism"~"^(attraction|museum|gallery|viewpoint|zoo|theme_park|aquarium|artwork)$"];
  nwr(around:{radius},{lat},{lon})["name"]["historic"~"^(monument|memorial|castle|archaeological_site|ruins)$"];
  nwr(around:{radius},{lat},{lon})["name"]["leisure"~"^(park|garden)$"];
  nwr(around:{radius},{lat},{lon})["name"]["natural"~"^(beach|waterfall|cave_entrance)$"];
  nwr(around:{radius},{lat},{lon})["name"]["amenity"="place_of_worship"];
);
out center qt 120;'''
    raw = None
    last_error = "The place search servers did not respond."
    # The public Overpass instances can become saturated independently. Try a
    # separate global operator first, then Private.coffee (formerly Kumi),
    # then the main FOSSGIS instance.
    endpoints = (
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    )
    for endpoint in endpoints:
        req = urllib.request.Request(
            endpoint,
            data=urllib.parse.urlencode({"data": query}).encode(),
            headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                raw = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as error:
            last_error = f"OpenStreetMap search returned HTTP {error.code}."
            detail = error.read(400).decode("utf-8", errors="replace").strip().replace("\n", " ")
            print(f"Place search endpoint {endpoint} failed: HTTP {error.code} {detail[:240]}")
        except (URLError, TimeoutError) as error:
            last_error = "Could not connect to the OpenStreetMap place search service."
            print(f"Place search endpoint {endpoint} failed: {error}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            last_error = "The OpenStreetMap place search returned an unreadable response."
            print(f"Place search endpoint {endpoint} returned invalid JSON.")
        except Exception as error:
            last_error = "The OpenStreetMap place search is not responding right now."
            print(f"Place search endpoint {endpoint} failed: {type(error).__name__}: {error}")
    if raw is None:
        try:
            places = wikipedia_places(lat, lon, radius)
        except Exception as error:
            print(f"Wikipedia fallback failed: {type(error).__name__}: {error}")
            raise RuntimeError(last_error)
        if not places:
            raise RuntimeError(last_error)
        with CACHE_LOCK:
            PLACE_CACHE[key] = (time.time() + 300, places)
        return places
    places = []
    for element in raw.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name:en") or tags.get("name")
        if not name:
            continue
        point = element.get("center", element)
        place_lat, place_lon = point.get("lat"), point.get("lon")
        if place_lat is None or place_lon is None:
            continue
        tourism = tags.get("tourism", "")
        kind = tourism.replace("_", " ").title() if tourism else next((v.replace("_", " ").title() for k in ("historic", "natural", "leisure", "amenity") if (v := tags.get(k))), "Place")
        places.append({
            "id": f"{element.get('type')}/{element.get('id')}", "name": name,
            "kind": kind, "category": osm_category(tags),
            "latitude": place_lat, "longitude": place_lon,
            "region": tags.get("addr:suburb") or tags.get("addr:city") or "",
            "country": "", "population": 0, "timezone": "",
            "description": tags.get("description:en") or tags.get("description") or "",
            "website": tags.get("website") or tags.get("contact:website") or "",
            "wikipedia": tags.get("wikipedia") or "",
            "osmUrl": f"https://www.openstreetmap.org/{element.get('type')}/{element.get('id')}",
            "dataSource": "openstreetmap",
            "tags": tags, "image": "",
        })
    attach_images(places)
    with CACHE_LOCK:
        PLACE_CACHE[key] = (time.time() + 1800, places)
        if len(PLACE_CACHE) > 50:
            oldest = min(PLACE_CACHE, key=lambda item: PLACE_CACHE[item][0])
            PLACE_CACHE.pop(oldest, None)
    return places


def distance_km(lat1, lon1, lat2, lon2):
    from math import asin, cos, radians, sin, sqrt
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return round(6371 * 2 * asin(sqrt(a)), 1)


def destination(row):
    feature = row.get("feature_code", "") or ""
    population = int(row.get("population") or 0)
    kind = "Capital" if feature in ("PPLC", "PPLG") else ("Major city" if population >= 500000 else "Town")
    return {
        "id": str(row.get("id", "")), "name": row.get("name", ""),
        "country": row.get("country", ""), "countryCode": row.get("country_code", "").upper(),
        "region": row.get("admin1", ""), "latitude": row.get("latitude"),
        "longitude": row.get("longitude"), "population": population,
        "featureCode": feature, "kind": kind, "timezone": row.get("timezone", "")
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "TripWise/1.0"

    def log_message(self, *_):
        pass

    def send_json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def body_json(self):
        length = min(int(self.headers.get("Content-Length", "0")), 100_000)
        return json.loads(self.rfile.read(length) or b"{}")

    def owner(self):
        value = self.headers.get("X-TripWise-User", "")
        if not value or len(value) > 80 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in value):
            raise ValueError("A valid itinerary profile is required.")
        return value

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/api/health":
                return self.send_json(200, {"status": "ok"})
            if parsed.path == "/api/destinations":
                query = (params.get("q", [""])[0]).strip()
                if len(query) < 2:
                    return self.send_json(400, {"error": "Enter at least two characters to search."})
                count = min(max(int(params.get("count", ["20"])[0]), 1), 50)
                url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({"name": query, "count": count, "language": "en", "format": "json"})
                try:
                    data = external_json(url, timeout=5)
                    results = [destination(r) for r in data.get("results", [])]
                except Exception as error:
                    print(f"Open-Meteo geocoding failed ({type(error).__name__}: {error}); using Nominatim")
                    results = nominatim_cities(query, count)
                kind = params.get("kind", ["all"])[0]
                if kind != "all":
                    results = [r for r in results if r["kind"].lower().replace(" ", "-") == kind]
                sort = params.get("sort", ["relevance"])[0]
                if sort == "population":
                    results.sort(key=lambda r: r["population"], reverse=True)
                return self.send_json(200, {"results": results, "count": len(results), "source": "Open-Meteo Geocoding API"})
            if parsed.path == "/api/places":
                try:
                    lat = float(params.get("latitude", [""])[0])
                    lon = float(params.get("longitude", [""])[0])
                    radius = int(params.get("radius", ["15000"])[0])
                except (ValueError, IndexError):
                    return self.send_json(400, {"error": "Choose a valid city to search nearby places."})
                if not (-90 <= lat <= 90 and -180 <= lon <= 180 and 1000 <= radius <= 30000):
                    return self.send_json(400, {"error": "Search radius must be between 1 and 30 km."})
                try:
                    places = nearby_places(lat, lon, radius)
                except Exception as error:
                    print(f"Place search error: {type(error).__name__}: {error}")
                    return self.send_json(502, {"error": str(error) if isinstance(error, RuntimeError) else "The nearby-place service could not complete the search. Please retry in a moment."})
                city_name = params.get("city", [""])[0][:120]
                category = params.get("category", ["all"])[0]
                if category != "all":
                    places = [p for p in places if p["category"].lower() == category]
                for place in places:
                    place["distanceKm"] = distance_km(lat, lon, place["latitude"], place["longitude"])
                    place["nearCity"] = city_name
                    place["country"] = city_name
                sort = params.get("sort", ["distance"])[0]
                if sort == "name":
                    places.sort(key=lambda p: p["name"].casefold())
                else:
                    places.sort(key=lambda p: p["distanceKm"])
                source = "Wikipedia nearby landmarks" if places and places[0].get("dataSource") == "wikipedia" else "OpenStreetMap contributors via Overpass API"
                return self.send_json(200, {"results": places, "count": len(places), "source": source, "radius": radius})
            if parsed.path.startswith("/api/destinations/"):
                name = params.get("name", [""])[0].strip()
                try:
                    lat, lon = float(params.get("latitude", [""])[0]), float(params.get("longitude", [""])[0])
                except (ValueError, IndexError):
                    return self.send_json(400, {"error": "Destination coordinates are required."})
                if not name or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    return self.send_json(400, {"error": "A valid destination is required."})
                weather_url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({"latitude": lat, "longitude": lon, "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m", "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_probability_max", "timezone": "auto", "forecast_days": 5})
                weather = external_json(weather_url)
                return self.send_json(200, {"name": name, "weather": weather, "source": "Open-Meteo Forecast API"})
            if parsed.path == "/api/trips":
                owner = self.owner()
                with db() as con:
                    rows = con.execute("SELECT id, destination_id, name, country, payload, created_at FROM itinerary WHERE owner=? ORDER BY created_at DESC", (owner,)).fetchall()
                return self.send_json(200, {"items": [{**dict(r), "destination": json.loads(r["payload"])} for r in rows]})
            if parsed.path.startswith("/api/"):
                return self.send_json(404, {"error": "Endpoint not found."})
            return self.serve_static(parsed.path)
        except (ValueError, json.JSONDecodeError) as e:
            return self.send_json(400, {"error": str(e) or "Invalid request."})
        except Exception as e:
            print(f"API error: {type(e).__name__}: {e}")
            return self.send_json(502, {"error": f"The request could not be completed ({type(e).__name__}). Please retry in a moment."})

    def do_POST(self):
        if self.path.rstrip("/") != "/api/trips":
            return self.send_json(404, {"error": "Endpoint not found."})
        try:
            owner = self.owner()
            data = self.body_json()
            dest = data.get("destination")
            if not isinstance(dest, dict) or not dest.get("id") or not dest.get("name"):
                return self.send_json(400, {"error": "A valid destination is required."})
            payload = json.dumps(dest, ensure_ascii=False)
            item_id = str(uuid.uuid4())
            with db() as con:
                con.execute("INSERT OR IGNORE INTO itinerary (id, owner, destination_id, name, country, payload) VALUES (?, ?, ?, ?, ?, ?)", (item_id, owner, str(dest["id"]), str(dest["name"])[:160], str(dest.get("country", ""))[:120], payload))
                row = con.execute("SELECT id, destination_id, name, country, payload, created_at FROM itinerary WHERE owner=? AND destination_id=?", (owner, str(dest["id"]))).fetchone()
            result = {**dict(row), "destination": json.loads(row["payload"])}
            return self.send_json(201, {"item": result})
        except (ValueError, json.JSONDecodeError) as e:
            return self.send_json(400, {"error": str(e) or "Invalid request."})
        except Exception as e:
            print(f"API error: {type(e).__name__}: {e}")
            return self.send_json(500, {"error": "Could not save this destination."})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        item_id = parsed.path.removeprefix("/api/trips/")
        if not item_id or "/" in item_id:
            return self.send_json(404, {"error": "Itinerary item not found."})
        try:
            owner = self.owner()
            with db() as con:
                cur = con.execute("DELETE FROM itinerary WHERE id=? AND owner=?", (item_id, owner))
            if cur.rowcount == 0:
                return self.send_json(404, {"error": "Itinerary item not found."})
            return self.send_json(200, {"deleted": True})
        except ValueError as e:
            return self.send_json(400, {"error": str(e)})

    def serve_static(self, path):
        requested = (ROOT / "static" / path.lstrip("/")).resolve()
        static_root = (ROOT / "static").resolve()
        if static_root not in requested.parents and requested != static_root:
            self.send_error(403)
            return
        if requested.is_dir():
            requested = requested / "index.html"
        if not requested.exists():
            requested = static_root / "index.html"
        types = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml"}
        data = requested.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", types.get(requested.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    with db() as connection:
        connection.execute("PRAGMA journal_mode=WAL")
    print(f"TripWise running at http://localhost:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
