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

def list_snapshots(ec2_client, cutoff_date, until_date, pattern=None):
    """List all snapshots optionally filtering by a pattern and creation date range."""
    snapshots_to_delete = []
    
    response = ec2_client.describe_snapshots(OwnerIds=['self'])
    
    for snapshot in response['Snapshots']:
        snapshot_name = ''
        for tag in snapshot.get('Tags', []):
            if tag['Key'] == 'Name':
                snapshot_name = tag['Value']
        
        creation_time_str = snapshot['StartTime'].strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        creation_time = snapshot['StartTime']
        logging.debug(f"Checking Snapshot: {snapshot_name} with Creation Time: {creation_time}")
        if (not cutoff_date or cutoff_date <= creation_time) and (not until_date or creation_time <= until_date):
            if pattern is None or re.search(pattern, snapshot_name, re.IGNORECASE):
                snapshots_to_delete.append({
                    'SnapshotId': snapshot['SnapshotId'],
                    'Name': snapshot_name,
                    'CreationTime': creation_time_str
                })
    
    return snapshots_to_delete

def delete_snapshot(ec2_client, snapshot_id):
    """Delete the specified snapshot."""
    try:
        ec2_client.delete_snapshot(SnapshotId=snapshot_id)
        logging.info(f"Deleted Snapshot: {snapshot_id}")
    except ec2_client.exceptions.ClientError as e:
        logging.error(f"Error deleting Snapshot {snapshot_id}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Delete AWS EBS volume snapshots matching specific criteria.")
    parser.add_argument("--cutoff-date", help="Cutoff date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC)")
    parser.add_argument("--until-date", default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        help="Until date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC), default is now")
    parser.add_argument("--pattern", "-p", help="Pattern to filter snapshot names for deletion.")
    parser.add_argument("snapshot_names", nargs='*', help="List of specific snapshot names to delete.")
    parser.add_argument("--force", "-f", action="store_true", help="Force deletion without confirmation")
    parser.add_argument("--log-file", "-l", help="Log file to store the output")
    parser.add_argument("--log-dir", "-d", help="Directory to store the log file", default="./.script-logs")
    args = parser.parse_args()

    # Check that at least one criterion is provided
    if not args.cutoff_date and not args.pattern and not args.snapshot_names:
        logging.error("You must provide at least one of --cutoff-date, --pattern, or snapshot_names.")
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

    snapshots_to_delete = []

    # List snapshots based on date range and pattern
    if cutoff_date or args.pattern:
        logging.info(f"Listing snapshots created between {cutoff_date} and {until_date} with pattern {args.pattern}...")
        snapshots_to_delete.extend(list_snapshots(ec2_client, cutoff_date, until_date, pattern=args.pattern))
    
    # List snapshots based on specific names
    if args.snapshot_names:
        snapshot_names = args.snapshot_names
        logging.info(f"Listing snapshots with specific names: {snapshot_names}")
        response = ec2_client.describe_snapshots(OwnerIds=['self'])
        for snapshot in response['Snapshots']:
            snapshot_name = ''
            for tag in snapshot.get('Tags', []):
                if tag['Key'] == 'Name' and tag['Value'] in snapshot_names:
                    snapshot_name = tag['Value']
                    snapshots_to_delete.append({
                        'SnapshotId': snapshot['SnapshotId'],
                        'Name': snapshot_name,
                        'CreationTime': snapshot['StartTime'].strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    })

    # Remove duplicates
    snapshots_to_delete = list({snapshot['SnapshotId']: snapshot for snapshot in snapshots_to_delete}.values())

    # Summary of snapshots to delete
    logging.info(f"Found {len(snapshots_to_delete)} snapshots matching the criteria:")
    if snapshots_to_delete:
        logging.info("Snapshots to be deleted:")
        for snapshot in snapshots_to_delete:
            logging.info(f" - {snapshot['SnapshotId']} (Name: {snapshot['Name']}, CreationTime: {snapshot['CreationTime']})")
        
        # Prompt to delete all snapshots
        if not args.force:
            confirm_all = input("Do you want to delete them all? (yes/no): ")
            logging.info(f"User prompt response: {confirm_all}")
            if confirm_all.lower() == 'yes':
                delete_all = True
            else:
                delete_all = False
        else:
            delete_all = True

    success = True  # Track the success of snapshot deletions
    for snapshot in snapshots_to_delete:
        try:
            if delete_all:
                delete_snapshot(ec2_client, snapshot['SnapshotId'])
            else:
                confirm_each = input(f"Do you want to delete the snapshot {snapshot['SnapshotId']} (Name: {snapshot['Name']})? (yes/no): ")
                logging.info(f"User prompt response for {snapshot['SnapshotId']}: {confirm_each}")
                if confirm_each.lower() == 'yes':
                    delete_snapshot(ec2_client, snapshot['SnapshotId'])
                else:
                    logging.info(f"Skipping deletion of snapshot: {snapshot['SnapshotId']}")
        except Exception as e:
            logging.error(f"Error during deletion of snapshot {snapshot['SnapshotId']}: {e}")
            success = False

    # Rename the log file if any snapshot failed to delete; assign exit_code value for later call
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
