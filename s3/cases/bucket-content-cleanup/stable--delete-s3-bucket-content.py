import sys
import boto3

def bucket_exists(bucket_name):
    s3 = boto3.client('s3')
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except s3.exceptions.ClientError:
        return False

def delete_objects(bucket_name):
    s3 = boto3.client('s3')
    response = s3.list_objects_v2(Bucket=bucket_name)

    if 'Contents' in response:
        print(f"Objects found in bucket '{bucket_name}'. Deleting all objects...")
        objects = [{'Key': obj['Key']} for obj in response['Contents']]
        s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
        print(f"All objects deleted in bucket '{bucket_name}'.")
    else:
        print(f"Bucket '{bucket_name}' is empty. No objects to delete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_s3_objects.py <bucket-name1> <bucket-name2> ...")
        sys.exit(1)

    bucket_names = sys.argv[1:]

    for bucket_name in bucket_names:
        if bucket_exists(bucket_name):
            delete_objects(bucket_name)
        else:
            print(f"Bucket '{bucket_name}' does not exist.")
