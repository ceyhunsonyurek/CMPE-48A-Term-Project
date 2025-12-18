"""
Cloud Function for URL Redirection
Handles short URL redirection and click tracking
"""
import pymysql
from dbutils.pooled_db import PooledDB
from hashids import Hashids
import os
from flask import redirect
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connection pool for Cloud Function
# Cloud Functions can reuse instances, so a global pool is beneficial
_db_pool = None

def get_db_pool():
    """
    Initialize and return database connection pool.
    Uses lazy initialization - pool is created on first use.
    """
    global _db_pool
    
    if _db_pool is None:
        # Get database configuration from environment variables
        db_host = os.getenv("DB_HOST")
        db_port = int(os.getenv("DB_PORT", 3306))
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_database = os.getenv("DB_DATABASE", "urlshortener")
        
        # Connection pool configuration
        # Smaller pool size for Cloud Functions (each instance has its own pool)
        pool_min_size = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
        pool_max_size = int(os.getenv("DB_POOL_MAX_SIZE", "5"))
        
        if not all([db_host, db_user, db_password]):
            raise ValueError("Database configuration missing")
        
        try:
            _db_pool = PooledDB(
                creator=pymysql,
                mincached=pool_min_size,
                maxcached=pool_max_size,
                maxconnections=pool_max_size,
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_database,
                autocommit=False,
                connect_timeout=10,
                read_timeout=10,
                write_timeout=10,
                charset='utf8mb4',
                use_unicode=True,
            )
            logger.info(f"Database connection pool initialized (min={pool_min_size}, max={pool_max_size})")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    return _db_pool


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
    
    try:
        # Get connection from pool (lazy initialization)
        pool = get_db_pool()
        conn = pool.connection()
        
        try:
            # Get original URL and current click count
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT original_url, clicks FROM urls WHERE id = %s",
                    (url_id,)
                )
                url_data = cursor.fetchone()
            
            if not url_data:
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
            
            # Redirect to original URL
            return redirect(original_url, code=302)
            
        except pymysql.Error as e:
            # Rollback on error
            try:
                conn.rollback()
            except:
                pass
            logger.error(f"Database error: {e}")
            return f"Database error: {str(e)}", 500
        finally:
            # Return connection to pool (not close it)
            conn.close()  # In pooled connections, close() returns connection to pool
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return f"Database configuration error: {str(e)}", 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return f"Error: {str(e)}", 500

