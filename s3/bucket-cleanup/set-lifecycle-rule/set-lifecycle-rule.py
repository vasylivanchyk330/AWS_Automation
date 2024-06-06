import sys
import os
import json
import boto3

def apply_combined_lifecycle_policy(bucket_name, policy_files):
    s3_client = boto3.client('s3')

    combined_policies = {
        "Rules": []
    }

    # Read and combine the lifecycle policies
    for policy_file in policy_files:
        if not os.path.isfile(policy_file):
            print(f"Lifecycle policy file {policy_file} not found!")
            sys.exit(1)

        with open(policy_file, 'r') as file:
            policy_json = json.load(file)
            combined_policies["Rules"].extend(policy_json["Rules"])

    # Apply the combined lifecycle policy
    try:
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=combined_policies
        )
        print(f"Combined lifecycle rules from {', '.join(policy_files)} applied successfully to {bucket_name}")
    except Exception as e:
        print(f"Failed to apply combined lifecycle rules to {bucket_name}: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 3:
        print("Usage: python script.py <bucket-name> <lifecycle-policy1> <lifecycle-policy2> ...")
        sys.exit(1)

    bucket_name = sys.argv[1]
    lifecycle_policy_files = sys.argv[2:]

    apply_combined_lifecycle_policy(bucket_name, lifecycle_policy_files)

if __name__ == "__main__":
    main()
