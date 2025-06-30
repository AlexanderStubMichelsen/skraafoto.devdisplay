import React, { useRef, useEffect } from 'react';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/WebGLTile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import Feature from 'ol/Feature';
import Point from 'ol/geom/Point';
import { Style, Icon } from 'ol/style';
import GeoTIFF from 'ol/source/GeoTIFF';
import 'ol/ol.css'; // Import OpenLayers CSS
import proj4 from 'proj4';
import { register } from 'ol/proj/proj4';

// Define and register the EPSG:25832 projection
proj4.defs('EPSG:25832', '+proj=utm +zone=32 +datum=WGS84 +units=m +no_defs');
register(proj4);

const GeoTIFFMap = ({ url, center }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null); // Keep reference to map instance
  const viewRef = useRef(null); // Reference to the map's view for updating center

  // Cleanup function for WebGL context and OpenLayers Map
  const cleanupMap = () => {
    if (mapInstanceRef.current) {
      const layers = mapInstanceRef.current.getLayers().getArray();
      // Dispose of layers and their sources
      layers.forEach((layer) => {
        if (layer.getSource()) {
          layer.getSource().dispose?.(); // Dispose of the source
        }
        layer.dispose?.(); // Dispose of the layer
      });

      // Release the WebGL context manually if available
      const canvas = mapRef.current?.querySelector('canvas');
      if (canvas) {
        const gl = canvas.getContext('webgl');
        if (gl) {
          const loseContext = gl.getExtension('WEBGL_lose_context');
          if (loseContext) {
            loseContext.loseContext();
          }
        }
      }

      mapInstanceRef.current.setTarget(null); // Detach the map from DOM
      mapInstanceRef.current.dispose(); // Dispose of the map
      mapInstanceRef.current = null; // Clear the map reference
    }
  };

  useEffect(() => {
    if (!url) return;

    // If mapInstanceRef already exists, do not recreate map to avoid multiple WebGL contexts
    if (!mapInstanceRef.current) {
      // Create a GeoTIFF source with the specified URL
      const source = new GeoTIFF({
        sources: [{ url, bands: [1, 2, 3] }],
        convertToRGB: true, // Convert to RGB if supported
        transition: 0, // Disable fade-in transition
      });

      // Create a vector source and layer for the marker
      const vectorSource = new VectorSource();
      const vectorLayer = new VectorLayer({
        source: vectorSource,
      });

      // Initialize the map
      const map = new Map({
        target: mapRef.current,
        layers: [
          new TileLayer({
            source,
          }),
          vectorLayer, // Add vector layer to the map
        ],
        view: new View({
          zoom: 16, // Adjust zoom level
          minZoom: 13,
          maxZoom: 18,
          projection: 'EPSG:25832', // Use EPSG:25832 projection
        }),
      });

      // Store map instance reference to avoid re-creation
      mapInstanceRef.current = map;

      viewRef.current = map.getView();

      // Create and add the marker feature if a center is provided
      if (center) {
        const markerFeature = new Feature({
          geometry: new Point(center),
        });

        markerFeature.setStyle(new Style({
          image: new Icon({
            src: 'src/assets/marker.svg', // Path to the marker image
            scale: 0.05, // Adjust size of the marker
            opacity: 0.75,
          }),
        }));

        vectorSource.addFeature(markerFeature);
      }
    }

    // Cleanup on unmount or URL change
    return () => {
      cleanupMap();
    };
  }, [url, center]);

  useEffect(() => {
    if (viewRef.current && center) {
      // Update the center of the view when the center prop changes
      viewRef.current.setCenter(center);
    }
  }, [center]);

  useEffect(() => {
    const mapViewer = mapRef.current;
    let isDragging = false;
    let isDoubleClick = false;

    const handleMouseDown = () => {
      isDragging = true;
      // Delay the cursor change to avoid quick double-click issues
      setTimeout(() => {
        if (!isDoubleClick && isDragging) {
          mapViewer.style.cursor = 'grabbing';
        }
      }, 250); // Adjust the delay time if needed
    };

    const handleMouseUp = () => {
      isDragging = false;
      mapViewer.style.cursor = 'crosshair';
    };

    const handleDoubleClick = () => {
      isDoubleClick = true;
      // Prevent cursor from changing to grabbing on double-click
      setTimeout(() => {
        isDoubleClick = false;
      }, 400); // Adjust this delay as needed
    };

    if (mapViewer) {
      mapViewer.style.cursor = 'crosshair';
      mapViewer.addEventListener('mousedown', handleMouseDown);
      mapViewer.addEventListener('mouseup', handleMouseUp);
      mapViewer.addEventListener('dblclick', handleDoubleClick);
    }

    // Clean up event listeners on component unmount
    return () => {
      if (mapViewer) {
        mapViewer.removeEventListener('mousedown', handleMouseDown);
        mapViewer.removeEventListener('mouseup', handleMouseUp);
        mapViewer.removeEventListener('dblclick', handleDoubleClick);
      }
    };
  }, []);

  return (
    <div
      className='map-container'
      ref={mapRef}
      style={{
        width: '100%',
        height: '100%',
      }}
    />
  );
};

export default GeoTIFFMap;
