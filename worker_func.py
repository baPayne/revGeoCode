import requests
import reverse_geocoder as rg


#reverse geocode function
def reverseGeocode(coords):
    result = rg.search(coords)
    for res in result:
        print(res)  