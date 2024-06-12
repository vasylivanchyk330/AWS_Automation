import boto3
import logging
from datetime import datetime, timezone
import sys
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def list_stacks_created_after(cf_client, cutoff_date, exclude_stacks):
    """List all CloudFormation stacks created after the specified cutoff date, excluding specific stacks."""
    stacks_to_delete = []
    paginator = cf_client.get_paginator('describe_stacks')
    for page in paginator.paginate():
        for stack in page['Stacks']:
            creation_time = stack['CreationTime']
            if creation_time > cutoff_date and stack['StackName'] not in exclude_stacks:
                stacks_to_delete.append(stack['StackName'])
    return stacks_to_delete

def delete_stack(cf_client, stack_name, force):
    """Delete the specified CloudFormation stack."""
    try:
        if not force:
            confirm = input(f"Are you sure you want to delete the stack {stack_name}? (yes/no): ")
            if confirm.lower() != 'yes':
                logging.info(f"Skipping deletion of stack: {stack_name}")
                return
        cf_client.delete_stack(StackName=stack_name)
        logging.info(f"Initiated deletion of stack: {stack_name}")
    except Exception as e:
        logging.error(f"Error deleting stack {stack_name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Delete CloudFormation stacks created after a specific date-time.")
    parser.add_argument("cutoff_date", help="Cutoff date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC)")
    parser.add_argument("--exclude-stacks", "-e", nargs="*", default=[], help="List of stacks to exclude from deletion")
    parser.add_argument("--force", "-f", action="store_true", help="Force deletion without confirmation")
    
    args = parser.parse_args()

    try:
        cutoff_date = datetime.strptime(args.cutoff_date, "%Y-%m-%dT%H:%M:%SZ")
        cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
    except ValueError:
        logging.error("Incorrect date-time format. Use YYYY-MM-DDTHH:MM:SSZ (UTC).")
        sys.exit(1)

    cf_client = boto3.client('cloudformation')

    stacks_to_delete = list_stacks_created_after(cf_client, cutoff_date, args.exclude_stacks)
    logging.info(f"Found {len(stacks_to_delete)} stacks created after {args.cutoff_date}")

    for stack_name in stacks_to_delete:
        delete_stack(cf_client, stack_name, args.force)

if __name__ == "__main__":
    main()
