import math
import logging
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# These functions are imported from node_modules/@dataforsyningen/saul/modules/saul-core.js or '@dataforsyningen/saul' 
def radians(degrees):
    """Convert degrees to radians."""
    return degrees * (math.pi / 180)

def get_image_xy(image_data, X, Y, Z=0):
    """
    Converts world lat, lon coordinates to x, y coordinates within a specific image.
    
    :param image_data: Dictionary containing image metadata.
    :param X: Easting.
    :param Y: Northing.
    :param Z: Elevation (geoide).
    :return: Tuple of (x, y) Column/row image coordinates.
    """
    try:
        # Extract constants from image_data
        interior_orientation = image_data['properties']['pers:interior_orientation']
        xx0 = interior_orientation['principal_point_offset'][0]
        yy0 = interior_orientation['principal_point_offset'][1]
        ci = interior_orientation['focal_length']
        pix = interior_orientation['pixel_spacing'][0]
        dimXi = interior_orientation['sensor_array_dimensions'][0]
        dimYi = interior_orientation['sensor_array_dimensions'][1]
        X0 = image_data['properties']['pers:perspective_center'][0]
        Y0 = image_data['properties']['pers:perspective_center'][1]
        Z0 = image_data['properties']['pers:perspective_center'][2]
        Ome = image_data['properties']['pers:omega']
        Phi = image_data['properties']['pers:phi']
        Kap = image_data['properties']['pers:kappa']
        
        # Recalculate values
        c = ci * (-1)
        dimX = dimXi * pix / 2 * (-1)
        dimY = dimYi * pix / 2 * (-1)
        
        # Convert degrees to radians
        o = radians(Ome)
        p = radians(Phi)
        k = radians(Kap)
        
        # Rotation matrix components
        D11 = math.cos(p) * math.cos(k)
        D12 = -math.cos(p) * math.sin(k)
        D13 = math.sin(p)
        D21 = math.cos(o) * math.sin(k) + math.sin(o) * math.sin(p) * math.cos(k)
        D22 = math.cos(o) * math.cos(k) - math.sin(o) * math.sin(p) * math.sin(k)
        D23 = -math.sin(o) * math.cos(p)
        D31 = math.sin(o) * math.sin(k) - math.cos(o) * math.sin(p) * math.cos(k)
        D32 = math.sin(o) * math.cos(k) + math.cos(o) * math.sin(p) * math.sin(k)
        D33 = math.cos(o) * math.cos(p)
        
        # Image coordinates
        x_dot = (-1) * c * ((D11 * (X - X0) + D21 * (Y - Y0) + D31 * (Z - Z0)) / (D13 * (X - X0) + D23 * (Y - Y0) + D33 * (Z - Z0)))
        y_dot = (-1) * c * ((D12 * (X - X0) + D22 * (Y - Y0) + D32 * (Z - Z0)) / (D13 * (X - X0) + D23 * (Y - Y0) + D33 * (Z - Z0)))
        
        col = ((x_dot - xx0) + (dimX)) * (-1) / pix
        row = ((y_dot - yy0) + (dimY)) * (-1) / pix
        return (round(col), round(row))
        

    except Exception as e:
        print(f"Error in get_image_xy function: {e}")
        return (0, 0)  # Return a default value or handle the error accordingly

def update_center(coordinate, item, kote=0):
    """
    Uses world coordinate and image data to calculate an image coordinate.
    
    :param coordinate: List containing the X and Y coordinates.
    :param item: Dictionary containing image metadata.
    :param kote: Optional parameter for elevation (default is 0).
    :return: Dictionary with world coordinates and image coordinates.
    """
    try:
        if not item:
            print("Error: No item provided to update_center function.")
            return None
        
        image_coord = get_image_xy(item, coordinate[0], coordinate[1], kote)
        return {
            'worldCoord': list(coordinate) + [kote],
            'imageCoord': image_coord
        }
    except Exception as e:
        print(f"Error in update_center function: {e}")
        return None
