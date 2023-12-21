import logging
import os
import boto3
import sys

import tarfile
import shutil
from pathlib import Path

sys.path.append(os.getcwd())
LOGGING_LEVEL = logging.DEBUG


def upload_file_to_s3(file_name, bucket, directory=None, object_name=None, region=None):
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Add the directory to the object_name
    if directory:
        object_name = f"{directory}/{object_name}"

    # Upload the file
    try:
        if region:
            s3_client = boto3.client(service_name='s3', region_name=region)
        else:
            s3_client = boto3.client('s3')
        s3_client.upload_file(file_name, bucket, object_name)
        print(f"File {file_name} uploaded to {bucket}/{object_name}")
    except Exception as e:
        print(f"Error occurred while uploading {file_name} to {bucket}/{object_name}: {e}")
        return False
    return True


def download_folder_from_s3(bucket_name, s3_folder_path, local_folder_path, region=None):
    if region:
        s3_resource = boto3.resource(service_name='s3', region_name=region)
    else:
        s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(bucket_name)
    for obj in bucket.objects.filter(Prefix=s3_folder_path):
        obj_dirname = os.sep.join(os.path.dirname(obj.key).split("/")[1:])
        obj_basename = os.path.basename(obj.key)
        local_sub_folder_path = os.path.join(local_folder_path, obj_dirname)
        if not os.path.exists(local_sub_folder_path):
            os.makedirs(local_sub_folder_path)
        bucket.download_file(obj.key, os.path.join(local_sub_folder_path, obj_basename))  # save to same path


def download_folder_from_s3_by_tar(bucket_name, s3_tar_path, local_tar_path, target_dir=".", region=None):
    if region:
        s3_client = boto3.client(service_name='s3', region_name=region)
    else:
        s3_client = boto3.client('s3')
    s3_client.download_file(bucket_name, s3_tar_path, local_tar_path)
    tar(mode='x', archive=local_tar_path, verbose=True, change_dir=target_dir)
    # rm(local_tar_path, recursive=True)


def get_bucket_name_from_s3_path(s3_path) -> str:
    s3_path = s3_path.replace("s3://", "")
    return s3_path.split("/")[0]


def get_path_from_s3_path(s3_path) -> str:
    s3_path = s3_path.replace("s3://", "")
    return "/".join(s3_path.split("/")[1:])


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


def mv(src, dest, force=False):
    """
    Description:
        Move or rename files and directories.
    Args:
        src (str): Source file or directory path.
        dest (str): Destination file or directory path.
        force (bool): If True, overwrite the destination if it exists. Default is False.
    Usage:
        # Rename a file
        mv('old_name.txt', 'new_name.txt')

        # Move a file to a new directory
        mv('file.txt', 'new_directory/file.txt')

        # Move a directory to another directory
        mv('source_directory', 'destination_directory')

        # Force move (overwrite) a file or directory
        mv('source_file.txt', 'existing_destination_file.txt', force=True)
    """
    src_path = Path(src)
    dest_path = Path(dest)

    if src_path.exists():
        if dest_path.exists() and not force:
            raise FileExistsError(f"Destination path '{dest}' already exists and 'force' is not set")
        else:
            if dest_path.is_file():
                dest_path.unlink()
            elif dest_path.is_dir():
                shutil.rmtree(dest_path)

        if src_path.is_file() or src_path.is_dir():
            shutil.move(src, dest)
    else:
        raise FileNotFoundError(f"Source path '{src}' does not exist")


if __name__ == '__main__':
    import sys

    # upload_file_to_s3(sys.argv[1], 'aws-gcr-csdc-atl-exp-us-west-2', sys.argv[2])
    # fast_upload(boto3.Session(), 'aws-gcr-csdc-atl-exp-us-west-2', sys.argv[2], [sys.argv[1]])
    # upload_folder_to_s3_by_tar('models/dreambooth/sagemaker_test/samples', 'aws-gcr-csdc-atl-exp-us-west-2',
    #                            'aigc-webui-test-samples', '')
    # download_folder_from_s3_by_tar('aws-gcr-csdc-atl-exp-us-west-2', 'aigc-webui-test-samples/samples.tar',
    #                                'samples.tar')
