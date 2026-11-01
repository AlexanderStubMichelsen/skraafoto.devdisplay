import { configuration } from './configuration.js'

/**
 * finds every element 
 * @param {number[]} bbox 4 numbers that sets the bounding box for the search
 */
const findImgLinksInBox = async (bbox) => {
    const url = `${configuration.API_STAC_BASEURL}/search?bbox=${bbox[0]},${bbox[1]},${bbox[2]},${bbox[3]}`
    const response = await fetch(url)

    const itr = getNextSet(await response.json())
    const elemntsOfBox = []
    for await (const element of itr) {
        elemntsOfBox.push(...element)
    }
    return elemntsOfBox.filter(e => e.id != '2023_jul_i_job')
}


async function* getNextSet(first) {
    let next = first
    let isFinal = false
    do {
        if (next.links.length < 2) return //todo: maybe throw an error
        // Paging links are rewritten by the backend to point at its proxy
        const nextResponse = await fetch(next.links[1].href)
        const current = next
        next = await nextResponse.json()
        yield current.features
        if (next.links[1].rel == "previous") yield next.features

    }
    while (next.links[1].rel == "next" || isFinal)


}

export { findImgLinksInBox}