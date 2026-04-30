"""
PlaceHub – Campus Placement Portal
=====================================
KEY FIX: The insert_one() and redirect() are in separate try blocks.
Once data is inserted, a crash in redirect() will NEVER show
"failed to register" — it logs the real error and still sends
the user to the login page.
"""

import os
import hashlib
import datetime
import logging
import traceback

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
#  APP SETUP
# ══════════════════════════════════════════════════════════════════════════════
app = Flask(__name__)

# SECRET_KEY — must be set in Render env vars, stable across all workers
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    SECRET_KEY = "local-dev-fallback-key"
    logging.warning("⚠️  SECRET_KEY not set in environment! Sessions will break on Render.")
app.secret_key = SECRET_KEY

# Session cookie settings
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Only set Secure=True when HTTPS is actually working on your domain
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("HTTPS", "false").lower() == "true"

# Upload
UPLOAD_FOLDER      = os.environ.get("UPLOAD_FOLDER", "/tmp/uploads")
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
app.config["UPLOAD_FOLDER"]      = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Admin
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# DB
from config import students_col, recruiters_col, jobs_col, applications_col

# Logging — full tracebacks go to Render log viewer
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ══════════════════════════════════════════════════════════════════════════════
#  HOME
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")


# ══════════════════════════════════════════════════════════════════════════════
#  STUDENT — REGISTER
#
#  THE CRITICAL FIX IS HERE:
#  ─────────────────────────
#  We use THREE separate phases, each with its own error handling:
#
#  Phase 1 — Validate form input         → on error: stay on register page
#  Phase 2 — Insert into DB              → on error: stay on register page (nothing saved)
#  Phase 3 — Redirect to login           → on error: STILL go to login (data IS saved)
#
#  This means a crash in Phase 3 can never show "failed to register"
#  when the data was already saved in Phase 2.
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/student/register", methods=["GET", "POST"])
def student_register():

    if request.method == "GET":
        return render_template("student_register.html")

    # ── PHASE 1: Validate ─────────────────────────────────────────────────────
    try:
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        branch   = request.form.get("branch", "").strip()
        cgpa     = request.form.get("cgpa", "").strip()
        phone    = request.form.get("phone", "").strip()

        if not all([name, email, password, branch, cgpa, phone]):
            flash("All fields are required.", "danger")
            return redirect(url_for("student_register"))

        try:
            cgpa_val = float(cgpa)
            if not 0 <= cgpa_val <= 10:
                raise ValueError
        except ValueError:
            flash("CGPA must be a number between 0 and 10.", "danger")
            return redirect(url_for("student_register"))

        if students_col.find_one({"email": email}):
            flash("Email already registered. Please login.", "danger")
            return redirect(url_for("student_register"))

    except Exception:
        logger.error("PHASE 1 ERROR (student_register validation):\n%s", traceback.format_exc())
        flash("Form error. Please try again.", "danger")
        return redirect(url_for("student_register"))

    # ── PHASE 2: Insert into DB ───────────────────────────────────────────────
    try:
        students_col.insert_one({
            "name":       name,
            "email":      email,
            "password":   hash_password(password),
            "branch":     branch,
            "cgpa":       cgpa_val,
            "phone":      phone,
            "resume":     None,
            "created_at": datetime.datetime.utcnow(),
        })
        logger.info("✅ Student registered: %s", email)

    except Exception:
        logger.error("PHASE 2 ERROR (student DB insert):\n%s", traceback.format_exc())
        flash("Database error during registration. Please try again.", "danger")
        return redirect(url_for("student_register"))

    # ── PHASE 3: Redirect to login ────────────────────────────────────────────
    # Data is now saved. Even if something goes wrong here, we go to login.
    # We do NOT redirect back to register (that would confuse the user).
    try:
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("student_login"))

    except Exception:
        # url_for or redirect failed — log it, but still send to login by URL
        logger.error("PHASE 3 ERROR (student redirect after register):\n%s", traceback.format_exc())
        # Hard-coded fallback so user always reaches login
        return redirect("/student/login")


# ══════════════════════════════════════════════════════════════════════════════
#  STUDENT — LOGIN
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    try:
        if request.method == "POST":
            email    = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            student = students_col.find_one(
                {"email": email, "password": hash_password(password)}
            )
            if student:
                session["user_id"]   = str(student["_id"])
                session["user_type"] = "student"
                session["user_name"] = student["name"]
                flash(f"Welcome back, {student['name']}!", "success")
                return redirect(url_for("student_dashboard"))

            flash("Invalid email or password.", "danger")

        return render_template("student_login.html")

    except Exception:
        logger.error("ERROR in student_login:\n%s", traceback.format_exc())
        flash("Login error. Please try again.", "danger")
        return render_template("student_login.html")


# ══════════════════════════════════════════════════════════════════════════════
#  STUDENT — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/student/dashboard")
def student_dashboard():
    try:
        if session.get("user_type") != "student":
            return redirect(url_for("student_login"))

        student = students_col.find_one({"_id": ObjectId(session["user_id"])})
        if not student:
            session.clear()
            return redirect(url_for("student_login"))

        applied_count = applications_col.count_documents(
            {"student_id": session["user_id"]}
        )
        return render_template(
            "student_dashboard.html",
            student=student,
            applied_count=applied_count,
        )
    except Exception:
        logger.error("ERROR in student_dashboard:\n%s", traceback.format_exc())
        flash("Dashboard error. Please login again.", "danger")
        session.clear()
        return redirect(url_for("student_login"))


# ══════════════════════════════════════════════════════════════════════════════
#  STUDENT — UPLOAD RESUME
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/student/upload_resume", methods=["POST"])
def upload_resume():
    try:
        if session.get("user_type") != "student":
            return redirect(url_for("student_login"))

        file = request.files.get("resume")
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{session['user_id']}_{file.filename}")
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            students_col.update_one(
                {"_id": ObjectId(session["user_id"])},
                {"$set": {"resume": filename}},
            )
            flash("Resume uploaded successfully.", "success")
        else:
            flash("Invalid file. Only PDF / DOC / DOCX allowed (max 5 MB).", "danger")

        return redirect(url_for("student_dashboard"))

    except Exception:
        logger.error("ERROR in upload_resume:\n%s", traceback.format_exc())
        flash("Upload failed. Please try again.", "danger")
        return redirect(url_for("student_dashboard"))


# ══════════════════════════════════════════════════════════════════════════════
#  STUDENT — VIEW JOBS
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/jobs")
def view_jobs():
    try:
        if session.get("user_type") != "student":
            return redirect(url_for("student_login"))

        jobs        = list(jobs_col.find())
        applied_ids = [
            a["job_id"]
            for a in applications_col.find({"student_id": session["user_id"]})
        ]
        return render_template("view_jobs.html", jobs=jobs, applied_ids=applied_ids)

    except Exception:
        logger.error("ERROR in view_jobs:\n%s", traceback.format_exc())
        flash("Could not load jobs. Please try again.", "danger")
        return redirect(url_for("student_dashboard"))


# ══════════════════════════════════════════════════════════════════════════════
#  STUDENT — APPLY FOR JOB
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/apply/<job_id>", methods=["GET", "POST"])
def apply_job(job_id):
    try:
        if session.get("user_type") != "student":
            return redirect(url_for("student_login"))

        try:
            job = jobs_col.find_one({"_id": ObjectId(job_id)})
        except Exception:
            flash("Invalid job ID.", "danger")
            return redirect(url_for("view_jobs"))

        if not job:
            flash("Job not found.", "danger")
            return redirect(url_for("view_jobs"))

        if applications_col.find_one(
            {"student_id": session["user_id"], "job_id": job_id}
        ):
            flash("You have already applied for this job.", "warning")
            return redirect(url_for("view_jobs"))

        if request.method == "POST":
            cover_letter = request.form.get("cover_letter", "").strip()
            student      = students_col.find_one({"_id": ObjectId(session["user_id"])})
            applications_col.insert_one({
                "student_id":   session["user_id"],
                "student_name": student["name"],
                "job_id":       job_id,
                "job_title":    job["title"],
                "company":      job.get("company", ""),
                "cover_letter": cover_letter,
                "status":       "pending",
                "applied_at":   datetime.datetime.utcnow(),
            })
            flash("Application submitted successfully!", "success")
            return redirect(url_for("view_jobs"))

        return render_template("apply_job.html", job=job)

    except Exception:
        logger.error("ERROR in apply_job:\n%s", traceback.format_exc())
        flash("Application error. Please try again.", "danger")
        return redirect(url_for("view_jobs"))


# ══════════════════════════════════════════════════════════════════════════════
#  STUDENT — MY APPLICATIONS
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/student/my_applications")
def my_applications():
    try:
        if session.get("user_type") != "student":
            return redirect(url_for("student_login"))

        apps = list(applications_col.find({"student_id": session["user_id"]}))
        for a in apps:
            job      = jobs_col.find_one({"_id": ObjectId(a["job_id"])})
            a["job"] = job or {}

        return render_template("my_applications.html", applications=apps)

    except Exception:
        logger.error("ERROR in my_applications:\n%s", traceback.format_exc())
        flash("Could not load applications.", "danger")
        return redirect(url_for("student_dashboard"))


# ══════════════════════════════════════════════════════════════════════════════
#  RECRUITER — REGISTER
#
#  Same three-phase pattern as student_register.
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/recruiter/register", methods=["GET", "POST"])
def recruiter_register():

    if request.method == "GET":
        return render_template("recruiter_register.html")

    # ── PHASE 1: Validate ─────────────────────────────────────────────────────
    try:
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        company  = request.form.get("company", "").strip()
        phone    = request.form.get("phone", "").strip()

        if not all([name, email, password, company, phone]):
            flash("All fields are required.", "danger")
            return redirect(url_for("recruiter_register"))

        if recruiters_col.find_one({"email": email}):
            flash("Email already registered. Please login.", "danger")
            return redirect(url_for("recruiter_register"))

    except Exception:
        logger.error("PHASE 1 ERROR (recruiter_register validation):\n%s", traceback.format_exc())
        flash("Form error. Please try again.", "danger")
        return redirect(url_for("recruiter_register"))

    # ── PHASE 2: Insert ───────────────────────────────────────────────────────
    try:
        recruiters_col.insert_one({
            "name":       name,
            "email":      email,
            "password":   hash_password(password),
            "company":    company,
            "phone":      phone,
            "created_at": datetime.datetime.utcnow(),
        })
        logger.info("✅ Recruiter registered: %s", email)

    except Exception:
        logger.error("PHASE 2 ERROR (recruiter DB insert):\n%s", traceback.format_exc())
        flash("Database error during registration. Please try again.", "danger")
        return redirect(url_for("recruiter_register"))

    # ── PHASE 3: Redirect ─────────────────────────────────────────────────────
    try:
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("recruiter_login"))

    except Exception:
        logger.error("PHASE 3 ERROR (recruiter redirect after register):\n%s", traceback.format_exc())
        return redirect("/recruiter/login")


# ══════════════════════════════════════════════════════════════════════════════
#  RECRUITER — LOGIN
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/recruiter/login", methods=["GET", "POST"])
def recruiter_login():
    try:
        if request.method == "POST":
            email     = request.form.get("email", "").strip().lower()
            password  = request.form.get("password", "")
            recruiter = recruiters_col.find_one(
                {"email": email, "password": hash_password(password)}
            )
            if recruiter:
                session["user_id"]   = str(recruiter["_id"])
                session["user_type"] = "recruiter"
                session["user_name"] = recruiter["name"]
                flash(f"Welcome back, {recruiter['name']}!", "success")
                return redirect(url_for("recruiter_dashboard"))

            flash("Invalid email or password.", "danger")

        return render_template("recruiter_login.html")

    except Exception:
        logger.error("ERROR in recruiter_login:\n%s", traceback.format_exc())
        flash("Login error. Please try again.", "danger")
        return render_template("recruiter_login.html")


# ══════════════════════════════════════════════════════════════════════════════
#  RECRUITER — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/recruiter/dashboard")
def recruiter_dashboard():
    try:
        if session.get("user_type") != "recruiter":
            return redirect(url_for("recruiter_login"))

        recruiter = recruiters_col.find_one({"_id": ObjectId(session["user_id"])})
        if not recruiter:
            session.clear()
            return redirect(url_for("recruiter_login"))

        jobs      = list(jobs_col.find({"recruiter_id": session["user_id"]}))
        job_ids   = [str(j["_id"]) for j in jobs]
        app_count = applications_col.count_documents({"job_id": {"$in": job_ids}})

        return render_template(
            "recruiter_dashboard.html",
            recruiter=recruiter,
            jobs=jobs,
            app_count=app_count,
        )
    except Exception:
        logger.error("ERROR in recruiter_dashboard:\n%s", traceback.format_exc())
        flash("Dashboard error. Please login again.", "danger")
        session.clear()
        return redirect(url_for("recruiter_login"))


# ══════════════════════════════════════════════════════════════════════════════
#  RECRUITER — POST JOB
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/recruiter/post_job", methods=["GET", "POST"])
def post_job():
    try:
        if session.get("user_type") != "recruiter":
            return redirect(url_for("recruiter_login"))

        if request.method == "POST":
            title       = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            eligibility = request.form.get("eligibility", "").strip()
            salary      = request.form.get("salary", "").strip()
            deadline    = request.form.get("deadline", "").strip()
            location    = request.form.get("location", "").strip()

            if not all([title, description, eligibility, salary, deadline]):
                flash("All fields are required.", "danger")
                return redirect(url_for("post_job"))

            recruiter = recruiters_col.find_one({"_id": ObjectId(session["user_id"])})
            jobs_col.insert_one({
                "title":          title,
                "description":    description,
                "eligibility":    eligibility,
                "salary":         salary,
                "deadline":       deadline,
                "location":       location,
                "recruiter_id":   session["user_id"],
                "company":        recruiter["company"],
                "recruiter_name": recruiter["name"],
                "posted_at":      datetime.datetime.utcnow(),
            })
            flash("Job posted successfully!", "success")
            return redirect(url_for("recruiter_dashboard"))

        return render_template("post_job.html")

    except Exception:
        logger.error("ERROR in post_job:\n%s", traceback.format_exc())
        flash("Could not post job. Please try again.", "danger")
        return redirect(url_for("recruiter_dashboard"))


# ══════════════════════════════════════════════════════════════════════════════
#  RECRUITER — VIEW APPLICATIONS
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/recruiter/applications")
def view_applications():
    try:
        if session.get("user_type") != "recruiter":
            return redirect(url_for("recruiter_login"))

        jobs    = list(jobs_col.find({"recruiter_id": session["user_id"]}))
        job_map = {str(j["_id"]): j for j in jobs}
        apps    = list(applications_col.find({"job_id": {"$in": list(job_map.keys())}}))

        for a in apps:
            a["job"]     = job_map.get(a["job_id"], {})
            student      = students_col.find_one({"_id": ObjectId(a["student_id"])})
            a["student"] = student or {}

        return render_template("view_applications.html", applications=apps)

    except Exception:
        logger.error("ERROR in view_applications:\n%s", traceback.format_exc())
        flash("Could not load applications.", "danger")
        return redirect(url_for("recruiter_dashboard"))


# ══════════════════════════════════════════════════════════════════════════════
#  RECRUITER — ACCEPT / REJECT
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/recruiter/update_status/<app_id>/<status>")
def update_application_status(app_id, status):
    try:
        if session.get("user_type") != "recruiter":
            return redirect(url_for("recruiter_login"))

        if status in ("accepted", "rejected"):
            applications_col.update_one(
                {"_id": ObjectId(app_id)},
                {"$set": {"status": status}},
            )
            flash(f"Application marked as {status}.", "success")

        return redirect(url_for("view_applications"))

    except Exception:
        logger.error("ERROR in update_application_status:\n%s", traceback.format_exc())
        flash("Status update failed.", "danger")
        return redirect(url_for("view_applications"))


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN — LOGIN
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    try:
        if request.method == "POST":
            if (request.form.get("username", "").strip() == ADMIN_USERNAME
                    and request.form.get("password", "") == ADMIN_PASSWORD):
                session["user_type"] = "admin"
                session["user_name"] = "Admin"
                flash("Welcome, Admin!", "success")
                return redirect(url_for("admin_dashboard"))
            flash("Invalid admin credentials.", "danger")

        return render_template("admin_login.html")

    except Exception:
        logger.error("ERROR in admin_login:\n%s", traceback.format_exc())
        flash("Admin login error.", "danger")
        return render_template("admin_login.html")


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/admin/dashboard")
def admin_dashboard():
    try:
        if session.get("user_type") != "admin":
            return redirect(url_for("admin_login"))

        return render_template(
            "admin_dashboard.html",
            students=list(students_col.find()),
            recruiters=list(recruiters_col.find()),
            jobs=list(jobs_col.find()),
            applications=list(applications_col.find()),
        )
    except Exception:
        logger.error("ERROR in admin_dashboard:\n%s", traceback.format_exc())
        flash("Dashboard error.", "danger")
        return redirect(url_for("admin_login"))


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN — DELETE ACTIONS
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/admin/delete_student/<sid>")
def delete_student(sid):
    try:
        if session.get("user_type") != "admin":
            return redirect(url_for("admin_login"))
        students_col.delete_one({"_id": ObjectId(sid)})
        applications_col.delete_many({"student_id": sid})
        flash("Student deleted.", "success")
    except Exception:
        logger.error("ERROR in delete_student:\n%s", traceback.format_exc())
        flash("Delete failed.", "danger")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_recruiter/<rid>")
def delete_recruiter(rid):
    try:
        if session.get("user_type") != "admin":
            return redirect(url_for("admin_login"))
        for j in jobs_col.find({"recruiter_id": rid}):
            applications_col.delete_many({"job_id": str(j["_id"])})
        jobs_col.delete_many({"recruiter_id": rid})
        recruiters_col.delete_one({"_id": ObjectId(rid)})
        flash("Recruiter and all their jobs deleted.", "success")
    except Exception:
        logger.error("ERROR in delete_recruiter:\n%s", traceback.format_exc())
        flash("Delete failed.", "danger")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_job/<jid>")
def delete_job(jid):
    try:
        if session.get("user_type") != "admin":
            return redirect(url_for("admin_login"))
        jobs_col.delete_one({"_id": ObjectId(jid)})
        applications_col.delete_many({"job_id": jid})
        flash("Job deleted.", "success")
    except Exception:
        logger.error("ERROR in delete_job:\n%s", traceback.format_exc())
        flash("Delete failed.", "danger")
    return redirect(url_for("admin_dashboard"))


# ══════════════════════════════════════════════════════════════════════════════
#  LOGOUT
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


# ══════════════════════════════════════════════════════════════════════════════
#  ERROR HANDLERS
# ══════════════════════════════════════════════════════════════════════════════
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(413)
def too_large(e):
    flash("File too large. Maximum allowed size is 5 MB.", "danger")
    return redirect(request.referrer or url_for("index"))

@app.errorhandler(500)
def server_error(e):
    logger.error("Unhandled 500:\n%s\n%s", e, traceback.format_exc())
    return render_template("500.html"), 500


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )
