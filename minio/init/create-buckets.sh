#!/bin/sh
set -e

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

IFS=','
for bucket in $MINIO_BUCKETS; do
  echo "Ensuring bucket '$bucket' exists..."
  mc mb --ignore-existing "local/$bucket"
done

echo "MinIO buckets provisioned: $MINIO_BUCKETS"
