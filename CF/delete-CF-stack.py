import boto3
import logging
from datetime import datetime, timezone
import sys
import argparse
import os

# Configure logging
def setup_logger(log_file):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
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

def list_stacks_created_between(cf_client, cutoff_date, until_date, exclude_stacks, pattern=None):
    """List all CloudFormation stacks created between the specified cutoff date and until date, excluding specific stacks."""
    stacks_to_delete = []
    paginator = cf_client.get_paginator('describe_stacks')
    for page in paginator.paginate():
        for stack in page['Stacks']:
            creation_time = stack['CreationTime']
            if cutoff_date < creation_time <= until_date and stack['StackName'] not in exclude_stacks:
                if pattern and pattern.lower() not in stack['StackName'].lower():
                    continue
                stacks_to_delete.append(stack['StackName'])
    return stacks_to_delete

def delete_stack(cf_client, stack_name, force, retries=3):
    """Delete the specified CloudFormation stack with retry logic for DELETE_FAILED status."""
    try:
        for attempt in range(retries):
            if not force:
                confirm = input(f"Are you sure you want to delete the stack {stack_name}? (yes/no): ")
                if confirm.lower() != 'yes':
                    logging.info(f"Skipping deletion of stack: {stack_name}")
                    return

            cf_client.delete_stack(StackName=stack_name)
            logging.info(f"Initiated deletion of stack: {stack_name}")
            
            # Wait for the stack to reach a terminal state
            waiter = cf_client.get_waiter('stack_delete_complete')
            waiter.wait(StackName=stack_name)

            logging.info(f"Successfully deleted stack: {stack_name}")
            return

    except cf_client.exceptions.ClientError as e:
        logging.error(f"Error deleting stack {stack_name}: {e}")
        if 'DELETE_FAILED' in str(e):
            logging.error(f"Stack {stack_name} entered DELETE_FAILED state. Retrying... (Attempt {attempt+1}/{retries})")
        else:
            logging.error(f"Failed to delete stack {stack_name}: {e}")
            return

    logging.error(f"Failed to delete stack {stack_name} after {retries} attempts. Please investigate manually.")

def read_exclude_stacks(file_path):
    """Read the list of stack names to exclude from a file."""
    if not os.path.isfile(file_path):
        logging.error(f"Exclude stacks file {file_path} not found!")
        sys.exit(1)
    with open(file_path, 'r') as file:
        exclude_stacks = [line.strip() for line in file if line.strip()]
    return exclude_stacks

def main():
    parser = argparse.ArgumentParser(description="Delete CloudFormation stacks created between specific date-times.")
    parser.add_argument("cutoff_date", help="Cutoff date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC)")
    parser.add_argument("until_date", nargs='?', default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        help="Until date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC), default is now")
    parser.add_argument("--exclude-stacks", "-e", help="List of stacks to exclude from deletion, can be a comma-separated list or a file containing stack names")
    parser.add_argument("--force", "-f", action="store_true", help="Force deletion without confirmation")
    parser.add_argument("--log-file", "-l", help="Log file to store the output")
    parser.add_argument("--log-dir", "-d", help="Directory to store the log file", default="./.script-logs")
    parser.add_argument("--pattern", "-p", help="Pattern to filter stacks for deletion")

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

    # Handle exclude stacks
    exclude_stacks = []
    if args.exclude_stacks:
        if os.path.isfile(args.exclude_stacks):
            exclude_stacks = read_exclude_stacks(args.exclude_stacks)
        else:
            exclude_stacks = [stack.strip() for stack in args.exclude_stacks.split(',')]

    cf_client = boto3.client('cloudformation')

    stacks_to_delete = list_stacks_created_between(cf_client, cutoff_date, until_date, exclude_stacks, args.pattern)
    
    # Summary of stacks to delete
    logging.info(f"Found {len(stacks_to_delete)} stacks created between {args.cutoff_date} and {args.until_date}")
    if stacks_to_delete:
        logging.info("Stacks to be deleted:")
        for stack_name in stacks_to_delete:
            logging.info(f" - {stack_name}")
        
        # Prompt to delete all stacks
        confirm_all = input("Do you want to delete them all? (yes/no): ")
        logging.info(f"User prompt response: {confirm_all}")
        if confirm_all.lower() != 'yes':
            logging.info("Aborting deletion of all stacks.")
            sys.exit(0)

    success = True  # Track the success of stack deletions
    for stack_name in stacks_to_delete:
        try:
            delete_stack(cf_client, stack_name, args.force)
        except Exception as e:
            logging.error(f"Error during deletion of stack {stack_name}: {e}")
            success = False

    # Rename the log file if any stack failed to delete; assign exit_code value for later call
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
