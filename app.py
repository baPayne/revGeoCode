from flask import Flask, flash, render_template, request, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import csv, os

import re
import json
import os
import sqlite3
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
import requests

# Internal imports
from db import init_db_command
from user import User
import config

#redis rq ################
from rq import Queue
from worker import conn

q = Queue(connection=conn)
from worker_func import csvReader
###########################


# Configuration --google auth
app = Flask(__name__)
app.config["CSV_UPLOADS"] = "uploads"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "random string"

Bootstrap(app)
# User session management setup--google auth
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)

# OAuth 2 client setup
client = WebApplicationClient(config.GOOGLE_CLIENT_ID)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def get_google_provider_cfg():
    return requests.get(config.GOOGLE_DISCOVERY_URL).json() 

def setLoginOutUrl():
    if current_user.is_authenticated == False:
        return 'login'     
    else:
        return 'logout'    

def checkUser():
    if current_user.is_authenticated == False:
        return "Login with Google account..."    
    else:
        return "Logout, " + str(current_user.email)   
        

# Naive database setup
    try:
        init_db_command()
    except sqlite3.OperationalError:
        # Assume it's already been created
        pass    
# --end google auth    

#db 
db = SQLAlchemy(app)
#create db model
class users(db.Model):
    id = db.Column('user_id', db.Integer, primary_key = True)
    firstName = db.Column('FirstName', db.String(25))
    lastName = db.Column('LastName', db.String(25))
    email = db.Column('Email', db.String(50))
    role = db.Column('Role', db.String(10))

    def __init__(self, firstName, lastName, email, role):
        self.firstName = firstName
        self.lastName = lastName
        self.email = email
        self.role = role  

class trans(db.Model):
    trans_id = db.Column('trans_id', db.Integer, primary_key = True)
    user_id = db.Column('user_id', db.Integer)
    csvFile = db.Column('filename', db.String(100))  

    def __init__(self, user_id, csvFile):
        self.user_id = user_id
        self.csvFile = csvFile        


 



@app.route('/', methods =["GET", "POST"])
def index():
    
    if request.method == "POST":
        
        if request.files:
            importFile = request.files["myFile"]
            filename = os.path.join(app.config["CSV_UPLOADS"], importFile.filename)
            filenameBase = filename
            suffix = 0
            for x in range (0,99):
                suffix = suffix + 1
                strng = "_" + str(suffix) + ".csv"
                filename = filenameBase.replace(".csv", strng)
                print(filename)
                if not os.path.exists(filename):
                    break        
                

            if not os.path.exists(filename):              
                user = users.query.filter(users.email == request.form['userEmail']).first()
                importFile.save(filename)
                job = trans(user_id=user.id ,csvFile=filename)
                db.session.add(job)
                db.session.commit()
                flash("Job number " + str(job.trans_id) +" has been added.", 'info')
                result = q.enqueue(csvReader, filename)
                print(result.get_id()+str(len(q)))
                redirect(url_for("processing"))
            else: 
                flash("File could not be uploaded. Please rename and try again", 'error')      
            
                    
    return render_template('index.html', currentUser=checkUser(), login_out=setLoginOutUrl())
#test routes for authentication    
@app.route("/auth")
def index1():
    print(config.GOOGLE_CLIENT_ID)
    if current_user.is_authenticated:
        return (
            "<p>Hello, {}! You're logged in! Email: {}</p>"
            "<div><p>Google Profile Picture:</p>"
            '<img src="{}" alt="Google profile pic"></img></div>'
            '<a class="button" href="/logout">Logout</a>'.format(
                current_user.name, current_user.email, current_user.profile_pic
            )
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'  

@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)   

@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")    
    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]      
    
    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(config.GOOGLE_CLIENT_ID, config.GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json())) 

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    # Create a user in your db with the information provided
    # by Google
    user = User(
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )


    # Doesn't exist? Add it to the database.
    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email, picture)

    # Begin user session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("index"))    

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/processing")
def processing():
    return render_template("processing.html")
     



@app.route('/admin', methods =["GET", "POST"])
def admin():
    if request.method == 'POST':
        if not request.form['inputFirstName'] or not request.form['inputLastName'] or not request.form['inputEmail'] or not request.form['inputRole']:
           flash("Please complete all fields", 'error')
        else:
            user = users(firstName=request.form['inputFirstName'], lastName=request.form['inputLastName'], email=request.form['inputEmail'], role=request.form['inputRole'])   
            db.session.add(user)
            db.session.commit()
            flash('New Record Added!', 'success')
            
    return render_template('admin.html',all_users = users.query.all(), currentUser=checkUser(), login_out=setLoginOutUrl() ) 

@app.route('/delete-user.html/<user_id>', methods =["GET", "POST"])
def delete_user(user_id):
    if request.method == 'POST':
        user = users.query.get(user_id)
        db.session.delete(user)
        db.session.commit()
        flash("Record " + str(user.id) + " " + user.firstName + " " + user.lastName + " deleted", 'info')
        return redirect('/admin')
    #else: if not post, then redirect somewhere else


@app.route('/edit-user.html/<user_id>', methods =["GET", "POST"])
def edit_user(user_id):
    if request.method == 'POST':
        user = users.query.get(user_id)
        return render_template('/edit-user.html', user=user, currentUser=checkUser(), login_out=setLoginOutUrl())
    #else: if not post, then redirect somewhere else
        
@app.route('/update-user/<user_id>', methods =["GET", "POST"])
def update_user(user_id):
    if request.method == 'POST':
        if not request.form['inputFirstName'] or not request.form['inputLastName'] or not request.form['inputEmail'] or not request.form['inputRole']:
           flash("Please complete all fields", 'error')
        else:
            user = users.query.get(user_id)
            user.firstName = request.form['inputFirstName']
            user.lastName = request.form['inputLastName']
            user.email = request.form['inputEmail']
            user.role = request.form['inputRole']   
            db.session.commit()
            flash('Record Updated!', 'success')
        return redirect('/admin')
    #else: if not post, then redirect somewhere else

@app.route('/job-list', methods=['GET','POST'])
def show_jobs():
    return render_template('jobs.html', jobs=trans.query.all(), currentUser=checkUser(), login_out=setLoginOutUrl())  

@app.route('/delete-job.html/<trans_id>', methods =["GET", "POST"])
def delete_job(trans_id):
    if request.method == 'POST':
        job = trans.query.get(trans_id)
        try:
            print(job.csvFile)
            os.remove(job.csvFile)
            db.session.delete(job)
            db.session.commit()
            flash("Job " + str(trans_id)  + " has been canceled and file removed", 'info')
            return redirect('/job-list') 
        except Exception as error:
            flash("Job " + str(trans_id)  + " could not be removed", 'error')
            return redirect('/job-list') 

@app.route('/cancel-job.html/<trans_id>', methods =["GET", "POST"])
def cancel_job(trans_id):
    if request.method == 'POST':
        job = trans.query.get(trans_id)
        db.session.delete(job)
        db.session.commit()
        flash("Job " + str(trans_id)  + " has been canceled, but file remains", 'info')
        return redirect('/job-list') 
                   
        
        
             


       

if __name__ == "__main__":
    app.run(debug =True,ssl_context="adhoc") #,ssl_context="adhoc"
    

    
