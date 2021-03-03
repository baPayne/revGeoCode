import requests
import reverse_geocoder as rg
import yagmail
import os, csv

from keyring import get_keyring
print(get_keyring())


#sendemail
def sendEmailAtt(emailaddr,file_attachment):
    receiver = emailaddr
    body = "Thanks for using Reverse Geocoder.  Your results are attached. \n \n Thanks, \n\n Byron"
    
    yag = yagmail.SMTP(user='butler.mydev@gmail.com')
    yag.send(
        to=emailaddr,
        subject="Reverse Geocoding Results Attached!",
        contents=body, 
        attachments=file_attachment,
    )

#reverse geocode function
def reverseGeocode(coords):
    result = rg.search(coords)
    return(result[0])  


#read contents of uploaded csv File
def csvReader(in_file,outputFilename,emailaddr):
    
    with open(outputFilename, 'a', newline='') as csvfile_out:
        writer = csv.writer(csvfile_out, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
        with open(in_file, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='|')
            for line in reader:
                coords = (line[0], line[1])
                result = reverseGeocode(coords)
                writer.writerow([result['lat'], result['lon'], result['name'], result['admin1'], result['cc']])
                print(f"lattitude: {result['lat']}, longitude: {result['lon']}, city: {result['name']}, state: {result['admin1']}, country: {result['cc']}")  
    csvfile_out.close()
    sendEmailAtt(emailaddr,outputFilename)
    return("Job Complete")            

