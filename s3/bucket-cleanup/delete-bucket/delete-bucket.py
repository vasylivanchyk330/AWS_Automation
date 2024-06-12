import sys
import boto3
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create the S3 client once and reuse it
s3 = boto3.client('s3')

def bucket_exists(bucket_name):
    """Check if a bucket exists."""
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except s3.exceptions.ClientError:
        return False

def is_bucket_empty(bucket_name):
    """Check if a bucket is empty."""
    response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
    return 'Contents' not in response

def delete_bucket(bucket_name):
    """Delete the bucket."""
    try:
        s3.delete_bucket(Bucket=bucket_name)
        logging.info(f"Bucket '{bucket_name}' deleted successfully.")
    except s3.exceptions.ClientError as e:
        logging.error(f"Error deleting bucket '{bucket_name}': {e}")

def main():
    """Main function to check and delete empty buckets."""
    if len(sys.argv) < 2:
        logging.error("Usage: python delete_s3_buckets_if_empty.py <bucket-name1> <bucket-name2> ...")
        sys.exit(1)

    bucket_names = sys.argv[1:]
    for bucket_name in bucket_names:
        if bucket_exists(bucket_name):
            if is_bucket_empty(bucket_name):
                delete_bucket(bucket_name)
            else:
                logging.info(f"Bucket '{bucket_name}' is not empty.")
        else:
            logging.warning(f"Bucket '{bucket_name}' does not exist.")

if __name__ == "__main__":
    main()

