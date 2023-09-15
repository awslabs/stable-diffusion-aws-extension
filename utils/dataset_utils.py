import argparse
import time

import boto3


parser = argparse.ArgumentParser(description="Generate metadata according to the content in S3 bucket")
parser.add_argument("--s3_path", required=True, help="S3 path of the folder, eg. s3://s3-bucket-name/dataset/your-folder/")
parser.add_argument("--region", required=False, default="us-east-1", help="AWS region")
parser.add_argument("--desc", required=False, default="Default description created by utils", help="Dataset description")

args = parser.parse_args()
arg_folder_path = args.s3_path
arg_aws_region = args.region
arg_desc = args.desc

# Initialize the AWS clients for S3 and DynamoDB
s3_client = boto3.client("s3", region_name=arg_aws_region)
dynamodb_client = boto3.client("dynamodb", region_name=arg_aws_region)

info_table_name = "DatasetInfoTable"
item_table_name = "DatasetItemTable"

parts = arg_folder_path.split("/")
s3_bucket = parts[2]
s3_prefix = "/".join(parts[3:])
create_time = str(time.time())
if arg_folder_path.endswith("/"):
    # Ignore the last forward slash
    s3_dataset = parts[-2]
else:
    s3_dataset = parts[-1]


def insert_item(dataset_name: str, file_name: str, create_time: str):
    """Insert data into DynamoDB table DatasetItemTable

    Args:
        dataset_name (str): dataset name
        file_name (str): S3 file name
        create_time (str): create time in timestamp format
    """
    dataset_item = {
        "dataset_name": {
            "S": dataset_name
        },
        "sort_key": {
            "S": create_time + "_" + file_name
        },
        "data_status": {
            "S": "Enabled"
        },
        "name": {
            "S": file_name
        },
        "params": {
            "M": {
                "original_file_name": {
                    "S": file_name
                }
            }
        },
        "type": {
            "S": "image"
        }
    }
    try:
        response = dynamodb_client.put_item(
            TableName=item_table_name,
            Item=dataset_item
        )
        print(f"Inserted {dataset_item} into DynamoDB with response: {response}")
    except Exception as e:
        print(f"Error inserting {dataset_item} into DynamoDB: {e}")


def insert_info(s3_dataset: str, desc: str, create_time: str):
    """Insert data into DynamoDB table DatasetInfoTable

    Args:
        s3_dataset (str): dataset name
        desc (str): dataset description
        create_time (str): create time in timestamp format
    """
    dataset_info = {
        "dataset_name": {
            "S": s3_dataset
        },
        "dataset_status": {
            "S": "Enabled"
        },
        "params": {
            "M": {
                "description": {
                    "S": desc
                }
            }
        },
        "timestamp": {
            "N": create_time
        }
    }
    try:
        response = dynamodb_client.put_item(
            TableName=info_table_name,
            Item=dataset_info
        )
        print(f"Inserted {dataset_info} into DynamoDB with response: {response}")
    except Exception as e:
        print(f"Error inserting {dataset_info} into DynamoDB: {e}")


if __name__ == "__main__":
    # List S3 objects in the specified folder
    s3_objects = s3_client.list_objects(Bucket=s3_bucket, Prefix=s3_prefix)
    if "Contents" in s3_objects:
        for obj in s3_objects["Contents"]:
            print(obj)
            file_name = obj["Key"].split("/")[-1]
            print(file_name)
            if len(file_name.strip()) != 0:
                # Insert file information into DynamoDB
                insert_item(s3_dataset, file_name, create_time)
    else:
        print(f"No objects found in {s3_prefix}")

    insert_info(s3_dataset, arg_desc, create_time)
