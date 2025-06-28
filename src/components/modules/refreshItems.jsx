import { queryItems, getTerrainData } from '../../util/api.js';


export async function refreshItems(coordinates, collection) {
    const itemTerrainPairs = {
      nadir: null,
      north: null,
      south: null,
      east: null,
      west: null
    }
    let itemPromises = []
    let terrainPromises = []
    for (const key of Object.keys(itemTerrainPairs)) {
      itemPromises.push(queryItems(coordinates, key, collection))
    }
    const items = await Promise.all(itemPromises)
    for (const i in items) {
      terrainPromises.push(getTerrainData(items[i].features[0]))
    }
    const terrains = await Promise.all(terrainPromises)
    for (const i in items) {
      const item = items[i].features[0]
      itemTerrainPairs[item.properties.direction] = {
        item: item,
        terrain: terrains[i]
      }
    }
    return itemTerrainPairs
  }

  export default refreshItems;