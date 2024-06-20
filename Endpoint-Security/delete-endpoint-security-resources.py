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

# Function to list AMIs based on provided criteria
def list_amis(ec2_client, cutoff_date, until_date, pattern=None):
    amis_to_delete = []
    response = ec2_client.describe_images(Owners=['self'])
    for image in response['Images']:
        creation_date_str = image['CreationDate']
        creation_date = datetime.strptime(creation_date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        ami_name = image.get('Name', '')
        logging.debug(f"Checking AMI: {ami_name} with Creation Date: {creation_date}")
        if (not cutoff_date or cutoff_date <= creation_date) and (not until_date or creation_date <= until_date):
            if pattern is None or re.search(pattern, ami_name, re.IGNORECASE):
                amis_to_delete.append({
                    'ImageId': image['ImageId'],
                    'Name': ami_name,
                    'CreationDate': creation_date_str
                })
    return amis_to_delete

# Function to delete AMIs
def delete_ami(ec2_client, image_id):
    try:
        ec2_client.deregister_image(ImageId=image_id)
        logging.info(f"Deregistered AMI: {image_id}")
        snapshots = ec2_client.describe_snapshots(Filters=[{'Name': 'description', 'Values': [f'*{image_id}*']}])
        for snapshot in snapshots['Snapshots']:
            try:
                ec2_client.delete_snapshot(SnapshotId=snapshot['SnapshotId'])
                logging.info(f"Deleted snapshot: {snapshot['SnapshotId']} for AMI: {image_id}")
            except ec2_client.exceptions.ClientError as e:
                logging.error(f"Error deleting snapshot {snapshot['SnapshotId']} for AMI {image_id}: {e}")
    except ec2_client.exceptions.ClientError as e:
        logging.error(f"Error deleting AMI {image_id}: {e}")

# Function to list Image Pipelines based on provided criteria
def list_image_pipelines(imagebuilder_client, cutoff_date, until_date, pattern=None):
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

# Function to delete Image Pipelines
def delete_image_pipeline(imagebuilder_client, pipeline_arn):
    try:
        imagebuilder_client.delete_image_pipeline(imagePipelineArn=pipeline_arn)
        logging.info(f"Deleted Image Pipeline: {pipeline_arn}")
    except imagebuilder_client.exceptions.ClientError as e:
        logging.error(f"Error deleting Image Pipeline {pipeline_arn}: {e}")

# Function to list Images based on provided criteria
def list_images(imagebuilder_client, cutoff_date, until_date, pattern=None):
    images_to_delete = []
    response = imagebuilder_client.list_images()
    for image in response['imageVersionList']:
        image_arn = image['arn']
        image_name = image.get('name', '')
        logging.debug(f"Processing Image: {image_name} ({image_arn})")
        try:
            build_versions = imagebuilder_client.list_image_build_versions(imageVersionArn=image_arn)
            logging.debug(f"Response for image build versions: {build_versions}")
            if 'imageSummaryList' in build_versions:
                for build_version in build_versions['imageSummaryList']:
                    creation_time_str = build_version['dateCreated']
                    creation_time = datetime.strptime(creation_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                    logging.debug(f"Checking Image Build Version: {build_version['arn']} with Creation Time: {creation_time}")
                    if (not cutoff_date or cutoff_date <= creation_time) and (not until_date or creation_time <= until_date):
                        if pattern is None or re.search(pattern, image_name, re.IGNORECASE):
                            images_to_delete.append({
                                'Arn': build_version['arn'],
                                'Name': image_name,
                                'CreationTime': creation_time_str
                            })
            else:
                logging.warning(f"No imageSummaryList found for image ARN: {image_arn}")
        except imagebuilder_client.exceptions.ClientError as e:
            logging.error(f"Error listing build versions for image {image_arn}: {e}")
    return images_to_delete

# Function to delete Images
def delete_image(imagebuilder_client, image_arn):
    try:
        logging.info(f"Deleting Image Version: {image_arn}")
        imagebuilder_client.delete_image(imageBuildVersionArn=image_arn)
        logging.info(f"Successfully deleted Image Version: {image_arn}")
    except Exception as e:
        logging.error(f"Error deleting Image Version {image_arn}: {e}")

# Function to list Snapshots based on provided criteria
def list_snapshots(ec2_client, cutoff_date, until_date, pattern=None):
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

# Function to delete Snapshots
def delete_snapshot(ec2_client, snapshot_id):
    try:
        ec2_client.delete_snapshot(SnapshotId=snapshot_id)
        logging.info(f"Deleted Snapshot: {snapshot_id}")
    except ec2_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'InvalidSnapshot.NotFound':
            logging.warning(f"Snapshot {snapshot_id} not found. It may have already been deleted.")
        else:
            logging.error(f"Error deleting Snapshot {snapshot_id}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Delete AWS resources matching specific criteria.")
    parser.add_argument("--resource-types", nargs='+', choices=['ami', 'pipeline', 'image', 'snapshot'], required=True, help="Types of resources to delete.")
    parser.add_argument("--cutoff-date", help="Cutoff date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC)")
    parser.add_argument("--until-date", default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        help="Until date-time in format YYYY-MM-DDTHH:MM:SSZ (UTC), default is now")
    parser.add_argument("--pattern", "-p", help="Pattern to filter resource names for deletion.")
    parser.add_argument("--resource-names", nargs='*', help="List of specific resource names to delete.")
    parser.add_argument("--force", "-f", action="store_true", help="Force deletion without confirmation")
    parser.add_argument("--log-file", "-l", help="Log file to store the output")
    parser.add_argument("--log-dir", "-d", help="Directory to store the log file", default="./.script-logs")
    args = parser.parse_args()

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

    # Initialize clients
    ec2_client = boto3.client('ec2')
    imagebuilder_client = boto3.client('imagebuilder')

    # Dictionary to store resources to delete
    resources_to_delete = {resource_type: [] for resource_type in args.resource_types}

    # List resources based on date range and pattern if provided
    if cutoff_date or args.pattern:

        logging.info(f"Listing resources created between {cutoff_date} and {until_date} with pattern {args.pattern}...")

        if 'ami' in args.resource_types:
            resources_to_delete['ami'].extend(list_amis(ec2_client, cutoff_date, until_date, pattern=args.pattern))
        if 'pipeline' in args.resource_types:
            resources_to_delete['pipeline'].extend(list_image_pipelines(imagebuilder_client, cutoff_date, until_date, pattern=args.pattern))
        if 'image' in args.resource_types:
            resources_to_delete['image'].extend(list_images(imagebuilder_client, cutoff_date, until_date, pattern=args.pattern))
        if 'snapshot' in args.resource_types:
            resources_to_delete['snapshot'].extend(list_snapshots(ec2_client, cutoff_date, until_date, pattern=args.pattern))

    # List all resources if neither cutoff_date nor pattern is provided
    if not cutoff_date and not args.pattern:
        logging.info("No cutoff date or pattern provided. Listing all resources of the specified types...")

        if 'ami' in args.resource_types:
            resources_to_delete['ami'].extend(list_amis(ec2_client, None, until_date))
        if 'pipeline' in args.resource_types:
            resources_to_delete['pipeline'].extend(list_image_pipelines(imagebuilder_client, None, until_date))
        if 'image' in args.resource_types:
            resources_to_delete['image'].extend(list_images(imagebuilder_client, None, until_date))
        if 'snapshot' in args.resource_types:
            resources_to_delete['snapshot'].extend(list_snapshots(ec2_client, None, until_date))

    # List resources based on specific names if provided
    if args.resource_names:
        resource_names = args.resource_names
        logging.info(f"Listing resources with specific names: {resource_names}")

        if 'ami' in args.resource_types:
            response = ec2_client.describe_images(Owners=['self'])
            for image in response['Images']:
                if image.get('Name') in resource_names:
                    resources_to_delete['ami'].append({
                        'ImageId': image['ImageId'],
                        'Name': image.get('Name', 'N/A'),
                        'CreationDate': image['CreationDate']
                    })

        if 'pipeline' in args.resource_types:
            response = imagebuilder_client.list_image_pipelines()
            for pipeline in response['imagePipelineList']:
                if pipeline.get('name') in resource_names:
                    resources_to_delete['pipeline'].append({
                        'Arn': pipeline['arn'],
                        'Name': pipeline.get('name', 'N/A'),
                        'CreationTime': pipeline['dateCreated']
                    })

        if 'image' in args.resource_types:
            response = imagebuilder_client.list_images()
            for image in response['imageVersionList']:
                if image.get('name') in resource_names:
                    # List image build versions
                    build_versions = imagebuilder_client.list_image_build_versions(imageVersionArn=image['arn'])
                    logging.debug(f"Response for image build versions: {build_versions}")
                    if 'imageSummaryList' in build_versions:
                        for build_version in build_versions['imageSummaryList']:
                            resources_to_delete['image'].append({
                                'Arn': build_version['arn'],
                                'Name': image.get('name', 'N/A'),
                                'CreationTime': build_version['dateCreated']
                            })
                    else:
                        logging.warning(f"No imageSummaryList found for image ARN: {image['arn']}")

        if 'snapshot' in args.resource_types:
            response = ec2_client.describe_snapshots(OwnerIds=['self'])
            for snapshot in response['Snapshots']:
                snapshot_name = ''
                for tag in snapshot.get('Tags', []):
                    if tag['Key'] == 'Name' and tag['Value'] in resource_names:
                        snapshot_name = tag['Value']
                        resources_to_delete['snapshot'].append({
                            'SnapshotId': snapshot['SnapshotId'],
                            'Name': snapshot_name,
                            'CreationTime': snapshot['StartTime'].strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                        })

    # Remove duplicates from the resources to delete
    for resource_type in args.resource_types:
        if resource_type == 'ami':
            resources_to_delete[resource_type] = list({ami['ImageId']: ami for ami in resources_to_delete[resource_type]}.values())
        elif resource_type == 'pipeline':
            resources_to_delete[resource_type] = list({pipeline['Arn']: pipeline for pipeline in resources_to_delete[resource_type]}.values())
        elif resource_type == 'image':
            resources_to_delete[resource_type] = list({image['Arn']: image for image in resources_to_delete[resource_type]}.values())
        elif resource_type == 'snapshot':
            resources_to_delete[resource_type] = list({snapshot['SnapshotId']: snapshot for snapshot in resources_to_delete[resource_type]}.values())

    # Summary of resources to delete
    for resource_type in args.resource_types:
        logging.info(f"Found {len(resources_to_delete[resource_type])} {resource_type}s matching the criteria:")
        if resources_to_delete[resource_type]:
            logging.info(f"{resource_type.capitalize()}s to be deleted:")
            for resource in resources_to_delete[resource_type]:
                if resource_type == 'ami':
                    logging.info(f" - {resource['ImageId']} (Name: {resource['Name']}, CreationDate: {resource['CreationDate']})")
                elif resource_type == 'snapshot':
                    logging.info(f" - {resource['SnapshotId']} (Name: {resource['Name']}, CreationTime: {resource['CreationTime']})")
                else:
                    logging.info(f" - {resource['Arn']} (Name: {resource['Name']}, CreationTime: {resource['CreationTime']})")

    # Check if there are any resources to delete
    total_resources_to_delete = sum(len(resources_to_delete[resource_type]) for resource_type in args.resource_types)
    if total_resources_to_delete == 0:
        logging.info("No resources found to delete.")
        sys.exit(0)
    
    # Prompt to delete all resources
    if not args.force:
        confirm_all = input("Do you want to delete them all? (yes/no): ")
        logging.info(f"User prompt response: {confirm_all}")
        delete_all = confirm_all.lower() == 'yes'
    else:
        delete_all = True

    success = True  # Track the success of resource deletions
    for resource_type in args.resource_types:
        for resource in resources_to_delete[resource_type]:
            try:
                if delete_all:
                    if resource_type == 'ami':
                        delete_ami(ec2_client, resource['ImageId'])
                    elif resource_type == 'pipeline':
                        delete_image_pipeline(imagebuilder_client, resource['Arn'])
                    elif resource_type == 'image':
                        delete_image(imagebuilder_client, resource['Arn'])
                    elif resource_type == 'snapshot':
                        delete_snapshot(ec2_client, resource['SnapshotId'])
                else:
                    confirm_each = input(f"Do you want to delete the {resource_type} {resource['ImageId' if resource_type == 'ami' else 'Arn' if resource_type in ['pipeline', 'image'] else 'SnapshotId']} (Name: {resource['Name']})? (yes/no): ")
                    logging.info(f"User prompt response for {resource['ImageId' if resource_type == 'ami' else 'Arn' if resource_type in ['pipeline', 'image'] else 'SnapshotId']}: {confirm_each}")
                    if confirm_each.lower() == 'yes':
                        if resource_type == 'ami':
                            delete_ami(ec2_client, resource['ImageId'])
                        elif resource_type == 'pipeline':
                            delete_image_pipeline(imagebuilder_client, resource['Arn'])
                        elif resource_type == 'image':
                            delete_image(imagebuilder_client, resource['Arn'])
                        elif resource_type == 'snapshot':
                            delete_snapshot(ec2_client, resource['SnapshotId'])
                    else:
                        logging.info(f"Skipping deletion of {resource_type}: {resource['ImageId' if resource_type == 'ami' else 'Arn' if resource_type in ['pipeline', 'image'] else 'SnapshotId']}")
            except Exception as e:
                logging.error(f"Error during deletion of {resource_type} {resource['ImageId' if resource_type == 'ami' else 'Arn' if resource_type in ['pipeline', 'image'] else 'SnapshotId']}: {e}")
                success = False

    # Rename the log file if any resource failed to delete; assign exit_code value for later call
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
