# usage: `python delete-CF-stack-base-on-date-time.py 2024-06-10T00:00:00Z stack1 stack2 ...`
import boto3
import logging
from datetime import datetime, timezone
import sys

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

def delete_stack(cf_client, stack_name):
    """Delete the specified CloudFormation stack."""
    try:
        cf_client.delete_stack(StackName=stack_name)
        logging.info(f"Initiated deletion of stack: {stack_name}")
    except Exception as e:
        logging.error(f"Error deleting stack {stack_name}: {e}")

def main():
    if len(sys.argv) < 2:
        logging.error("Usage: python delete-CF-stack-base-on-date-time.py <cutoff-date-time> [<exclude-stack1> <exclude-stack2> ...]")
        logging.error("Date-time format: YYYY-MM-DDTHH:MM:SSZ (UTC)")
        sys.exit(1)

    cutoff_date_str = sys.argv[1]
    exclude_stacks = sys.argv[2:]
    
    try:
        cutoff_date = datetime.strptime(cutoff_date_str, "%Y-%m-%dT%H:%M:%SZ")
        cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
    except ValueError:
        logging.error("Incorrect date-time format. Use YYYY-MM-DDTHH:MM:SSZ (UTC).")
        sys.exit(1)

    cf_client = boto3.client('cloudformation')

    stacks_to_delete = list_stacks_created_after(cf_client, cutoff_date, exclude_stacks)
    logging.info(f"Found {len(stacks_to_delete)} stacks created after {cutoff_date_str}")

    for stack_name in stacks_to_delete:
        delete_stack(cf_client, stack_name)

if __name__ == "__main__":
    main()
