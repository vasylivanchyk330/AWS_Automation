import time
import sys
import subprocess
import logging
import json
import math
import random
from concurrent.futures import ThreadPoolExecutor
import boto3

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create the S3 client once and reuse it
s3 = boto3.client('s3')

def bucket_exists(bucket_name):
    """Check if a bucket exists using AWS CLI."""
    try:
        result = subprocess.run(["aws", "s3api", "head-bucket", "--bucket", bucket_name], capture_output=True, text=True, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def get_bucket_stats(bucket_name):
    """Get the total number and size of objects in a bucket using AWS CLI."""
    result = subprocess.run(
        ["aws", "s3api", "list-objects-v2", "--bucket", bucket_name, "--query", "Contents[].Size"],
        capture_output=True,
        text=True,
        check=True
    )
    if result.stdout.strip():
        sizes = json.loads(result.stdout)
        if sizes:
            total_size = sum(sizes)
            total_count = len(sizes)
            return total_count, total_size
    return 0, 0

def get_bucket_versions_stats(bucket_name):
    """Get the total number and size of object versions and delete markers in a bucket using AWS CLI."""
    result = subprocess.run(
        ["aws", "s3api", "list-object-versions", "--bucket", bucket_name, "--query", "[Versions[].Size, DeleteMarkers[].Size]"],
        capture_output=True,
        text=True,
        check=True
    )
    if result.stdout.strip():
        sizes = json.loads(result.stdout)
        version_sizes = sizes[0] if sizes[0] else []
        marker_sizes = sizes[1] if sizes[1] else []
        total_version_size = sum(version_sizes)
        total_version_count = len(version_sizes)
        total_marker_size = sum(marker_sizes)
        total_marker_count = len(marker_sizes)
        return total_version_count, total_version_size, total_marker_count, total_marker_size
    return 0, 0, 0, 0

def delete_objects_in_page(bucket_name, objects):
    """Delete a batch of objects in a bucket with exponential backoff."""
    if objects:
        max_retries = 5
        base_delay = 1  # starting delay in seconds

        for attempt in range(max_retries):
            try:
                response = s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
                deleted = response.get('Deleted', [])
                if 'Errors' in response:
                    logging.error(f"Errors: {response['Errors']}")
                return len(deleted)
            except s3.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'SlowDown':
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logging.error(f"Error deleting objects in page: {e}. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    logging.error(f"Error deleting objects in page: {e}. Not retrying.")
                    return 0
    return 0

def delete_all_versions(bucket_name):
    """Delete all object versions and delete markers in a bucket."""
    paginator = s3.get_paginator('list_object_versions')
    object_count = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=5) as executor:  # Limiting the number of threads
        while True:
            futures = []
            pages_deleted = 0
            for page in paginator.paginate(Bucket=bucket_name):
                objects_to_delete = []
                if 'Versions' in page:
                    objects_to_delete.extend([{'Key': version['Key'], 'VersionId': version['VersionId']} for version in page['Versions']])
                if 'DeleteMarkers' in page:
                    objects_to_delete.extend([{'Key': marker['Key'], 'VersionId': marker['VersionId']} for marker in page['DeleteMarkers']])

                if objects_to_delete:
                    futures.append(executor.submit(delete_objects_in_page, bucket_name, objects_to_delete))

            for future in futures:
                pages_deleted += future.result()
                object_count += future.result()

            # Check if any pages were deleted, if none were deleted break the loop
            if pages_deleted == 0:
                break

    end_time = time.time()
    duration = end_time - start_time
    logging.info(f"Deleted {object_count} versions and delete markers from bucket '{bucket_name}' in {duration:.2f} seconds.")
    return object_count, duration

def delete_all_objects(bucket_name):
    """Delete all objects in a bucket."""
    paginator = s3.get_paginator('list_objects_v2')
    object_count = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=5) as executor:  # Limiting the number of threads
        futures = []
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                futures.append(executor.submit(delete_objects_in_page, bucket_name, objects_to_delete))

        for future in futures:
            object_count += future.result()

    end_time = time.time()
    duration = end_time - start_time
    return object_count, duration

def bytes_to_human_readable(size_in_bytes):
    """Convert bytes to a human-readable format."""
    if size_in_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_in_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_in_bytes / p, 2)
    return f"{s} {size_name[i]}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("Usage: python delete_s3_objects.py <bucket-name1> <bucket-name2> ...")
        sys.exit(1)

    start_time = time.time()
    bucket_names = sys.argv[1:]

    for bucket_name in bucket_names:
        if bucket_exists(bucket_name):
            pre_delete_count, pre_delete_size = get_bucket_stats(bucket_name)
            pre_version_count, pre_version_size, pre_marker_count, pre_marker_size = get_bucket_versions_stats(bucket_name)
            total_bucket_size_before = pre_delete_size + pre_version_size + pre_marker_size

            logging.info(f"Total Object Count Before Deletion: {pre_delete_count}")
            logging.info(f"Total Object Size Before Deletion: {bytes_to_human_readable(pre_delete_size)}")
            logging.info(f"Total Version Count Before Deletion: {pre_version_count}")
            logging.info(f"Total Version Size Before Deletion: {bytes_to_human_readable(pre_version_size)}")
            logging.info(f"Total Delete Marker Count Before Deletion: {pre_marker_count}")
            logging.info(f"Total Delete Marker Size Before Deletion: {bytes_to_human_readable(pre_marker_size)}")
            logging.info(f"Total Bucket Size Before Deletion: {bytes_to_human_readable(total_bucket_size_before)}")

            obj_count, obj_duration = delete_all_objects(bucket_name)
            version_count, version_duration = delete_all_versions(bucket_name)

            post_delete_count, post_delete_size = get_bucket_stats(bucket_name)
            post_version_count, post_version_size, post_marker_count, post_marker_size = get_bucket_versions_stats(bucket_name)
            total_bucket_size_after = post_delete_size + post_version_size + post_marker_size

            logging.info(f"Total Object Count After Deletion: {post_delete_count}")
            logging.info(f"Total Object Size After Deletion: {bytes_to_human_readable(post_delete_size)}")
            logging.info(f"Total Version Count After Deletion: {post_version_count}")
            logging.info(f"Total Version Size After Deletion: {bytes_to_human_readable(post_version_size)}")
            logging.info(f"Total Delete Marker Count After Deletion: {post_marker_count}")
            logging.info(f"Total Delete Marker Size After Deletion: {bytes_to_human_readable(post_marker_size)}")
            logging.info(f"Total Bucket Size After Deletion: {bytes_to_human_readable(total_bucket_size_after)}")

            logging.info(f"Time to delete objects: {obj_duration:.2f} seconds")
            logging.info(f"Time to delete versions and delete markers: {version_duration:.2f} seconds")
        else:
            logging.warning(f"Bucket '{bucket_name}' does not exist.")

    end_time = time.time()
    total_duration = end_time - start_time

    # Print summary of operations
    logging.info(f"Total script duration: {total_duration:.2f} seconds")
