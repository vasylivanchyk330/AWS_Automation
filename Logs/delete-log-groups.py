import boto3
import logging
from datetime import datetime, timezone
import sys
import argparse
import os

# Configure logging
def setup_logger(log_file):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Set to DEBUG to capture all log messages
    
    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(log_file)
    
    # Create formatters and add them to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

def list_log_groups_created_between(cw_client, cutoff_date, until_date, exclude_log_groups, pattern=None):
    """List all CloudWatch log groups created between the specified cutoff date and until date, excluding specific log groups."""
    log_groups_to_delete = []
    paginator = cw_client.get_paginator('describe_log_groups')
    for page in paginator.paginate():
        for log_group in page['logGroups']:
            creation_time = datetime.fromtimestamp(log_group['creationTime'] / 1000, tz=timezone.utc)
            if cutoff_date < creation_time <= until_date and log_group['logGroupName'] not in exclude_log_groups:
                if pattern and pattern.lower() not in log_group['logGroupName'].lower():
                    continue
                log_groups_to_delete.append(log_group['logGroupName'])
    return log_groups_to_delete

def delete_log_group(cw_client, log_group_name, force, retries=3):
    """Delete the specified CloudWatch log group with retry logic."""
    try:
        for attempt in range(retries):
            if not force:
                confirm = input(f"Are you sure you want to delete the log group {log_group_name}? (yes/no): ")
                if confirm.lower() != 'yes':
                    logging.info(f"Skipping deletion of log group: {log_group_name}")
                    return

            cw_client.delete_log_group(logGroupName=log_group_name)
            logging.info(f"Initiated deletion of log group: {log_group_name}")
            logging.info(f"Successfully deleted log group: {log_group_name}")
            return

    except cw_client.exceptions.ResourceNotFoundException:
        logging.error(f"Log group {log_group_name} not found.")
    except cw_client.exceptions.ClientError as e:
        logging.error(f"Error deleting log group {log_group_name}: {e}")
        if attempt < retries - 1:
            logging.error(f"Retrying... (Attempt {attempt + 1}/{retries})")
        else:
            logging.error(f"Failed to delete log group {log_group_name} after {retries} attempts. Please investigate manually.")
            return

def read_exclude_log_groups(file_path):
    """Read the list of log group names to exclude from a file."""
    if not os.path.isfile(file_path):
        logging.error(f"Exclude log groups file {file_path} not found!")
        sys.exit(1)
    with open(file_path, 'r') as file:
        exclude_log_groups = [line.strip() for line in file if line.strip()]
    return exclude_log_groups

def main():
    try:
        parser = argparse.ArgumentParser(description="Delete CloudWatch log groups created between specific date-times.")
        parser.add_argument("cutoff_date", help="Cutoff date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC)")
        parser.add_argument("until_date", nargs='?', default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            help="Until date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC), default is now")
        parser.add_argument("--exclude-log-groups", "-e", help="List of log groups to exclude from deletion, can be a comma-separated list or a file containing log group names")
        parser.add_argument("--force", "-f", action="store_true", help="Force deletion without confirmation")
        parser.add_argument("--log-file", "-l", help="Log file to store the output")
        parser.add_argument("--log-dir", "-d", help="Directory to store the log file", default="./.script-logs")
        parser.add_argument("--pattern", "-p", help="Pattern to filter log groups for deletion")

        args = parser.parse_args()

        try:
            cutoff_date = datetime.strptime(args.cutoff_date, "%Y-%m-%dT%H:%M:%SZ")
            cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
        except ValueError:
            logging.error("Incorrect cutoff date-time format. Use YYYY-MM-DDTHH:MM:SSZ (UTC).")
            sys.exit(1)

        try:
            until_date = datetime.strptime(args.until_date, "%Y-%m-%dT%H:%M:%SZ")
            until_date = until_date.replace(tzinfo=timezone.utc)
        except ValueError:
            logging.error("Incorrect until date-time format. Use YYYY-MM-DDTHH:MM:SSZ (UTC).")
            sys.exit(1)

        # Define the default log file path
        log_dir = args.log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = args.log_file or os.path.join(log_dir, f"script_run_{datetime.now().strftime('%Y_%m_%d___%H%M%S')}.log")

        # Setup logger
        setup_logger(log_file)
        logging.info("Logger setup complete.")

        # Handle exclude log groups
        exclude_log_groups = []
        if args.exclude_log_groups:
            if os.path.isfile(args.exclude_log_groups):
                exclude_log_groups = read_exclude_log_groups(args.exclude_log_groups)
            else:
                exclude_log_groups = [log_group.strip() for log_group in args.exclude_log_groups.split(',')]

        logging.info("Starting to list log groups.")
        cw_client = boto3.client('logs')

        log_groups_to_delete = list_log_groups_created_between(cw_client, cutoff_date, until_date, exclude_log_groups, args.pattern)
        
        # Summary of log groups to delete
        logging.info(f"Found {len(log_groups_to_delete)} log groups created between {args.cutoff_date} and {args.until_date}")
        if log_groups_to_delete:
            logging.info("Log groups to be deleted:")
            for log_group_name in log_groups_to_delete:
                logging.info(f" - {log_group_name}")

        success = True  # Track the success of log group deletions
        for log_group_name in log_groups_to_delete:
            try:
                delete_log_group(cw_client, log_group_name, args.force)
            except Exception as e:
                logging.error(f"Error during deletion of log group {log_group_name}: {e}")
                success = False

        # Rename the log file if any log group failed to delete; assign exit_code value for later call
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

    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
