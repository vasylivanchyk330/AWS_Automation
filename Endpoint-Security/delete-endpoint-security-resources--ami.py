import boto3
import logging
from datetime import datetime, timezone
import sys
import argparse
import os
import re

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

def list_amis(ec2_client, cutoff_date, until_date, pattern=None):
    """List all AMIs owned by the account within the date range, optionally filtering by a pattern."""
    amis_to_delete = []
    
    response = ec2_client.describe_images(Owners=['self'])
    
    for image in response['Images']:
        creation_date = image['CreationDate']
        if cutoff_date <= creation_date <= until_date:
            if pattern is None or re.search(pattern, image.get('Name', ''), re.IGNORECASE):
                amis_to_delete.append({
                    'ImageId': image['ImageId'],
                    'Name': image.get('Name', 'N/A'),
                    'CreationDate': creation_date
                })
    
    return amis_to_delete

def delete_ami(ec2_client, image_id):
    """Delete the specified AMI and its associated snapshots."""
    try:
        # Deregister the AMI
        ec2_client.deregister_image(ImageId=image_id)
        logging.info(f"Deregistered AMI: {image_id}")
        
        # Delete associated snapshots
        snapshots = ec2_client.describe_snapshots(Filters=[{'Name': 'description', 'Values': [f'*{image_id}*']}])
        for snapshot in snapshots['Snapshots']:
            ec2_client.delete_snapshot(SnapshotId=snapshot['SnapshotId'])
            logging.info(f"Deleted snapshot: {snapshot['SnapshotId']} for AMI: {image_id}")
    except ec2_client.exceptions.ClientError as e:
        logging.error(f"Error deleting AMI {image_id}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Delete AMIs owned by your account within a specified date range.")
    parser.add_argument("--cutoff-date", help="Cutoff date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC)")
    parser.add_argument("--until-date", default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        help="Until date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC), default is now")
    parser.add_argument("--pattern", "-p", help="Pattern to filter AMI names for deletion.")
    parser.add_argument("ami_names", nargs='*', help="List of specific AMI names to delete.")
    parser.add_argument("--force", "-f", action="store_true", help="Force deletion without confirmation")
    parser.add_argument("--log-file", "-l", help="Log file to store the output", default="ami_cleanup.log")
    parser.add_argument("--log-dir", "-d", help="Directory to store the log file", default="./.script-logs")
    args = parser.parse_args()

    # Check that at least one criterion is provided
    if not args.cutoff_date and not args.pattern and not args.ami_names:
        logging.error("You must provide at least one of --cutoff-date, --pattern, or ami_names.")
        parser.print_help()
        sys.exit(1)

    # Validate date formats if provided
    try:
        cutoff_date = datetime.strptime(args.cutoff_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if args.cutoff_date else None
        until_date = datetime.strptime(args.until_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as e:
        logging.error(f"Invalid date format: {e}")
        sys.exit(1)

    # Define the default log file path
    log_dir = args.log_dir
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = args.log_file or os.path.join(log_dir, f"script_run_{datetime.now().strftime('%Y_%m_%d___%H%M%S')}.log")

    # Setup logger
    setup_logger(log_file)

    ec2_client = boto3.client('ec2')

    amis_to_delete = []

    # List AMIs based on date range and pattern
    if cutoff_date:
        logging.info(f"Listing AMIs owned by the account between {cutoff_date} and {until_date} with pattern {args.pattern}...")
        amis_to_delete.extend(list_amis(ec2_client, cutoff_date.strftime("%Y-%m-%dT%H:%M:%SZ"), until_date.strftime("%Y-%m-%dT%H:%M:%SZ"), pattern=args.pattern))
    
    # List AMIs based on specific names
    if args.ami_names:
        ami_names = args.ami_names
        logging.info(f"Listing AMIs with specific names: {ami_names}")
        response = ec2_client.describe_images(Owners=['self'])
        for image in response['Images']:
            if image.get('Name') in ami_names:
                amis_to_delete.append({
                    'ImageId': image['ImageId'],
                    'Name': image.get('Name', 'N/A'),
                    'CreationDate': image['CreationDate']
                })

    # Remove duplicates
    amis_to_delete = {ami['ImageId']: ami for ami in amis_to_delete}.values()

    # Summary of AMIs to delete
    logging.info(f"Found {len(amis_to_delete)} AMIs matching the criteria:")
    if amis_to_delete:
        logging.info("AMIs to be deleted:")
        for ami in amis_to_delete:
            logging.info(f" - {ami['ImageId']} (Name: {ami['Name']}, CreationDate: {ami['CreationDate']})")
        
        # Prompt to delete all AMIs
        if not args.force:
            confirm_all = input("Do you want to delete them all? (yes/no): ")
            logging.info(f"User prompt response: {confirm_all}")
            if confirm_all.lower() == 'yes':
                delete_all = True
            else:
                delete_all = False
        else:
            delete_all = True

    success = True  # Track the success of AMI deletions
    for ami in amis_to_delete:
        try:
            if delete_all:
                delete_ami(ec2_client, ami['ImageId'])
            else:
                confirm_each = input(f"Do you want to delete the AMI {ami['ImageId']} (Name: {ami['Name']})? (yes/no): ")
                logging.info(f"User prompt response for {ami['ImageId']}: {confirm_each}")
                if confirm_each.lower() == 'yes':
                    delete_ami(ec2_client, ami['ImageId'])
                else:
                    logging.info(f"Skipping deletion of AMI: {ami['ImageId']}")
        except Exception as e:
            logging.error(f"Error during deletion of AMI {ami['ImageId']}: {e}")
            success = False

    # Rename the log file if any AMI failed to delete; assign exit_code value for later call
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
