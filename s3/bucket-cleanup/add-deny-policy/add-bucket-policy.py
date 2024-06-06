import sys
import os
import json
import tempfile
import boto3

def create_bucket_policy(bucket_name):
    s3_client = boto3.client('s3')

    template_file = "deny-bucket-policy-template.json"

    # Check if the template file exists
    if not os.path.isfile(template_file):
        print(f"Template file {template_file} not found!")
        sys.exit(1)

    # Read the template file
    with open(template_file, "r") as template:
        template_data = template.read()
        policy_data = template_data.replace("BUCKET_NAME_PLACEHOLDER", bucket_name)

    # Create a temporary file to store the policy
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        tmp_file.write(policy_data)
        tmp_file.flush()

        # Apply the bucket policy
        with open(tmp_file.name, "r") as policy:
            policy_json = json.load(policy)
            s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy_json))

        print(f"Bucket policy applied successfully to {bucket_name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <bucket-name1> <bucket-name2> ...")
        sys.exit(1)

    bucket_names = sys.argv[1:]

    for bucket_name in bucket_names:
        create_bucket_policy(bucket_name)
