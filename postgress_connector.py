import os
import json
import math
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl, quote

import requests
from pyproj import CRS
from flask import Flask, Response, jsonify, send_from_directory, request
from flask_cors import CORS
from dotenv import load_dotenv

# Optional imports
try:
    import geopandas as gpd  # type: ignore
    import pandas as pd  # type: ignore
    from shapely.geometry import mapping  # type: ignore
except ImportError:
    gpd = None  # type: ignore
    pd = None  # type: ignore
    mapping = None  # type: ignore


# ───────────────────────────────
# Environment & logging
# ───────────────────────────────
if os.path.exists("/var/www/skraafoto/.env"):
    load_dotenv(dotenv_path="/var/www/skraafoto/.env")
elif os.path.exists(".env.flask"):
    load_dotenv(dotenv_path=".env.flask")
else:
    load_dotenv()

# API credentials live only on the server. The deploy workflow writes them to
# /etc/skraafoto/secrets.env (outside the web root); locally, use .env.flask.
if os.path.exists("/etc/skraafoto/secrets.env"):
    load_dotenv(dotenv_path="/etc/skraafoto/secrets.env", override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

wgs84 = CRS("epsg:4326")
etrs89_utm32n = CRS("epsg:25832")


# ───────────────────────────────
# GeoPackage setup
# ───────────────────────────────
def _resolve_default_gpkg_path() -> Optional[Path]:
    """Resolve GeoPackage path from environment variables or fallback."""
    candidate = (
        os.getenv("PLAN_GPKG_PATH")
        or os.getenv("VITE_PLAN_GPKG_PATH")
        or "plandata.gpkg"
    )
    candidate_path = Path(candidate).expanduser()
    if not candidate_path.is_absolute():
        candidate_path = Path.cwd() / candidate_path
    return candidate_path


PLAN_GPKG_FILE = _resolve_default_gpkg_path()

# ✅ If the GeoPackage is not deployed with the app (too large for free plan),
# download it from GitHub LFS the first time the app starts.
if not PLAN_GPKG_FILE.exists():
    GPKG_URL = "https://github.com/AlexanderStubMichelsen/skraafoto.devdisplay/raw/Azure-SQLite-GeoPackage/plandata.gpkg"
    logger.info("📦 GeoPackage not found locally, downloading from GitHub LFS...")
    resp = requests.get(GPKG_URL)
    resp.raise_for_status()
    PLAN_GPKG_FILE.write_bytes(resp.content)
    logger.info(f"✅ Downloaded GeoPackage to {PLAN_GPKG_FILE}")

if gpd is None:
    raise ImportError("GeoPandas is required for GeoPackage mode")

logger.info("✅ Using local GeoPackage: %s", PLAN_GPKG_FILE)

# ───────────────────────────────
# Flask app setup
# ───────────────────────────────
app = Flask(__name__, static_folder="dist", static_url_path="")
app.config["DEBUG"] = True
CORS(app)

app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
app.config["JSON_SORT_KEYS"] = False


# ───────────────────────────────
# JSON sanitization helper
# ───────────────────────────────
def _sanitize_for_json(obj):
    """Recursively replace NaN/inf values with None to make valid JSON."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


# ───────────────────────────────
# GeoPackage utilities
# ───────────────────────────────
@lru_cache(maxsize=None)
def _load_gpkg_layer(layer_name: str):
    """Safely load a layer by name from the GeoPackage."""
    logger.info("Loading GeoPackage layer '%s'...", layer_name)
    try:
        return gpd.read_file(PLAN_GPKG_FILE, layer=layer_name)
    except ValueError:
        raise FileNotFoundError(f"Layer '{layer_name}' not found in {PLAN_GPKG_FILE}")


def _create_geojson_feature(row: "pd.Series", color: Optional[str] = None) -> Dict[str, Any]:
    """Convert a GeoDataFrame row to GeoJSON."""
    properties = {col: row[col] for col in row.index if col != "geometry"}
    if color:
        properties["color"] = color
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": mapping(row["geometry"]),
    }


# ───────────────────────────────
# Routes
# ───────────────────────────────
@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health_check():
    """Basic health check."""
    return jsonify({"status": "ok", "message": "Flask + GeoPackage online"}), 200


@app.route("/toggle/<layer>", methods=["GET"])
@app.route("/api/toggle/<layer>", methods=["GET"])
def toggle_layer(layer: str):
    """Return GeoJSON for a given GeoPackage layer."""
    try:
        gdf = _load_gpkg_layer(layer)
    except FileNotFoundError as e:
        logger.error(e)
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        logger.error(f"Failed to load layer '{layer}': {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    if gdf.empty:
        return jsonify({"status": "error", "message": f"No data in {layer}"}), 404

    # Assign colors for visualization
    colors = ["red", "blue", "green", "yellow", "purple", "orange"]
    features = []
    for i, row in gdf.iterrows():
        color = colors[i % len(colors)]
        features.append(_create_geojson_feature(row, color=color))

    result = {"type": "FeatureCollection", "features": features}
    return jsonify(_sanitize_for_json(result))


@app.route("/get_plandata/<address>", methods=["GET"])
@app.route("/api/get_plandata/<address>", methods=["GET"])
def get_plandata(address: str):
    """Return kommuneplan + lokalplan for given address string (case-insensitive match)."""
    try:
        kommune_layers = [
            "theme_pdk_kommuneplan_oversigt_vedtaget_v",
            "theme_pdk_kommuneplan_oversigt_forslag_v",
        ]
        lokal_layers = [
            "theme_pdk_lokalplan_vedtaget_v",
            "theme_pdk_lokalplan_forslag_v",
        ]

        kommune_match = []
        lokal_match = []

        for layer in kommune_layers:
            gdf = _load_gpkg_layer(layer)
            if "adgangsadressebetegnelse" not in gdf.columns:
                continue
            mask = gdf["adgangsadressebetegnelse"].astype(str).str.contains(address, case=False, na=False)
            kommune_match.extend(gdf[mask].to_dict("records"))

        for layer in lokal_layers:
            gdf = _load_gpkg_layer(layer)
            if "adgangsadressebetegnelse" not in gdf.columns:
                continue
            mask = gdf["adgangsadressebetegnelse"].astype(str).str.contains(address, case=False, na=False)
            lokal_match.extend(gdf[mask].to_dict("records"))

        result = {
            "kommuneplan": kommune_match,
            "lokalplan": lokal_match,
        }

        return jsonify(_sanitize_for_json(result))

    except Exception as e:
        logger.error(f"Error reading from GeoPackage: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ───────────────────────────────
# API proxy: keeps Dataforsyningen/Datafordeler credentials server-side
# ───────────────────────────────
DF_TOKEN = os.getenv("DATAFORSYNINGEN_TOKEN") or os.getenv("VITE_API_TOKEN") or ""
DHM_USERNAME = os.getenv("DHM_USERNAME") or os.getenv("VITE_API_DHM_TOKENA") or ""
DHM_PASSWORD = os.getenv("DHM_PASSWORD") or os.getenv("VITE_API_DHM_TOKENB") or ""

STAC_BASE = "https://api.dataforsyningen.dk/rest/skraafoto_api/v1.0"
GSEARCH_BASE = "https://api.dataforsyningen.dk/rest/gsearch/v2.0"
ADGANGSADRESSER_URL = "https://api.dataforsyningen.dk/adgangsadresser"
DHM_KOTER_URL = "https://services.datafordeler.dk/DHMTerraen/DHMKoter/1.0.0/GEOREST/HentKoter"
DHM_WCS_URL = "https://services.datafordeler.dk/DHMNedboer/dhm_wcs/1.0.0/WCS"

# Only these hosts may be fetched through /api/proxy/file (prevents an open proxy).
FILE_PROXY_HOSTS = {"api.dataforsyningen.dk", "cdn.dataforsyningen.dk"}
_CREDENTIAL_PARAMS = {"token", "username", "password"}
_PASSTHROUGH_HEADERS = ("Content-Type", "Content-Length", "Content-Range",
                        "Accept-Ranges", "Cache-Control", "ETag", "Last-Modified")
_TIMEOUT = 30

if not DF_TOKEN:
    logger.warning("DATAFORSYNINGEN_TOKEN is not set; skraafoto API calls will fail")
if not (DHM_USERNAME and DHM_PASSWORD):
    logger.warning("DHM_USERNAME/DHM_PASSWORD are not set; elevation calls will fail")


def _client_params() -> list:
    """Query params from the browser, minus any credential fields."""
    return [(k, v) for k, v in request.args.items(multi=True)
            if k.lower() not in _CREDENTIAL_PARAMS]


def _strip_credentials(url: str) -> str:
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k.lower() not in _CREDENTIAL_PARAMS]
    return urlunsplit(parts._replace(query=urlencode(query)))


def _proxy_base() -> str:
    # Relative on purpose: behind Apache/Azure TLS termination request.host_url would be
    # http://, which browsers block as mixed content on the https:// site.
    return "/api/proxy"


def _rewrite_hrefs(obj, proxy_base: str):
    """Point STAC links at this proxy and strip any token Dataforsyningen echoes back."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "href" and isinstance(v, str):
                clean = _strip_credentials(v)
                if clean.startswith(STAC_BASE):
                    out[k] = proxy_base + "/stac" + clean[len(STAC_BASE):]
                elif urlsplit(clean).hostname in FILE_PROXY_HOSTS:
                    out[k] = proxy_base + "/file?url=" + quote(clean, safe="")
                else:
                    out[k] = clean
            else:
                out[k] = _rewrite_hrefs(v, proxy_base)
        return out
    if isinstance(obj, list):
        return [_rewrite_hrefs(v, proxy_base) for v in obj]
    return obj


def _relay(upstream: requests.Response) -> Response:
    # requests has already decompressed the body, so let Flask compute Content-Length.
    headers = {h: upstream.headers[h] for h in _PASSTHROUGH_HEADERS
               if h in upstream.headers and h != "Content-Length"}
    return Response(upstream.content, status=upstream.status_code, headers=headers)


def _json_relay(upstream: requests.Response) -> Response:
    """Relay a JSON response with hrefs rewritten; fall back to raw relay for non-JSON."""
    try:
        data = upstream.json()
    except ValueError:
        return _relay(upstream)
    return jsonify(_rewrite_hrefs(data, _proxy_base())), upstream.status_code


@app.route("/api/proxy/stac", defaults={"subpath": ""}, methods=["GET"])
@app.route("/api/proxy/stac/<path:subpath>", methods=["GET"])
def proxy_stac(subpath: str):
    url = f"{STAC_BASE}/{subpath}" if subpath else STAC_BASE
    upstream = requests.get(url, params=_client_params() + [("token", DF_TOKEN)], timeout=_TIMEOUT)
    return _json_relay(upstream)


@app.route("/api/proxy/gsearch/<path:subpath>", methods=["GET"])
def proxy_gsearch(subpath: str):
    upstream = requests.get(f"{GSEARCH_BASE}/{subpath}", params=_client_params(),
                            headers={"token": DF_TOKEN}, timeout=_TIMEOUT)
    return _relay(upstream)


@app.route("/api/proxy/adgangsadresser", methods=["GET"])
def proxy_adgangsadresser():
    upstream = requests.get(ADGANGSADRESSER_URL, params=_client_params(),
                            headers={"token": DF_TOKEN}, timeout=_TIMEOUT)
    return _relay(upstream)


@app.route("/api/proxy/dhm/koter", methods=["GET"])
def proxy_dhm_koter():
    params = _client_params() + [("username", DHM_USERNAME), ("password", DHM_PASSWORD)]
    return _relay(requests.get(DHM_KOTER_URL, params=params, timeout=_TIMEOUT))


@app.route("/api/proxy/dhm/wcs", methods=["GET"])
def proxy_dhm_wcs():
    params = _client_params() + [("username", DHM_USERNAME), ("password", DHM_PASSWORD)]
    return _relay(requests.get(DHM_WCS_URL, params=params, timeout=_TIMEOUT))


@app.route("/api/proxy/file", methods=["GET", "HEAD"])
def proxy_file():
    """Stream an image (COG) from Dataforsyningen, passing Range through for tiled reads."""
    target = request.args.get("url", "")
    parts = urlsplit(target)
    if parts.scheme != "https" or parts.hostname not in FILE_PROXY_HOSTS:
        return jsonify({"status": "error", "message": "URL not allowed"}), 400

    query = parse_qsl(parts.query, keep_blank_values=True) + [("token", DF_TOKEN)]
    url = urlunsplit(parts._replace(query=urlencode(query)))
    # identity encoding keeps Content-Length/Content-Range byte-accurate for range reads
    headers = {"Accept-Encoding": "identity"}
    if "Range" in request.headers:
        headers["Range"] = request.headers["Range"]

    upstream = requests.request(request.method, url, headers=headers, stream=True, timeout=_TIMEOUT)
    out_headers = {h: upstream.headers[h] for h in _PASSTHROUGH_HEADERS if h in upstream.headers}
    body = upstream.iter_content(chunk_size=64 * 1024) if request.method == "GET" else b""
    return Response(body, status=upstream.status_code, headers=out_headers, direct_passthrough=True)


# ───────────────────────────────
# React frontend fallback
# ───────────────────────────────
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path):
    """Serve the React frontend build."""
    static_folder = Path(app.static_folder or "dist")
    requested_path = static_folder / path

    if path and requested_path.is_file():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


# ───────────────────────────────
# Entrypoint
# ───────────────────────────────
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
