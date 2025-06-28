import argparse
import time
import sys
import os
import aiohttp
import asyncio
import json
import urllib.parse
import logging
import json
import yaml
import rasterio
from rasterio.windows import Window
from PIL import Image
from geotiff_utils import update_center  # Import the function from geotiff_utils.py
from dotenv import load_dotenv
from aiohttp import TCPConnector

# Load settings from settings.yaml
with open('settings.yaml', 'r') as f:
    settings = yaml.safe_load(f)

# Settings from settings.yaml
cache_dir = settings["cache_dir"]
collection = settings["collection"]
crop_sizes = settings["crop_sizes"]
image_resize = settings["image_resize"]
image_quality = settings["image_quality"]
max_concurrent_requests = settings["concurrency"]["max_concurrent_requests"]
limit_per_host = settings["concurrency"]["limit_per_host"]
retry_limit = settings["retry_limit"]
retry_delay = settings["retry_delay"]
threshold = settings["threshold"]
logging_level = settings["logging_level"]
crop_sizes = settings["crop_sizes"]
image_summary = settings["image_summary"]


# Load environment variables from a .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
detailed_logger = logging.getLogger('detailed')
summary_logger = logging.getLogger('summary')

# Create handlers
detailed_handler = logging.FileHandler('detailed_log.log', mode = 'w') # 'w' mode truncates the file on each run
summary_handler = logging.FileHandler('summary_log.log', mode='w')  # 'w' mode truncates the file on each run

# Define formats
detailed_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
summary_format = logging.Formatter('%(message)s')  # Simple format for summary log

# Set formatters for handlers
detailed_handler.setFormatter(detailed_format)
summary_handler.setFormatter(summary_format)

if not os.path.exists("detailed_log.log"):  #Adds logging files if they dont exist
    open("detailed_log.log", 'w').close()

if not os.path.exists("summary_log.log"):
    open("summary_log.log", 'w').close()

# Add handlers to loggers
detailed_logger.addHandler(detailed_handler)
summary_logger.addHandler(summary_handler)

# Set levels for each logger
detailed_logger.setLevel(logging_level) 
summary_logger.setLevel(logging.INFO)

# List for failed coordinates
failed_coordinates = []

# Initialize counters for summary
successful_jobs = 0
failed_jobs = 0
status_codes = set()
error_log = set()
progress = 0
start_time = time.time()

# Disable propagation to avoid double logging to the root logger
detailed_logger.propagate = False
summary_logger.propagate = False

# Set the max image pixels to None to avoid decompression bomb warnings
Image.MAX_IMAGE_PIXELS = None

# Ensure the cache directory exists
os.makedirs(settings["cache_dir"], exist_ok=True)

parser = argparse.ArgumentParser(prog='download_from_coordinates')
parser.add_argument("-f", "--file", type=str, help="Path to the text file with coordinates")

# Used to reset variables for testing enviorement
def reset_counters():
    global failed_jobs, successful_jobs, progress
    failed_jobs = 0 
    successful_jobs = 0 
    progress = 0


session = None

async def create_shared_session():
    #Create a shared aiohttp session
    global session
    if session is None:  # Create the session only if it doesn't exist
        session = aiohttp.ClientSession(connector=TCPConnector(limit_per_host=limit_per_host))

async def close_shared_session():
    #Close the shared aiohttp session
    global session
    if session:
        await session.close()
        session = None

class STACImageProcessor:
    DIRECTIONS = ['north', 'south', 'east', 'west', 'nadir']  # Define DIRECTIONS here

    def __init__(self, api_baseurl, api_token):
        self.api_baseurl = api_baseurl
        self.api_token = api_token

    async def query_items(self, coord, direction, collection, limit=1):
        global session

        if session is None:
            raise RuntimeError("Session is not initialized")
        """
        Queries the STAC API for items based on a coordinate and other parameters asynchronously.
        
        :param coord: Coordinate [x, y].
        :param direction: Direction of the item images.
        :param collection: Collection to fetch items from.
        :param limit: Number of results to return.
        :return: Response data as JSON.
        """
        search_query = {
            "and": [
                {"intersects": [{"property": "geometry"}, {"type": "Point", "coordinates": coord}]}
            ]
        }
        
        if direction:
            search_query["and"].append({"eq": [{"property": "direction"}, direction]})
        
        if collection:
            search_query["and"].append({"eq": [{"property": "collection"}, collection]})
        
        query_string = json.dumps(search_query)
        query_encoded = urllib.parse.quote(query_string)
        
        url = (f"{self.api_baseurl}/search?limit={limit}&filter={query_encoded}"
               "&filter-lang=cql-json&filter-crs=http://www.opengis.net/def/crs/EPSG/0/25832"
               "&crs=http://www.opengis.net/def/crs/EPSG/0/25832")
        
        headers = {
            'token': self.api_token  # Using token as a header
        }
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    status_codes.add(response.status)
                    raise Exception(f"API request failed with status code {response.status}")
                response_data = await response.json()
                return response_data
        except aiohttp.ClientError as e:
            status_codes.add(response.status)
            error_log.add(e.message)
            logger.error(f"Error querying items: {e}")
            detailed_logger.error(f"Error querying items: {e}")
            raise

    async def query_images_for_center(self, center_coord, collection, kote=0):
        """
        Queries the STAC API for multiple directions around a coordinate and returns the images covering the area.
        
        :param center_coord: Coordinate.
        :return: Dictionary with direction URLs and image coordinates.
        """
        results = {}
        
        # Format the folder name based on coordinates
        coord_folder_name = f"{center_coord[0]}_{center_coord[1]}"
        coord_dir = os.path.join(cache_dir, coord_folder_name)
        os.makedirs(coord_dir, exist_ok=True)

        try:
            async with asyncio.TaskGroup() as tg:
                tasks = []  # Keep track of tasks
                for direction in self.DIRECTIONS:
                    detailed_logger.debug(f"Querying image from {direction}, {center_coord}")
                    task = tg.create_task(self.img_from_direction(center_coord, collection, kote, results, coord_dir, direction))
                    tasks.append(task)

                    # Wait for the task and check for exceptions
                    try:
                        await task
                    except Exception as e:
                        logger.error(f"Error in img_from_direction for '{center_coord}': {e}")
                        detailed_logger.error(f"Error in img_from_direction for '{center_coord}': {e}")
                        failed_jobs +=1
                        for t in tasks:
                            t.cancel()
                        break  # Exit the loop once an error is encountered
        except Exception as e:
            logger.error(f"TaskGroup exception for center {center_coord}: {e}")
            detailed_logger.error(f"TaskGroup exception for center {center_coord}: {e}")
            return

        await self.create_summary_image(coord_dir)

    async def create_summary_image(self, coord_dir):
        """
        Creates a summary image from cached cropped images in the given directory and saves it as a summary image.
        
        :param coord_dir: Directory where cropped images are cached.
        """
        try:
            # Check if summary image creation is enabled in settings
            if not image_summary:
                return
            
            # Search for all PNG images in the coord_dir
            image_files = [os.path.join(coord_dir, f) for f in os.listdir(coord_dir) if f.endswith('.png')]
            if not image_files:
                logger.warning(f"No images found in cache directory {coord_dir}")
                return
            
            # Sort files alphabetically to ensure consistent layout
            image_files.sort()

            # Check if summary image already exists
            summary_image_path = os.path.join(coord_dir, 'summary_image.png')
            if os.path.exists(summary_image_path):
                # Open the existing summary image to update it
                summary_image = Image.open(summary_image_path)
                detailed_logger.debug(f"Found existing summary image, updating it.")
            else:
                # Create a new summary image if it doesn't exist
                total_width = 0
                max_height = 0
                images = []

            # Open images and resize for layout
            for file in image_files:
                img = Image.open(file).resize((image_resize, image_resize))
                images.append(img)
                total_width += img.width
                max_height = max(max_height, img.height)

            # Create a new blank image to hold the summary
            summary_image = Image.new("RGB", (total_width, max_height))

            # Paste images side by side
            x_offset = 0
            for img in images:
                summary_image.paste(img, (x_offset, 0))
                x_offset += img.width

            # Save the summary image
            summary_image.save(summary_image_path, format='PNG')
            detailed_logger.debug(f"Summary image created/updated and saved at: {summary_image_path}")

        except Exception as e:
            detailed_logger.error(f"Failed to create summary image: {e}")
            
    async def fetch_and_crop_cog(self, image_url, direction, image_coord, coord_dir):
        """
        Fetches and crops an image from a Cloud Optimized GeoTIFF (COG).
        
        Args:
            image_url (str): URL to the COG file.
            image_coord (tuple): (x, y) pixel coordinates in the COG where the point of interest is located.
            crop_sizes (list): List of crop sizes (in pixels).
            cache_dir (str): Directory to save cropped images.
        
        Returns:
            dict: Dictionary with paths to cropped images.
        """
        results = {}
        image_x, image_y = image_coord

        # Define crop sizes (in pixels) and their corresponding output file names
        crop_outputs = {f"{direction}_box_{i+1}": os.path.join(coord_dir, f"cropped_{direction}_box_{i+1}.png") 
                                for i in range(len(crop_sizes))}
        
        try:
            # Open the COG directly using rasterio with remote access
            with rasterio.open(image_url) as src:
                for i, crop_size in enumerate(crop_sizes, start=1):
                    half_crop = crop_size // 2

                    # Adjust y-coordinate for top-left origin (invert y-coordinate)
                    adjusted_y = src.height - image_y

                    # Define the window of interest for partial read
                    window = Window(
                        col_off=max(0, image_x - half_crop),
                        row_off=max(0, adjusted_y - half_crop),
                        width=min(crop_size, src.width - (image_x - half_crop)),
                        height=min(crop_size, src.height - (adjusted_y - half_crop))
                    )

                    # Read the window from the COG
                    cropped_img = src.read(
                        out_shape=(3, int(window.height), int(window.width)),  # Reading RGB bands
                        window=window
                    ).transpose(1, 2, 0)  # Transform to (height, width, bands)

                    # Save the cropped image as JPEG
                    cropped_image_path = crop_outputs[f"{direction}_box_{i}"]  # Access the correct path in the dictionary

                    Image.fromarray(cropped_img).save(cropped_image_path, format='JPEG', quality=image_quality)
                    results[f'box_{i}'] = cropped_image_path

        except Exception as e:
            logger.error(f"Error fetching and cropping COG: {e}")
            raise Exception
        detailed_logger.debug(f"Cropped image: {results}")
        return results


    async def img_from_direction(self, center_coord, collection, kote, results, coord_dir, direction):
        global failed_jobs, failed_coordinates
        try:
            # Query the STAC API to get image metadata
            response = await self.query_items(center_coord, direction, collection)
            
            # Check if there are any features in the response
            if 'features' in response and len(response['features']) > 0:
                item = response['features'][0]
                image_url = item.get('assets', {}).get('data', {}).get('href')
                
                if not image_url:
                    error_message = f"No image URL found for direction '{direction}' at coordinate {center_coord}"
                    logger.error(error_message)
                    detailed_logger.error(error_message)
                    results[direction] = None
                    return

                # Update the image coordinate based on the provided center coordinate and elevation (kote)
                update_result = update_center(center_coord, item, kote)
                if update_result:
                    image_coord = update_result['imageCoord']

                    try:
                        # Asynchronously fetch and crop images at the specified sizes
                        image_coord = (image_coord[0], image_coord[1])
                        await self.fetch_and_crop_cog(
                            image_url, direction, image_coord, coord_dir
                        )
                    except Exception as e:
                        logger.error(f"Failed to fetch and crop image from COG for direction '{direction}': {e}")
                        detailed_logger.error(f"Failed to fetch and crop image from COG for direction '{direction}': {e}")
                        results[direction] = None
                else:
                    results[direction] = None
            else:
                detailed_logger.error(f"No features found in STAC response for direction '{direction}'")
                results[direction] = None

        except Exception as e:
            
            logger.error(f"Unhandled error in img_from_direction for '{center_coord}': {e}")
            detailed_logger.error(f"Unhandled error in img_from_direction for '{center_coord}': {e}")
            failed_coordinates.append(center_coord)
            results[direction] = None

class ElevationData:
    def __init__(self, api_dhm_tokena, api_dhm_tokenb):
        self.api_dhm_tokena = api_dhm_tokena
        self.api_dhm_tokenb = api_dhm_tokenb

    async def get_kote(self, point):
        global session
        if session is None:
            raise RuntimeError("Session is not initialized")
        point = f'POINT({point[0]}%20{point[1]})'
        url = (f'https://services.datafordeler.dk/DHMTerraen/DHMKoter/1.0.0/GEOREST/HentKoter'
            f'?username={self.api_dhm_tokena}&password={self.api_dhm_tokenb}&geop={point}')
        
        try: 
            async with session.get(url) as response:
                # Raise an exception for non-2xx HTTP status codes
                response.raise_for_status()
                response_data = await response.json()
        except aiohttp.ClientError as e:
            status_codes.add(response.status)
            error_message = f"Error querying elevation data: {e}"
            detailed_logger.debug(error_message)
            error_log.add(e.message)
            raise Exception("Failed to query elevation data") from e
        except ValueError as e:  # Handles JSON decoding issues
            logger.error(f"Error parsing JSON response: {e}")
            detailed_logger.error(f"Error parsing JSON response: {e}")
            raise Exception("Invalid JSON response") from e

        # Validate response data
        try:
            kote_data = response_data["HentKoterRespons"]["data"]
            kote = kote_data[0]["kote"]
        except (KeyError, IndexError) as e:
            error_message = f"Missing or invalid elevation data in response: {response_data}"
            logger.error(error_message)
            detailed_logger.error(error_message)
            raise Exception("No elevation data found") from e

        if kote is None:
            raise Exception("Elevation data is missing")
        return kote

# Function to read coordinates from a file
def read_coordinates_from_file(file_path):
    coordinates = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                x, y = map(float, line.strip().split())
                coordinates.append((x, y))
            except ValueError:
                logger.warning(f"Skipping invalid line in file: {line.strip()}")
                detailed_logger.warning(f"Skipping invalid line in file: {line.strip()}")
                
    return coordinates

def summary_log(total_coords, failed):
        end_time = time.time()
        total_runtime = end_time - start_time   
        
        # Logging 
        processed_coordinates = successful_jobs + failed_jobs
        summary_logger.info(f"Total coordinates processed: {processed_coordinates}/{total_coords}")
        summary_logger.info(f"Successful jobs: {successful_jobs}")
        summary_logger.info(f"Failed jobs: {failed_jobs}")

        #Write failed coordinates to log 
        with open("failed_coordinates.txt", "w") as f:
            for coord in failed_coordinates:
                f.write(f"{coord[0]} {coord[1]}\n")

        if failed == True:
            detailed_logger.critical(f" Too many failed attempts, process stopped after {total_runtime:.2f} seconds")
            logger.error(f"Too many failed attempts, process stopped after {total_runtime:.2f} seconds")
            summary_logger.error(f"ERROR: Process was stopped, after reaching fail threshold")
            summary_logger.info(f"Total runtime: {total_runtime:.2f}\n")

        if not failed:
            logger.info(f"Script finished. Total runtime: {end_time - start_time:.2f} seconds")
            detailed_logger.info(f"Script finished. Total runtime: {end_time - start_time:.2f} seconds")
            summary_logger.info(f"Total runtime: {total_runtime:.2f}\n")

        if status_codes: 
            summary_logger.error("Status-codes:")
            for code in status_codes:
                summary_logger.error(f"{code}")
        if error_log:
            unique_errors = {str(error).strip().lower() for error in error_log}  # Normalize errors
            summary_logger.error("Unique errors occured:")
            for error in unique_errors:
                summary_logger.error(f"{error}")

async def process_coordinate(processor, elevationProcessor, center_coord, collection, semaphore, total_coords):
    global successful_jobs, failed_jobs, threshold, progress
    async def handle_failure(e):
        global failed_jobs, progress
        
        failed_coordinates.append(center_coord)
        failed_jobs += 1
        progress += 1
        error_log.add(e)

        percentage = (progress / total_coords) * 100
        sys.stdout.write(f"\rProgress: {progress} / {total_coords} ({percentage:.2f}%) ")
        sys.stdout.flush()

        detailed_logger.error(f"Failed to fetch height data for {center_coord} after {retry_limit} attempts: {e}")
        logger.error(f"Failed to fetch height data for {center_coord}")

        if failed_jobs >= total_coords * (threshold / 100):
            summary_log(total_coords, True)
            sys.exit(1)
        return

    async with semaphore:  # Limit concurrent tasks
        # Retry fetching the elevation data
        kote = None
        for attempt in range(1, retry_limit + 1):
            try:
                kote = await elevationProcessor.get_kote(center_coord)
                if kote == None or kote == -9999.0 or kote == 0.0:
                    detailed_logger.debug(f"Elevation data is missing or invalid for {center_coord}, kote: {kote}")
                    break
                else:
                    detailed_logger.debug(f"Fetched kote sucessfully: {kote} for {center_coord}")
                    break  
            except Exception as e:
                if attempt == retry_limit:
                    await handle_failure(e)
                else:          
                    wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    detailed_logger.debug(f"Failed to fetch height data for {center_coord} after attempts: {attempt}, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
        # Retry fetching the STAC data
        if kote == None or kote == -9999.0 or kote == 0.0:
            detailed_logger.debug(f"Bad kote, skipping download for {center_coord}, kote: {kote}")
            raise Exception("Elevation data is missing or invalid")
        for attempt in range(1, retry_limit + 1):
            try:
                await processor.query_images_for_center(center_coord, collection, kote)
                detailed_logger.debug(f"Fetched image for: {center_coord}")
                break  
            except Exception as e:
                if attempt == retry_limit:
                    await handle_failure(e)
                else:
                    wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    detailed_logger.debug(f"Failed to fetch height data for {center_coord} after attempts: {attempt}, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)

        progress += 1
        successful_jobs += 1
        detailed_logger.info(f"Coordinate successfully processed: {center_coord}")
        percentage = (progress / total_coords) * 100
        sys.stdout.write(f"\rProgress: {progress} / {total_coords} ({percentage:.2f}%) ")
        sys.stdout.flush()

def remove_failed_coords():
    source_file = "failed_coordinates.txt"
    target_file = "coordinates.txt"
    try:
        # Read lines from source file
        with open(source_file, 'r', encoding='utf-8') as sf:
            lines_to_remove = set(sf.read().splitlines())

        # Read and filter lines from target file
        with open(target_file, 'r', encoding='utf-8') as tf:
            target_lines = tf.read().splitlines()

        # Filter and overwrite target file
        with open(target_file, 'w', encoding='utf-8') as tf:
            tf.writelines(line + '\n' for line in target_lines if line not in lines_to_remove)

        print("Coordinates successsfully removed from file")
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

async def main():
    global session
    await create_shared_session()
    args = parser.parse_args()
    # Read coordinates from the file
    if not args.file:
        print("Please provide the path to a file with coordinates using the -f flag.")
        sys.exit(1)

    coordinates = read_coordinates_from_file(args.file)
    total_coords = len(coordinates)
    detailed_logger.info(f"Loading {total_coords} coordinates from file...")

    if not coordinates:
        print("No valid coordinates found in the provided file.")
        sys.exit(1)

    # Set up a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent_requests)

    # Initialize the session here
    try:
        processor = STACImageProcessor(
            api_baseurl=os.getenv("api_baseurl"),
            api_token=os.getenv("api_token"),
        )
        elevationProcessor = ElevationData(
            api_dhm_tokena=os.getenv("api_dhm_tokena"),
            api_dhm_tokenb=os.getenv("api_dhm_tokenb")
        )

        tasks = []
        for center_coord in (coordinates):

            task = process_coordinate(processor, elevationProcessor, center_coord, collection, semaphore, total_coords)
            tasks.append(task)

        # Run all tasks concurrently
        detailed_logger.info(f"Running tasks concurrently")
        await asyncio.gather(*tasks, return_exceptions=True)

    finally:
        summary_log(total_coords, False)
        if failed_jobs > 0:
            response = input("Do you want to remove failed coordinates? (y/n): ").strip().lower()
            if response == 'y':
                remove_failed_coords()
                
        await close_shared_session()

if __name__ == "__main__":
    asyncio.run(main()) 