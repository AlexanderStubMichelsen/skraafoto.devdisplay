from pyproj import Proj, transform

# Define the coordinate systems
wgs84 = Proj(init='epsg:4326')  # WGS84
etrs89_utm32n = Proj(init='epsg:25832')  # ETRS89 / UTM zone 32N

# Example geographic coordinates (latitude, longitude)
lat, lon = 55.992079, 12.397136  # Example for Copenhagen, Denmark

# Convert geographic coordinates to EPSG:25832
easting, northing = transform(wgs84, etrs89_utm32n, lon, lat)

print(f"Coordinates in EPSG:25832: Easting = {easting}, Northing = {northing}")
