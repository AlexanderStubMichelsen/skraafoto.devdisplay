import { configuration } from './configuration.js'

const addressToCoords = async (address) => {
  try {
    const query = `${address.road} ${address.housenumber} ${address.postalcode}`;
    const url = `https://api.dataforsyningen.dk/rest/gsearch/v2.0/husnummer?q=${encodeURIComponent(query)}&limit=99&srid=25832`;
    
    const response = await fetch(url, {
      headers: {
        "token": configuration.API_STAC_TOKEN,
      }
    });
    
    const houses = await response.json();

    if (!Array.isArray(houses) || houses.length === 0) {
      throw new Error('No houses found for the given address.');
    }

    // Find the house that matches the road name, house number, and postal code
    const house = houses.find(h => 
      h.husnummertekst === address.housenumber && 
      h.postnummer === address.postalcode
    );

    if (!house || !house.geometri || !house.geometri.coordinates) {
      throw new Error('House or coordinates not found in the response.');
    }

    const coords = house.geometri.coordinates[0];

    if (!Array.isArray(coords) || coords.length < 2) {
      throw new Error('Invalid coordinates found.');
    }

    return coords;

  } catch (error) {
    console.error('Error in addressToCoords:', error.message);
    if (error.message.includes('No houses found')) {
      console.warn('The address might be incorrect or not available in the dataset.');
    }
    throw error;
  }
};

// Function to get address suggestions based on the input
const addressAutocomplete = async (input) => {
  const url = `https://api.dataforsyningen.dk/rest/gsearch/v2.0/husnummer?q=${input}&limit=100&srid=25832`;
  const response = await fetch(url, {
    headers: {
      "token": configuration.API_STAC_TOKEN,
    }
  });
  
  const rawAddress = await response.json();

  return rawAddress.map(a => ({
    value: { 
      road: a.vejnavn, 
      housenumber: a.husnummertekst,
      postalcode: a.postnummer // Include postal code in the value
    }, 
    label: `${a.visningstekst}, ${a.postnummer}` // Show postal code in the label
  }));
};


export { addressToCoords, addressAutocomplete }