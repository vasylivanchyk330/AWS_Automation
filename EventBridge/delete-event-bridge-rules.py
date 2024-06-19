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

def list_eventbridge_rules(events_client, pattern=None):
    """List all EventBridge rules, optionally filtering by a pattern."""
    rules_to_delete = []
    # if no pattern provided, return an empty list of rules_to_delete
    if not pattern:
        return rules_to_delete

    paginator = events_client.get_paginator('list_rules')
    for page in paginator.paginate():
        for rule in page['Rules']:
            if re.search(pattern, rule['Name'], re.IGNORECASE):
                rules_to_delete.append(rule['Name'])
    return rules_to_delete


def delete_eventbridge_rule(events_client, rule_name, retries=3):
    """Delete the specified EventBridge rule with retry logic."""
    for attempt in range(retries):
        try:
            # First, remove all targets associated with the rule.
            # Targets themselves are not deleted. They are simply detached from EventBridge rules.
            targets = events_client.list_targets_by_rule(Rule=rule_name)['Targets']
            if targets:
                target_ids = [target['Id'] for target in targets]
                events_client.remove_targets(Rule=rule_name, Ids=target_ids)
                logging.info(f"Removed targets from rule: {rule_name}")
            
            # Now delete the rule
            events_client.delete_rule(Name=rule_name, Force=True)
            logging.info(f"Deleted EventBridge rule: {rule_name}")
            return

        except events_client.exceptions.ClientError as e:
            logging.error(f"Error deleting EventBridge rule {rule_name}: {e}")
            if 'ResourceNotFoundException' in str(e):
                logging.error(f"Rule {rule_name} not found. It may have already been deleted.")
                return
            else:
                logging.error(f"Failed to delete rule {rule_name} on attempt {attempt + 1}: {e}")

    logging.error(f"Failed to delete rule {rule_name} after {retries} attempts. Please investigate manually.")

def read_exclude_rules(file_path):
    """Read the list of rule names to exclude from a file."""
    if not os.path.isfile(file_path):
        logging.error(f"Exclude rules file {file_path} not found!")
        sys.exit(1)
    with open(file_path, 'r') as file:
        exclude_rules = [line.strip() for line in file if line.strip()]
    return exclude_rules

def main():
    parser = argparse.ArgumentParser(description="Delete EventBridge rules matching a specific pattern or provided names.")
    parser.add_argument("rules", nargs='*', help="Names of rules to delete.")
    parser.add_argument("--pattern", "-p", help="Pattern to filter rule names for deletion.")
    parser.add_argument("--exclude-rules", "-e", help="List of rules to exclude from deletion, can be a comma-separated list or a file containing rule names")
    parser.add_argument("--force", "-f", action="store_true", help="Force deletion without confirmation")
    parser.add_argument("--log-file", "-l", help="Log file to store the output", default="eventbridge_cleanup.log")
    parser.add_argument("--log-dir", "-d", help="Directory to store the log file", default="./.script-logs")
    args = parser.parse_args()

    if not args.rules and not args.pattern:
        logging.error("You must provide at least one rule name or a pattern.")
        parser.print_help()
        sys.exit(1)

    # Define the default log file path
    log_dir = args.log_dir
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = args.log_file or os.path.join(log_dir, f"script_run_{datetime.now().strftime('%Y_%m_%d___%H%M%S')}.log")

    # Setup logger
    setup_logger(log_file)

    # Handle exclude rules
    exclude_rules = []
    if args.exclude_rules:
        if os.path.isfile(args.exclude_rules):
            exclude_rules = read_exclude_rules(args.exclude_rules)
        else:
            exclude_rules = [rule.strip() for rule in args.exclude_rules.split(',')]

    events_client = boto3.client('events')

    rules_to_delete = args.rules if args.rules else []

    # add the pattern_matched_rules to rules provided provided as arguments 
    if args.pattern:
        pattern_matched_rules = list_eventbridge_rules(events_client, args.pattern)
        rules_to_delete.extend(pattern_matched_rules)
    
    # Remove duplicates and filter out the excluded rules
    rules_to_delete = list(set(rules_to_delete) - set(exclude_rules))
    
    # Summary of rules to delete
    logging.info(f"Found {len(rules_to_delete)} rules matching the criteria:")
    if rules_to_delete:
        logging.info("Rules to be deleted:")
        for rule_name in rules_to_delete:
            logging.info(f" - {rule_name}")
        
        # Prompt to delete all rules
        if not args.force:
            confirm_all = input("Do you want to delete them all? (yes/no): ")
            logging.info(f"User prompt response: {confirm_all}")
            if confirm_all.lower() == 'yes':
                delete_all = True
            else:
                delete_all = False
        else:
            delete_all = True

    success = True  # Track the success of rule deletions
    for rule_name in rules_to_delete:
        try:
            if delete_all:
                delete_eventbridge_rule(events_client, rule_name)
            else:
                confirm_each = input(f"Do you want to delete the rule {rule_name}? (yes/no): ")
                logging.info(f"User prompt response for {rule_name}: {confirm_each}")
                if confirm_each.lower() == 'yes':
                    delete_eventbridge_rule(events_client, rule_name)
                else:
                    logging.info(f"Skipping deletion of rule: {rule_name}")
        except Exception as e:
            logging.error(f"Error during deletion of rule {rule_name}: {e}")
            success = False

    # Rename the log file if any rule failed to delete; assign exit_code value for later call
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
