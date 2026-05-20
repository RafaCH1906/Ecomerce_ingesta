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

ORDERS_SERVICE_URL = os.getenv('ORDERS_SERVICE_URL', 'http://localhost:3003/api')
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

def fetch_orders(token: str):
    """Fetch all orders from Orders Service API (Node.js)."""
    logger.info(f"Starting fetch from {ORDERS_SERVICE_URL}/orders")
    
    try:
        url = f"{ORDERS_SERVICE_URL}/orders"
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        
        orders = response.json()
        
        if not isinstance(orders, list):
            orders = [orders]
        
        logger.info(f"Total orders fetched: {len(orders)}")
        return orders
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching orders: {e}")
        raise

def flatten_order(order: dict) -> dict:
    """Flatten nested order structure for CSV export."""
    flat = {
        'order_id': order.get('_id', order.get('id')),
        'user_id': order.get('user_id'),
        'estado': order.get('estado'),
        'total': order.get('total'),
        'created_at': order.get('created_at', order.get('fecha')),
    }
    
    # Handle nested productos array - take first or aggregate
    productos = order.get('productos', [])
    if productos:
        flat['product_id'] = productos[0].get('product_id')
        flat['product_nombre'] = productos[0].get('nombre')
        flat['cantidad'] = productos[0].get('cantidad')
        flat['precio_unitario'] = productos[0].get('precio_unitario')
    
    # Handle nested direccion_envio
    direccion = order.get('direccion_envio', {})
    flat['ciudad'] = direccion.get('ciudad')
    flat['pais'] = direccion.get('pais')
    flat['codigo_postal'] = direccion.get('codigo_postal')
    
    return flat

def save_to_csv(orders: list, filename: str) -> str:
    """Convert orders list to CSV and save locally."""
    try:
        flat_orders = [flatten_order(order) for order in orders]
        df = pd.DataFrame(flat_orders)
        df.to_csv(filename, index=False)
        logger.info(f"Saved {len(df)} orders to {filename}")
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
        logger.info("=== Starting Orders Ingesta ===")
        
        token = authenticate()
        orders = fetch_orders(token)
        
        if not orders:
            logger.warning("No orders to ingest")
            return
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        csv_file = f"/tmp/orders_{timestamp}.csv"
        
        save_to_csv(orders, csv_file)
        
        s3_key = f"ingesta/orders/orders_{timestamp}.csv"
        upload_to_s3(csv_file, s3_key)
        
        logger.info("=== Orders Ingesta Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Fatal error in orders ingesta: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
