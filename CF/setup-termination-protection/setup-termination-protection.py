import boto3
import logging
import argparse
import re

def setup_logger(log_file):
    """Set up logging to file and console."""
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

def get_stacks(cf_client, pattern=None):
    """Get the list of CloudFormation stacks, optionally filtering by a pattern."""
    stacks = []
    paginator = cf_client.get_paginator('describe_stacks')
    
    for page in paginator.paginate():
        for stack in page['Stacks']:
            if pattern:
                # Use re.search with re.IGNORECASE to match the pattern with the stack name in a case-insensitive manner
                if re.search(pattern, stack['StackName'], re.IGNORECASE):
                    stacks.append(stack['StackName'])
            else:
                stacks.append(stack['StackName'])
                
    return stacks

def enable_termination_protection(cf_client, stack_name):
    """Enable termination protection for the specified CloudFormation stack."""
    try:
        cf_client.update_termination_protection(
            StackName=stack_name,
            EnableTerminationProtection=True
        )
        logging.info(f"Enabled termination protection for stack: {stack_name}")
    except cf_client.exceptions.ClientError as e:
        logging.error(f"Error enabling termination protection for stack {stack_name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Enable termination protection for CloudFormation stacks.")
    parser.add_argument("--pattern", "-p", help="Pattern to filter stack names for updating.")
    parser.add_argument("--log-file", "-l", help="Log file to store the output", default="termination_protection.log")
    args = parser.parse_args()

    # Setup logger
    setup_logger(args.log_file)

    cf_client = boto3.client('cloudformation')

    stacks = get_stacks(cf_client, args.pattern)

    if not stacks:
        logging.info("No stacks found matching the pattern.")
        return

    logging.info(f"Found {len(stacks)} stacks matching the pattern:")
    for stack_name in stacks:
        logging.info(f" - {stack_name}")

    # Prompt the user to confirm
    confirm = input("Do you want to enable termination protection for all the listed stacks? (yes/no): ")
    if confirm.lower() == 'yes':
        for stack_name in stacks:
            enable_termination_protection(cf_client, stack_name)
    else:
        for stack_name in stacks:
            confirm_each = input(f"Do you want to enable termination protection for stack {stack_name}? (yes/no): ")
            if confirm_each.lower() == 'yes':
                enable_termination_protection(cf_client, stack_name)
            else:
                logging.info(f"Skipping termination protection for stack: {stack_name}")

    logging.info("Completed enabling termination protection for the specified stacks.")

if __name__ == "__main__":
    main()
