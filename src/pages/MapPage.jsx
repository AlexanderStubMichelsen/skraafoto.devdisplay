import React, { useEffect, useRef, useState } from "react";
import { queryItems, getElevationData } from "../util/api";
import { updateCenter } from "../util/centerImage.js";
import "@dataforsyningen/okapi/dist/okapi.css";
import GeoTIFFMAP from "../components/GeoTIFFMAP.jsx";
import "ol/ol.css";
import { Map, View } from "ol";
import TileLayer from "ol/layer/Tile";
import OSM from "ol/source/OSM";
import Overlay from "ol/Overlay";
import Draw from "ol/interaction/Draw";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import { Circle as CircleStyle, Fill, Stroke, Style } from "ol/style";
import "../App.css";
import { configuration } from "../util/configuration.js";
import { imgsFromPolygon } from "../util/api.js";
import { getArea } from "ol/sphere";

const directions = ["north", "south", "east", "west", "nadir"];
const limit = 5;
const MAX_POLYGON_AREA = 500000; // Example: 500,000 square meters


function MapPage() {
  const mapRef = useRef(null);
  const geoTIFFMapRef = useRef(null);
  const [imagesTif, setImagesTif] = useState({});
  const [coordinates, setCoordinates] = useState([728368.05, 6174304.56]);  //Initial skrafooto on load 
  const [selectedDirection, setSelectedDirection] = useState("north");   //Initial diretion
  const [center, setCenter] = useState(null);
  const [map, setMap] = useState(null);
  const [overlay, setOverlay] = useState(null);
  const popupRef = useRef(null);
  const popupCloserRef = useRef(null);
  const [drawingMode, setDrawingMode] = useState(false);
  const [vectorLayer, setVectorLayer] = useState(null);
  const [selectedCollection, setSelectedCollection] = useState("skraafotos2023"); 
  const [isDrawing, setIsDrawing] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null); 
  const [collectionName, setCollectionName] = useState("");
  const [errorMessage, setErrorMessage] = useState({message: null, statusCode: null}); 

  // Effect to initialize the OpenLayers map when the component mounts
  useEffect(() => {
    const initialVectorSource = new VectorSource();
    const initialVectorLayer = new VectorLayer({
      source: initialVectorSource,
      style: new Style({
        fill: new Fill({
          color: "rgba(255, 255, 255, 0.5)", // Set fill color for the polygon
        }),
        stroke: new Stroke({
          color: "#545C5D", // Set stroke color for the polygon
          width: 3,
        }),
        image: new CircleStyle({
          radius: 7,  // Set circle radius for points in our polygon
          fill: new Fill({
            color: "#545C5D", // set fill color for the circle
          }),
        }),
      }),
    });

    // Create the OpenLayers map instance with base OSM(OpenStreetMap) layer and vector layer
    const initialMap = new Map({
      target: mapRef.current,
      layers: [
        new TileLayer({
          source: new OSM(), // OpenStreetMap as base layer
        }),
        initialVectorLayer, // Add vector layer to map
      ],
      view: new View({
        center: [714841.046854, 6194210.065399], // Initial center position for the map
        zoom: 10, // Initial zoom level for the map
        projection: "EPSG:25832", // Set the projection to EPSG:25832 (ETRS89 / UTM zone 32N)
      }),
    });

    setMap(initialMap); // Set the map instance to the state
    setVectorLayer(initialVectorLayer); // Set the vector layer instance to the state

    // Overlay to show the popup
    if (popupRef.current && popupCloserRef.current) {
      const initialOverlay = new Overlay({
        element: popupRef.current, // Reference to popup DOM element
        autoPan: {
          animation: {
            duration: 250, // Pan the map to show popup with animation
          },
        },
      });

      setOverlay(initialOverlay); // Set overlay in state
      initialMap.addOverlay(initialOverlay); // Add overlay to the map

      // Handle popup close button click event
      popupCloserRef.current.onclick = function () {
        initialOverlay.setPosition(undefined); // Hide the popup
        popupCloserRef.current.blur();
        return false;
      };
    }

    return () => {
      if (initialMap) {
        initialMap.setTarget(null); // Clean up map on unmount
      }
    };
  }, []);

  // Effect to handle map click and show popups with coordinate data
  useEffect(() => {
    if (!map) {
      return;
    }
  
    const updatePopupContent = (polygonDataArray) => {
      if (Array.isArray(polygonDataArray)) { //checks if polygonData is loaded
        document.getElementById(
          "popup-content"
        ).innerHTML = `<p>Polygon:</p><code> Antal adresser i polygon: ${polygonDataArray.length}</code>`;  
      } else {
        document.getElementById(
          "popup-content"
        ).innerHTML = `<p>Loading data...</p>`; //Shows loading if data is unloaded
      }
    };
  
    const handleClick = (evt) => {
      if (drawingMode) {    // Disables geotiff-clicking while drawing polygon
        return;
      }
  
      const coordinate = evt.coordinate;
      setCoordinates(coordinate);
  
      const pixel = map.getPixelFromCoordinate(coordinate);
      const features = map.getFeaturesAtPixel(pixel);
  
      if (features.length > 0) {
        const feature = features[0];
        const featureData = feature.getProperties(); 
  
        // Display loading message initially
        document.getElementById("popup-content").innerHTML = `<p>Loading data...</p>`;
  
        // Check if polygon data is available
        const polygonDataArray = featureData.polygonData; 
  
        if (!Array.isArray(polygonDataArray)) {
          // If data is not available, set a timeout to retry
          setTimeout(() => {
            checkFeatureData(feature); // Retry data check
          }, 1000); // Adjust retry interval as needed
        } else {
          updatePopupContent(polygonDataArray); // Data is available, update popup
        }
        
        overlay.setPosition(coordinate);
      } else {
        document.getElementById("popup-content").innerHTML = `<p>You clicked here:</p><code>${coordinate}</code>`;
        overlay.setPosition(coordinate);
      }
    };
  
    const checkFeatureData = (feature) => {
      const featureData = feature.getProperties();
      const polygonDataArray = featureData.polygonData; 
  
      // Retry fetching polygon data if it's not available
      if (!Array.isArray(polygonDataArray)) {
        // Retry if data is not available
        setTimeout(() => {
          checkFeatureData(feature); // Retry data check
        }, 1000); // Adjust retry interval as needed
      } else {
        updatePopupContent(polygonDataArray); // Data is available, update popup
      }
    };
  
    // Register the click event
    map.on("singleclick", handleClick);
  
    // Use `map.once` to detect when layers are added to the map
    map.once('postrender', () => {
      const layers = map.getLayers().getArray();
      const vectorLayer = layers.find(layer => layer.get('name') === 'PolygonLayer'); 
  
      if (vectorLayer) {
  
        const source = vectorLayer.getSource();
        source.on('addfeature', (event) => {
          checkFeatureData(event.feature);
        });
        source.on('changefeature', (event) => {
          checkFeatureData(event.feature);
        });
        source.on('clear', () => {
          document.getElementById("popup-content").innerHTML = `<p>No polygon data available</p>`;
        });
      }
    });
  
    // Cleanup on component unmount
    return () => {
      if (map) {
        map.un("singleclick", handleClick);
      }
  
      const layers = map.getLayers().getArray();
      const vectorLayer = layers.find(layer => layer.get('name') === 'PolygonLayer');
  
      if (vectorLayer) {
        const source = vectorLayer.getSource();
        source.un('addfeature', checkFeatureData);
        source.un('changefeature', checkFeatureData);
      }
    };
  }, [map, isDrawing, drawingMode, overlay]);
  
  // Effect to handle drawing polygons on the map
  useEffect(() => {
    if (!map || !vectorLayer) return;
  
    const source = vectorLayer.getSource();
    const draw = new Draw({
      source: source, // Set the source for the draw interaction
      type: "Polygon", // Set the geometry type to polygon
    });
  
    const handleDrawEnd = async (event) => {
      setIsDrawing(false); // Set drawing flag to false when drawing ends
      const feature = event.feature; // Get the feature drawn by the user
      const geometry = feature.getGeometry(); // Get the geometry of the feature
    
      // Assign a unique ID if not already set
      if (!feature.getId()) {
        feature.setId(`polygon-${Date.now()}`);
      }
    
      // Get the area of the polygon
      const area = getArea(geometry);
    
      //console.log("Polygon area:", area);
      //console.log("Polygon information:", feature);
    
      // Log all features in source before any action
      //console.log("All features before action:", source.getFeatures().map(f => f.getId()));
    
      if (area > MAX_POLYGON_AREA) {
        // Delay removal to ensure that drawing is complete
        setTimeout(() => {
          alert(`Polygon size exceeds the maximum limit of ${MAX_POLYGON_AREA} square meters and has been removed.`);
          
          // Log feature ID being removed
          const featureId = feature.getId();
          //console.log("Removing feature with ID:", featureId);
    
          // Log all features before removal
          //console.log("All features before removal:", source.getFeatures().map(f => f.getId()));
    
          // Remove only the oversized feature
          const featureToRemove = source.getFeatureById(featureId);
    
          if (featureToRemove) {
            source.removeFeature(featureToRemove);
    
            // Notify the vector layer that the source has changed
            vectorLayer.getSource().changed(); // Notify that the source has changed
    
            // Optionally, re-render the map to ensure the changes are reflected
            map.updateSize(); // Update map size (optional)
            map.render(); // Force a re-render of the map
    
            // Log all features after removal
            //console.log("All features after removal:", source.getFeatures().map(f => f.getId()));
          } else {
            console.warn("Feature to remove not found.");
          }
        }, 100); // 100 ms delay
        return; // Exit the function early
      }
    
      const coordinates = geometry.getCoordinates(); // Get the coordinates of the geometry
      try {
        const polygonData = await imgsFromPolygon(coordinates); // Get the polygon data
    
        feature.set("coordinates", coordinates); // Store the coordinates in the feature
        feature.set("polygonData", polygonData); // Store the polygon data in the feature
    
        // Log all features after adding new feature data
        //console.log("All features after adding data:", source.getFeatures().map(f => f.getId()));
      } catch (error) {
        console.error("Error setting polygon data:", error);
      }
    };
    
    draw.on("drawend", handleDrawEnd);
  
    if (drawingMode) {
      setIsDrawing(true); // Set drawing flag to true when entering drawing mode
      map.addInteraction(draw);
    } else {
      setIsDrawing(false); // Set drawing flag to false when exiting drawing mode
      map.removeInteraction(draw); // Remove draw interaction when drawing mode is off
    }
  
    return () => {
      if (map) {
        map.removeInteraction(draw); // Remove draw interaction on unmount
      }
    };
  }, [map, drawingMode, vectorLayer]);
  
  // Effect for fetching images, related data, and elevation based on coordinates
useEffect(() => {
  if (!coordinates) return; 

  const fetchImages = async () => {
    const newImagesTif = {};
    const newSTACItems = {};
    let currentSelectedItem = null;

    try {
      // Fetch images and related data
      for (const direction of directions) {
        try {
          const response = await queryItems(
            coordinates,
            direction,
            selectedCollection,
            limit
          );

          if (response.features && response.features.length > 0) {
            const feature = response.features[0];
            const imagesUrl = feature.assets?.data?.href || null;
            const STACItem = feature;

            newImagesTif[direction] = imagesUrl;
            newSTACItems[direction] = STACItem;

            if (direction === selectedDirection) {
              currentSelectedItem = feature;
            }
          } else {
            setErrorMessage({ message: "Invalid authorization credentials", statusCode: 401})
            newImagesTif[direction] = null;
            newSTACItems[direction] = null;
          }
        } catch (error) {
          console.error(`Error fetching STAC items for ${direction}:`, error);
          setErrorMessage({ message: "The API server seems to be down for the moment", statusCode: 503})
          newImagesTif[direction] = null;
          newSTACItems[direction] = null;
        }
      }

      setSelectedItem(currentSelectedItem); // Set the selected item after fetching
      setImagesTif(newImagesTif);

      // Fetch elevation data and update center
      if (currentSelectedItem) {
        const elevation = await getElevationData(
          configuration.API_DHM_TOKENA,
          configuration.API_DHM_TOKENB,
          coordinates
        );

        const result = await updateCenter(coordinates, currentSelectedItem, elevation);
        if (result && result.imageCoord) {
          setCenter(result.imageCoord); // Update center with the image coordinates
        }
      }
    } catch (error) {
      console.error("Error fetching images or related data:", error);
      setErrorMessage({ message: "The API server seems to be down for the moment", statusCode: 503})
    }
  };

  fetchImages();
}, [coordinates, selectedDirection, selectedCollection, setErrorMessage]);


  const toggleDrawingMode = () => {
    setDrawingMode((prev) => !prev);
  };

  const downloadGeoTIFF = () => {
    if (!geoTIFFMapRef.current) return;

    const geoTIFFCanvas = geoTIFFMapRef.current.querySelector("canvas");
    if (!geoTIFFCanvas) return;

    const imageData = geoTIFFCanvas.toDataURL("image/png");
    const link = document.createElement("a");
    link.href = imageData;
    link.download = `geotiff_image.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Clear all drawn polygons from the map
  const clearDrawings = () => {
    if (vectorLayer) {
      const source = vectorLayer.getSource();
      source.clear(); // This will remove all features from the vector layer
    }
  };

  // Send polygons data to database
  // Send polygons data to database
const printPolygons = async () => {
  if (!vectorLayer) return;

  const polygons = vectorLayer.getSource().getFeatures().flatMap(f => f.getGeometry().getCoordinates());

  try {
    const response = await fetch(`http://localhost:5000/add_polygon_collection/${collectionName}`, {
      ...configuration,
      method: 'PUT',
      mode: 'cors',
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(polygons)
    });

    if (response.ok) {
      // Notify user of successful completion
      alert(`Polygon data saved successfully for collection: ${collectionName}!`);
    } else if (response.status === 409) {
      alert(`Polygon data not saved for collection: ${collectionName}! That collection name is already in use.`);
    } else {
      // If response fails, log status and message
      const errorMessage = await response.text();
      console.error(`Failed to save polygon data. Status: ${response.status}, Message: ${errorMessage}`);
    }
  } catch (e) {
    // Catch network/connection issues or other unexpected errors
    console.error(`Something went wrong with the PostGIS connector: \n\t ${e.message}`);
  }
};

  // Handle changes in the collection name input field
  const handleCollectionNameChange = (event) => {
    setCollectionName(event.target.value)
  }

  return (
    <div className="mapcenterpage">
      <div className="map-header col-9">
        <div className="toolbar">
          <div className="select-container">
            <select
              className="tool-btn"
              value={selectedCollection}
              onChange={(e) => setSelectedCollection(e.target.value)}
            >
              <option value="" disabled>Select Collection</option>
              <option value="skraafotos2023">2023</option>
              <option value="skraafotos2021">2021</option>
              <option value="skraafotos2019">2019</option>
              <option value="skraafotos2017">2017</option>
            </select>
          </div>
  
          <button className="tool-btn" onClick={toggleDrawingMode}>
            {drawingMode ? "Stop Drawing" : "Draw Polygon"}
            <img src="src/assets/polygon.svg" className="btnSvg btnP" alt="Polygon Icon" />
          </button>
          
          {drawingMode && (
            <button className="tool-btn" onClick={clearDrawings}>
              {"Clear"}
            </button>
          )}
  
          {!drawingMode && (
            <>
              <input onChange={handleCollectionNameChange} placeholder="Collection name" />
              <button className="tool-btn" onClick={printPolygons}>
                {"Postgis polygon"}
              </button>
            </>
          )}
  
          <button className="tool-btn" onClick={downloadGeoTIFF}>
            {"Download "}
            <img src="src/assets/download.svg" className="btnSvg btnD" alt="Download Icon" />
          </button>
        </div>
      </div>
      
      <div className="mappage col-9">
        <div id="map" className="geomap" ref={mapRef}></div>
        
        <div id="popup" className="ol-popup" ref={popupRef}>
          <a href="#" id="popup-closer" className="ol-popup-closer" ref={popupCloserRef}></a>
          <div id="popup-content"></div>
        </div>
          {errorMessage.message ? (
            <div className="error-page" >
              <h1> {errorMessage.statusCode} </h1>
              <h2> {errorMessage.message} </h2>
              <p> Please try again later</p>
            </div>
          ) : (
            <div className="map-viewer">
              {imagesTif[selectedDirection] && (
                <div className="high-quality-viewer" ref={geoTIFFMapRef}>
                  <GeoTIFFMAP url={imagesTif[selectedDirection]} center={center} />
                  
                  <div className="compass">
                    <div
                      className={`direction north ${selectedDirection === "north" ? "active" : ""}`}
                      onClick={() => setSelectedDirection("north")}
                    >
                      N
                    </div>
                    <div
                      className={`direction east ${selectedDirection === "east" ? "active" : ""}`}
                      onClick={() => setSelectedDirection("east")}
                    >
                      E
                    </div>
                    <div
                      className={`direction south ${selectedDirection === "south" ? "active" : ""}`}
                      onClick={() => setSelectedDirection("south")}
                    >
                      S
                    </div>
                    <div
                      className={`direction west ${selectedDirection === "west" ? "active" : ""}`}
                      onClick={() => setSelectedDirection("west")}
                    >
                      W
                    </div>
                    <div
                      className={`direction nadir ${selectedDirection === "nadir" ? "active" : ""}`}
                      onClick={() => setSelectedDirection("nadir")}
                    >
                      T
                    </div>
                  </div> 
                </div> 
              )}
            </div> 
          )}
        </div>
      </div>
  );
}

export default MapPage;