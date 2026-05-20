import os
import logging
from datetime import datetime
import requests
import pandas as pd
import boto3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

USERS_SERVICE_URL = os.getenv('USERS_SERVICE_URL', 'http://localhost:8000/api')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'rafael@superadmin.com')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
S3_BUCKET = os.getenv('S3_BUCKET', 'ecommerce-athena-results-12345')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')


def authenticate() -> str:
    login_url = f"{USERS_SERVICE_URL}/auth/login"
    logger.info(f"Authenticating against {login_url}")

    response = requests.post(
        login_url,
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    response.raise_for_status()

    token = response.json().get('access_token')
    if not token:
        raise RuntimeError('No access_token returned by users service login')

    return token

def fetch_users(token: str):
    """Fetch all users from Users Service API."""
    logger.info(f"Starting fetch from {USERS_SERVICE_URL}/users")
    
    all_users = []
    skip = 0
    limit = 1000
    
    while True:
        try:
            url = f"{USERS_SERVICE_URL}/users?skip={skip}&limit={limit}"
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            response.raise_for_status()
            
            users = response.json()
            if not users:
                break
            
            all_users.extend(users)
            logger.info(f"Fetched {len(users)} users (total: {len(all_users)})")
            
            skip += limit
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching users: {e}")
            raise

    logger.info(f"Total users fetched: {len(all_users)}")
    return all_users

def save_to_csv(users: list, filename: str) -> str:
    """Convert users list to CSV and save locally."""
    try:
        df = pd.DataFrame(users)
        df.to_csv(filename, index=False)
        logger.info(f"Saved {len(df)} users to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error saving to CSV: {e}")
        raise

def upload_to_s3(file_path: str, object_key: str):
    """Upload CSV file to S3."""
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        s3_client.upload_file(file_path, S3_BUCKET, object_key)
        logger.info(f"Uploaded {file_path} to s3://{S3_BUCKET}/{object_key}")
    except Exception as e:
        logger.error(f"Error uploading to S3: {e}")
        raise

def main():
    try:
        logger.info("=== Starting Users Ingesta ===")
        
        token = authenticate()
        users = fetch_users(token)
        
        if not users:
            logger.warning("No users to ingest")
            return
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        csv_file = f"/tmp/users_{timestamp}.csv"
        
        save_to_csv(users, csv_file)
        
        s3_key = f"ingesta/users/users_{timestamp}.csv"
        upload_to_s3(csv_file, s3_key)
        
        logger.info("=== Users Ingesta Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Fatal error in users ingesta: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
