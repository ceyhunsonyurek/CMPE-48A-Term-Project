import pymysql
import json
import os
import tempfile
import logging
import hashlib
from datetime import datetime
from io import BytesIO
from hashids import Hashids
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify, send_file, Response
import plotly.graph_objects as go
import qrcode
from google.cloud import storage
from plotly.subplots import make_subplots
from dotenv import load_dotenv
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from contextlib import contextmanager

# Load environment variables from .env file
load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Simple metrics tracking (for /metrics endpoint)
# Note: In production, use proper monitoring tools (Prometheus, Cloud Monitoring)
_metrics = {
    'requests_total': 0,
    'errors_total': 0,
}

# Load configuration from environment variables (fallback to config.json for backward compatibility)
def load_config():
    # Try to load from config.json first (for backward compatibility)
    config = {}
    if os.path.exists("config.json"):
        with open("config.json") as f:
            config = json.load(f)
    
    # Override with environment variables if they exist
    # GCP Cloud Storage configuration
    gcs_bucket_name = os.getenv("GCS_BUCKET_NAME", config.get("gcs_bucket_name", config.get("bucket_name", "")))
    gcp_project_id = os.getenv("GCP_PROJECT_ID", config.get("gcp_project_id", ""))
    
    # Database configuration
    host = os.getenv("DB_HOST", config.get("db_host", "localhost"))
    port = int(os.getenv("DB_PORT", config.get("db_port", 3306)))
    user = os.getenv("DB_USER", config.get("db_user", ""))
    password = os.getenv("DB_PASSWORD", config.get("db_password", ""))
    database = os.getenv("DB_DATABASE", config.get("db_database", ""))
    
    return {
        "gcs_bucket_name": gcs_bucket_name,
        "gcp_project_id": gcp_project_id,
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database
    }

config = load_config()
gcs_bucket_name = config["gcs_bucket_name"]
gcp_project_id = config["gcp_project_id"]
host = config["host"]
port = config["port"]
user = config["user"]
password = config["password"]
database = config["database"]

# Connection pool configuration from environment variables
# Default values are optimized for production use
DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "2"))  # Minimum connections in pool
DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))  # Maximum connections in pool
DB_POOL_AUTOCOMMIT = os.getenv("DB_POOL_AUTOCOMMIT", "false").lower() == "true"

# Initialize MySQL connection pool
# Connection pooling improves performance by reusing database connections
# instead of creating a new connection for each request
_db_pool = None

def init_db_pool():
    """Initialize the database connection pool."""
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = PooledDB(
                creator=pymysql,
                mincached=DB_POOL_MIN_SIZE,  # Minimum number of connections to keep in pool
                maxcached=DB_POOL_MAX_SIZE,  # Maximum number of connections in pool
                maxconnections=DB_POOL_MAX_SIZE,  # Maximum total connections
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                cursorclass=DictCursor,
                autocommit=DB_POOL_AUTOCOMMIT,
                connect_timeout=10,
                read_timeout=10,
                write_timeout=10,
                charset='utf8mb4',
                use_unicode=True,
            )
            logger.info(f"Database connection pool initialized (min={DB_POOL_MIN_SIZE}, max={DB_POOL_MAX_SIZE})")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}", exc_info=True)
            raise
    return _db_pool

# Initialize pool at module load
try:
    init_db_pool()
except Exception as e:
    logger.warning(f"Database pool initialization failed, will retry on first connection: {e}")

# Database connection with connection pooling
@contextmanager
def get_db_connection():
    """
    Get database connection from pool with context manager (auto-return to pool).
    
    Connection pooling benefits:
    - Reuses existing connections instead of creating new ones
    - Reduces connection overhead and improves performance
    - Prevents "too many connections" errors
    - Especially important for serverless/cloud environments
    """
    conn = None
    try:
        # Ensure pool is initialized
        if _db_pool is None:
            init_db_pool()
        
        # Get connection from pool
        conn = _db_pool.connection()
        yield conn
    except pymysql.Error as e:
        _metrics['errors_total'] += 1
        logger.error(f"Database error: {e}", exc_info=True)
        # Rollback transaction on error
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise
    except Exception as e:
        _metrics['errors_total'] += 1
        logger.error(f"Unexpected error: {e}", exc_info=True)
        # Rollback transaction on error
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise
    finally:
        # Return connection to pool (not close it)
        if conn:
            try:
                conn.close()  # In pooled connections, close() returns connection to pool
            except:
                pass

# QR code generation is now handled internally using qrcode library
# No external API dependencies required

# Initialize GCP Cloud Storage client
# Note: GCP credentials should be set via GOOGLE_APPLICATION_CREDENTIALS env var or
# the client will use default credentials from gcloud
# Explicitly set scopes for GCS operations
try:
    from google.cloud import storage
    from google.auth import default
    
    # Get default credentials with storage-specific scopes
    # Use cloud-platform scope for full access (required for GKE service accounts)
    credentials, project = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    
    if gcp_project_id:
        gcs_client = storage.Client(project=gcp_project_id, credentials=credentials)
    else:
        gcs_client = storage.Client(credentials=credentials)
    logger.info("GCS client initialized successfully with storage scopes")
except Exception as e:
    logger.warning(f"Could not initialize GCS client: {e}")
    # Fallback: try without explicit scopes (let default handle it)
    try:
        if gcp_project_id:
            gcs_client = storage.Client(project=gcp_project_id)
        else:
            gcs_client = storage.Client()
        logger.info("GCS client initialized with default credentials")
    except Exception as e2:
        logger.warning(f"Fallback GCS client initialization also failed: {e2}")
        logger.warning("GCS functionality will be disabled.")
        gcs_client = None


def upload_to_gcs(file_path, bucket_name, blob_name):
    """
    Upload a file to Google Cloud Storage bucket.
    
    Args:
        file_path: Local path to the file to upload
        bucket_name: Name of the GCS bucket
        blob_name: Name of the blob (file) in the bucket
        
    Returns:
        Public URL of the uploaded file, or None if upload fails
    """
    if not gcs_client:
        logger.error("GCS client not initialized")
        return None
        
    try:
        logger.info(f"Uploading QR to GCS bucket: {bucket_name}, blob: {blob_name}")
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        
        # Make the blob publicly accessible
        blob.make_public()
        
        # Return the public URL
        public_url = blob.public_url
        logger.info(f"Upload successful: {public_url}")
        return public_url
    except Exception as e:
        _metrics['errors_total'] += 1
        logger.error(f"Error uploading image to GCS: {e}", exc_info=True)
        return None


def get_gcs_public_url(bucket_name, blob_name):
    """
    Get the public URL for a file in GCS bucket.
    
    Args:
        bucket_name: Name of the GCS bucket
        blob_name: Name of the blob (file) in the bucket
        
    Returns:
        Public URL of the file
    """
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"


def generate_qr_code(short_url, hashid):
    """
    Generate QR code locally using qrcode library.
    
    Args:
        short_url: The URL to encode in the QR code
        hashid: Unique identifier for the QR code file name
        
    Returns:
        Path to the generated QR code image file, or None if generation fails
    """
    try:
        logger.info(f"Generating QR code for hashid: {hashid}")
        
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(short_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to temp directory
        temp_dir = tempfile.gettempdir()
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{hashid}.png")
        img.save(temp_path)
        
        logger.info(f"QR code generated: {temp_path}")
        return temp_path
    except Exception as e:
        _metrics['errors_total'] += 1
        logger.error(f"Error generating QR code: {e}", exc_info=True)
        return None


application = Flask(__name__)
application.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "Divi")

hashids = Hashids(min_length=4, salt=application.config["SECRET_KEY"])

# Simple request tracking (only for metrics)
@application.before_request
def before_request():
    """Track total requests for metrics."""
    _metrics['requests_total'] += 1


@application.context_processor
def inject_gcs_config():
    """Inject GCS bucket configuration into all templates."""
    return {
        'gcs_bucket_name': gcs_bucket_name,
        'gcs_base_url': f"https://storage.googleapis.com/{gcs_bucket_name}" if gcs_bucket_name else ""
    }


def insert_url(url, user_id):
    """Insert a new URL into the database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO urls (original_url, user_id) VALUES (%s, %s)", (url, user_id)
                )
                conn.commit()
                url_id = cursor.lastrowid
                logger.info(f"URL inserted with id: {url_id}")
                return url_id
    except Exception as e:
        logger.error(f"Error inserting URL: {e}", exc_info=True)
        raise


def get_short_url(url_id):
    hashid = hashids.encode(url_id)
    # If Cloud Function redirect is enabled, use Cloud Function URL directly
    use_cloud_function = os.getenv("USE_CLOUD_FUNCTION_REDIRECT", "false").lower() == "true"
    cloud_function_url = os.getenv("CLOUD_FUNCTION_REDIRECT_URL", "")
    
    if use_cloud_function and cloud_function_url:
        # Use Cloud Function URL directly for QR codes (no Flask app redirect needed)
        short_url = f"{cloud_function_url}/{hashid}"
    else:
        # Fallback to Flask app URL
        short_url = request.host_url + hashid
    return short_url, hashid


@application.route("/", methods=("GET", "POST"))
def index():
    """Main page for URL shortening."""
    if "user_id" not in session:
        flash("You must be logged in to access this page.")
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            url = request.form.get("url", "").strip()
            
            if not url:
                flash("The URL is required!")
                return redirect(url_for("index"))

            user_id = session["user_id"]
            url_id = insert_url(url, user_id)
            short_url, hashid = get_short_url(url_id)
            logger.info(f"URL shortened: {url} -> {short_url} (user_id: {user_id})")

            # Generate QR code internally using qrcode library
            result = None
            qr_path = generate_qr_code(short_url, hashid)
            
            if qr_path and gcs_bucket_name:
                # Upload to GCS and get public URL
                blob_name = f"{hashid}.png"
                result = upload_to_gcs(qr_path, gcs_bucket_name, blob_name)
                if not result:
                    logger.error(f"GCS upload failed for {blob_name}. QR code will not be displayed.")
                    result = None
                
                # Clean up temp file
                try:
                    if os.path.exists(qr_path):
                        os.remove(qr_path)
                except Exception as e:
                    logger.warning(f"Could not remove temp file {qr_path}: {e}")

            return render_template("index.html", short_url=short_url, image_path=result)
        except Exception as e:
            logger.error(f"Error in index POST: {e}", exc_info=True)
            flash("An error occurred while processing your request. Please try again.")
            return redirect(url_for("index"))

    return render_template("index.html")


@application.route("/<id>")
def url_redirect(id):
    """Redirect short URL to original URL."""
    # Check if Cloud Function redirect is enabled
    use_cloud_function = os.getenv("USE_CLOUD_FUNCTION_REDIRECT", "false").lower() == "true"
    cloud_function_url = os.getenv("CLOUD_FUNCTION_REDIRECT_URL", "")
    
    if use_cloud_function and cloud_function_url:
        # Redirect to Cloud Function for URL redirection
        logger.info(f"Redirecting to Cloud Function for hashid: {id}")
        return redirect(f"{cloud_function_url}/{id}", code=302)
    
    # Fallback to Flask app redirect (for local development or if Cloud Function is disabled)
    try:
        original_id = hashids.decode(id)
        if not original_id:
            logger.warning(f"Invalid hashid: {id}")
            return "Invalid URL", 404
        
        original_id = original_id[0]
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT original_url, clicks FROM urls WHERE id = %s", (original_id,)
                )
                url_data = cursor.fetchone()

            if url_data:
                # Handle both dict and tuple results
                if isinstance(url_data, dict):
                    original_url = url_data["original_url"]
                    clicks = url_data["clicks"]
                else:
                    original_url = url_data[0]
                    clicks = url_data[1]

                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE urls SET clicks = %s WHERE id = %s",
                        (clicks + 1, original_id),
                    )

                conn.commit()
                logger.info(f"Redirecting {id} -> {original_url} (clicks: {clicks + 1})")
                return redirect(original_url)
            else:
                logger.warning(f"URL not found for id: {original_id}")
                return "URL not found", 404
    except Exception as e:
        logger.error(f"Error in url_redirect: {e}", exc_info=True)
        flash("An error occurred while redirecting. Please try again.")
        return redirect(url_for("index"))


@application.route("/download-qr/<hashid>")
def download_qr(hashid):
    """
    Download QR code image from GCS.
    This endpoint serves the QR code as a downloadable file.
    """
    try:
        if not gcs_client or not gcs_bucket_name:
            logger.error("GCS client or bucket not configured")
            return "QR code download not available", 503
        
        blob_name = f"{hashid}.png"
        bucket = gcs_client.bucket(gcs_bucket_name)
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            logger.warning(f"QR code not found: {blob_name}")
            return "QR code not found", 404
        
        # Download blob to BytesIO (in-memory)
        image_data = BytesIO()
        blob.download_to_file(image_data)
        image_data.seek(0)
        
        logger.info(f"Serving QR code download: {blob_name}")
        
        # Create response with explicit headers for forced download
        response = Response(
            image_data.getvalue(),
            mimetype='image/png',
            headers={
                'Content-Disposition': f'attachment; filename="{hashid}.png"',
                'Content-Type': 'image/png',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        return response
    except Exception as e:
        _metrics['errors_total'] += 1
        logger.error(f"Error downloading QR code: {e}", exc_info=True)
        return "Error downloading QR code", 500


@application.route("/stats")
def stats():
    """Display statistics for user's URLs."""
    if "user_id" not in session:
        flash("You must be logged in to access this page.")
        return redirect(url_for("login"))

    try:
        user_id = session["user_id"]
        
        # Limit URLs fetched from database to prevent large queries
        # Show only last 100 URLs for performance (or all if less than 100)
        MAX_TABLE_ITEMS = 100
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Optimized: 2 queries instead of 3, and use single query for totals
                # This reduces connection pool usage and database round trips
                # First: Get totals in one query (with aliases for DictCursor compatibility)
                cursor.execute("SELECT COUNT(*) as total_count, COALESCE(SUM(clicks), 0) as total_clicks FROM urls WHERE user_id = %s", (user_id,))
                totals = cursor.fetchone()
                if totals:
                    if isinstance(totals, dict):
                        total_count = totals.get("total_count", 0)
                        total_clicks = totals.get("total_clicks", 0)
                    else:
                        total_count = totals[0] if len(totals) > 0 else 0
                        total_clicks = totals[1] if len(totals) > 1 else 0
                else:
                    total_count = 0
                    total_clicks = 0
                
                # Second: Fetch only the URLs we need (with LIMIT)
                cursor.execute(
                    "SELECT id, created, original_url, clicks FROM urls WHERE user_id = %s ORDER BY id DESC LIMIT %s",
                    (user_id, MAX_TABLE_ITEMS),
                )
                db_urls = cursor.fetchall()

        # Pre-compute Cloud Function URL to avoid repeated env lookups
        use_cloud_function = os.getenv("USE_CLOUD_FUNCTION_REDIRECT", "false").lower() == "true"
        cloud_function_url = os.getenv("CLOUD_FUNCTION_REDIRECT_URL", "")
        base_url = cloud_function_url if (use_cloud_function and cloud_function_url) else request.host_url
        
        urls = []
        clicks_data = []
        # Reverse to show oldest first (since we fetched DESC)
        for url in reversed(db_urls):
            # Handle both dict and tuple results
            if isinstance(url, dict):
                url_id = url["id"]
                created = url["created"]
                original_url = url["original_url"]
                clicks = url["clicks"]
            else:
                url_id = url[0]
                created = url[1]
                original_url = url[2]
                clicks = url[3]
            
            # Hashid encoding is CPU intensive - but necessary for display
            hashid = hashids.encode(url_id)
            short_url = f"{base_url}{hashid}" if base_url.endswith('/') else f"{base_url}/{hashid}"
            
            url_data = {
                "id": url_id,
                "created": created,
                "original_url": original_url,
                "clicks": clicks,
                "short_url": short_url,
                "hashid": hashid
            }
            urls.append(url_data)
            clicks_data.append(clicks)

        # URLs already limited by database query
        display_urls = urls
        total_urls = total_count
        average_clicks = total_clicks // total_urls if total_urls > 0 else 0
        has_more = total_urls > len(display_urls)

        logger.info(f"Stats page accessed by user_id: {user_id} (total_urls: {total_urls}, showing: {len(display_urls)})")
        # Charts removed for performance - table shows all necessary data
        return render_template("stats.html", urls=display_urls, graph1=None, graph2=None, total_urls=total_urls, total_clicks=total_clicks, average_clicks=average_clicks, has_more=has_more)
    except Exception as e:
        logger.error(f"Error in stats: {e}", exc_info=True)
        flash("An error occurred while loading statistics. Please try again.")
        return redirect(url_for("index"))


# Registration and login routes


@application.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Perform validation checks
        if not username or not password or not confirm_password:
            flash("All fields are required.")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("register"))

        # Check if the username is already taken
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                    if cursor.fetchone():
                        flash("Username already exists. Please choose a different username.")
                        return redirect(url_for("register"))

                # Create a new user
                # Hash password with SHA256 before storing
                password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (username, password) VALUES (%s, %s)",
                        (username, password_hash),
                    )
                conn.commit()
                logger.info(f"New user registered: {username}")
        except Exception as e:
            logger.error(f"Error in register: {e}", exc_info=True)
            flash("An error occurred during registration. Please try again.")
            return redirect(url_for("register"))

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@application.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Perform validation checks
        if not username or not password:
            flash("All fields are required.")
            return redirect(url_for("login"))

        # Check if the username and password are valid
        try:
            # Hash the provided password with SHA256
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, username FROM users WHERE username = %s AND password = %s",
                        (username, password_hash),
                    )
                    user = cursor.fetchone()

            if user:
                # Handle both tuple and dict results (DictCursor vs regular cursor)
                if isinstance(user, dict):
                    user_id = user["id"]
                    session["user_id"] = user_id
                    session["username"] = user["username"]
                else:
                    user_id = user[0]
                    session["user_id"] = user_id
                    session["username"] = user[1]
                logger.info(f"User logged in: {username} (id: {user_id})")
                flash("Login successful!", "success")
                return redirect(url_for("index"))
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                flash("Invalid username or password.")
                return redirect(url_for("login"))
        except Exception as e:
            logger.error(f"Error in login: {e}", exc_info=True)
            flash("An error occurred during login. Please try again.")
            return redirect(url_for("login"))

    return render_template("login.html")


@application.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@application.route("/health")
def health():
    """Health check endpoint for Kubernetes and Docker.
    
    Ultra-fast health check optimized for high-load scenarios.
    Avoids database queries under load to prevent timeouts and pod restarts.
    """
    try:
        # Ultra-fast health check: just verify pool exists, don't query DB
        # This prevents health check from blocking under load
        db_status = "connected" if _db_pool is not None else "pool_not_initialized"
        
        # Check GCS client (if configured) - this is fast, no timeout needed
        gcs_status = "available" if gcs_client else "not_configured"
        
        # Only return unhealthy if pool is completely broken
        # Don't do actual DB query to avoid blocking under load
        if db_status == "pool_not_initialized":
            return jsonify({
                "status": "unhealthy",
                "service": "url-shortener",
                "database": db_status,
                "gcs": gcs_status,
                "timestamp": datetime.utcnow().isoformat()
            }), 503
        

        # Actual DB connectivity is tested by real requests, not health checks
        return jsonify({
            "status": "healthy",
            "service": "url-shortener",
            "database": db_status,
            "gcs": gcs_status,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "error": str(e)[:100],  # Limit error message length
            "timestamp": datetime.utcnow().isoformat()
        }), 503


@application.route("/metrics")
def metrics():
    """
    Prometheus-compatible metrics endpoint.
    
    Why metrics?
    - Monitor application health and performance
    - Track error rates and request counts
    - Used by monitoring tools (Prometheus, Grafana, Cloud Monitoring)
    - Helps identify performance bottlenecks
    """
    try:
        # Simple Prometheus format metrics
        metrics_text = f"""# HELP url_shortener_requests_total Total number of requests
# TYPE url_shortener_requests_total counter
url_shortener_requests_total {_metrics['requests_total']}

# HELP url_shortener_errors_total Total number of errors
# TYPE url_shortener_errors_total counter
url_shortener_errors_total {_metrics['errors_total']}
"""
        return metrics_text, 200, {'Content-Type': 'text/plain; version=0.0.4'}
    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        return jsonify({"error": "Failed to generate metrics"}), 500


if __name__ == "__main__":
    application.run(debug=True)
