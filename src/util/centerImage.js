/**
 * Module is taken from the SDFIdk/skraafoto_frontend.(Klimadatastyrelsen) on GitHub.
 * the specific module is burrowed from within the application at:
 * node_modules/@dataforsyning/saul/modules/saul-core.js
 */
/**
 * Uses world coordinate and image data to calculate an image coordinate
 * @param {Array} coordinate - Array containing the X and Y coordinates.
 * @param {Object} item - STAC item object containing image metadata.
 * @returns {Object} Object with world coordinates and image coordinates.
 */
async function updateCenter(coordinate, item, kote) {
    try {
      if (!item) {
        console.error("Error: No item provided to updateCenter function.");
        return;
      }
  
      const imageCoord = getImageXY(item, coordinate[0], coordinate[1], kote);
      const result = {
        worldCoord: [...coordinate, kote],
        imageCoord: imageCoord
      };
      
      return result;
    } catch (error) {
      console.error("Error in updateCenter function:", error);
      return null;
    }
  }
  
  /** 
   * Converts world lat, lon coordinates to x, y coordinates within a specific image.
   * Note that the pixel coordinates have their origin in the bottom left corner of the image with the x-axis positive towards the right and the y-axis positive up.
   * @param {Object} image_data - skraafoto-stac-api image data.
   * @param {Number} X - Easting.
   * @param {Number} Y - Northing.
   * @param {Number} [Z=0] - Elevation (geoide).
   * @returns {Array} [x, y] Column/row image coordinates.
   */
  function getImageXY(image_data, X, Y, Z = 0) {
    try {
      // Extract constants from image_data
      const xx0 = image_data.properties['pers:interior_orientation'].principal_point_offset[0];
      const yy0 = image_data.properties['pers:interior_orientation'].principal_point_offset[1];
      const ci = image_data.properties['pers:interior_orientation'].focal_length;
      const pix = image_data.properties['pers:interior_orientation'].pixel_spacing[0];
      const dimXi = image_data.properties['pers:interior_orientation'].sensor_array_dimensions[0];
      const dimYi = image_data.properties['pers:interior_orientation'].sensor_array_dimensions[1];
      const X0 = image_data.properties['pers:perspective_center'][0];
      const Y0 = image_data.properties['pers:perspective_center'][1];
      const Z0 = image_data.properties['pers:perspective_center'][2];
      const Ome = image_data.properties['pers:omega'];
      const Phi = image_data.properties['pers:phi'];
      const Kap = image_data.properties['pers:kappa'];
  
      // Recalculate values
      const c = ci * (-1);
      const dimX = dimXi * pix / 2 * (-1);
      const dimY = dimYi * pix / 2 * (-1);
  
      // Convert degrees to radians
      const o = radians(Ome);
      const p = radians(Phi);
      const k = radians(Kap);
  
      // Rotation matrix components
      const D11 = Math.cos(p) * Math.cos(k);
      const D12 = -Math.cos(p) * Math.sin(k);
      const D13 = Math.sin(p);
      const D21 = Math.cos(o) * Math.sin(k) + Math.sin(o) * Math.sin(p) * Math.cos(k);
      const D22 = Math.cos(o) * Math.cos(k) - Math.sin(o) * Math.sin(p) * Math.sin(k);
      const D23 = -Math.sin(o) * Math.cos(p);
      const D31 = Math.sin(o) * Math.sin(k) - Math.cos(o) * Math.sin(p) * Math.cos(k);
      const D32 = Math.sin(o) * Math.cos(k) + Math.cos(o) * Math.sin(p) * Math.sin(k);
      const D33 = Math.cos(o) * Math.cos(p);
  
      // Image coordinates
      const x_dot = (-1) * c * ((D11 * (X - X0) + D21 * (Y - Y0) + D31 * (Z - Z0)) / (D13 * (X - X0) + D23 * (Y - Y0) + D33 * (Z - Z0)));
      const y_dot = (-1) * c * ((D12 * (X - X0) + D22 * (Y - Y0) + D32 * (Z - Z0)) / (D13 * (X - X0) + D23 * (Y - Y0) + D33 * (Z - Z0)));
  
      const col = ((x_dot - xx0) + (dimX)) * (-1) / pix;
      const row = ((y_dot - yy0) + (dimY)) * (-1) / pix;
      
      return [Math.round(col), Math.round(row)];
    } catch (error) {
      console.error("Error in getImageXY function:", error);
      return [0, 0];  // Return a default value or handle the error accordingly
    }
    
/** Converts degress to radians */
function radians(degrees) {
    return degrees * (Math.PI / 180)
  }
  }
  
  export {
    updateCenter
  };
  