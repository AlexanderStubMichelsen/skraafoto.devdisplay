import React, { useEffect, useRef, useState } from "react";
import "ol/ol.css";
import { Map, View } from "ol";
import TileLayer from "ol/layer/Tile";
import OSM from "ol/source/OSM";
import Overlay from "ol/Overlay";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import { Circle as CircleStyle, Fill, Stroke, Style } from "ol/style";
import GeoJSON from "ol/format/GeoJSON";
import AddressSearch from "../components/AddressSearch.jsx";
import Select from "ol/interaction/Select";
import "../App.css";
import { configuration } from "../util/configuration.js";
import loadingGif2 from "../assets/loading-loader-ezgif.com-effects.gif";
import { set } from "ol/transform.js";

function ZonePage() {
  const mapRef = useRef(null);
  const popupRef = useRef(null);
  const popupCloserRef = useRef(null);
  const [map, setMap] = useState(null);
  const [vectorLayer, setVectorLayer] = useState(null);
  const [address, setAddress] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState("");
  const [loading, setLoading] = useState(false);

  // Effect to initialize the OpenLayers map when the component mounts
  useEffect(() => {
    const vectorSource = new VectorSource();
    const vectorLayer = new VectorLayer({
      source: vectorSource,
      style: new Style({
        fill: new Fill({ color: "rgba(255, 255, 255, 0.5)" }),
        stroke: new Stroke({ color: "#545C5D", width: 3 }),
      }),
    });

    const map = new Map({
      target: mapRef.current,
      layers: [
        new TileLayer({ source: new OSM() }),
        vectorLayer,
      ],
      view: new View({
        center: [714841.046854, 6194210.065399],
        zoom: 10,
        projection: "EPSG:25832",
      }),
    });

    const popupOverlay = new Overlay({
      element: popupRef.current,
      autoPan: { animation: { duration: 250 } },
    });

    map.addOverlay(popupOverlay);
    setMap(map);
    setVectorLayer(vectorLayer);

    const handleMapClick = (evt) => {
      const clickedCoordinate = evt.coordinate;
      let clickedFeature = null;

      map.forEachFeatureAtPixel(evt.pixel, (feature) => {
        clickedFeature = feature;
        return true; // Stop iteration after the first feature
      });

      if (clickedFeature) {
        setLoading(true);
        const properties = clickedFeature.getProperties();
        const popupContent = document.getElementById("popup-content");
      
        if (!popupContent) {
          console.error("Popup content element not found.");
          setLoading(false);
          return;
        }
      
        let linkHTML = '';
        
        if (properties.doklink) {
          if (properties.gml_id) {
            console.log("gml_id found in the feature properties:", properties.gml_id);
            const planType = extractPlanType(properties.gml_id);
            linkHTML = `
              <a href="${properties.doklink}" target="_blank" style="color: blue; text-decoration: underline;">
                Open Doklink (${planType})
              </a>`;
          } else {
            console.log("Doklink found in the feature properties (but no gml_id):", properties);
            linkHTML = `
              <a href="${properties.doklink}" target="_blank" style="color: blue; text-decoration: underline;">
                Open Doklink
              </a>`;
          }
      
          // Set the popup content and position
          popupContent.innerHTML = linkHTML;
          popupOverlay.setPosition(clickedCoordinate);
        } else {
          console.warn("No doklink found in the feature properties.");
          popupOverlay.setPosition(undefined); // Hide the popup
        }
      
        setLoading(false); // End loading process
      } else {
        popupOverlay.setPosition(undefined); // Hide the popup if no feature was clicked
      } 
    };     

    const extractPlanType = (feature) => {
      const parts = feature.split('_'); 
      if (parts[2] === "kommuneplan") {
        return `${parts[4].charAt(0).toUpperCase() + parts[4].slice(1).toLowerCase()} Til ${parts[2].charAt(0).toUpperCase() + parts[2].slice(1).toLowerCase()} `; // Proper string concatenation using template literals
      }
      if (parts[2] === "lokalplan") {
        return `${parts[3].charAt(0).toUpperCase() + parts[3].slice(1).toLowerCase()} Til ${parts[2].charAt(0).toUpperCase() + parts[2].slice(1).toLowerCase()} `; // Proper string concatenation using template literals
      } 
      return null; // Return null or an alternative message if not "kommuneplan"
    };
    

    map.on("singleclick", handleMapClick);

    const handlePopupClose = (evt) => {
      evt.preventDefault();
      popupOverlay.setPosition(undefined);
      popupCloserRef.current.blur();
    };

    popupCloserRef.current.addEventListener("click", handlePopupClose);
    
    const select_interaction = new Select();
    select_interaction.getFeatures().on("add", function (e) {
        const feature = e.element; //the feature selected
    });

    map.addInteraction(select_interaction);
    return () => {
      map.un("singleclick", handleMapClick);
      map.setTarget(null);
    };

  }, []);

  // Effect to call getPolygons when the address changes
  useEffect(() => {
    if (address) {
      getPolygons();
    }
  }, [address]);

  const getPolygons = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${configuration.api_base_url}/get_plandata/${address.road} ${address.housenumber}, ${address.postalcode}`, {
        method: "GET",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const polygons = await response.json();
      if (!polygons.komuneplan && !polygons.lokalplan) {
        console.warn("No polygons found for the address.");
      }
      const vectorSource = new VectorSource();

      if (polygons.komuneplan) {
        vectorSource.addFeatures(new GeoJSON().readFeatures(polygons.komuneplan, {
          dataProjection: "EPSG:25832",
          featureProjection: map.getView().getProjection(),
        }));
      }

      if (polygons.lokalplan) {
        vectorSource.addFeatures(new GeoJSON().readFeatures(polygons.lokalplan, {
          dataProjection: "EPSG:25832",
          featureProjection: map.getView().getProjection(),
        }));
      }


      vectorLayer.setSource(vectorSource);
    } catch (error) {
      console.error("Error fetching polygons:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleFeature = async () => {
    if (!selectedFeature) {
      // If no feature is selected, clear the map
      if (vectorLayer && vectorLayer.getSource()) {
        vectorLayer.getSource().clear(); // Clear all features from the vector source
        console.log("Map cleared because no feature was selected.");
      }
      return; // Exit early, no need to fetch any new features
    }

    try {
      setLoading(true);
      const response = await fetch(`${configuration.api_base_url}/toggle/${selectedFeature}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const geojson = await response.json();
      
      // Check if the response is valid GeoJSON
      if (!geojson || !geojson.type) {
        console.error("Invalid GeoJSON response:", geojson);
        return;
      }

      const vectorSource = new VectorSource({
        features: new GeoJSON().readFeatures(geojson, {
          dataProjection: "EPSG:25832",
          featureProjection: map.getView().getProjection(),
        }),
      });

      vectorLayer.setSource(vectorSource);
    } catch (error) {
      console.error("Error toggling feature:", error);
    } finally {
      setLoading(false);
    } 
  };

  useEffect(() => {
    toggleFeature();
  }, [selectedFeature]);

  return (
    <div className="mapcenterpage">
      <div className="map-header col-9">
        <div className="toolbar">
          <div className="title-and-search">
            <AddressSearch setAddress={setAddress} />
          </div>
          <p className="white">Insert address to view relevant zones</p>
          <button className="tool-btn" onClick={getPolygons}>
            Get Zones
          </button>
        <div className="select-container">
          <select
            className="tool-select"
            value={selectedFeature}
            onChange={(e) => setSelectedFeature(e.target.value)}
          >
            <option value="">Select Overlay</option>
            <option value="theme_pdk_kommuneplan_oversigt_forslag_v">Forslag til kommuneplaner</option>
            <option value="theme_pdk_kommuneplan_oversigt_vedtaget_v">Vedtagne kommuneplaner</option>
            <option value="theme_pdk_lokalplan_forslag_v">Forslag til lokalplaner</option>
            <option value="theme_pdk_lokalplan_vedtaget_v">Vedtagne lokalplaner</option>
          </select>
        </div>
        <p className="white">Select feature to view relevant zones</p>
        {loading && ( 
          <div className="loading">
            <img src={loadingGif2} alt="loading" />
          </div>
        )}
      </div>
      </div>

      <div className="mappage col-9">
        <div id="map" className="geomap" ref={mapRef}></div>

        <div id="popup" className="ol-popup" ref={popupRef}>
          <a href="#" id="popup-closer" className="ol-popup-closer" ref={popupCloserRef}></a>
          <div id="popup-content"></div>
        </div>
      </div>
    </div>
  );
}

export default ZonePage;
