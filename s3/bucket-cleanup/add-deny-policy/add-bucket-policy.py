import sys
import os
import json
import tempfile
import boto3

s3_client = boto3.client('s3')

def apply_bucket_policy(bucket_name, template_file):

    # Check if the template file exists
    if not os.path.isfile(template_file):
        print(f"Template file {template_file} not found!")
        return

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

        print(f"Bucket policy from {template_file} applied successfully to {bucket_name}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python script.py <bucket-name1> <bucket-name2> ... <template-file1> <template-file2> ...")
        sys.exit(1)

    # Separate bucket names and template files
    bucket_names = []
    template_files = []

    # Collect bucket names and template files based on input arguments
    for arg in sys.argv[1:]:
        if os.path.isfile(arg):
            template_files.append(arg)
        else:
            bucket_names.append(arg)

    if not bucket_names or not template_files:
        print("Error: Provide at least one bucket name and one template file.")
        sys.exit(1)

    for bucket_name in bucket_names:
        for template_file in template_files:
            apply_bucket_policy(bucket_name, template_file)

if __name__ == "__main__":
    main()
