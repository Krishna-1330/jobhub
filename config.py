import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load .env file for local development (ignored on Render — Render uses its own env)
load_dotenv()

logger = logging.getLogger(__name__)

# ── Read the Atlas connection string from environment ─────────────────────────
# On Render: set this in Dashboard → Environment
# Locally:   put it in your .env file
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb://localhost:27017/placement_portal"   # fallback for local dev only
)

# ── Auto-detect Atlas vs local so we add TLS only when needed ─────────────────
is_atlas = MONGO_URI.startswith("mongodb+srv://")

connection_options = {
    "serverSelectionTimeoutMS": 10000,
    "connectTimeoutMS":         15000,
    "socketTimeoutMS":          30000,
    "retryWrites":              True,
}
if is_atlas:
    connection_options["tls"] = True   # Atlas always requires TLS

# ── Connect ───────────────────────────────────────────────────────────────────
try:
    client = MongoClient(MONGO_URI, **connection_options)
    client.admin.command("ping")       # quick reachability check
    logger.info("✅ MongoDB connected (%s)", "Atlas" if is_atlas else "localhost")
except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
    logger.error("❌ MongoDB connection failed: %s", exc)
    raise RuntimeError(
        "Cannot connect to MongoDB. "
        "Check your MONGO_URI and Atlas Network Access settings."
    ) from exc

# ── Database ──────────────────────────────────────────────────────────────────
db = client["placement_portal"]

# ── Collections ───────────────────────────────────────────────────────────────
students_col     = db["students"]
recruiters_col   = db["recruiters"]
jobs_col         = db["jobs"]
applications_col = db["applications"]

# ── Indexes (run once at startup; safe to repeat) ─────────────────────────────
try:
    students_col.create_index("email",   unique=True, background=True)
    recruiters_col.create_index("email", unique=True, background=True)
    jobs_col.create_index("recruiter_id",              background=True)
    applications_col.create_index(
        [("student_id", 1), ("job_id", 1)],
        unique=True, background=True
    )
    logger.info("✅ Indexes ensured.")
except Exception as exc:
    logger.warning("⚠️  Index creation warning: %s", exc)
