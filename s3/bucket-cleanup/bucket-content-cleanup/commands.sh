#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <bucket-name>"
    exit 1
fi

BUCKET_NAME=$1
LIFECYCLE_POLICY_FILES=("lifecycle-policy-01.json" "lifecycle-policy-02.json")

# Check if the lifecycle policy files exist
for FILE in "${LIFECYCLE_POLICY_FILES[@]}"; do
    if [ ! -f "$FILE" ]; then
        echo "Lifecycle policy file $FILE not found!"
        exit 1
    fi
done

# Apply the lifecycle policies to the bucket
for FILE in "${LIFECYCLE_POLICY_FILES[@]}"; do
    aws s3api put-bucket-lifecycle-configuration --bucket $BUCKET_NAME --lifecycle-configuration file://$FILE
    if [ $? -eq 0 ]; then
        echo "Lifecycle policy $FILE applied successfully to $BUCKET_NAME"
        sleep 10
    else
        echo "Failed to apply lifecycle policy $FILE to $BUCKET_NAME"
        exit 1
    fi
    echo "Waiting for the previous rule to be created..."
    
done


