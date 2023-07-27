import json
from typing import Dict
import os
import tarfile
import boto3

s3 = boto3.client('s3')


def publish_msg(topic_arn, msg, subject):
    client = boto3.client('sns')
    client.publish(
        TopicArn=topic_arn,
        Message=str(msg),
        Subject=subject
    )


def get_s3_presign_urls(bucket_name, base_key, filenames) -> Dict[str, str]:
    return _get_s3_presign_urls(bucket_name, base_key, filenames, expires=3600 * 24 * 7, method='put_object')


def get_s3_get_presign_urls(bucket_name, base_key, filenames) -> Dict[str, str]:
    return _get_s3_presign_urls(bucket_name, base_key, filenames, expires=3600 * 24, method='get_object')


def _get_s3_presign_urls(bucket_name, base_key, filenames, expires=3600, method='put_object') -> Dict[str, str]:
    s3 = boto3.client('s3')
    presign_url_map = {}
    for filename in filenames:
        key = f'{base_key}/{filename}'
        url = s3.generate_presigned_url(method,
                                        Params={'Bucket': bucket_name,
                                                'Key': key,
                                                },
                                        ExpiresIn=expires)
        presign_url_map[filename] = url

    return presign_url_map


def generate_presign_url(bucket_name, key, expires=3600, method='put_object') -> Dict[str, str]:
    s3 = boto3.client('s3')
    return s3.generate_presigned_url(method,
                                     Params={'Bucket': bucket_name,
                                             'Key': key,
                                             },
                                     ExpiresIn=expires)


def load_json_from_s3(bucket_name: str, key: str):
    '''
    Get the JSON file from the specified bucket and key
    '''
    response = s3.get_object(Bucket=bucket_name, Key=key)
    json_file = response['Body'].read().decode('utf-8')
    data = json.loads(json_file)

    return data


def save_json_to_file(json_string: str, folder_path: str, file_name: str):
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, file_name)

    with open(file_path, 'w') as file:
        file.write(json.dumps(json_string))

    return file_path


def tar(mode, archive, sfiles=None, verbose=False, change_dir=None):
    """
    Description:
        Create or extract a tar archive.
    Args:
        mode: 'c' for create or 'x' for extract
        archive: the archive file name
        files: a list of files to add to the archive (when creating) or extract (when extracting); None to extract all files
        verbose: whether to print the names of the files as they are being processed
        change_dir: the directory to change to before performing any other operations; None to use the current directory
    Usage:
        # Create a new archive
        tar(mode='c', archive='archive.tar', sfiles=['file1.txt', 'file2.txt'])

        # Extract files from an archive
        tar(mode='x', archive='archive.tar')

        # Create a new archive with verbose mode and input directory
        tar(mode='c', archive='archive.tar', sfiles='./some_directory', verbose=True)

        # Extract files from an archive with verbose mode and change directory
        tar(mode='x', archive='archive.tar', verbose=True, change_dir='./some_directory')
    """
    if mode == 'c':
        # os.chdir(change_dir)
        with tarfile.open(archive, mode='w') as tar:
            # check if input option file is a list or string
            if isinstance(sfiles, list):
                for file in sfiles:
                    if verbose:
                        print(f"Adding {file} to {archive}")
                    tar.add(file)
            # take it as a folder name string
            else:
                for folder_path, subfolders, files in os.walk(sfiles):
                    for file in files:
                        if verbose:
                            print(f"Adding {os.path.join(folder_path, file)} to {archive}")
                        tar.add(os.path.join(folder_path, file))

    elif mode == 'x':
        with tarfile.open(archive, mode='r') as tar:
            # sfiles is set to all files in the archive if not specified
            if not sfiles:
                sfiles = tar.getnames()
            for file in sfiles:
                if verbose:
                    print(f"Extracting {file} from {archive}")
                # extra to specified directory
                if change_dir:
                    tar.extract(file, path=change_dir)
                else:
                    tar.extract(file)


def upload_file_to_s3():
    resp = s3.put_object(Bucket=S3_BUCKET_NAME, Key='inference/' + file_name, Body=json_data)
    
    return resp

