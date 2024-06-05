import time
import sys
import boto3
from concurrent.futures import ThreadPoolExecutor


# Function to check if a bucket exists
def bucket_exists(bucket_name):
    s3 = boto3.client('s3')
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except s3.exceptions.ClientError:
        return False

# Function to delete a batch of objects in a bucket
def delete_objects_in_page(bucket_name, objects):
    s3 = boto3.client('s3')
    if objects:
        s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
        return len(objects)
    return 0

# Function to delete delete markers in a bucket
def delete_delete_markers(bucket_name):
    s3 = boto3.client('s3')

    # paginator -- to overcome 1000-record limitation
    paginator = s3.get_paginator('list_object_versions')

    delete_marker_count = 0
    start_time = time.time()

    # ThreadPoolExecutor -- to make paginated delete-marker records deleted concurrently
    with ThreadPoolExecutor() as executor:
        futures = []
        for page in paginator.paginate(Bucket=bucket_name):
            if 'DeleteMarkers' in page:
                delete_markers = [{'Key': marker['Key'], 'VersionId': marker['VersionId']} for marker in page['DeleteMarkers']]
                futures.append(executor.submit(delete_objects_in_page, bucket_name, delete_markers))
        
        for future in futures:
            delete_marker_count += future.result()

    end_time = time.time()
    duration = end_time - start_time
    print(f"Deleted {delete_marker_count} delete markers from bucket '{bucket_name}' in {duration:.2f} seconds.")
    return delete_marker_count, duration

# Function to delete objects in a bucket
def delete_objects(bucket_name):
    s3 = boto3.client('s3')

    # paginator -- to overcome 1000-record limitation
    paginator = s3.get_paginator('list_objects_v2')

    object_count = 0
    start_time = time.time()

    # ThreadPoolExecutor -- to make paginated object records deleted concurrently
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
    print(f"Deleted {object_count} objects from bucket '{bucket_name}' in {duration:.2f} seconds.")
    return object_count, duration

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_s3_objects.py <bucket-name1> <bucket-name2> ...")
        sys.exit(1)

    start_time = time.time()
    bucket_names = sys.argv[1:]

    total_object_count = 0
    total_delete_marker_count = 0

    for bucket_name in bucket_names:
        if bucket_exists(bucket_name):
            obj_count, obj_duration = delete_objects(bucket_name)
            del_marker_count, del_marker_duration = delete_delete_markers(bucket_name)
            total_object_count += obj_count
            total_delete_marker_count += del_marker_count
        else:
            print(f"Bucket '{bucket_name}' does not exist.")

    end_time = time.time()
    total_duration = end_time - start_time

    # Print summary of operations
    print(f"Total objects deleted: {total_object_count}")
    print(f"Total delete markers deleted: {total_delete_marker_count}")
    print(f"Total script duration: {total_duration:.2f} seconds")
