import boto3

ficheroUpload = "data.csv"
bucket = "ecommerce-athena-results-12345"
object_key = "analytics/orders/data.csv"

s3 = boto3.client("s3")
s3.upload_file(
    ficheroUpload,
    bucket,
    object_key,
)

print("Ingesta completada")