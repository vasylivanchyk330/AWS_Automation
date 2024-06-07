
# First add the DENY bucket policy - there could be cases when an app use the bucket as a target for logs.
# add the lifecycle rule with "Expire current versions of objects" and "Permanently delete noncurrent versions of objects"
# then, do this:


# 1. Check for and Delete Delete-Markers
# List delete markers and save their keys and version IDs to a file
aws s3api list-object-versions --bucket a-bucket-name \
    --query "DeleteMarkers[].[Key, VersionId]" \
    --output text > delete_markers.txt
# format properly 
jq -R -s -c 'split("\n") | .[:-1] | map(split("\t")) | {Objects: map({Key: .[0], VersionId: .[1]})}' delete_markers.txt > delete_markers.json
# delete 
aws s3api delete-objects --bucket a-bucket-name \
    --delete file://delete_markers.json
# there might be too many delete-markers to get deleted for the duration of one session. u might want to set a fixed delete-marker number - use `--max-items 5000`, e.g.
aws s3api list-object-versions --max-items 5000  \
    --bucket a-bucket-name \
    --query "DeleteMarkers[].[Key, VersionId]" \
    --output text > delete_markers.txt


# 2. Check for and Abort Incomplete Multipart Uploads
# List incomplete multipart uploads and save their upload IDs
aws s3api list-multipart-uploads --bucket a-bucket-name \
    --query "Uploads[].[Key, UploadId]" \
    --output text > multipart_uploads.txt
# Abort each incomplete multipart upload
while read -r key uploadId; do
    aws s3api abort-multipart-upload --bucket a-bucket-name --key "$key" --upload-id "$uploadId"
done < multipart_uploads.txt




# ----
# check, if Bucket is Empty
aws s3api list-object-versions --bucket a-bucket-name
aws s3api list-multipart-uploads --bucket a-bucket-name
aws s3api list-objects-v2 \
    --bucket a-bucket-name \
    --query "Contents[].Key" \
    --output text | tr '\t' '\n'

# delete.
aws s3 rb s3://a-bucket-name --force
#
aws s3 ls





# apendex. glossary

# a bucket key - (of bucket level point of view) path to an object in the bucket:
    # `my-bucket`  -- a bucket name
    # `photos/2024/vacation.jpg`  -- a key, where the object is stored at
    # `s3://my-bucket/photos/2024/vacation.jpg`  -- the full path

# delete-marker:
    # when versioning is enabled on a bucket, deleting an object does not actually remove its data. 
    # Instead, a delete marker is created.
    # This allows to recover deleted objects if needed.

# Multipart upload - a feature in Amazon S3 that allows to upload a single object as a set of parts. Each part is uploaded independently, and the parts can be uploaded in parallel to reduce the time taken to upload large files
# Such multipart uploads could get failed. and it might cause unexpected later on when, e.g. u try to delete a bucket.
# e.g. list 
aws s3api list-multipart-uploads --bucket my-bucket
