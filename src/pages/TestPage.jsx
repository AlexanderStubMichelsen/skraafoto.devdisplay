import { useState, useEffect } from 'react';
import { queryItems } from '../util/api';
import ImageViewer from '../components/ImageViewer.jsx';
import AddressSearch from '../components/AddressSearch.jsx';
import '../App.css';
import LocationComponent from '../components/LocationComponent.jsx';

// const direction = 'north'; // Example direction
const collection = 'skraafotos2021'; // Example collection ID
const limit = 5; // Example limit on the number of items

function Test() {
  const [imageUrl, setImageUrl] = useState(null);
  const [coordinates, setCoordinates] = useState([714841.046854, 6194210.065399])
  const [direction, setDirection] = useState('north');

  useEffect(() => {
    queryItems(coordinates, direction, collection, limit)
      .then(response => {
        if (response.features && response.features.length > 0) {
          const imageHref = response.features[0].assets.thumbnail.href;
          setImageUrl(imageHref);
        } else {
          setImageUrl(null); // Handle case where no image is found
        }
      })
      .catch(error => {
        console.error('Error fetching STAC items:', error);
      });
  }, [direction, coordinates]); // Empty dependency array means this useEffect runs once on component mount

  return (
    <>
      <div className='centerpage'>
        <div className='page col-9'>
          <div className='title-and-search'>
            <h2 className='white'>STAC API Image:</h2>
            <p className='white'>Insert address to view oblique aerial images from multiple directions</p>
            <AddressSearch setCoordinates={setCoordinates} />
          </div>


          <div className="response">

            {imageUrl ? (
              <ImageViewer src={imageUrl} setDirection={setDirection} />
            ) : (
              <p>Loading image viewer...</p>
            )}
            <div>
              <LocationComponent setCoordinates={setCoordinates}/>
            </div>
          </div>
        </div>
      </div>

    </>
  );
}

export default Test;