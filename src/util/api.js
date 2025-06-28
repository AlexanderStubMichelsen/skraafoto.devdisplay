import { getSTAC, getTerrainGeoTIFF } from '@dataforsyningen/saul';
import axios from 'axios';
import { configuration } from './configuration.js';
import { useState,} from 'react';


/**
 * Helper to add retry logic to any async function
 * @param {Function} fn - The async function to wrap with retries
 * @param {number} retries - Number of retry attempts
 * @param {number} delay - Delay between retries in milliseconds
 * @returns {Function} A wrapped function with retry logic
 */
function retryWrapper(fn) {
    return async (...args) => {
        let retries = 5; 
        let delay = 5000;
        for (let attempt = 1; attempt <= retries; attempt++) {
            try {
                return await fn(...args); // Call the original function
            } catch (error) {
                console.error(`Attempt ${attempt} failed`);
                if (attempt >= retries) {
                    throw error; // Throw error if max retries reached
                }
                await new Promise(resolve => setTimeout(resolve, delay)); // Wait before retrying
            }
        }
    };
}

/** 
 * Fetches data from a given URL
 * @param {string} url - The API URL to fetch from
 * @param {object} config - Optional configuration object for the fetch request
 * @param {boolean} is_json - Flag to parse response as JSON
 * @returns {Promise<object>} The fetched data
 */
function get(url, config = {}, is_json = true) {
    if (!url) {
        console.error('Could not fetch data. Missing API URL');
        return Promise.reject('Missing API URL');
    }
    return fetch(url, {
        ...config,
        method: 'GET',
        mode: 'cors'
    })
    .then(response => is_json ? response.json() : response.text())
    .catch(error => {
        console.error(`Fetch error: ${error}`);
        throw error;
    });
}

/** 
 * Queries STAC API for items based on location and other parameters
 * @param {Array<number>} coord - EPSG:25832 coordinates [x, y]
 * @param {string} direction - Direction of the item images
 * @param {string} [collection] - Collection to fetch items from
 * @param {number} [limit] - Number of results to return
 * @returns {Promise<object>} A featureCollection of STAC items
 */
async function queryItems(coord, direction, collection, limit = 1) {
    let search_query = { 
        "and": [
            { "contains": [{ "property": "geometry" }, { "type": "Point", "coordinates": [coord[0], coord[1]] }] },
            { "eq": [{ "property": "direction" }, direction] }
        ]
    };
    if (collection) {
        search_query.and.push({ "eq": [{ "property": "collection" }, collection] });
    }
    try {
        const response = await getSTAC(`/search?limit=${limit}&filter=${encodeURI(JSON.stringify(search_query))}&filter-lang=cql-json&filter-crs=http://www.opengis.net/def/crs/EPSG/0/25832&crs=http://www.opengis.net/def/crs/EPSG/0/25832`, configuration);
        return response;
    } catch (error) {
        console.error(`Error querying items: ${error}`);
        throw error;
    }
}

/** 
 * Fetches a list of non-TEST collections from the STAC database
 * @returns {Promise<Array>} A list of collection IDs
 */
function getCollections() {
    return getSTAC(`/collections`, configuration)
        .then(data => {
            const sorted_collections = data.collections.sort((a, b) => a.id.localeCompare(b.id));
            return sorted_collections.filter(coll => !coll.id.toLowerCase().includes('test'));
        })
        .catch(error => {
            console.error(`Error fetching collections: ${error}`);
            throw error;
        });
}


/**
 * DHM/Danmarks Højdemodel is a terrainmodel of Denmark, that gives us access to elevation data at specific coordinates
 * If you have a user account, you can access the data through the API
 * A user account can be created at https://datafordeler.dk/ and by adding a service/tjenestebruger,
 * which username and password will be your API_DHM_TOKENA and API_DHM_TOKENB in the configuration file.
 /** 
 * Fetches elevation data from DHM Terraen
 * @param {string} [username] - API username (default from configuration)
 * @param {string} [password] - API password (default from configuration)
 * @param {Array<number>} coordinates - Array containing [longitude, latitude] in UTM (EPSG:25832)
 * @returns {Promise<number>} Elevation (kote) value
 */
async function getElevationData(username = configuration.API_DHM_TOKENA, password = configuration.API_DHM_TOKENB, coordinates) {
    try {
        const point = `POINT(${coordinates.join(' ')})`;
        const url = `https://services.datafordeler.dk/DHMTerraen/DHMKoter/1.0.0/GEOREST/HentKoter?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&geop=${encodeURIComponent(point)}`;
        const response = await axios.get(url);
        //console.log('Elevation url:', url);
        if (response.data && response.data.HentKoterRespons && response.data.HentKoterRespons.data.length > 0) {
            return response.data.HentKoterRespons.data[0].kote;
        } else {
            throw new Error('No elevation data found.');
        }
    } catch (error) {
        console.error('Error fetching elevation data:', error);
        throw error;
    }
}

/** 
 * Fetches a GeoTIFF image object with elevation data covering the same area as a given STAC item
 * @param {object} item - A STAC item
 * @returns {Promise<object>} GeoTIFF image with elevation data
 */
function getTerrainData(item) {
    return getTerrainGeoTIFF(item, configuration, 0.03)
        .then(geotiff => geotiff)
        .catch(error => {
            console.error('Error fetching terrain data:', error);
            throw error;
        });
}

const imgsFromPolygon = async (polygon) => {
    const polygonString = JSON.stringify(polygon);
    const url = `https://api.dataforsyningen.dk/adgangsadresser?polygon=${polygonString}&srid=25832&struktur=mini`
    //struktur=mini for less data, more effecient
    try{
        const response = await fetch(url, {
            method:'GET',
            headers: {
                "token": configuration.API_STAC_TOKEN, 
                'Content-Type': 'application/json',
            }
        })
        if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        return data; 
    }catch (error) {
        console.error('Error fetching adresses:', error);
    }   
}

// Apply retryWrapper to each function
const queryItemsWithRetry = retryWrapper(queryItems);
const getCollectionsWithRetry = retryWrapper(getCollections);
const getElevationDataWithRetry = retryWrapper(getElevationData);
const getTerrainDataWithRetry = retryWrapper(getTerrainData);
const imgsFromPolygonWithRetry = retryWrapper(imgsFromPolygon);


export {
    queryItemsWithRetry as queryItems,
    getCollectionsWithRetry as getCollections,
    getElevationDataWithRetry as getElevationData,
    getTerrainDataWithRetry as getTerrainData,
    imgsFromPolygonWithRetry as imgsFromPolygon
};
