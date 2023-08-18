#!/usr/bin/python3

import boto3

all_ddb_tables = [
    "ModelTable",
    "TrainingTable",
    "CheckpointTable",
    "DatasetInfoTable",
    "DatasetItemTable",
    "SDInferenceJobTable",
    "SDEndpointDeploymentJobTable"
]

ddb = boto3.client('dynamodb')

# Backup all tables
def backup_all_tables():
    for ddb_table in all_ddb_tables:
        print("Creating backup for table: " + ddb_table)
        ddb.create_backup(
            TableName=ddb_table,
            BackupName=ddb_table + "_backup_for_upgrade"
        )

if __name__ == "__main__":
    backup_all_tables()
