from flask import Flask, flash, render_template, request, redirect
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import csv, os
import reverse_geocoder as rg

app = Flask(__name__)
app.config["CSV_UPLOADS"] = "uploads"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config['SECRET_KEY'] = "random string"
Bootstrap(app)

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

#reverse geocode function
def reverseGeocode(coords):
    result = rg.search(coords)
    for res in result:
        print(res)  
 

@app.route('/', methods =["GET", "POST"])
def index():
    if request.method == "POST":
        if request.files:
            importFile = request.files["myFile"]
        #    print(importFile.filename)
            filename = os.path.join(app.config["CSV_UPLOADS"], importFile.filename)
            filenameBase = filename
            #filenameBase =  importFile.filename

            suffix = 0
            while True:
                suffix = suffix + 1
                strng = "_" + str(suffix) + ".csv"
                filename = filenameBase.replace(".csv", strng)
                print(filename)
                if not os.path.exists(filename):
                    importFile.save(filename)
                    user = users.query.filter(users.email == request.form['userEmail']).first()
                    job = trans(user_id=user.id ,csvFile=filename)
                    db.session.add(job)
                    db.session.commit()
                    flash("Job number " + str(job.trans_id) +" has been added.", 'info')
                    break
                if suffix >= 99: 
                    flash("File could not be uploaded. Please rename and try again", 'error')
                    break
                
        #    csvReader(importFile.filename)
        #    return redirect(request.url)
                        
           
            # add transaction to processing list
            

    return render_template('index.html')

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
            
    return render_template('admin.html',all_users = users.query.all() ) 

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
        return render_template('/edit-user.html', user=user)
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
    return render_template('jobs.html', jobs=trans.query.all())  

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
                   
        
        
             

#read contents of uploaded csv File
def csvReader(in_file):
    with open(os.path.join(app.config["CSV_UPLOADS"], in_file), newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for line in reader:
            coords = (line[0], line[1])
            reverseGeocode(coords)
            print(line)
       

if __name__ == "__main__":
    app.run(debug =True)
    db.create_all()
