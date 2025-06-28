import { useState, useEffect } from 'react';
import { queryItems, getElevationData } from '../util/api.js';
import MultiViewer from '../components/MultiViewer.jsx';
import { configuration } from '../util/configuration.js';
import { updateCenter } from '../util/centerImage.js';
import GeoTIFFMAP from '../components/GeoTIFFMAP.jsx'; 
import AddressSearch from '../components/AddressSearch.jsx';
import '../App.css'; 

const directions = ['north', 'south', 'east', 'west', 'nadir']; // List of all directions
const collection = 'skraafotos2023'; // Example collection ID
const limit = 5; // Example limit on the number of items

function MultiViewerPage() {
  const [images, setImages] = useState({});
  const [imagesTif, setImagesTif] = useState({});
  const [coordinates, setCoordinates] = useState([728368.05, 6174304.56]);
  const [kote, setKote] = useState(null);
  const [selectedDirection, setSelectedDirection] = useState('north'); // Default to the first direction
  const [center, setCenter] = useState(null); // New state to store the center of the GeoTIFF image
  const [selectedItem, setSelectedItem] = useState(null); // State to store the selected item

  // Effect for fetching images and related data
  useEffect(() => {
    if (!coordinates) return;

    const fetchImages = async () => {
      const newImages = {};
      const newImagesTif = {};
      const newSTACItems = {};
      let currentSelectedItem = null;

      try {
        for (const direction of directions) {
          try {
            const response = await queryItems(coordinates, direction, collection, limit);

            if (response.features && response.features.length > 0) {
              const feature = response.features[0];
              const imageHref = feature.assets?.thumbnail?.href || null;
              const imagesUrl = feature.assets?.data?.href || null;
              const STACItem = feature;
              newImages[direction] = imageHref;
              newImagesTif[direction] = imagesUrl;
              newSTACItems[direction] = STACItem;

              if (direction === selectedDirection) {
                currentSelectedItem = feature;
              }
            } else {
              console.warn(`No features found for ${direction}`);
              newImages[direction] = null;
              newImagesTif[direction] = null;
              newSTACItems[direction] = null;
            }
          } catch (error) {
            console.error(`Error fetching STAC items for ${direction}:`, error);
            newImages[direction] = null;
            newImagesTif[direction] = null;
            newSTACItems[direction] = null;
          }
        }

        setSelectedItem(currentSelectedItem); // Set the selected item after fetching
        setImages(newImages);
        setImagesTif(newImagesTif);
      } catch (error) {
        console.error('Error fetching images or related data:', error);
      }
    };

    fetchImages();
  }, [coordinates, selectedDirection]); // Re-run effect when coordinates or selected direction change

  // Effect for fetching elevation data and updating the center
  useEffect(() => {
    const fetchElevationAndUpdateCenter = async () => {
      if (!coordinates || !selectedItem) return;

      try {
        const elevation = await getElevationData(
          configuration.API_DHM_TOKENA,
          configuration.API_DHM_TOKENB,
          coordinates
        );
        setKote(elevation);

        const result = await updateCenter(coordinates, selectedItem, kote);
        if (result && result.imageCoord) {
          setCenter(result.imageCoord); // Update center with the image coordinates
        }
      } catch (error) {
        console.error('Error fetching elevation data or updating center:', error);
        setKote(null);
      }
    };

    fetchElevationAndUpdateCenter();
  }, [coordinates, selectedItem]); // Re-run effect when coordinates or selected item change

  return (
    <div className='centerpage'>
      <div className='page col-9 column'>
        <div>
          <div className='title-and-search'>
      
            <AddressSearch setCoordinates={setCoordinates} />
                <p className='white'>Insert address to view oblique aerial images from multiple directions</p>
          </div>
          
        </div>
        
        <div className="image-gallery">
          {/* High-quality image viewer for the selected direction */}
          {imagesTif[selectedDirection] && (
            <div className="high-quality-viewer">
              <GeoTIFFMAP url={imagesTif[selectedDirection]} center={center} />
            </div>
          )}

          {/* Thumbnails for the other directions */}
          <div className="thumbnails">
            {directions.filter((direction) => direction !== selectedDirection).map((direction) => (
              <div key={direction} className="thumbnail-container">
                <p className="direction-title">
                  {direction.charAt(0).toUpperCase() + direction.slice(1)}
                </p>
                {images[direction] ? (
                  <MultiViewer
                    src={images[direction]}
                    onClick={() => setSelectedDirection(direction)} // Set selected direction on click
                  />
                ) : (
                  <p>Loading {direction} image...</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default MultiViewerPage;
