#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <bucket-name>"
    exit 1
fi

BUCKET_NAME=$1
POLICY_FOLDER="generated-deny-policies"
POLICY_FILE="bucket-policy--${BUCKET_NAME}.json"
POLICY_PATH="${POLICY_FOLDER}/${POLICY_FILE}"
TEMPLATE_FILE="deny-bucket-policy-template.json"

# Create the policy folder if it doesn't exist
if [ ! -d "$POLICY_FOLDER" ]; then
    mkdir -p $POLICY_FOLDER
fi

# Check if the template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Template file $TEMPLATE_FILE not found!"
    exit 1
fi

# Replace placeholder with actual bucket name and write to POLICY_PATH
sed "s/BUCKET_NAME_PLACEHOLDER/${BUCKET_NAME}/g" $TEMPLATE_FILE > $POLICY_PATH

# Check if the POLICY_PATH is not empty
if [ ! -s "$POLICY_PATH" ]; then
    echo "Failed to create policy file $POLICY_PATH"
    exit 1
fi

# Apply the bucket policy
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://$POLICY_PATH

if [ $? -eq 0 ]; then
    echo "Bucket policy applied successfully to $BUCKET_NAME"
else
    echo "Failed to apply bucket policy to $BUCKET_NAME"
fi
