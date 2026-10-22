# E-Learning Course Analytics System — Web Application

## Features
- Browser-based dashboard built with Flask
- MySQL data storage
- Course, learner, enrolment and activity management
- Completion-rate and weekly-activity reports using Pandas and NumPy
- Matplotlib charts
- 14-day inactivity review list
- Responsive layout for desktop and mobile

## 1. Prerequisites
Install Python 3.10+ and MySQL Server. Create the database and tables using the `database.sql` file from your original project. The tables must be named `courses`, `learners`, `enrollments`, and `activities` with the columns in the project guide.

## 2. Install
Open a terminal in this folder:
```bash
python -m venv .venv
```
Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```
Install packages:
```bash
python -m pip install -r requirements.txt
```

## 3. Configure MySQL
Set environment variables before starting the app.

PowerShell example:
```powershell
$env:DB_HOST="localhost"
$env:DB_USER="root"
$env:DB_PASSWORD="YOUR_MYSQL_PASSWORD"
$env:DB_NAME="elearning_analytics"
$env:DB_PORT="3306"
$env:FLASK_SECRET_KEY="replace-with-a-long-random-secret"
```
Do not commit real passwords or secrets to a public repository.

## 4. Run the website
```bash
python app.py
```
Open http://127.0.0.1:5000 in your browser. Keep the terminal and Python process running while you use the local site.

## 5. Sharing with group members
`127.0.0.1` is only your own computer. To share a permanent URL, deploy the Flask app to a hosting provider and use a hosted MySQL database reachable from that provider. Configure the same `DB_*` environment variables in the hosting dashboard. Do not use your laptop's `localhost` database for a cloud deployment: `localhost` on the hosting service refers to the host itself.

For a classroom demo on the same Wi-Fi, you may run Flask with `app.run(host="0.0.0.0", port=5000)` and share your laptop's LAN IP as `http://YOUR-LAN-IP:5000`; this is temporary and only works on the same network when firewall rules allow it. Do not expose a development server directly to the public internet.

## Methodology notes
- Completion rate denominator = active + completed enrolments; withdrawn enrolments are excluded.
- Completion is an explicit status recorded by the operator, not inferred from lesson records.
- An active enrolment is flagged for review if there has been no recorded activity for 14 days or more. Enrolments with no activity records use the enrolment timestamp as a baseline and are labelled for verification.
- Missing activity is not evidence of lack of learning.
- Use fictional/sample data for demonstrations unless you have permission to use real learner records.

## Important
This is a college-project prototype, not a production learning management system. Before public deployment, add authentication/authorization, CSRF protection, secure secrets management, production WSGI serving, and backups.
