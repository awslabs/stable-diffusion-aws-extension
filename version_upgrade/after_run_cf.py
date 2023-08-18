#!/usr/bin/python3

import boto3
import time
import subprocess

all_ddb_tables = [
    "ModelTable",
    "TrainingTable",
    "CheckpointTable",
    "DatasetInfoTable",
    "DatasetItemTable",
    "SDInferenceJobTable",
    "SDEndpointDeploymentJobTable"
]

src_bucket = "stable-diffusion-aws-exten-sds3aigcbucket7db76a0b-1h79q9vrv13kd"
dst_bucket = "sd-extension-v1-1-0-sds3aigcbucket7db76a0b-1bu1vouwlfccm"

ddb = boto3.client('dynamodb')

# Delete all tables create by CloudFormation
def delete_all_tables():
    for ddb_table in all_ddb_tables:
        print("Deleting table: " + ddb_table)
        ddb.delete_table(
            TableName=ddb_table
        )

# Restore all tables from backup created by before_run_cf.py
def restore_all_tables():
    for ddb_table in all_ddb_tables:
        print("Restoring backup for table: " + ddb_table)
        backups = ddb.list_backups(TableName=ddb_table)
        backup_arn = backups['BackupSummaries'][0]['BackupArn']
        ddb.restore_table_from_backup(
            TargetTableName=ddb_table,
            BackupArn=backup_arn
        )

# Check all tables status, restoring may take a while
def checking_restore_status():
    ret = True
    print("Checking all tables status")
    for ddb_table in all_ddb_tables:
        response = ddb.describe_table(
            TableName=ddb_table
        )
        print(f"Table {ddb_table} status: " + response['Table']['TableStatus'])
        if response['Table']['TableStatus'] != 'ACTIVE':
            ret = False
    return ret

def delete_all_backups():
    for ddb_table in all_ddb_tables:
        print("Deleting all backups for table: " + ddb_table)
        backups = ddb.list_backups(TableName=ddb_table)
        for backup in backups['BackupSummaries']:
            backup_arn = backup['BackupArn']
            ddb.delete_backup(
                BackupArn=backup_arn
            )

def restore_s3_bucket(src_bucket_name, dst_bucket_name):
    print(f"Restoring S3 bucket: from {src_bucket_name} to {dst_bucket_name}" )
    subprocess.run(["aws", "s3", "sync", "s3://" + src_bucket_name, "s3://" + dst_bucket_name])

def main():
    delete_all_tables()
    restore_all_tables()
    restore_s3_bucket(src_bucket, dst_bucket)

    all_done = False
    while all_done == False:
        all_done = checking_restore_status()
        if all_done:
            print("All tables are restored")
            break
        print("Sleep 5s...")
        time.sleep(5)

    delete_all_backups()

if __name__ == "__main__":
    main()
