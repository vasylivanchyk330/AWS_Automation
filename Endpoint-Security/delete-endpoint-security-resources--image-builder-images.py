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

def list_images(imagebuilder_client, cutoff_date, until_date, pattern=None):
    """List all images optionally filtering by a pattern and creation date range."""
    images_to_delete = []
    
    response = imagebuilder_client.list_images()
    
    for image in response['imageVersionList']:
        image_name = image.get('name', '')
        creation_time_str = image['dateCreated']
        creation_time = datetime.strptime(creation_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        logging.debug(f"Checking Image: {image_name} with Creation Time: {creation_time}")
        if (not cutoff_date or cutoff_date <= creation_time) and (not until_date or creation_time <= until_date):
            if pattern is None or re.search(pattern, image_name, re.IGNORECASE):
                images_to_delete.append({
                    'Arn': image['arn'],
                    'Name': image_name,
                    'CreationTime': creation_time_str
                })
    
    return images_to_delete

def delete_image(imagebuilder_client, image_arn):
    """Delete the specified image."""
    try:
        imagebuilder_client.delete_image(imageBuildVersionArn=image_arn)
        logging.info(f"Deleted Image: {image_arn}")
    except imagebuilder_client.exceptions.ClientError as e:
        logging.error(f"Error deleting Image {image_arn}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Delete AWS EC2 Image Builder images matching specific criteria.")
    parser.add_argument("--cutoff-date", help="Cutoff date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC)")
    parser.add_argument("--until-date", default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        help="Until date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC), default is now")
    parser.add_argument("--pattern", "-p", help="Pattern to filter image names for deletion.")
    parser.add_argument("image_names", nargs='*', help="List of specific image names to delete.")
    parser.add_argument("--force", "-f", action="store_true", help="Force deletion without confirmation")
    parser.add_argument("--log-file", "-l", help="Log file to store the output")
    parser.add_argument("--log-dir", "-d", help="Directory to store the log file", default="./.script-logs")
    args = parser.parse_args()

    # Check that at least one criterion is provided
    if not args.cutoff_date and not args.pattern and not args.image_names:
        logging.error("You must provide at least one of --cutoff-date, --pattern, or image_names.")
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

    images_to_delete = []

    # List images based on date range and pattern
    if cutoff_date or args.pattern:
        logging.info(f"Listing images created between {cutoff_date} and {until_date} with pattern {args.pattern}...")
        images_to_delete.extend(list_images(imagebuilder_client, cutoff_date, until_date, pattern=args.pattern))
    
    # List images based on specific names
    if args.image_names:
        image_names = args.image_names
        logging.info(f"Listing images with specific names: {image_names}")
        response = imagebuilder_client.list_images()
        for image in response['imageVersionList']:
            if image.get('name') in image_names:
                images_to_delete.append({
                    'Arn': image['arn'],
                    'Name': image.get('name', 'N/A'),
                    'CreationTime': image['dateCreated']
                })

    # Remove duplicates
    images_to_delete = list({image['Arn']: image for image in images_to_delete}.values())

    # Summary of images to delete
    logging.info(f"Found {len(images_to_delete)} images matching the criteria:")
    if images_to_delete:
        logging.info("Images to be deleted:")
        for image in images_to_delete:
            logging.info(f" - {image['Arn']} (Name: {image['Name']}, CreationTime: {image['CreationTime']})")
        
        # Prompt to delete all images
        if not args.force:
            confirm_all = input("Do you want to delete them all? (yes/no): ")
            logging.info(f"User prompt response: {confirm_all}")
            if confirm_all.lower() == 'yes':
                delete_all = True
            else:
                delete_all = False
        else:
            delete_all = True

    success = True  # Track the success of image deletions
    for image in images_to_delete:
        try:
            if delete_all:
                delete_image(imagebuilder_client, image['Arn'])
            else:
                confirm_each = input(f"Do you want to delete the image {image['Arn']} (Name: {image['Name']})? (yes/no): ")
                logging.info(f"User prompt response for {image['Arn']}: {confirm_each}")
                if confirm_each.lower() == 'yes':
                    delete_image(imagebuilder_client, image['Arn'])
                else:
                    logging.info(f"Skipping deletion of image: {image['Arn']}")
        except Exception as e:
            logging.error(f"Error during deletion of image {image['Arn']}: {e}")
            success = False

    # Rename the log file if any image failed to delete; assign exit_code value for later call
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
