from geopy.geocoders import Nominatim

def get_coordinates(address):
    geolocator = Nominatim(user_agent="skraafoto")
    location = geolocator.geocode(address)
    if location:
        return (location.latitude, location.longitude)
    else:
        return None

address = "Kovangen 520"
coordinates = get_coordinates(address)

if coordinates:
    print(f"Coordinates for '{address}': {coordinates}")
else:
    print(f"Could not find coordinates for '{address}'.")
