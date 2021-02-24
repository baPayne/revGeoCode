import requests
import reverse_geocoder as rg
import os, csv

#reverse geocode function
def reverseGeocode(coords):
    result = rg.search(coords)
    for res in result:
        print(res)  


#read contents of uploaded csv File
def csvReader(in_file):
    with open(in_file, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for line in reader:
            coords = (line[0], line[1])
            reverseGeocode(coords)
            print(line)

