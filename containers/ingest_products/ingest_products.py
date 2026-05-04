import os
import logging
import json
from datetime import datetime
import requests
import pandas as pd
import boto3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PRODUCTS_SERVICE_URL = os.getenv('PRODUCTS_SERVICE_URL', 'http://localhost:8081/api')
S3_BUCKET = os.getenv('S3_BUCKET', 'ecommerce-athena-results-12345')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

def fetch_products():
    """Fetch all products from Products Service API (Java)."""
    logger.info(f"Starting fetch from {PRODUCTS_SERVICE_URL}/products")
    
    all_products = []
    page = 0
    size = 100
    
    while True:
        try:
            url = f"{PRODUCTS_SERVICE_URL}/products?page={page}&size={size}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            products = data.get('content', [])
            
            if not products:
                break
            
            all_products.extend(products)
            logger.info(f"Fetched page {page} with {len(products)} products (total: {len(all_products)})")
            
            page += 1
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching products: {e}")
            raise

    logger.info(f"Total products fetched: {len(all_products)}")
    return all_products

def save_to_csv(products: list, filename: str) -> str:
    """Convert products list to CSV and save locally."""
    try:
        df = pd.DataFrame(products)
        df.to_csv(filename, index=False)
        logger.info(f"Saved {len(df)} products to {filename}")
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
        logger.info("=== Starting Products Ingesta ===")
        
        products = fetch_products()
        
        if not products:
            logger.warning("No products to ingest")
            return
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        csv_file = f"/tmp/products_{timestamp}.csv"
        
        save_to_csv(products, csv_file)
        
        s3_key = f"ingesta/products/products_{timestamp}.csv"
        upload_to_s3(csv_file, s3_key)
        
        logger.info("=== Products Ingesta Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Fatal error in products ingesta: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
