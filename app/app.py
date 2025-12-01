import pymysql
import json
import os
from hashids import Hashids
from flask import Flask, render_template, request, flash, redirect, url_for, session
import plotly.graph_objects as go
from gradio_client import Client
from google.cloud import storage
from plotly.subplots import make_subplots
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

# Gradio client initialization (can be set via environment variable)
client_uri = os.getenv("GRADIO_ENDPOINT", "")
if not client_uri:
    print("Run the Notebook to get the Generative Endpoint")
    print("Notebook Link: https://www.kaggle.com/code/eswardivi/qr-code-generator")
    client_uri = input("Enter the Generative Endpoint: ")

client = Client(client_uri) if client_uri else None

# Initialize GCP Cloud Storage client
# Note: GCP credentials should be set via GOOGLE_APPLICATION_CREDENTIALS env var or
# the client will use default credentials from gcloud
try:
    if gcp_project_id:
        gcs_client = storage.Client(project=gcp_project_id)
    else:
        gcs_client = storage.Client()
except Exception as e:
    print(f"Warning: Could not initialize GCS client: {e}")
    print("GCS functionality will be disabled. Set GOOGLE_APPLICATION_CREDENTIALS or configure gcloud.")
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
        print("Error: GCS client not initialized")
        return None
        
    try:
        print(f"Uploading QR to GCS bucket: {bucket_name}")
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        
        # Make the blob publicly accessible
        blob.make_public()
        
        # Return the public URL
        public_url = blob.public_url
        print(f"Upload successful: {public_url}")
        return public_url
    except Exception as e:
        print(f"Error uploading image to GCS: {e}")
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


application = Flask(__name__)
application.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "Divi")

hashids = Hashids(min_length=4, salt=application.config["SECRET_KEY"])


@application.context_processor
def inject_gcs_config():
    """Inject GCS bucket configuration into all templates."""
    return {
        'gcs_bucket_name': gcs_bucket_name,
        'gcs_base_url': f"https://storage.googleapis.com/{gcs_bucket_name}" if gcs_bucket_name else ""
    }


def get_db_connection():
    connection = pymysql.connect(
        host=host, port=port, user=user, password=password, database=database
    )
    return connection


def insert_url(url, user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO urls (original_url, user_id) VALUES (%s, %s)", (url, user_id)
    )
    connection.commit()
    url_id = cursor.lastrowid
    cursor.close()
    connection.close()
    return url_id


def get_short_url(url_id):
    hashid = hashids.encode(url_id)
    short_url = request.host_url + hashid
    return short_url, hashid


@application.route("/", methods=("GET", "POST"))
def index():
    if "user_id" not in session:
        flash("You must be logged in to access this page.")
        return redirect(url_for("login"))

    if request.method == "POST":
        url = request.form["url"]
        img_desc = request.form["image-description"]
        if not url:
            flash("The URL is required!")
            return redirect(url_for("index"))

        user_id = session["user_id"]
        url_id = insert_url(url, user_id)
        short_url, hashid = get_short_url(url_id)

        result = None
        if img_desc and client:
            print("Image is Generating")
            result = client.predict(
                f"{short_url}",  # str  in 'QR Code Content' Textbox component
                f"{img_desc}",  # str  in 'Prompt' Textbox component
                "ugly, disfigured, low quality, blurry, nsfw",  # str  in 'Negative Prompt' Textbox component
                fn_index=0,
            )
            # Upload to GCS and get public URL
            blob_name = f"{hashid}.png"
            result = upload_to_gcs(result, gcs_bucket_name, blob_name)
            if not result:
                # Fallback to constructing URL if upload fails but file exists
                result = get_gcs_public_url(gcs_bucket_name, blob_name)
            print(f"QR code URL: {result}")

        return render_template("index.html", short_url=short_url, image_path=result)

    return render_template("index.html")


@application.route("/<id>")
def url_redirect(id):
    conn = get_db_connection()

    original_id = hashids.decode(id)
    if original_id:
        original_id = original_id[0]
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
            conn.close()
            return redirect(original_url)
        else:
            flash("Invalid URL")
            return redirect(url_for("index"))
    else:
        flash("Invalid URL")
        return redirect(url_for("index"))


@application.route("/stats")
def stats():
    if "user_id" not in session:
        flash("You must be logged in to access this page.")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()

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
    # fig2.update_layout(title="Distribution of Clicks among URLs")

    graph1 = fig1.to_html(full_html=False)
    graph2 = fig2.to_html(full_html=False)

    total_urls = len(urls)
    total_clicks = sum(clicks_data)
    average_clicks = total_clicks // total_urls if total_urls > 0 else 0

    return render_template("stats.html", urls=urls, graph1=graph1, graph2=graph2, total_urls=total_urls, total_clicks=total_clicks, average_clicks=average_clicks)


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
        conn = get_db_connection()
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
        conn.close()

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
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username FROM users WHERE username = %s AND password = %s",
                (username, password),
            )
            user = cursor.fetchone()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            flash("Login successful!")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.")
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
        # Basic health check - can be extended to check database, GCS, etc.
        return {"status": "healthy", "service": "url-shortener"}, 200
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503


if __name__ == "__main__":
    application.run(debug=True)
