# Preparing a Test Environment for S3 Bucket Cleanup

This document provides (more-or-less) detailed instructions for setting up a test environment for the S3 Bucket Cleanup scripts.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setting Up AWS Resources](#setting-up-aws-resources)
- [Useful Commands](#useful-commands)
- [Cleaning Up](#cleaning-up)
- [Notes](#notes)


## Prerequisites

- An AWS account with appropriate permissions.
- Python 3.x installed.
- AWS CLI installed and configured.
- Boto3 library installed.

### Setting Up AWS Resources

1. **Create S3 Buckets and Upload Test Files**

    ```sh
    # Define the number of buckets and files
    NUM_BUCKETS=5
    NUM_FILES=300

    # Loop to create buckets and add files to each bucket
    for i in $(seq 1 $NUM_BUCKETS); do 
        BUCKET_NAME="viv-testing2-scripts-0$i"
        aws s3api create-bucket --bucket $BUCKET_NAME --region us-east-1
        echo "Created bucket: $BUCKET_NAME"

        # Enable versioning on the bucket
        aws s3api put-bucket-versioning --bucket $BUCKET_NAME --versioning-configuration Status=Enabled

        # Create Y files
        for j in $(seq 1 $NUM_FILES); do
            echo "This is test file $j; hfjsadhflkjhadskfjhsdkljfhksdajhfkasdhfjksdhkfjhasdkjfhkdsahfkjsd" > testfile--$j
        done

        # Sync files to the bucket
        aws s3 sync ./ s3://$BUCKET_NAME/ --exclude "*" --include "testfile-*"
        
        # Clean up test files
        rm testfile-*
    done
    aws s3 ls
    ```

### Useful Commands

Here are some useful AWS CLI commands with brief explanations:

- **List all buckets:**
    ```sh
    aws s3 ls
    ```

- **Count the number of objects in a specific bucket:**
    ```sh
    aws s3 ls s3://viv-testing-scripts-03 --recursive | wc -l
    ```

- **Upload a file to a specific bucket:**
    ```sh
    aws s3 cp ./testfile s3://viv-testing-scripts/
    ```

- **Enable versioning on a specific bucket:**
    ```sh
    aws s3api put-bucket-versioning --bucket viv-testing-scripts-01 --versioning-configuration Status=Enabled
    ```

- **Get the total size of objects in a bucket (in MB):**
    ```sh
    aws s3 ls s3://your-bucket-name --recursive --summarize | grep "Total Size" | awk '{print $3/1024/1024 " MB"}'
    ```

- **Create multiple test files, upload to S3, and remove local copies:**
    ```sh
    for i in {1..12}; do echo "This is test file $i" > testfile-$i; aws s3 cp testfile-$i s3://viv-testing-scripts/; rm testfile-$i; done
    ```

- **Create multiple buckets:**
    ```sh
    for i in $(seq 1 5); do aws s3api create-bucket --bucket viv-testing2-scripts-0$i --region us-east-1; done
    ```

### Cleaning Up

After testing, you can clean up the resources to avoid unnecessary charges.

1. **Delete Test Files**

    ```sh
    aws s3 rm s3://my-test-bucket/testfile.txt
    ```

2. **Delete the S3 Bucket**

    Ensure all objects are deleted before deleting the bucket.

    ```sh
    aws s3 rb s3://my-test-bucket --force
    ```

## Notes

- Make sure to follow AWS best practices for security and cost management.
- Test thoroughly in a safe environment before running scripts on production buckets.
