import React, { useState } from 'react';
import proj4 from 'proj4';
import 'ol/ol.css';

// Define the EPSG:25832 projection
proj4.defs('EPSG:25832', '+proj=utm +zone=32 +datum=WGS84 +units=m +no_defs');

// Define the WGS84 projection (default for coordinates from geolocation)
proj4.defs('EPSG:4326', '+proj=longlat +datum=WGS84 +no_defs');

const LocationComponent = ({ setCoordinates }) => {
  const [error, setError] = useState(null);

  // Function to get the current location and convert the coordinates
  const handleLocationAndConvert = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          
          try {
            // Convert WGS84 to EPSG:25832
            const [x, y] = proj4('EPSG:4326', 'EPSG:25832', [longitude, latitude]);
            setCoordinates([x, y]); // Pass transformed coordinates to setCoordinates
            setError(null); // Clear any previous errors
          } catch (err) {
            setError('Error converting coordinates.');
          }
        },
        (error) => {
          setError(error.message); // Set error message if location fetching fails
        }
      );
    } else {
      setError('Geolocation is not supported by this browser.');
    }
  };

  return (
    <div>
      <button onClick={handleLocationAndConvert}>Go to Current Location</button>
      {error && <p>Error: {error}</p>}
    </div>
  );
};

export default LocationComponent;
