import pymysql
import json
import os
import tempfile
import logging
from datetime import datetime
from hashids import Hashids
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
import plotly.graph_objects as go
import qrcode
from google.cloud import storage
from plotly.subplots import make_subplots
from dotenv import load_dotenv
from pymysql.cursors import DictCursor
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

# Simple database connection with context manager
# Note: For production, consider using SQLAlchemy with connection pooling
@contextmanager
def get_db_connection():
    """Get database connection with context manager (auto-close)."""
    conn = None
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=DictCursor,
            autocommit=False,
            connect_timeout=10,
            read_timeout=10,
            write_timeout=10,
        )
        yield conn
    except pymysql.Error as e:
        _metrics['errors_total'] += 1
        logger.error(f"Database error: {e}", exc_info=True)
        raise
    except Exception as e:
        _metrics['errors_total'] += 1
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# QR code generation is now handled internally using qrcode library
# No external API dependencies required

# Initialize GCP Cloud Storage client
# Note: GCP credentials should be set via GOOGLE_APPLICATION_CREDENTIALS env var or
# the client will use default credentials from gcloud
try:
    if gcp_project_id:
        gcs_client = storage.Client(project=gcp_project_id)
    else:
        gcs_client = storage.Client()
    logger.info("GCS client initialized successfully")
except Exception as e:
    logger.warning(f"Could not initialize GCS client: {e}")
    logger.warning("GCS functionality will be disabled. Set GOOGLE_APPLICATION_CREDENTIALS or configure gcloud.")
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
            img_desc = request.form.get("image-description", "").strip()
            
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
                    # Fallback to constructing URL if upload fails but file exists
                    result = get_gcs_public_url(gcs_bucket_name, blob_name)
                    logger.warning(f"GCS upload failed, using fallback URL: {result}")
                
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
            flash("Invalid URL")
            return redirect(url_for("index"))
        
        original_id = original_id[0]
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT original_url, clicks FROM urls WHERE id = %s", (original_id,)
                )
                url_data = cursor.fetchone()

            if url_data:
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
                flash("Invalid URL")
                return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Error in url_redirect: {e}", exc_info=True)
        flash("An error occurred while redirecting. Please try again.")
        return redirect(url_for("index"))


@application.route("/stats")
def stats():
    """Display statistics for user's URLs."""
    if "user_id" not in session:
        flash("You must be logged in to access this page.")
        return redirect(url_for("login"))

    try:
        user_id = session["user_id"]
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, created, original_url, clicks FROM urls WHERE user_id = %s",
                    (user_id,),
                )
                db_urls = cursor.fetchall()

        urls = []
        clicks_data = []
        for url in db_urls:
            url_data = {
                "id": url[0],
                "created": url[1],
                "original_url": url[2],
                "clicks": url[3],
            }
            url_data["short_url"] = request.host_url + hashids.encode(url_data["id"])
            urls.append(url_data)
            clicks_data.append(url_data["clicks"])

        # Create a bar graph showing number of clicks per URL
        fig1 = go.Figure(data=[go.Bar(x=[url["short_url"] for url in urls], y=clicks_data)])
        fig1.update_layout(
            xaxis_title="URL",
            yaxis_title="Number of Clicks",
        )

        # Create a pie chart showing the distribution of clicks among URLs
        fig2 = go.Figure(data=[go.Pie(labels=[url["short_url"] for url in urls], values=clicks_data)])

        graph1 = fig1.to_html(full_html=False)
        graph2 = fig2.to_html(full_html=False)

        total_urls = len(urls)
        total_clicks = sum(clicks_data)
        average_clicks = total_clicks // total_urls if total_urls > 0 else 0

        logger.info(f"Stats page accessed by user_id: {user_id} (total_urls: {total_urls})")
        return render_template("stats.html", urls=urls, graph1=graph1, graph2=graph2, total_urls=total_urls, total_clicks=total_clicks, average_clicks=average_clicks)
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
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (username, password) VALUES (%s, %s)",
                        (username, password),
                    )
                conn.commit()
                logger.info(f"New user registered: {username}")
        except Exception as e:
            logger.error(f"Error in register: {e}", exc_info=True)
            flash("An error occurred during registration. Please try again.")
            return redirect(url_for("register"))

        flash("Registration successful! You can now log in.")
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
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, username FROM users WHERE username = %s AND password = %s",
                        (username, password),
                    )
                    user = cursor.fetchone()

            if user:
                session["user_id"] = user[0]
                session["username"] = user[1]
                logger.info(f"User logged in: {username} (id: {user[0]})")
                flash("Login successful!")
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
    flash("You have been logged out.")
    return redirect(url_for("login"))


@application.route("/health")
def health():
    """Health check endpoint for Kubernetes and Docker."""
    try:
        # Check database connection
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        
        # Check GCS client (if configured)
        gcs_status = "available" if gcs_client else "not_configured"
        
        return jsonify({
            "status": "healthy",
            "service": "url-shortener",
            "database": "connected",
            "gcs": gcs_status,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
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
