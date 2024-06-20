import boto3
import subprocess
import json

def get_deleted_stacks(date_time):
    command = [
        "aws", "cloudformation", "list-stacks",
        "--query", f"StackSummaries[?CreationTime >= `{date_time}` && StackStatus == 'DELETE_COMPLETE'].[StackName, StackId]",
        "--output", "json"
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Failed to list deleted stacks: {result.stderr}")
    
    return json.loads(result.stdout)

def get_tagged_resources():
    client = boto3.client('resourcegroupstaggingapi')
    paginator = client.get_paginator('get_resources')
    response_iterator = paginator.paginate(
        TagFilters=[
            {
                'Key': 'aws:cloudformation:stack-id'
            }
        ]
    )

    resources = []
    for response in response_iterator:
        resources.extend(response['ResourceTagMappingList'])
    return resources

def find_orphaned_resources(deleted_stacks, tagged_resources):
    deleted_stack_ids = [stack[1] for stack in deleted_stacks]
    orphaned_resources = []
    for resource in tagged_resources:
        for tag in resource['Tags']:
            if tag['Key'] == 'aws:cloudformation:stack-id' and tag['Value'] in deleted_stack_ids:
                orphaned_resources.append(resource)
                break
    return orphaned_resources

def main():
    date_time = "2024-05-01T00:00:00Z"  # Replace with your specific date and time
    deleted_stacks = get_deleted_stacks(date_time)
    print(f"Found {len(deleted_stacks)} deleted stacks.")

    tagged_resources = get_tagged_resources()
    print(f"Found {len(tagged_resources)} tagged resources.")

    orphaned_resources = find_orphaned_resources(deleted_stacks, tagged_resources)
    if not orphaned_resources:
        print("No orphaned resources found.")
    else:
        print(f"Found {len(orphaned_resources)} orphaned resources:")
        for resource in orphaned_resources:
            print(f"Resource ARN: {resource['ResourceARN']}")
            for tag in resource['Tags']:
                print(f"  Tag Key: {tag['Key']}, Tag Value: {tag['Value']}")

if __name__ == "__main__":
    main()
