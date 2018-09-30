from flask import Flask
from flask import render_template, send_from_directory
from flask import request, url_for, redirect, session, flash
from datetime import date
from datetime import time
from datetime import datetime
from werkzeug import secure_filename
import dbHandler
import re, os
import json
import requests
from hashlib import md5

app = Flask(__name__)
app.config['SECRET_KEY'] = 'e5ac358c-f0bf-11e5-9e39-d3b532c10a28'

def make_dir(upload_dir):
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)


# @app.after_request
# def after_request(response):
#     response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     return response

@app.route('/', methods=['POST', 'GET'])
@app.route('/home', methods=['POST', 'GET'])
def index():
    if 'username' in session:
        username = session['username']
        # If company
        if re.match( "^.*@.*$", username):
            company = dbHandler.getCompany(username)
            jobopenings = dbHandler.getJobOpenings(username)
            students = dbHandler.getAllStudents()
            return render_template('recruiter_dashboard.html', students=students, company=company[0], jobopenings=jobopenings, recruiter=True)
        else:
            resume = list_resume(username)
            studentdata = dbHandler.getStudentData(username)
            companies = dbHandler.getAllCompanies()
            return render_template('student_dashboard.html', companies=companies, username=username, resume=resume, student=True, studentdata=studentdata)
    return render_template('index.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if 'username' in session:
        return redirect(url_for('index'))
    else:
        return render_template('register.html')

@app.route('/student_register', methods=['POST', 'GET'])
def student_register():
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        if not dbHandler.uniqstudent(username):
            return render_template('register.html', notUniq="nonunique")
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        dbHandler.insertStudent(username, password, email, name)
        upload_dir = './resumes/'
        upload_dir = upload_dir + username
        make_dir(upload_dir)
        session['username'] = username
        return redirect(url_for('index'))
    else:
        return render_template('register.html')

@app.route('/recruiter_register', methods=['POST', 'GET'])
def recruiter_register():
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form['email']
        if not dbHandler.uniqrecruiter(email):
            return render_template('register.html', notUniq="nonunique")
        password = request.form['password']
        company = request.form['company']
        dbHandler.insertRecruiter(company, password, email)
        session['username'] = email
        return redirect(url_for('index'))
    else:
        return render_template('register.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if 'username' in session:
        return redirect(url_for('index'))
    else:
        return render_template('login.html')

@app.route('/student_login', methods=['POST', 'GET'])
def student_login():
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if dbHandler.allowLoginStudent(username, password):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', failedLogin="failed")
    else:
        return render_template('login.html')

@app.route('/recruiter_login', methods=['POST', 'GET'])
def recruiter_login():
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if dbHandler.allowLoginRecruiter(email, password):
            session['username'] = email
            return redirect(url_for('index'))
        else:
            return render_template('login.html', failedLogin="failed")
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    if 'username' in session:
        session.pop('username', None)
    return redirect(url_for('index'))

def list_resume(username):
    path = './resumes/' + username
    onlyfiles = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    if len(onlyfiles) == 0:
        return False
    else:
        return onlyfiles[0]

@app.route('/uploader', methods = ['GET', 'POST'])
def upload_resume():
    if 'username' in session:
        username = session['username']
        if request.method == 'POST':
            file = request.files['file']
            upload_dir = './resumes/'
            upload_dir = upload_dir + username
            filename = secure_filename(file.filename)
            file.save(os.path.join(upload_dir, filename))
    return redirect(url_for('index'))

@app.route('/downloader/<username>', methods = ['GET', 'POST'])
def download_resume(username):
    resume = list_resume(username)
    return send_from_directory('./resumes/' + username, resume, as_attachment=True)

@app.route('/deleter', methods = ['GET', 'POST'])
def delete_resume():
    username = session['username']
    resume = list_resume(username)
    os.remove('./resumes/' + username + '/' + str(resume))
    return redirect(url_for('index'))

@app.route('/create_opening', methods = ['GET', 'POST'])
def create_job_opening():
    if 'username' in session:
        if request.method == 'POST':
            email = session['username']
            title = request.form['title']
            job_description = request.form['job_description']
            company_id = dbHandler.getCompanyID(email)
            dbHandler.createJobOpening(company_id, title, job_description)
    return redirect(url_for('index'))

@app.route('/delete_opening', methods = ['GET', 'POST'])
def delete_job_opening():
    if 'username' in session:
        if request.method == 'POST':
            id = request.args.get('id')
            dbHandler.deleteJobOpening(id)
    return redirect(url_for('index'))

@app.route('/search', methods=['GET', 'POST'])
def search_jobs():
    if 'username' in session:
        if request.method == 'POST':
            title = request.form['search']
            jobs = dbHandler.getJobs(title)
            companies = dbHandler.getCompanies(title)
            return render_template('job_openings.html', jobs=jobs, companies=companies)
    return redirect(url_for('index'))

@app.route('/user_search', methods=['GET', 'POST'])
def search_candidate():
    if 'username' in session:
        if request.method == 'POST':
            username = request.form['search']
            name = dbHandler.getUser(username)
            studentdata = dbHandler.getStudentData(username)
            if not studentdata:
                return redirect(url_for('index'))
            resume = list_resume(username)
            studentdata = dbHandler.getStudentData(username)
            return render_template('student_dashboard.html', studentdata=studentdata, student=False, username=username, name=name[0], resume=resume)
        username = request.args.get('student')
        name = dbHandler.getUser(username)
        resume = list_resume(username)
        studentdata = dbHandler.getStudentData(username)  
        return render_template('student_dashboard.html', studentdata=studentdata, student=False, username=username, name=name[0], resume=resume)
    return redirect(url_for('index'))

@app.route('/company', methods=['GET', 'POST'])
def viewCompany():
    company_id = request.args.get('company_id')
    if 'username' in session:
        email = dbHandler.getCompanyEmail(company_id)
        company = dbHandler.getCompany(email)
        jobopenings = dbHandler.getJobOpenings(email)
        return render_template('recruiter_dashboard.html', company=company[0], jobopenings=jobopenings, recruiter=False)
    return redirect(url_for('index'))

@app.route('/job', methods=['GET', 'POST'])
def viewJob():
    job_id = request.args.get('job_id')
    if 'username' in session:
        jobopening = dbHandler.getJob(job_id)
        return render_template('view_job.html', jobopening=jobopening)
    return redirect(url_for('index'))

@app.route('/github', methods=['GET', 'POST'])
def add_github_link():
    if 'username' in session:
        if request.method == 'POST':
            username = session['username']
            link = request.form['github']
            dbHandler.addGithubLink(link, username)
    return redirect(url_for('index'))

@app.route('/codeforces', methods=['GET', 'POST'])
def add_codeforces_link():
    if 'username' in session:
        if request.method == 'POST':
            username = session['username']
            link = request.form['codeforces']
            dbHandler.addCodeforcesLink(link, username)
    return redirect(url_for('index'))

def getGithubDetails(github_handle):
    stars = 0
    languages = []
    response = requests.get("https://api.github.com/users/" + github_handle + "/repos")
    data = response.json()
    for repo in data:
        stars = stars + repo['stargazers_count']
        if repo['language']:
            if repo['language'] not in languages:
                languages.append(repo['language'])
    print(stars)
    print(languages)

def getCodeforcesDetails(codeforces_handle):
    rating = 0
    rank = "unavailable"
    response = requests.get("https://codeforces.com/api/user.info?handles=" + codeforces_handle)
    data = response.json()
    for user in data['result']:
        rating = user['rating']
        rank = user['rank']
    print(rating)
    print(rank)


if __name__ == '__main__':
    app.run(debug=True)