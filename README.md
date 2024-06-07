# AWS_Automation

Welcome to the AWS_Automation repository. This repository contains automation scripts and configurations for managing various AWS services. Currently, the repository focuses on S3 bucket management, specifically for bucket cleanup tasks.

## Table of Contents

- [S3 Bucket Cleanup](#s3-bucket-cleanup)
  - [README](s3/bucket-cleanup/README.md)
  - [Preparing a Test Environment](s3/bucket-cleanup/README-prepare-test-env.md)

## S3 Bucket Cleanup

### Overview

The S3 Bucket Cleanup section contains scripts and configurations to automate the process of cleaning up S3 buckets. This includes removing objects, managing bucket policies, handling failed multipart uploads, and setting lifecycle rules.

### Current Structure

By now, there is only the S3 bucket part, and within it, there is only the bucket cleanup part.

- **Add Deny Policy**: Scripts to add deny policies to S3 buckets to prevent specific actions.
- **Bucket Content Cleanup**: Scripts to clean up the contents of an S3 bucket, including object versions and version delete markers.
- **Delete Bucket**: Scripts to delete an S3 bucket after cleaning up its contents.
- **Delete Failed Multipart Uploads**: Scripts to identify and delete failed multipart uploads in S3 buckets.
- **Set Lifecycle Rule**: Scripts to set lifecycle policies for S3 buckets.
- **Main Script**: A script to initiate the cleanup process across multiple buckets.

For detailed information on how to use these scripts, please refer to the respective READMEs linked below.

## Detailed READMEs

- [S3 Bucket Cleanup README](s3/bucket-cleanup/README.md)
- [Preparing a Test Environment](s3/bucket-cleanup/README-prepare-test-env.md)

## Getting Started

To get started with the S3 Bucket Cleanup scripts, follow the instructions provided in the [S3 Bucket Cleanup README](s3/bucket-cleanup/README.md).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
