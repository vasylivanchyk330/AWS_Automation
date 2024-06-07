# S3 Bucket Cleanup

This repository contains scripts and configurations for cleaning up AWS S3 buckets. The scripts are organized into different categories based on their functionality.

**The goal: automate cumbersome bucket clean-up "clicking"-like procedure.**

## Table of Contents

- [Nested Scripts](#nested-scripts):
  - [Add Deny Policy](#add-deny-policy)
  - [Bucket Content Cleanup](#bucket-content-cleanup)
  - [Delete Bucket](#delete-bucket)
  - [Delete Failed Multipart Uploads](#delete-failed-multipart-uploads)
  - [Set Lifecycle Rule](#set-lifecycle-rule)
- [Main Script](#main-script):
  - [Launch Bucket Cleanup](#launch-bucket-cleanup)
- [Log Location](#log-location)
- [Glossary](#glossary)
- [Preparing a Test Environment](#preparing-a-test-environment)

## Nested Scripts

#### Add Deny Policy

Scripts to add deny policies to S3 buckets to prevent specific actions.

- `add-deny-policy/add-bucket-policy.py`: Script to add a deny policy to an S3 bucket.
- `add-deny-policy/deny-bucket-policy-template.json`: Template JSON for the deny policy.

#### Bucket Content Cleanup

Scripts to clean up the contents of an S3 bucket, including object versions and version delete markers.

- `bucket-content-cleanup/delete-s3-bucket-objects-versions.py`: Script to delete all objects and versions in an S3 bucket.

**Pagination and ThreadPoolExecutor**

- **Pagination**: The `paginator` is used to handle large sets of data that cannot be retrieved in a single API call. In the context of S3 operations, pagination allows the script to efficiently manage and process large numbers of objects by retrieving them in batches (pages). This prevents memory overload and ensures that the script can handle large buckets with many objects or versions.

- **ThreadPoolExecutor**: The `ThreadPoolExecutor` from the `concurrent.futures` module is used to perform concurrent execution of function calls using a pool of threads. In this script, it is used to delete objects and versions in parallel, significantly speeding up the cleanup process. By submitting multiple deletion tasks to the thread pool, the script can handle multiple delete operations simultaneously, improving performance and reducing the total time required for cleanup.

#### Delete Bucket

Scripts to delete an S3 bucket.

- `delete-bucket/delete-bucket.py`: Script to delete an S3 bucket after cleaning up its contents.
- `delete-bucket/instruction-and-problem-statement--s3-bucket-deletion-problem.sh`: Instructions and problem statement for S3 bucket deletion.

#### Delete Failed Multipart Uploads

Scripts to identify and delete failed multipart uploads in S3 buckets.

- `delete-failed-multipart-uploads/delete-failed-multipart-uploads.py`: Script to delete failed multipart uploads from an S3 bucket.

#### Set Lifecycle Rule

Scripts to set lifecycle policies for S3 buckets.

- `set-lifecycle-rule/lifecycle-policy-01.json`: Example lifecycle policy JSON.
- `set-lifecycle-rule/lifecycle-policy-02.json`: Another example lifecycle policy JSON.
- `set-lifecycle-rule/set-lifecycle-rule.py`: Script to set lifecycle rules on an S3 bucket.

## Main Script

### Launch Bucket Cleanup

Main script to launch the bucket cleanup process.

- `launch-bucket-cleanup.py`: Main script to initiate the cleanup process across multiple buckets.


## Log Location

The script logs the output of each step to a log file. By default, the log location is `./.script-logs/`; the log file is named `script_<timestamp>.log`. You can specify a custom log file location using the `--log-file` argument when running the script.


## Getting Started

### Prerequisites

- Python 3.x
- AWS CLI configured with appropriate permissions
- Boto3 library

### Installation

1. Install Python:
    - On Windows, download and install from [python.org](https://www.python.org/downloads/).
    - On macOS, you can use Homebrew:
        ```sh
        brew install python
        ```
    - On Linux, use your package manager, for example on Ubuntu:
        ```sh
        sudo apt-get update
        sudo apt-get install python3
        ```

2. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/s3-bucket-cleanup.git
    cd s3-bucket-cleanup
    ```

3. Install the required Python libraries, if not installed already:
    ```sh
    pip install boto3
    ```

### Usage

1. Configure your AWS credentials:
    ```sh
    aws configure
    ```

2. Run the script that initializes all other `s3/bucket-cleanup` scripts:
    ```sh
    cd s3/bucket-cleanup/
    python launch-bucket-cleanup.py <bucket-name>
    ```

## Glossary

### Delete Marker

- **Definition**: When versioning is enabled on a bucket, deleting an object does not actually remove its data. Instead, a delete marker is created.
    - **Purpose**: Allows recovering deleted objects if needed.

### Multipart Upload

- **Definition**: A feature in Amazon S3 that allows uploading a single object as a set of parts. Each part is uploaded independently, and the parts can be uploaded in parallel to reduce the time taken to upload large files.
    - **Potential Issues**: Such multipart uploads could fail, causing unexpected issues later on, for example, when trying to delete a bucket.
    - **Example**: Listing multipart uploads in a bucket:
        ```sh
        aws s3api list-multipart-uploads --bucket my-bucket
        ```

### Object Key

- **Definition**: (from a bucket-level point of view) path to an object in the bucket.
    - Example:
        - `my-bucket` -- a bucket name
        - `photos/2024/vacation.jpg` -- a key, where the object is stored
        - `s3://my-bucket/photos/2024/vacation.jpg` -- the full path to the object


## Preparing a Test Environment

For detailed instructions on setting up a test environment, refer to [README-prepare-test-env.md](README-prepare-test-env.md).
