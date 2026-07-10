#!/bin/bash
DATE=$(date +%Y%m%d_%H%M)
FILE=/tmp/terra_backup_${DATE}.sql.gz
pg_dump -h 127.0.0.1 -U terraos terraos 2>/dev/null | gzip > $FILE
echo "Backup: $FILE size=$(du -sh $FILE | cut -f1)"
if [ -n "$AWS_S3_BUCKET" ]; then
    aws s3 cp $FILE s3://$AWS_S3_BUCKET/backups/ && echo "Uploaded to S3"
fi
