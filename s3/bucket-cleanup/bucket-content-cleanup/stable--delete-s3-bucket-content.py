import time
import sys
import boto3
from concurrent.futures import ThreadPoolExecutor

# ###########
start_time = time.time()
# ###########

def bucket_exists(bucket_name):
    s3 = boto3.client('s3')
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except s3.exceptions.ClientError:
        return False

def delete_objects_in_page(bucket_name, objects):
    s3 = boto3.client('s3')
    if objects:
        s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
        print(f"Deleted {len(objects)} objects from bucket '{bucket_name}'.")

def delete_delete_markers(bucket_name):
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_object_versions')

    with ThreadPoolExecutor() as executor:
        futures = []
        for page in paginator.paginate(Bucket=bucket_name):
            if 'DeleteMarkers' in page:
                delete_markers = [{'Key': marker['Key'], 'VersionId': marker['VersionId']} for marker in page['DeleteMarkers']]
                futures.append(executor.submit(delete_objects_in_page, bucket_name, delete_markers))
        
        for future in futures:
            future.result()

def delete_objects(bucket_name):
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')

    with ThreadPoolExecutor() as executor:
        futures = []
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                futures.append(executor.submit(delete_objects_in_page, bucket_name, objects_to_delete))
        
        for future in futures:
            future.result()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_s3_objects.py <bucket-name1> <bucket-name2> ...")
        sys.exit(1)

    bucket_names = sys.argv[1:]

    for bucket_name in bucket_names:
        if bucket_exists(bucket_name):
            delete_objects(bucket_name)
            delete_delete_markers(bucket_name)
        else:
            print(f"Bucket '{bucket_name}' does not exist.")

# ###########
end_time = time.time()
duration = end_time - start_time
print("Script duration:", duration, "seconds")
# ###########
