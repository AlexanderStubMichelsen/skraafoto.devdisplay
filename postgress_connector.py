import os
import json
import math
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from pyproj import CRS
from flask import Flask, jsonify, send_from_directory, request
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

if not PLAN_GPKG_FILE.exists():
    raise FileNotFoundError(f"GeoPackage file not found: {PLAN_GPKG_FILE}")

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
    app.run("0.0.0.0", port=5000, debug=True)
