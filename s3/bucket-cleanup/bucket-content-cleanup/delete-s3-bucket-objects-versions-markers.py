
import time
import sys
import boto3
import logging
import math
from concurrent.futures import ThreadPoolExecutor

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

s3 = boto3.client('s3')

def bucket_exists(bucket_name):
    """Check if a bucket exists."""
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except s3.exceptions.ClientError:
        return False

def get_bucket_stats(bucket_name):
    """Get the total number and size of objects in a bucket."""

    # paginator -- to overcome 1000-record limitation
    paginator = s3.get_paginator('list_objects_v2')
    total_size = 0
    total_count = 0

    for page in paginator.paginate(Bucket=bucket_name):
        if 'Contents' in page:
            total_count += len(page['Contents'])
            total_size += sum(obj['Size'] for obj in page['Contents'])

    return total_count, total_size

def delete_objects_in_page(bucket_name, objects):
    """Delete a batch of objects in a bucket."""
    if objects:
        try:
            response = s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
            deleted = response.get('Deleted', [])
            if 'Errors' in response:
                logging.error(f"Errors: {response['Errors']}")
            return len(deleted)
        except s3.exceptions.ClientError as e:
            logging.error(f"Error deleting objects in page: {e}")
            return 0
    return 0

def delete_all_versions(bucket_name):
    """Delete all object versions and delete markers in a bucket."""

    # paginator -- to overcome 1000-record limitation
    paginator = s3.get_paginator('list_object_versions')
    object_count = 0
    start_time = time.time()

    # ThreadPoolExecutor -- to make paginated records deleted concurrently
    with ThreadPoolExecutor() as executor:
        futures = []
        for page in paginator.paginate(Bucket=bucket_name):
            objects_to_delete = []
            if 'Versions' in page:
                objects_to_delete.extend([{'Key': version['Key'], 'VersionId': version['VersionId']} for version in page['Versions']])
            if 'DeleteMarkers' in page:
                objects_to_delete.extend([{'Key': marker['Key'], 'VersionId': marker['VersionId']} for marker in page['DeleteMarkers']])

            if objects_to_delete:
                futures.append(executor.submit(delete_objects_in_page, bucket_name, objects_to_delete))

        for future in futures:
            object_count += future.result()

    end_time = time.time()
    duration = end_time - start_time
    logging.info(f"Deleted {object_count} versions and delete markers from bucket '{bucket_name}' in {duration:.2f} seconds.")
    return object_count, duration

def delete_all_objects(bucket_name):
    """Delete all objects in a bucket."""
    paginator = s3.get_paginator('list_objects_v2')
    object_count = 0
    start_time = time.time()
    
    # ThreadPoolExecutor -- to make paginated records deleted concurrently
    with ThreadPoolExecutor() as executor:
        futures = []
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                futures.append(executor.submit(delete_objects_in_page, bucket_name, objects_to_delete))

        for future in futures:
            object_count += future.result()

    end_time = time.time()
    duration = end_time - start_time
    logging.info(f"Deleted {object_count} objects from bucket '{bucket_name}' in {duration:.2f} seconds.")
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

    total_object_count = 0
    total_version_count = 0
    total_size_before = 0
    total_size_after = 0

    for bucket_name in bucket_names:
        if bucket_exists(bucket_name):
            pre_delete_count, pre_delete_size = get_bucket_stats(bucket_name)
            logging.info(f"Bucket '{bucket_name}' contains {pre_delete_count} objects with total size {bytes_to_human_readable(pre_delete_size)} before deletion.")

            obj_count, obj_duration = delete_all_objects(bucket_name)
            version_count, version_duration = delete_all_versions(bucket_name)
            total_object_count += obj_count
            total_version_count += version_count

            post_delete_count, post_delete_size = get_bucket_stats(bucket_name)
            logging.info(f"Bucket '{bucket_name}' contains {post_delete_count} objects with total size {bytes_to_human_readable(post_delete_size)} after deletion.")

            total_size_before += pre_delete_size
            total_size_after += post_delete_size

            logging.info(f"Time to delete objects: {obj_duration:.2f} seconds")
            logging.info(f"Time to delete versions and delete markers: {version_duration:.2f} seconds")
        else:
            logging.warning(f"Bucket '{bucket_name}' does not exist.")

    end_time = time.time()
    total_duration = end_time - start_time

    # Print summary of operations
    logging.info(f"Total objects deleted: {total_object_count}")
    logging.info(f"Total versions and delete markers deleted: {total_version_count}")
    logging.info(f"Total size before deletion: {bytes_to_human_readable(total_size_before)}")
    logging.info(f"Total size after deletion: {bytes_to_human_readable(total_size_after)}")
    logging.info(f"Total script duration: {total_duration:.2f} seconds")
