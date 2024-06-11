import sys
import boto3

s3_client = boto3.client('s3')

def delete_failed_multipart_uploads(bucket_name):

    try:
        multipart_uploads = s3_client.list_multipart_uploads(Bucket=bucket_name)
        if 'Uploads' in multipart_uploads:
            for upload in multipart_uploads['Uploads']:
                s3_client.abort_multipart_upload(
                    Bucket=bucket_name,
                    Key=upload['Key'],
                    UploadId=upload['UploadId']
                )
                print(f"Aborted multipart upload: {upload['Key']} with UploadId: {upload['UploadId']}")
        else:
            print(f"No failed multipart uploads found for bucket: {bucket_name}")
    except Exception as e:
        print(f"Failed to check or delete multipart uploads for {bucket_name}: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <bucket-name>")
        sys.exit(1)

    bucket_name = sys.argv[1]
    delete_failed_multipart_uploads(bucket_name)

if __name__ == "__main__":
    main()
