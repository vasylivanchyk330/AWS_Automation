import boto3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize a session using Amazon Image Builder
client = boto3.client('imagebuilder')

def list_all_images(imagebuilder_client):
    images = []
    response = imagebuilder_client.list_images()
    images.extend(response['imageVersionList'])
    return images

def list_image_versions(imagebuilder_client, image_arn):
    versions = []
    response = imagebuilder_client.list_image_build_versions(
        imageVersionArn=image_arn
    )
    for image in response['imageSummaryList']:
        versions.append(image['arn'])
    return versions

def delete_image_version(imagebuilder_client, image_arn):
    try:
        logging.info(f"Deleting Image Version: {image_arn}")
        imagebuilder_client.delete_image(imageBuildVersionArn=image_arn)
        logging.info(f"Successfully deleted Image Version: {image_arn}")
    except Exception as e:
        logging.error(f"Error deleting Image Version {image_arn}: {e}")

def delete_all_image_versions(imagebuilder_client):
    images = list_all_images(imagebuilder_client)
    for image in images:
        image_arn = image['arn']
        image_name = image.get('name', '')
        logging.info(f"Processing Image: {image_name} ({image_arn})")
        versions = list_image_versions(imagebuilder_client, image_arn)
        for version in versions:
            response = input(f"Do you want to delete the image version {version} of {image_name}? (yes/no): ")
            if response.lower() == 'yes':
                delete_image_version(imagebuilder_client, version)
            else:
                logging.info(f"Skipping deletion of image version: {version}")

# Example usage
if __name__ == "__main__":
    delete_all_image_versions(client)
