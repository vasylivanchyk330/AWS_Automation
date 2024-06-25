import subprocess
import time
import argparse
import logging
import os
import sys
from datetime import datetime, timezone
import boto3
import re

def setup_logger(log_file):
    """Setup logger to log messages to both console and file."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(log_file)

    # Create formatters and add them to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

def log_unique_lines(log_func, message):
    """Log each line in the message uniquely."""
    seen_lines = set() # to keep track of lines that have already been logged
    for line in message.splitlines(): # splits the message into individual lines 
        if line not in seen_lines:
            log_func(line)
            seen_lines.add(line)

def run_script(script_path, script_args, retries=15, delay=10):
    """Run a script with arguments and wait for it to finish."""
    attempt = 0
    while attempt < retries:
        try:
            result = subprocess.run(["python", script_path] + script_args, check=True, capture_output=True, text=True)
            logging.info(f"Output of {script_path}:\n")
            if result.stdout:
                log_unique_lines(logging.info, result.stdout)
            if result.stderr:
                log_unique_lines(logging.info, result.stderr)
            return True
        except subprocess.CalledProcessError as e:
            if e.stdout:
                log_unique_lines(logging.error, e.stdout)
            if e.stderr:
                log_unique_lines(logging.error, e.stderr)
                if "SlowDown" in e.stderr:
                    attempt += 1
                    logging.error(f"SlowDown error encountered. Retrying in {delay} seconds... (Attempt {attempt}/{retries})")
                    time.sleep(delay)
                else:
                    return False
    return False

def list_buckets_created_between(s3_client, cutoff_date, until_date):
    """List all S3 buckets created between the specified cutoff date and until date."""
    buckets_to_delete = []
    response = s3_client.list_buckets()
    for bucket in response['Buckets']:
        creation_date = bucket['CreationDate']
        if cutoff_date < creation_date <= until_date:
            buckets_to_delete.append(bucket['Name'])
    return buckets_to_delete

def filter_buckets_by_pattern(bucket_names, pattern):
    """Filter bucket names by a case-insensitive pattern."""
    regex = re.compile(pattern, re.IGNORECASE)
    return [bucket for bucket in bucket_names if regex.search(bucket)]

def main():
    parser = argparse.ArgumentParser(description="Run a series of S3 bucket management scripts.")
    parser.add_argument("buckets", nargs='*', help="Names of the S3 buckets")
    parser.add_argument("--cutoff-date", help="Cutoff date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC)", default=None)
    parser.add_argument("--until-date", help="Until date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC)", default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    parser.add_argument("--pattern", help="Pattern to filter bucket names (case-insensitive)")
    parser.add_argument("--lifecycle-rules-wait", "-w", type=int, default=0, help="Minutes to wait after setting lifecycle rules")
    parser.add_argument("--log-file", "-l", help="Log file to store the output")
    parser.add_argument("--log-dir", "-d", help="Directory to store the log file", default="./.script-logs")
    
    args = parser.parse_args()

    # Validate that at least one of the required arguments is provided
    if not args.buckets and not args.cutoff_date and not args.until_date and not args.pattern:
        parser.error("You must provide at least one of the following: bucket names, --cutoff-date, --until-date, or --pattern")

    # Parse the dates if provided
    if args.cutoff_date:
        try:
            cutoff_date = datetime.strptime(args.cutoff_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            logging.error("Incorrect cutoff date-time format. Use YYYY-MM-DDTHH:MM:SSZ (UTC).")
            sys.exit(1)
    else:
        cutoff_date = datetime.min.replace(tzinfo=timezone.utc)

    if args.until_date:
        try:
            until_date = datetime.strptime(args.until_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            logging.error("Incorrect until date-time format. Use YYYY-MM-DDTHH:MM:SSZ (UTC).")
            sys.exit(1)
    else:
        until_date = datetime.now(timezone.utc)

    # Define the default log file path
    log_dir = args.log_dir
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = args.log_file or os.path.join(log_dir, f"script_run_{datetime.now().strftime('%Y_%m_%d___%H%M%S')}.log")

    # Setup logger
    setup_logger(log_file)

    s3_client = boto3.client('s3')

    # Get bucket names based on arguments
    bucket_names = []
    if args.buckets:
        bucket_names.extend(args.buckets)
    if args.cutoff_date or args.until_date:
        bucket_names.extend(list_buckets_created_between(s3_client, cutoff_date, until_date))
    if args.pattern:
        bucket_names = filter_buckets_by_pattern(bucket_names, args.pattern)

    # Remove duplicates
    bucket_names = list(set(bucket_names))

    logging.info(f"Found {len(bucket_names)} buckets to be processed.")

    if not bucket_names:
        print("No buckets found to process.")
        sys.exit(0)

    print("Buckets to be processed:")
    for bucket in bucket_names:
        print(f" - {bucket}")

    confirm_all = input("Do you want to delete them all? (yes/no): ").strip().lower()
    delete_all = confirm_all == 'yes'

    success = True  # Track the success of script runs

    for bucket_name in bucket_names:
        if not delete_all:
            confirm_each = input(f"Do you want to delete the bucket {bucket_name}? (yes/no): ").strip().lower()
            if confirm_each != 'yes':
                logging.info(f"Skipping deletion of bucket: {bucket_name}")
                continue

        logging.info(f"Processing bucket: {bucket_name}")

        # List of scripts to run in the given order with their respective arguments
        scripts = [
            ("add-deny-policy/add-bucket-policy.py", [bucket_name, "add-deny-policy/deny-bucket-policy-template.json"]),
            ("set-lifecycle-rule/set-lifecycle-rule.py", [bucket_name, "set-lifecycle-rule/lifecycle-policy-01.json", "set-lifecycle-rule/lifecycle-policy-02.json"]),
            ("delete-bucket-objects-versions-markers/delete-bucket-objects-versions-markers.py", [bucket_name]),
            ("delete-failed-multipart-uploads/delete-failed-multipart-uploads.py", [bucket_name]),
            ("delete-bucket/delete-bucket.py", [bucket_name])
        ]

        for script_path, script_args in scripts:
            logging.info(f"STARTING SCRIPT RUN -- {script_path}")
            logging.info(f"Running {script_path} with arguments {script_args}...")
            if run_script(script_path, script_args):
                logging.info(f"Finished running {script_path}.\n")
            else:
                logging.error(f"Failed to run {script_path} after maximum retries.\n")
                success = False
                break

            # If the current script is the lifecycle rule script, wait for the specified time
            if script_path == "set-lifecycle-rule/set-lifecycle-rule.py" and args.lifecycle_rules_wait > 0:
                logging.info(f"Waiting for {args.lifecycle_rules_wait} minutes before proceeding to the next script...")
                time.sleep(args.lifecycle_rules_wait * 60)  # Convert minutes to seconds

        if not success:
            break

    # Rename the log file if any script failed; assign exit_code value for later call
    if not success:
        error_log_file = log_file.replace('.log', '__errorred.log')
        os.rename(log_file, error_log_file)
        log_file = error_log_file
        exit_code = 1
    else:
        exit_code = 0

    # Print out the log file location at the end
    print(f"THE LOG FILE LOCATION IS: {log_file}")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
