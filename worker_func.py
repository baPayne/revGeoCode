import requests
import reverse_geocoder as rg
import yagmail
import os, csv
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from keyring import get_keyring

#connect to transaction database in order to change status state of job
conn = sqlite3.connect('users.sqlite3')
print("DB opened from worker_func")

#get current job and change status to in process
def getJob(job_nmbr):
    conn.execute("UPDATE trans set status = \"in process\" WHERE trans_id = ?", (job_nmbr,))
    conn.commit()
    job = conn.execute("SELECT trans_id, status FROM trans WHERE trans_id = ?", (job_nmbr,)).fetchone()
    return (job[1])

#get current job and change status to complete
def finishJob(job_nmbr):
    conn.execute("UPDATE trans set status = \"complete\" WHERE trans_id = ?", (job_nmbr,))
    conn.commit()
    job = conn.execute("SELECT trans_id, status FROM trans WHERE trans_id = ?", (job_nmbr,)).fetchone()
    return (job[1])  


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
def csvReader(in_file,outputFilename,emailaddr,job_id):

    status = getJob(job_id)
    print(status)
        
    with open(outputFilename, 'a', newline='') as csvfile_out:
        writer = csv.writer(csvfile_out, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
        with open(in_file, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='|')
            for line in reader:
                #make sure Line has text
                if (line[0] and line[1]):
                    #reformat to put text in proper format
                    if ('S' in line[0]):
                        line[0] = line[0].replace('S','-')
                    elif ('N' in line[0]):
                        line[0] = line[0].replace('N', '') 
                      

                    if ('W' in line[1]):
                        line[1] = line[1].replace('W','-')
                    elif ('E' in line[1]):
                        line[1] = line[1].replace('E', '')    

                    try:
                        line[0] = float(line[0])    
                        line[1] = float(line[1])
                        coords = (line[0], line[1])
                        result = reverseGeocode(coords)
                        writer.writerow([result['lat'], result['lon'], result['name'], result['admin1'], result['cc']])
                        print(f"lattitude: {result['lat']}, longitude: {result['lon']}, city: {result['name']}, state: {result['admin1']}, country: {result['cc']}")
                    except:
                        print("Incorrect format, line skipped") 
                        continue   

                    
    status = finishJob(job_id)
    print(status)
    conn.close()
    csvfile_out.close()
    sendEmailAtt(emailaddr,outputFilename)
    
    return("Job Complete")            

