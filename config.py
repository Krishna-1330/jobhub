import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/placement_portal")
is_atlas  = MONGO_URI.startswith("mongodb+srv://")

# ── KEY FIX: remove w="majority" write concern ────────────────────────────────
# w="majority" means MongoDB waits for the majority of replica set nodes to
# acknowledge the write before returning. On Atlas M0 free tier + Render,
# this acknowledgment can time out and raise an exception EVEN THOUGH the
# data was already written to the primary node.
# Removing it means insert_one() returns as soon as the primary confirms —
# which is what we actually need.
connection_options = {
    "serverSelectionTimeoutMS": 15000,   # wait up to 15s to find a server
    "connectTimeoutMS":         15000,   # wait up to 15s to open connection
    "socketTimeoutMS":          45000,   # wait up to 45s for any operation
    # retryWrites handles transient network blips automatically
    "retryWrites":              True,
}

if is_atlas:
    connection_options["tls"] = True

try:
    client = MongoClient(MONGO_URI, **connection_options)
    client.admin.command("ping")
    logger.info("✅ MongoDB connected (%s)", "Atlas" if is_atlas else "localhost")
except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
    logger.error("❌ MongoDB connection failed: %s", exc)
    raise RuntimeError(
        "Cannot connect to MongoDB. Check MONGO_URI and Atlas Network Access."
    ) from exc

db               = client["placement_portal"]
students_col     = db["students"]
recruiters_col   = db["recruiters"]
jobs_col         = db["jobs"]
applications_col = db["applications"]

# ── Indexes: background=True so startup is non-blocking ──────────────────────
try:
    students_col.create_index("email",   unique=True, background=True)
    recruiters_col.create_index("email", unique=True, background=True)
    jobs_col.create_index("recruiter_id",              background=True)
    applications_col.create_index(
        [("student_id", 1), ("job_id", 1)], unique=True, background=True
    )
    logger.info("✅ Indexes ensured.")
except Exception as exc:
    # Index creation failing must never crash the app
    logger.warning("⚠️  Index warning (non-fatal): %s", exc)
