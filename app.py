import os
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as np

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-development-key")

def get_connection():
    # Render MySQL providers commonly supply MYSQLHOST/MYSQLUSER/etc.; local fallback below.
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST", os.getenv("DB_HOST", "localhost")),
        user=os.getenv("MYSQLUSER", os.getenv("DB_USER", "root")),
        password=os.getenv("MYSQLPASSWORD", os.getenv("DB_PASSWORD", "")),
        database=os.getenv("MYSQLDATABASE", os.getenv("DB_NAME", "elearning_analytics")),
        port=int(os.getenv("MYSQLPORT", os.getenv("DB_PORT", "3306"))),
    )

def query_all(sql, params=()):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def execute(sql, params=()):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()

def build_analytics():
    courses = query_all("""
        SELECT c.course_id, c.course_name, c.category,
               COUNT(DISTINCT e.enrollment_id) AS enrollments,
               COUNT(DISTINCT CASE WHEN e.status='completed' THEN e.enrollment_id END) AS completed
        FROM courses c LEFT JOIN enrollments e ON e.course_id=c.course_id
        GROUP BY c.course_id, c.course_name, c.category
        ORDER BY enrollments DESC, c.course_name
    """)
    for c in courses:
        # Completion denominator: all enrolments in that course, including active and completed.
        c["completion_rate"] = round((c["completed"] / c["enrollments"] * 100), 1) if c["enrollments"] else 0

    learners = query_all("""
        SELECT l.learner_id, l.roll_no, l.learner_name,
               COUNT(DISTINCT e.enrollment_id) AS enrolled_courses,
               COUNT(DISTINCT CASE WHEN e.status='completed' THEN e.enrollment_id END) AS completed_courses,
               ROUND(AVG(CASE WHEN e.status='completed' THEN 100 ELSE
                   COALESCE(p.progress_pct, 0) END), 1) AS avg_progress,
               ROUND(AVG(pr.correct_count / NULLIF(pr.question_count, 0) * 100), 1) AS accuracy
        FROM learners l
        LEFT JOIN enrollments e ON e.learner_id=l.learner_id
        LEFT JOIN (
            SELECT enrollment_id, ROUND(AVG(completed)*100,1) AS progress_pct
            FROM activities GROUP BY enrollment_id
        ) p ON p.enrollment_id=e.enrollment_id
        LEFT JOIN practice_results pr ON pr.enrollment_id=e.enrollment_id
        GROUP BY l.learner_id, l.roll_no, l.learner_name
        ORDER BY l.roll_no
    """)
    for l in learners:
        l["avg_progress"] = float(l["avg_progress"] or 0)
        l["accuracy"] = float(l["accuracy"] or 0)

    activity_rows = query_all("""
        SELECT DATE_FORMAT(activity_date, '%x-W%v') AS week_label,
               COUNT(*) AS total_activities,
               SUM(completed=1) AS completed_activities
        FROM activities
        GROUP BY DATE_FORMAT(activity_date, '%x-W%v')
        ORDER BY MIN(activity_date)
    """)
    activity_types = query_all("""
        SELECT activity_type, COUNT(*) AS total
        FROM activities GROUP BY activity_type ORDER BY total DESC
    """)
    inactive = query_all("""
        SELECT l.learner_name, l.roll_no, c.course_name, e.enrolled_at,
               MAX(a.activity_date) AS last_activity
        FROM enrollments e
        JOIN learners l ON l.learner_id=e.learner_id
        JOIN courses c ON c.course_id=e.course_id
        LEFT JOIN activities a ON a.enrollment_id=e.enrollment_id
        WHERE e.status='active'
        GROUP BY e.enrollment_id, l.learner_name, l.roll_no, c.course_name, e.enrolled_at
        HAVING (last_activity IS NULL AND e.enrolled_at < DATE_SUB(CURDATE(), INTERVAL 14 DAY))
            OR (last_activity IS NOT NULL AND last_activity < DATE_SUB(CURDATE(), INTERVAL 14 DAY))
        ORDER BY last_activity
    """)
    # This is a follow-up list based on an explicit 14-day rule, not proof that a learner is not learning.
    weekly = pd.DataFrame(activity_rows)
    if not weekly.empty:
        weekly["total_activities"] = pd.to_numeric(weekly["total_activities"], errors="coerce").fillna(0)
        weekly["completed_activities"] = pd.to_numeric(weekly["completed_activities"], errors="coerce").fillna(0)
    summary = {
        "learners": len(learners),
        "enrollments": int(sum(c["enrollments"] for c in courses)),
        "completed": int(sum(c["completed"] for c in courses)),
        "completion_rate": round(sum(c["completed"] for c in courses) / sum(c["enrollments"] for c in courses) * 100, 1)
            if sum(c["enrollments"] for c in courses) else 0,
        "activity_count": int(sum(x["total_activities"] for x in activity_rows)),
        "inactive_count": len(inactive),
    }
    return courses, learners, activity_rows, activity_types, inactive, summary

@app.route("/")
def dashboard():
    courses, learners, activity_rows, activity_types, inactive, summary = build_analytics()
    return render_template("dashboard.html", courses=courses, learners=learners,
                           activity_rows=activity_rows, activity_types=activity_types,
                           inactive=inactive, summary=summary)

@app.route("/learners")
def learner_list():
    courses, learners, *_ = build_analytics()
    return render_template("learners.html", learners=learners)

@app.route("/add-learner", methods=["GET", "POST"])
def add_learner():
    if request.method == "POST":
        name = request.form.get("learner_name", "").strip()
        roll = request.form.get("roll_no", "").strip()
        if not name or not roll:
            flash("Enter both learner name and roll number.", "error")
        else:
            try:
                execute("INSERT INTO learners (learner_name, roll_no) VALUES (%s, %s)", (name, roll))
                flash("Learner added successfully.", "success")
                return redirect(url_for("learner_list"))
            except Error as exc:
                flash("Could not add learner. Check that the roll number is unique and the database is connected.", "error")
    return render_template("add_learner.html")

@app.route("/enroll", methods=["GET", "POST"])
def enroll():
    learners = query_all("SELECT learner_id, learner_name, roll_no FROM learners ORDER BY learner_name")
    courses = query_all("SELECT course_id, course_name FROM courses ORDER BY course_name")
    if request.method == "POST":
        try:
            learner_id = int(request.form["learner_id"])
            course_id = int(request.form["course_id"])
            execute("INSERT INTO enrollments (learner_id, course_id, enrolled_at, status) VALUES (%s,%s,CURDATE(),'active')",
                    (learner_id, course_id))
            flash("Enrolment added.", "success")
            return redirect(url_for("dashboard"))
        except (Error, ValueError, KeyError):
            flash("Enrolment could not be saved. The learner may already be enrolled in this course.", "error")
    return render_template("enroll.html", learners=learners, courses=courses)

@app.route("/activities", methods=["GET", "POST"])
def activities():
    enrollments = query_all("""
        SELECT e.enrollment_id, l.learner_name, c.course_name
        FROM enrollments e JOIN learners l ON l.learner_id=e.learner_id
        JOIN courses c ON c.course_id=e.course_id ORDER BY l.learner_name, c.course_name
    """)
    if request.method == "POST":
        try:
            execute("""INSERT INTO activities (enrollment_id, activity_date, activity_type, completed)
                       VALUES (%s,%s,%s,%s)""",
                    (int(request.form["enrollment_id"]), request.form["activity_date"],
                     request.form["activity_type"], int(request.form.get("completed", "0"))))
            flash("Activity recorded.", "success")
            return redirect(url_for("dashboard"))
        except (Error, ValueError, KeyError):
            flash("Activity could not be saved.", "error")
    return render_template("activities.html", enrollments=enrollments, today=date.today().isoformat())

@app.route("/health")
def health():
    try:
        query_all("SELECT 1 AS ok")
        return {"status": "ok", "database": "connected"}
    except Error as exc:
        return {"status": "error", "database": "not connected", "detail": str(exc)}, 500

if __name__ == "__main__":
    app.run(debug=True)
