# PlaceHub – Campus Placement Recruitment System

A full-stack campus placement portal built with **Flask**, **MongoDB**, and vanilla **HTML/CSS/JS**.

---

## 📁 Project Structure

```
placement_portal/
├── app.py                      # Main Flask application
├── config.py                   # MongoDB connection
├── requirements.txt
├── uploads/                    # Resume files stored here (auto-created)
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── student_register.html
    ├── student_login.html
    ├── student_dashboard.html
    ├── recruiter_register.html
    ├── recruiter_login.html
    ├── recruiter_dashboard.html
    ├── admin_login.html
    ├── admin_dashboard.html
    ├── post_job.html
    ├── view_jobs.html
    ├── apply_job.html
    ├── view_applications.html
    └── my_applications.html
```

---

## ⚙️ Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.8+ | https://python.org |
| MongoDB Community | 6.0+ | https://www.mongodb.com/try/download/community |
| pip | latest | bundled with Python |

---

## 🚀 Step-by-Step Setup & Run

### Step 1 – Clone / Download the project

Place all files in a folder called `placement_portal` and open a terminal inside it.

---

### Step 2 – Create a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

---

### Step 3 – Install dependencies

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install flask pymongo werkzeug
```

---

### Step 4 – Start MongoDB

**Windows (if installed as a service):**
```bash
net start MongoDB
```

**Windows (manual):**
```bash
"C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe" --dbpath="C:\data\db"
```

**macOS (Homebrew):**
```bash
brew services start mongodb-community
```

**Linux:**
```bash
sudo systemctl start mongod
```

> MongoDB must be running on **localhost:27017** (default port).  
> The database `placement_portal` and all collections are created automatically on first run.

---

### Step 5 – Run the Flask app

```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

Open your browser and go to: **http://localhost:5000**

---

## 🔑 Login Credentials

### Admin (fixed, hardcoded)
| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

### Students & Recruiters
Register through the portal UI — credentials are stored securely (SHA-256 hashed) in MongoDB.

---

## 🌐 URL Routes Reference

| URL | Description |
|-----|-------------|
| `/` | Home / Landing page |
| `/student/register` | Student registration |
| `/student/login` | Student login |
| `/student/dashboard` | Student dashboard |
| `/student/upload_resume` | Resume upload (POST) |
| `/student/my_applications` | Track application statuses |
| `/jobs` | Browse all jobs (students) |
| `/apply/<job_id>` | Apply for a job |
| `/recruiter/register` | Recruiter registration |
| `/recruiter/login` | Recruiter login |
| `/recruiter/dashboard` | Recruiter dashboard |
| `/recruiter/post_job` | Post a new job |
| `/recruiter/applications` | View & manage applications |
| `/recruiter/update_status/<id>/<status>` | Accept/Reject application |
| `/admin/login` | Admin login |
| `/admin/dashboard` | Admin dashboard |
| `/admin/delete_student/<id>` | Delete a student |
| `/admin/delete_recruiter/<id>` | Delete a recruiter |
| `/admin/delete_job/<id>` | Delete a job |
| `/logout` | Logout (all roles) |

---

## 🗄️ MongoDB Collections

### `students`
```json
{
  "name": "John Doe",
  "email": "john@college.edu",
  "password": "<sha256_hash>",
  "branch": "Computer Science",
  "cgpa": 8.5,
  "phone": "+91 9876543210",
  "resume": "abc123_resume.pdf",
  "created_at": "<datetime>"
}
```

### `recruiters`
```json
{
  "name": "Jane Smith",
  "email": "jane@company.com",
  "password": "<sha256_hash>",
  "company": "Acme Corp",
  "phone": "+91 9876543210",
  "created_at": "<datetime>"
}
```

### `jobs`
```json
{
  "title": "Software Engineer",
  "description": "...",
  "eligibility": "CGPA >= 7.5",
  "salary": "₹8 LPA",
  "location": "Bengaluru",
  "deadline": "2025-12-31",
  "recruiter_id": "<ObjectId>",
  "company": "Acme Corp",
  "recruiter_name": "Jane Smith",
  "posted_at": "<datetime>"
}
```

### `applications`
```json
{
  "student_id": "<ObjectId>",
  "student_name": "John Doe",
  "job_id": "<ObjectId>",
  "job_title": "Software Engineer",
  "company": "Acme Corp",
  "cover_letter": "...",
  "status": "pending | accepted | rejected",
  "applied_at": "<datetime>"
}
```

---

## ✅ Features Checklist

- [x] Student registration, login, dashboard
- [x] Resume upload (PDF/DOC/DOCX) stored in `uploads/`
- [x] Browse and apply for jobs with cover letter
- [x] Track application status (pending / accepted / rejected)
- [x] Recruiter registration, login, dashboard
- [x] Post jobs with title, description, eligibility, salary, deadline, location
- [x] View applicants, accept or reject applications
- [x] Admin login (fixed credentials)
- [x] Admin: view all students, recruiters, jobs, applications
- [x] Admin: delete students, recruiters, jobs (cascading)
- [x] Flash messages for all actions
- [x] Password hashing with SHA-256
- [x] Session-based authentication
- [x] Form validation (HTML5 + server-side)
- [x] Dark theme, clean responsive UI

---

## 🛠️ Troubleshooting

**`ModuleNotFoundError: No module named 'flask'`**
→ Run `pip install flask pymongo werkzeug` inside your activated venv.

**`pymongo.errors.ServerSelectionTimeoutError`**
→ MongoDB is not running. Start it with the commands in Step 4.

**Resume upload fails**
→ Ensure the `uploads/` folder exists in the project root (it's auto-created on startup).

**Port already in use**
→ Change the port: `app.run(debug=True, port=5001)`

---

## 📌 Notes

- Passwords are hashed using SHA-256 via Python's `hashlib` (no external auth library needed).
- The `uploads/` directory is created automatically when the app starts.
- The MongoDB database and collections are created automatically on first insert.
- For production, replace `app.secret_key` with a strong random key and disable `debug=True`.
