import boto3
import json
import argparse

def get_bucket_policy(s3_client, bucket_name):
    """Get the current bucket policy."""
    try:
        response = s3_client.get_bucket_policy(Bucket=bucket_name)
        policy = json.loads(response['Policy'])
        return policy
    except s3_client.exceptions.NoSuchBucketPolicy:
        return {"Version": "2012-10-17", "Statement": []}

def update_bucket_policy(s3_client, bucket_name):
    """Update the bucket policy to add the deny delete policy statement."""
    policy = get_bucket_policy(s3_client, bucket_name)
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    deny_delete_statement = {
        "Sid": "DenyDeleteBucket",
        "Effect": "Deny",
        "Principal": "*",
        "Action": [
            "s3:DeleteBucket",
            "s3:DeleteBucketPolicy"
        ],
        "Resource": bucket_arn
    }

    # Check if the policy statement already exists
    for statement in policy["Statement"]:
        if statement.get("Sid") == "DenyDeleteBucket":
            print(f"The policy statement already exists in the bucket {bucket_name}.")
            return

    # Add the new policy statement
    policy["Statement"].append(deny_delete_statement)

    # Update the bucket policy
    s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
    print(f"Updated policy for bucket {bucket_name}.")

def main():
    parser = argparse.ArgumentParser(description="Update S3 bucket policies to deny delete actions.")
    parser.add_argument("bucket_names", nargs='+', help="One or more bucket names to update.")
    args = parser.parse_args()

    s3_client = boto3.client('s3')

    for bucket_name in args.bucket_names:
        update_bucket_policy(s3_client, bucket_name)

if __name__ == "__main__":
    main()
