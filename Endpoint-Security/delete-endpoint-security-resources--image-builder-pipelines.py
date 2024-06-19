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

def list_image_pipelines(imagebuilder_client, cutoff_date, until_date, pattern=None):
    """List all image pipelines optionally filtering by a pattern and creation date range."""
    pipelines_to_delete = []
    
    response = imagebuilder_client.list_image_pipelines()
    
    for pipeline in response['imagePipelineList']:
        pipeline_name = pipeline.get('name', '')
        creation_time_str = pipeline['dateCreated']
        creation_time = datetime.strptime(creation_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        logging.debug(f"Checking Image Pipeline: {pipeline_name} with Creation Time: {creation_time}")
        if (not cutoff_date or cutoff_date <= creation_time) and (not until_date or creation_time <= until_date):
            if pattern is None or re.search(pattern, pipeline_name, re.IGNORECASE):
                pipelines_to_delete.append({
                    'Arn': pipeline['arn'],
                    'Name': pipeline_name,
                    'CreationTime': creation_time_str
                })
    
    return pipelines_to_delete

def delete_image_pipeline(imagebuilder_client, pipeline_arn):
    """Delete the specified image pipeline."""
    try:
        imagebuilder_client.delete_image_pipeline(imagePipelineArn=pipeline_arn)
        logging.info(f"Deleted Image Pipeline: {pipeline_arn}")
    except imagebuilder_client.exceptions.ClientError as e:
        logging.error(f"Error deleting Image Pipeline {pipeline_arn}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Delete AWS EC2 Image Builder pipelines matching specific criteria.")
    parser.add_argument("--cutoff-date", help="Cutoff date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC)")
    parser.add_argument("--until-date", default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        help="Until date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC), default is now")
    parser.add_argument("--pattern", "-p", help="Pattern to filter image pipeline names for deletion.")
    parser.add_argument("pipeline_names", nargs='*', help="List of specific image pipeline names to delete.")
    parser.add_argument("--force", "-f", action="store_true", help="Force deletion without confirmation")
    parser.add_argument("--log-file", "-l", help="Log file to store the output")
    parser.add_argument("--log-dir", "-d", help="Directory to store the log file", default="./.script-logs")
    args = parser.parse_args()

    # Check that at least one criterion is provided
    if not args.cutoff_date and not args.pattern and not args.pipeline_names:
        logging.error("You must provide at least one of --cutoff-date, --pattern, or pipeline_names.")
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

    imagebuilder_client = boto3.client('imagebuilder')

    pipelines_to_delete = []

    # List image pipelines based on date range and pattern
    if cutoff_date or args.pattern:
        logging.info(f"Listing image pipelines created between {cutoff_date} and {until_date} with pattern {args.pattern}...")
        pipelines_to_delete.extend(list_image_pipelines(imagebuilder_client, cutoff_date, until_date, pattern=args.pattern))
    
    # List image pipelines based on specific names
    if args.pipeline_names:
        pipeline_names = args.pipeline_names
        logging.info(f"Listing image pipelines with specific names: {pipeline_names}")
        response = imagebuilder_client.list_image_pipelines()
        for pipeline in response['imagePipelineList']:
            if pipeline.get('name') in pipeline_names:
                pipelines_to_delete.append({
                    'Arn': pipeline['arn'],
                    'Name': pipeline.get('name', 'N/A'),
                    'CreationTime': pipeline['dateCreated']
                })

    # Remove duplicates
    pipelines_to_delete = list({pipeline['Arn']: pipeline for pipeline in pipelines_to_delete}.values())

    # Summary of image pipelines to delete
    logging.info(f"Found {len(pipelines_to_delete)} image pipelines matching the criteria:")
    if pipelines_to_delete:
        logging.info("Image Pipelines to be deleted:")
        for pipeline in pipelines_to_delete:
            logging.info(f" - {pipeline['Arn']} (Name: {pipeline['Name']}, CreationTime: {pipeline['CreationTime']})")
        
        # Prompt to delete all image pipelines
        if not args.force:
            confirm_all = input("Do you want to delete them all? (yes/no): ")
            logging.info(f"User prompt response: {confirm_all}")
            if confirm_all.lower() == 'yes':
                delete_all = True
            else:
                delete_all = False
        else:
            delete_all = True

    success = True  # Track the success of image pipeline deletions
    for pipeline in pipelines_to_delete:
        try:
            if delete_all:
                delete_image_pipeline(imagebuilder_client, pipeline['Arn'])
            else:
                confirm_each = input(f"Do you want to delete the image pipeline {pipeline['Arn']} (Name: {pipeline['Name']})? (yes/no): ")
                logging.info(f"User prompt response for {pipeline['Arn']}: {confirm_each}")
                if confirm_each.lower() == 'yes':
                    delete_image_pipeline(imagebuilder_client, pipeline['Arn'])
                else:
                    logging.info(f"Skipping deletion of image pipeline: {pipeline['Arn']}")
        except Exception as e:
            logging.error(f"Error during deletion of image pipeline {pipeline['Arn']}: {e}")
            success = False

    # Rename the log file if any image pipeline failed to delete; assign exit_code value for later call
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
