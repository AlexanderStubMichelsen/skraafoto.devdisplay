import json
import os
import logging
from dotenv import load_dotenv
from pyproj import CRS, Proj, transform

from flask import Flask, request, jsonify
from flask_compress import Compress
from flask_cors import CORS
import json
import psycopg2 # type: ignore
from flask import jsonify # type: ignore
load_dotenv()
wgs84 = CRS('epsg:4326')  # WGS84
etrs89_utm32n = CRS('epsg:25832')  # ETRS89 / UTM zone 32N


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)
Compress(app)
app.config["DEBUG"] = True
CORS(app)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Flask app is running'}), 200

# Database connection with retry logic
def get_db_connection():
    dbconn = {'database': os.getenv("db"),
              'user': os.getenv("db_user"),
              'host': os.getenv("db_host"),
              'password': os.getenv("db_password"),
              'port': os.getenv("db_port")}
    
    try:
        conn = psycopg2.connect(**dbconn)
        return conn
    except psycopg2.DatabaseError as e:
        logger.error(f"Database connection error: {e}")
        logger.error(f"Connection params: {dbconn}")
        return None

# Initialize database connection
try:
    postgress_connector = get_db_connection()
    if postgress_connector:
        pg_cur = postgress_connector.cursor()
    else:
        pg_cur = None
        logger.warning("Database connection failed, some endpoints may not work")
except Exception as e:
    logger.error(f"Database initialization error: {e}")
    pg_cur = None

if __name__ == '__main__':
    app.run("0.0.0.0", port="5000", debug=True)

@app.route('/in_polygon/<point_string>/<polygon_string>', methods=['GET'])
def in_polygon(point_string, polygon_string):
    logger.info(f"point: {point_string}")
    logger.info(f"polygon: {polygon_string}")
    try:
        point = point_string.strip('()').replace(",", " ")
        pointList = [float(point) for point in polygon_string.strip('[]').replace("(", "").replace(")", "").split(",")]
        tupleList = list(zip(pointList[::2], pointList[1::2]))
        return is_in_polygon(point, tupleList)
    except Exception as e:
        logger.error(f"Error processing in_polygon request: {e}")
        return jsonify({'status': 'error', 'message': 'An error occurred while processing the request.'}), 405
    
def is_in_polygon(point, polygon):
    try:
        query = """
                SELECT ST_CoveredBy(ST_GeomFromText('POINT({})'), ST_GeomFromText('POLYGON(({}))'));
               """
        polyString = ",".join(f"{x} {y}" for x, y in polygon)
        query = query.format(point, polyString)
        pg_cur.execute(query)
        data = pg_cur.fetchall()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error executing is_in_polygon query: {e}")
        return jsonify({'status': 'error', 'message': 'An error occurred while querying the database.'}), 500

@app.route('/add_polygon_collection/<collection_name>', methods=['PUT'])
def add_polygon_collection(collection_name):    
    # Check if the collection_name is already present
    if is_collection_present(collection_name):
        message = f"Collection '{collection_name}' already exists."
        logger.warning(message)
        return jsonify({'status': 'error', 'message': message}), 409
    
    # Process the request
    try:
        polygons = request.json
        logger.info(f"Polygons data: {polygons}")
        logger.info(f"Collection name: {collection_name}")
        
        insert_polygon(collection_name, polygons)
        
        return jsonify({'status': 'success', 'message': 'Polygon collection added successfully.'}), 201
    except Exception as e:
        logger.error(f"Error inserting polygon collection: {e}")
        return jsonify({'status': 'error', 'message': 'An error occurred while adding the polygon collection.'}), 500


def is_collection_present(collection_name):
     # Query to check for the existence of the collection_name
    query = "SELECT EXISTS (SELECT 1 FROM skraafoto.polygons WHERE group_name = %s);"
    pg_cur.execute(query, (collection_name,))
        
    # Fetch the result
    exists = pg_cur.fetchone()[0]

    return exists

def insert_polygon(collection_name, polygons):
    polygons_string = "ST_MPolyFromText(\'MULTIPOLYGON(("
    for polygon in polygons:
        polygon_string = "("
        for point in polygon:
            transformed_point = transform(etrs89_utm32n, wgs84, point[0], point[1])
            polygon_string += f"{transformed_point[0]} {transformed_point[1]},"
        polygon_string = polygon_string[:-1]
        polygon_string += ")"
        polygons_string += polygon_string + ","
    polygons_string = polygons_string[:-1]
    polygons_string += "))\')"
    logger.info(f"polygons as part of postgis insert string:{polygons_string}")
    insert = f"""
                INSERT INTO skraafoto.polygons (group_name, multi_polygon)
                VALUES ('{collection_name}', {polygons_string});
             """
    logger.info(insert)
    pg_cur.execute(insert)
    postgress_connector.commit()

@app.route('/get_plandata/<address>')
def get_plandata(address):
    if pg_cur is None:
        return jsonify({
            'status': 'error', 
            'message': 'Database not available. Please start PostgreSQL server.'
        }), 503
    
    # TODO: input validation, currently u can proboly sql inject
    try:
        query_komuneplan = f"""
                           SELECT id,doklink, gml_id, ST_AsGeoJSON(ST_CurveToLine(geometri))
                           FROM plandata.theme_pdk_kommuneplan_oversigt_vedtaget_v kv 
                           WHERE id = (SELECT plan_id FROM plandata.komuneplan_for_adresse k WHERE k.adgangsadressebetegnelse LIKE '%{address}%' limit 1)
                           union 
                           SELECT id,doklink, gml_id, ST_AsGeoJSON(ST_CurveToLine(geometri))
                           FROM plandata.theme_pdk_kommuneplan_oversigt_forslag_v kf 
                           WHERE  id = (SELECT plan_id FROM plandata.komuneplan_for_adresse k WHERE k.adgangsadressebetegnelse LIKE '%{address}%' limit 1)
                           """
        query_lokalplan = f"""
                           SELECT id,doklink, gml_id, ST_AsGeoJSON(ST_CurveToLine(geometri))
                           FROM plandata.theme_pdk_lokalplan_vedtaget_v lv 
                           WHERE  id = (SELECT plan_id FROM plandata.lokalplan_for_adresse l WHERE l.adgangsadressebetegnelse LIKE '%{address}%' limit 1)
                           union 
                           SELECT id,doklink, gml_id, ST_AsGeoJSON(ST_CurveToLine(geometri))
                           FROM plandata.theme_pdk_lokalplan_forslag_v lf 
                           WHERE  id = (SELECT plan_id FROM plandata.lokalplan_for_adresse l WHERE l.adgangsadressebetegnelse LIKE '%{address}%' limit 1)
                           """
        
        pg_cur.execute(query_komuneplan)
        komuneplan_data = pg_cur.fetchone()
        pg_cur.execute(query_lokalplan)
        lokalplan_data  = pg_cur.fetchone()

        # Create GeoJSON Feature Collection with color property
        komune_geojson_features = []
        if(komuneplan_data):
            komune_geojson_features.append({
                "type": "Feature",
                "properties": {
                    "id": komuneplan_data[0],
                    "doklink": komuneplan_data[1],
                    "gml_id": komuneplan_data[2],
                    
                },
                "geometry": json.loads(komuneplan_data[3])  # Geometry remains in EPSG:25832
            })
        komune_geojson = {
            "type": "FeatureCollection",
            "features": komune_geojson_features
        }

        # Create GeoJSON Feature Collection for lokalplans
        lokal_geojson_features = []
        if(lokalplan_data):
            lokal_geojson_features.append({
                "type": "Feature",
                "properties": {
                    "id": lokalplan_data[0],
                    "doklink": lokalplan_data[1],
                    "gml_id": lokalplan_data[2],
                },
                "geometry": json.loads(lokalplan_data[3])  # Geometry remains in EPSG:25832
            })

        lokal_geojson = {
            "type": "FeatureCollection",
            "features": lokal_geojson_features
        }
    except Exception as e:
        logger.error(f"Error executing is_in_polygon query: {e}")
        return jsonify({'status': 'error', 'message': 'An error occurred while querying the database.'}), 500
    
    return jsonify({'komuneplan': komune_geojson, 'lokalplan':lokal_geojson})

@app.route('/toggle/<feature>', methods=['GET'])
def toggle_feature(feature):
    if pg_cur is None:
        return jsonify({
            'status': 'error', 
            'message': 'Database not available. Please start PostgreSQL server.'
        }), 503
    
    try:
        # Query to fetch geometries and their attributes, ensuring EPSG:25832 projection
        query = f"""
            SELECT ogc_fid, doklink, gml_id, ST_AsGeoJSON(ST_CurveToLine(geometri)) AS geometry,
                   CASE
                       WHEN ogc_fid % 3 = 0 THEN 'red'
                       WHEN ogc_fid % 3 = 1 THEN 'blue'
                       WHEN ogc_fid % 3 = 2 THEN 'green'
                       WHEN ogc_fid % 3 = 3 THEN 'yellow'
                       WHEN ogc_fid % 3 = 4 THEN 'purple'
                       ELSE 'orange'
                   END AS color
            FROM plandata.{feature}
        """
        pg_cur.execute(query)
        data = pg_cur.fetchall()

        # Check if data was retrieved
        if not data:
            return jsonify({'status': 'error', 'message': f'No data found for feature: {feature}'}), 404

        # Create GeoJSON Feature Collection with color property
        geojson_features = []
        for row in data:
            geojson_features.append({
                "type": "Feature",
                "properties": {
                    "id": row[0],
                    "doklink": row[1],
                    "gml_id": row[2],
                    "color": row[4]  # Correct column index for color
                },
                "geometry": json.loads(row[3])  # Geometry remains in EPSG:25832
            })

        geojson = {
            "type": "FeatureCollection",
            "features": geojson_features
        }

        return jsonify(geojson)

    except Exception as e:
        app.logger.error(f"Error: {e}")  # Use app.logger for better logging
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/')
def hello_world():
    return "Hello, World!"

