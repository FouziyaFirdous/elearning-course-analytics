import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "elearning_analytics"),
        port=int(os.getenv("DB_PORT", "3306"))
    )

def query_df(sql, params=None):
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()

def execute(sql, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid, cursor.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def completion_report():
    df = query_df("""
        SELECT c.course_id, c.course_name, c.category,
               COUNT(e.enrollment_id) AS total_enrollments,
               COALESCE(SUM(CASE WHEN e.status='completed' THEN 1 ELSE 0 END),0)
                   AS completed_enrollments
        FROM courses c
        LEFT JOIN enrollments e
          ON c.course_id=e.course_id AND e.status IN ('active','completed')
        GROUP BY c.course_id, c.course_name, c.category
        ORDER BY c.course_name
    """)
    if df.empty:
        df["completion_rate"] = pd.Series(dtype=float)
    else:
        den = df["total_enrollments"].to_numpy(dtype=float)
        num = df["completed_enrollments"].to_numpy(dtype=float)
        df["completion_rate"] = np.divide(
            num * 100, den, out=np.zeros_like(den), where=den != 0
        ).round(2)
    return df

def weekly_report():
    df = query_df("""
        SELECT activity_date, enrollment_id, activity_type, completed
        FROM activities ORDER BY activity_date
    """)
    if df.empty:
        return pd.DataFrame(columns=["week", "activity_count", "active_enrollments"])
    df["activity_date"] = pd.to_datetime(df["activity_date"])
    df["week"] = df["activity_date"].dt.to_period("W-SUN").dt.start_time
    return df.groupby("week").agg(
        activity_count=("enrollment_id", "size"),
        active_enrollments=("enrollment_id", "nunique")
    ).reset_index()

def inactive_report(days=14):
    df = query_df("""
        SELECT e.enrollment_id, l.roll_no, c.course_name, e.enrolled_at,
               MAX(a.activity_date) AS last_activity
        FROM enrollments e
        JOIN learners l ON e.learner_id=l.learner_id
        JOIN courses c ON e.course_id=c.course_id
        LEFT JOIN activities a ON e.enrollment_id=a.enrollment_id
        WHERE e.status='active'
        GROUP BY e.enrollment_id, l.roll_no, c.course_name, e.enrolled_at
        ORDER BY e.enrollment_id
    """)
    if df.empty:
        return df
    df["enrolled_at"] = pd.to_datetime(df["enrolled_at"])
    df["last_activity"] = pd.to_datetime(df["last_activity"])
    df["last_recorded_date"] = df["last_activity"].fillna(df["enrolled_at"])
    now = pd.Timestamp.now()
    df["days_since_activity"] = ((now - df["last_recorded_date"]).dt.total_seconds()/86400).round(1)
    result = df[df["days_since_activity"] >= days].copy()
    result["activity_note"] = np.where(
        result["last_activity"].isna(),
        "No activity recorded; verify data",
        "No recent activity recorded; verify"
    )
    return result

def create_charts():
    courses = completion_report()
    weekly = weekly_report()
    os.makedirs("static/generated", exist_ok=True)

    # Course comparison
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if not courses.empty:
        x = np.arange(len(courses))
        width = 0.36
        ax.bar(x-width/2, courses["total_enrollments"], width, label="Eligible enrolments")
        ax.bar(x+width/2, courses["completed_enrollments"], width, label="Completed")
        ax.set_xticks(x)
        ax.set_xticklabels(courses["course_name"], rotation=15, ha="right")
        ax.legend()
    ax.set_ylabel("Enrolments")
    ax.set_title("Enrolment vs Completion by Course")
    fig.tight_layout()
    fig.savefig("static/generated/course_comparison.png", dpi=140)
    plt.close(fig)

    # Completion rate
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if not courses.empty:
        bars = ax.bar(courses["course_name"], courses["completion_rate"])
        ax.bar_label(bars, fmt="%.1f%%", padding=3)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Completion rate (%)")
    ax.set_title("Course Completion Rates")
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig("static/generated/completion_rates.png", dpi=140)
    plt.close(fig)

    # Weekly activity
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if not weekly.empty:
        ax.plot(weekly["week"], weekly["activity_count"], marker="o")
    ax.set_ylabel("Recorded activity records")
    ax.set_xlabel("Week starting")
    ax.set_title("Weekly Learning Activity")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig("static/generated/weekly_activity.png", dpi=140)
    plt.close(fig)

@app.route("/")
def dashboard():
    try:
        courses = completion_report()
        learners = query_df("SELECT COUNT(*) AS n FROM learners").iloc[0]["n"]
        eligible = int(courses["total_enrollments"].sum()) if not courses.empty else 0
        completed = int(courses["completed_enrollments"].sum()) if not courses.empty else 0
        rate = round(completed * 100 / eligible, 2) if eligible else 0
        activity_count = int(query_df("SELECT COUNT(*) AS n FROM activities").iloc[0]["n"])
        create_charts()
        return render_template("dashboard.html", courses=courses.to_dict("records"),
            total_courses=len(courses), total_learners=int(learners),
            total_enrollments=eligible, total_completed=completed,
            overall_rate=rate, activity_count=activity_count,
            active_page="dashboard")
    except Exception as e:
        return render_template("error.html", error=str(e)), 500

@app.route("/courses", methods=["GET", "POST"])
def courses_page():
    if request.method == "POST":
        name = request.form.get("course_name", "").strip()
        category = request.form.get("category", "").strip()
        if not name or not category:
            flash("Course name and category are required.", "error")
        else:
            try:
                execute("INSERT INTO courses (course_name, category) VALUES (%s,%s)", (name, category))
                flash("Course added successfully.", "success")
            except Exception as e:
                flash(f"Could not add course: {e}", "error")
        return redirect(url_for("courses_page"))
    df = query_df("SELECT * FROM courses ORDER BY course_id DESC")
    return render_template("courses.html", courses=df.to_dict("records"), active_page="courses")

@app.route("/learners", methods=["GET", "POST"])
def learners_page():
    if request.method == "POST":
        roll = request.form.get("roll_no", "").strip()
        if not roll:
            flash("Roll number is required.", "error")
        else:
            try:
                execute("INSERT INTO learners (roll_no) VALUES (%s)", (roll,))
                flash("Learner registered successfully.", "success")
            except Exception as e:
                flash(f"Could not register learner: {e}", "error")
        return redirect(url_for("learners_page"))
    df = query_df("SELECT * FROM learners ORDER BY learner_id DESC")
    return render_template("learners.html", learners=df.to_dict("records"), active_page="learners")

@app.route("/enrollments", methods=["GET", "POST"])
def enrollments_page():
    if request.method == "POST":
        try:
            learner_id = int(request.form["learner_id"])
            course_id = int(request.form["course_id"])
            execute("INSERT INTO enrollments (learner_id, course_id) VALUES (%s,%s)", (learner_id, course_id))
            flash("Learner enrolled successfully.", "success")
        except Exception as e:
            flash(f"Could not create enrolment: {e}", "error")
        return redirect(url_for("enrollments_page"))
    enrollments = query_df("""
        SELECT e.enrollment_id, l.roll_no, c.course_name, e.enrolled_at, e.status
        FROM enrollments e JOIN learners l ON e.learner_id=l.learner_id
        JOIN courses c ON e.course_id=c.course_id ORDER BY e.enrollment_id DESC
    """)
    learners = query_df("SELECT learner_id, roll_no FROM learners ORDER BY roll_no")
    courses = query_df("SELECT course_id, course_name FROM courses ORDER BY course_name")
    return render_template("enrollments.html", enrollments=enrollments.to_dict("records"),
        learners=learners.to_dict("records"), courses=courses.to_dict("records"), active_page="enrollments")

@app.route("/activities", methods=["GET", "POST"])
def activities_page():
    if request.method == "POST":
        try:
            enrollment_id = int(request.form["enrollment_id"])
            activity_type = request.form["activity_type"].strip()
            completed = 1 if request.form.get("completed") == "yes" else 0
            _, count = execute("""
                INSERT INTO activities (enrollment_id, activity_type, completed)
                SELECT enrollment_id, %s, %s FROM enrollments
                WHERE enrollment_id=%s AND status='active'
            """, (activity_type, completed, enrollment_id))
            flash("Activity recorded." if count else "No active enrolment found with that ID.", "success" if count else "error")
        except Exception as e:
            flash(f"Could not record activity: {e}", "error")
        return redirect(url_for("activities_page"))
    activities = query_df("""
        SELECT a.activity_id, a.enrollment_id, l.roll_no, c.course_name,
               a.activity_date, a.activity_type, a.completed
        FROM activities a JOIN enrollments e ON a.enrollment_id=e.enrollment_id
        JOIN learners l ON e.learner_id=l.learner_id
        JOIN courses c ON e.course_id=c.course_id
        ORDER BY a.activity_date DESC LIMIT 200
    """)
    active = query_df("""
        SELECT e.enrollment_id, l.roll_no, c.course_name
        FROM enrollments e JOIN learners l ON e.learner_id=l.learner_id
        JOIN courses c ON e.course_id=c.course_id
        WHERE e.status='active' ORDER BY e.enrollment_id
    """)
    return render_template("activities.html", activities=activities.to_dict("records"),
        enrollments=active.to_dict("records"), active_page="activities")

@app.route("/complete/<int:enrollment_id>", methods=["POST"])
def complete_enrollment(enrollment_id):
    try:
        _, count = execute("UPDATE enrollments SET status='completed' WHERE enrollment_id=%s AND status='active'", (enrollment_id,))
        flash("Enrolment marked completed." if count else "No active enrolment found.", "success" if count else "error")
    except Exception as e:
        flash(f"Could not update enrolment: {e}", "error")
    return redirect(request.referrer or url_for("enrollments_page"))

@app.route("/reports")
def reports():
    try:
        courses = completion_report()
        weekly = weekly_report()
        inactive = inactive_report()
        return render_template("reports.html", courses=courses.to_dict("records"),
            weekly=weekly.to_dict("records"), inactive=inactive.to_dict("records"),
            active_page="reports")
    except Exception as e:
        return render_template("error.html", error=str(e)), 500

@app.route("/charts")
def charts():
    try:
        create_charts()
        return render_template("charts.html", active_page="charts")
    except Exception as e:
        return render_template("error.html", error=str(e)), 500

if __name__ == "__main__":
    app.run(debug=True)
