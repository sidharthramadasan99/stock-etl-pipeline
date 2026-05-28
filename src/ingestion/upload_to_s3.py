import boto3
import os
import logging
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

# -- Logging setup --
logging.basicConfig(
    filename="logs/s3_upload.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# -- Configurations --
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME        = os.getenv("S3_BUCKET_NAME")
RAW_DIR               = "data/raw"

# -- Create S3 client --
def get_s3_client():
    client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    logger.info("S3 client created")
    return client

# -- Upload all CSVs from data/raw to S3 --
def upload_raw_files(s3_client, local_dir, bucket_name):
    files = [f for f in os.listdir(local_dir) if f.endswith(".csv")]
    
    if not files:
        print("No CSV files found in data/raw/")
        return
    
    print(f"Uploading {len(files)} files to s3://{bucket_name}/raw/")

    for filename in files:
        local_path = os.path.join(local_dir, filename)
        s3_key     = f"raw/{filename}"

        try:
            s3_client.upload_file(local_path, bucket_name, s3_key)
            logger.info(f"Uploaded {filename} to s3://{bucket_name}/{s3_key}")
            print(f"  SUCCESS: {filename} -> s3://{bucket_name}/{s3_key}")
        except ClientError as e:
            logger.error(f"Failed to upload {filename}: {e}")
            print(f"  ERROR: Failed to upload {filename}: {e}")

# -- Upload processed parquet to S3 --
def upload_processed_files(s3_client, bucket_name):
    processed_files = [
        ("data/processed/enriched_stocks.parquet", "processed/enriched_stocks.parquet"),
        ("data/processed/ticker_summary.csv", "processed/ticker_summary.csv")
    ]

    print(f"\nUploading processed files to s3://{bucket_name}/processed/")

    for local_path, s3_key in processed_files:
        if not os.path.exists(local_path):
            print(f"  SKIP: {local_path} not found")
            continue
        try:
            s3_client.upload_file(local_path, bucket_name, s3_key)
            logger.info(f"Uploaded {local_path} to s3://{bucket_name}/{s3_key}")
            print(f"  SUCCESS: {local_path} -> s3://{bucket_name}/{s3_key}")
        except ClientError as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            print(f"  ERROR: {e}")

# -- Verify uploads by listing S3 bucket --
def verify_uploads(s3_client, bucket_name):
    print(f"\nFiles in s3://{bucket_name}/:")
    response = s3_client.list_objects_v2(Bucket=bucket_name)

    if "Contents" not in response:
        print("  Bucket is empty - uploads may have failed")
        return
    
    for obj in response["Contents"]:
        size_kb = round(obj["Size"] / 1024, 2)
        print(f"  {obj['Key']} ({size_kb} KB)")
    
    logger.info(f"Verified {len(response['Contents'])} files in S3 bucket")

# -- Entry point --
if __name__ == "__main__":
    s3_client = get_s3_client()
    upload_raw_files(s3_client, RAW_DIR, S3_BUCKET_NAME)
    upload_processed_files(s3_client, S3_BUCKET_NAME)
    verify_uploads(s3_client, S3_BUCKET_NAME)
    print("\nS3 upload complete. Check logs/s3_upload.log for details.")
