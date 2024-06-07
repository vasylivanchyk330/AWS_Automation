# S3 Bucket Cleanup

This repository contains scripts and configurations to manage and clean up AWS S3 buckets. The scripts are organized into different categories based on their functionality.

## Table of Contents

- [Add Deny Policy](#add-deny-policy)
- [Bucket Content Cleanup](#bucket-content-cleanup)
- [Delete Bucket](#delete-bucket)
- [Delete Failed Multipart Uploads](#delete-failed-multipart-uploads)
- [Set Lifecycle Rule](#set-lifecycle-rule)
- [Launch Bucket Cleanup](#launch-bucket-cleanup)
- [Instructions](#instructions)

## Add Deny Policy

Scripts to add deny policies to S3 buckets to prevent specific actions.

- `add-bucket-policy.py`: Script to add a deny policy to an S3 bucket.
- `deny-bucket-policy-template.json`: Template JSON for the deny policy.

## Bucket Content Cleanup

Scripts to clean up the contents of an S3 bucket, including object versions.

- `delete-s3-bucket-objects-versions.py`: Script to delete all objects and versions in an S3 bucket.

## Delete Bucket

Scripts to delete an S3 bucket.

- `delete-bucket.py`: Script to delete an S3 bucket after cleaning up its contents.

## Delete Failed Multipart Uploads

Scripts to identify and delete failed multipart uploads in S3 buckets.

- `delete-failed-multipart-uploads.py`: Script to delete failed multipart uploads from an S3 bucket.

## Set Lifecycle Rule

Scripts to set lifecycle policies for S3 buckets.

- `lifecycle-policy-01.json`: Example lifecycle policy JSON.
- `lifecycle-policy-02.json`: Another example lifecycle policy JSON.
- `set-lifecycle-rule.py`: Script to set lifecycle rules on an S3 bucket.

## Launch Bucket Cleanup

Scripts to launch the bucket cleanup process.

- `launch-bucket-cleanup.py`: Main script to initiate the cleanup process across multiple buckets.

## Instructions

Detailed instructions for using the S3 bucket cleanup scripts.

- `instruction---s3-bucket-deletion-cleanup.md`: Instructions for setting up and running the bucket cleanup scripts.

## .gitignore

- `.gitignore`: Git ignore file to exclude unnecessary files from the repository.

## Getting Started

### Prerequisites

- Python 3.x
- AWS CLI configured with appropriate permissions
- Boto3 library

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/s3-bucket-cleanup.git
    cd s3-bucket-cleanup
    ```

2. Install the required Python libraries:
    ```sh
    pip install boto3
    ```

### Usage

1. Configure your AWS credentials:
    ```sh
    aws configure
    ```

2. Run the desired script:
    ```sh
    python path/to/script.py
    ```

### Example

To delete all objects and versions in an S3 bucket:
```sh
python bucket-content-cleanup/delete-s3-bucket-objects-versions.py
