"""
Cloud Function for URL Redirection
Handles short URL redirection and click tracking
"""
import pymysql
from hashids import Hashids
import os
from flask import redirect


def url_redirect(request):
    """
    HTTP Cloud Function to handle URL redirection.
    
    Trigger: HTTP request to short URL
    Example: https://REGION-PROJECT.cloudfunctions.net/url-redirect/aB3d
    
    Args:
        request: Flask request object
        
    Returns:
        HTTP redirect response (302) to original URL
        or error message (404) if URL not found
    """
    # Extract hashid from request path
    # Path format: /url-redirect/{hashid} or /{hashid}
    path = request.path.strip('/')
    if path.startswith('url-redirect/'):
        hashid = path.split('/')[-1]
    else:
        hashid = path
    
    if not hashid:
        return "Invalid URL: hashid missing", 404
    
    # Decode hashid to get url_id
    # Use same salt as Flask app
    secret_key = os.getenv("SECRET_KEY", "Divi")
    hashids = Hashids(min_length=4, salt=secret_key)
    decoded = hashids.decode(hashid)
    
    if not decoded:
        return f"Invalid URL: {hashid}", 404
    
    url_id = decoded[0]
    
    # Get database configuration from environment variables
    db_host = os.getenv("DB_HOST")
    db_port = int(os.getenv("DB_PORT", 3306))
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_database = os.getenv("DB_DATABASE", "urlshortener")
    
    if not all([db_host, db_user, db_password]):
        return "Database configuration missing", 500
    
    try:
        # Connect to MySQL database (on VM)
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_database,
            connect_timeout=10
        )
        
        # Get original URL and current click count
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT original_url, clicks FROM urls WHERE id = %s",
                (url_id,)
            )
            url_data = cursor.fetchone()
        
        if not url_data:
            conn.close()
            return f"URL not found for hashid: {hashid}", 404
        
        original_url = url_data[0]
        clicks = url_data[1]
        
        # Increment click count
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE urls SET clicks = %s WHERE id = %s",
                (clicks + 1, url_id)
            )
        
        conn.commit()
        conn.close()
        
        # Redirect to original URL
        return redirect(original_url, code=302)
        
    except pymysql.Error as e:
        return f"Database error: {str(e)}", 500
    except Exception as e:
        return f"Error: {str(e)}", 500

