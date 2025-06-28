import sys
import os
import pytest
import asyncio
import aiohttp
import shutil
from aiohttp import ClientSession, TCPConnector, ClientResponseError
from unittest.mock import AsyncMock
from unittest import mock
from dotenv import load_dotenv
from aioresponses import aioresponses

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from download_from_coordinates import *
detailed_logger.info(f"RUNNING TEST ENVIRONMENT \n")

# Initial setup variables
coordinates = [
    (728368.05, 6174304.56),
    (700169.47, 6211841.32),
    (728368.05, 6174304.56),
    (700169.47, 6211841.32)

]

# Load environment variables from a .env file
load_dotenv()

detailed_logger.setLevel(logging.DEBUG)

processor_mock = AsyncMock()
elevation_mock = AsyncMock()

threshold = 50
collection = "skraafotos2021"
total_coords = len(coordinates)

 # Set up a semaphore to limit concurrency
semaphore = asyncio.Semaphore(10)

#Folder that need to be removed for before test
test_folders = [
    "728368.05_6174304.56"
]

#Setup before each test
@pytest.fixture(autouse=True)
async def before_each():
    #Resets variable counters
    reset_counters()
    await create_shared_session()
    
    #Removes all cached images
    for folder in test_folders: 
        folder_path = os.path.join("image_cache", folder)
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
    yield
    await close_shared_session()

#Unit testing of process_coordinates
@pytest.mark.asyncio
async def test_process_coordinate():
    detailed_logger.info("Test for process_coordinate on success")
    total_coords = len(coordinates)

    mock_kote = elevation_mock.get_kote.return_value = 10

    semaphore = asyncio.Semaphore(10)
    for coordinate in coordinates:
        await process_coordinate(
            processor_mock, elevation_mock, coordinate, "skraafoto2021", semaphore, total_coords
        ) 

    # Assert the mocked methods were called as expected
    processor_mock.query_images_for_center.assert_called_with(coordinates[total_coords-1], "skraafoto2021", mock_kote)
    elevation_mock.get_kote.assert_called_with(coordinates[total_coords-1])


    #Asserts that all coordinates are processed
    assert processor_mock.query_images_for_center.call_count == total_coords 
    assert elevation_mock.get_kote.call_count == total_coords

    detailed_logger.info("Calls correctly made") 

    detailed_logger.info(f"Test PASSED\n")


@pytest.mark.asyncio
async def test_process_coordinate_failure():
    detailed_logger.info("Test for process_coordinate on failure")
    total_coords = len(coordinates)

     # Simulate a 404 error in query_images_for_center
    processor_mock.query_images_for_center.side_effect = ClientResponseError(
        request_info=mock.Mock(),
        history=(),
        status=404,
        message="Not Found"
    )

    expected_lines = [
        "728368.05 6174304.56",
        "700169.47 6211841.32",
        "728368.05 6174304.56",
        "700169.47 6211841.32"
    ]

    semaphore = asyncio.Semaphore(10)
    for coordinate in coordinates:
        try:
            await process_coordinate(
                processor_mock, elevation_mock, coordinate, "skraafoto2021", semaphore, total_coords
            )
        except SystemExit as e:
            #Assert that system exit code = 1
            assert e.code == 1
            detailed_logger.info("System correctly exited with code 1")
            break
    
    with open("failed_coordinates.txt", 'r') as file:
        # Read and strip lines from the file
        actual_lines = [line.strip() for line in file.readlines()]

    threshold_calls = total_coords * (threshold / 100)
    assert processor_mock.query_images_for_center.call_count <= total_coords * 6 * (threshold / 100) #Checks that call count doesnt exceed threshold
    assert elevation_mock.get_kote.call_count == threshold_calls * retry_limit

    detailed_logger.info("Calls correctly made, threshold held")

    # Check if the file contains the correct number of lines
    assert len(actual_lines) == len(expected_lines)* (threshold / 100), (
        f"Line count mismatch: expected {len(expected_lines)} lines but found {len(actual_lines)}."
    )

    # Check if each line matches the expected lines
    for i, (expected, actual) in enumerate(zip(expected_lines, actual_lines)):
        assert expected == actual, (
            f"Mismatch at line {i + 1}: expected '{expected}' but found '{actual}'."
        )
    detailed_logger.info("Failed coordinates correctly logged")

    detailed_logger.info(f"Test PASSED\n")

# Unit testing get_kote
@pytest.mark.asyncio
async def test_get_kote():
    session = aiohttp.ClientSession(connector=TCPConnector(limit_per_host=30))
    detailed_logger.info("Test for get_kote on success")
    # Mock the point input and API tokens
    point = (728368.05, 6174304.56)
    api_dhm_tokena = "mock_user"
    api_dhm_tokenb = "mock_pass"

    # Expected URL
    expected_url = (
        f"https://services.datafordeler.dk/DHMTerraen/DHMKoter/1.0.0/GEOREST/HentKoter"
        f"?username={api_dhm_tokena}&password={api_dhm_tokenb}&geop=POINT({point[0]}%20{point[1]})"
    )

    # Mock response data
    mocked_response = {
        "HentKoterRespons": {
            "data": [{"kote": 21.244518}]
        }
    }

    # Use aioresponses to mock the HTTP request

    async with session:
        with aioresponses() as mock:
            mock.get(expected_url, payload=mocked_response)

            # Call the function being tested
            elevation_instance = ElevationData(api_dhm_tokena, api_dhm_tokenb)  
            result = await elevation_instance.get_kote(point)

    # Assert the result matches the mocked kote value
    assert result == 21.244518
    detailed_logger.info("Kote fetched successfully")
    detailed_logger.info(f"Test PASSED\n")


@pytest.mark.asyncio
async def test_get_kote_failure():
    session = aiohttp.ClientSession(connector=TCPConnector(limit_per_host=limit_per_host))
    detailed_logger.info("Test for get_kote on failure")
    point = (728368.05, 6174304.56)
    api_dhm_tokena = "mock_user"
    api_dhm_tokenb = "mock_pass"
    expected_url = (
        f"https://services.datafordeler.dk/DHMTerraen/DHMKoter/1.0.0/GEOREST/HentKoter"
        f"?username={api_dhm_tokena}&password={api_dhm_tokenb}&geop=POINT({point[0]}%20{point[1]})"
    )

    async with session:
        with aioresponses() as mock:
            mock.get(expected_url, status=500)
            elevation_instance = ElevationData(api_dhm_tokena, api_dhm_tokenb)
            with pytest.raises(Exception, match="Failed to query elevation data"):
                await elevation_instance.get_kote(point)
    detailed_logger.info("Exception correctly thrown on error")
               
    detailed_logger.info(f"Test PASSED\n")


####################### INTEGRATION TESING #######################

async def test_API_calls():
    detailed_logger.info("Test for API handling")
    test_coord = (728368.05, 6174304.56)
    bad_coord = (1231993123, 12399123131)

    try:
        # Initialize processors
        processor = STACImageProcessor(
            api_baseurl=os.getenv("api_baseurl"),
            api_token=os.getenv("api_token"),
        )
        elevationProcessor = ElevationData(
            api_dhm_tokena=os.getenv("api_dhm_tokena"),
            api_dhm_tokenb=os.getenv("api_dhm_tokenb"),
        )
    except Exception as e: 
        detailed_logger.error(f"Error while initializing: {e}")

    try: 
        #Testing get_kote on success
        kote = await elevationProcessor.get_kote(test_coord)
        assert kote == 2.5650272
        detailed_logger.info("Kote sucessfully fetched")

        #Testing process_coordinates on doesnt throw exception
        await process_coordinate(processor, elevationProcessor, test_coord, collection, semaphore, total_coords)

        #Asserting that an image for the coordinate is stored
        parent_path = "image_cache"
        folder_name = "728368.05_6174304.56"
        folder_path = os.path.join(parent_path, folder_name)
        
        assert os.path.isdir(folder_path), f"Folder '{folder_name}' does not exist in the parent path '{parent_path}'"
        detailed_logger.info("Image correctly fetched and stored")


    except Exception as e: 
        detailed_logger.error(f"Exception thrown while testing: {e}")
        pytest.fail(f"Exception thrown while testing: {e}")

    try: 
        #Testing get_kote on fail
        kote = await elevationProcessor.get_kote(bad_coord)
    except Exception as e: 
        assert e.args[0] == 'Elevation data is missing'
        detailed_logger.info("Exception correctly thrown for get_kote")
    
    try:
        #Testing process_coordinates on fail
        await process_coordinate(processor, elevationProcessor, bad_coord, collection, semaphore, total_coords)
    except Exception as e: 
        assert e.args[0] == 'Elevation data is missing or invalid'
        detailed_logger.info(f"Exception correctly thrown for process_coordinate")
    
    detailed_logger.info(f"Test PASSED\n")
    
    
    
