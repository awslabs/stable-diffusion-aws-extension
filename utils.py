import logging
import os
import requests
import boto3
import botocore
import boto3.s3.transfer as s3transfer
import sys
from urllib.parse import urlparse
import requests
import json
import gradio as gr

sys.path.append(os.getcwd())
# from modules.timer import Timer
import tarfile

import shutil
from pathlib import Path
import psutil

LOGGING_LEVEL = logging.DEBUG

class ModelsRef:
    def __init__(self):
        self.models_ref = {}

    def get_models_ref_dict(self):
        return self.models_ref

    def add_models_ref(self, model_name):
        if model_name in self.models_ref:
            self.models_ref[model_name] += 1
        else:
            self.models_ref[model_name] = 0

    def remove_model_ref(self,model_name):
        if self.models_ref.get(model_name):
            del self.models_ref[model_name]

    def get_models_ref(self, model_name):
        return self.models_ref.get(model_name)

    def get_least_ref_model(self):
        sorted_models = sorted(self.models_ref.items(), key=lambda item: item[1])
        if sorted_models:
            least_ref_model, least_counter = sorted_models[0]
            return least_ref_model,least_counter
        else:
            return None,None

    def pop_least_ref_model(self):
        sorted_models = sorted(self.models_ref.items(), key=lambda item: item[1])
        if sorted_models:
            least_ref_model, least_counter = sorted_models[0]
            del self.models_ref[least_ref_model]
            return least_ref_model,least_counter
        else:
            return None,None

    def get_sorted_models(self, key_list=None):
        print('!!!!!!!!!!!', key_list)
        if key_list is None:
            return sorted(self.models_ref.items(), key=lambda item: item[1])
        else:
            models_ref_tmp = {}
            for key_value in key_list:
                if key_value not in self.models_ref.keys():
                    models_ref_tmp[key_value] = -1
                else:
                    models_ref_tmp[key_value] = self.models_ref[key_value]
            models_sorted_info = sorted(models_ref_tmp.items(), key=lambda item: item[1])
            models_sorted = []
            for model_info in models_sorted_info:
                models_sorted.append(model_info[0])
            return models_sorted

# sd_models_Ref = ModelsRef()
# cn_models_Ref = ModelsRef()
# lora_models_Ref = ModelsRef()
# hyper_models_Ref = ModelsRef()
# embedding_Ref = ModelsRef()

def upload_folder_to_s3(local_folder_path, bucket_name, s3_folder_path):
    s3_client = boto3.client('s3')
    for root, dirs, files in os.walk(local_folder_path):
        for file in files:
            local_file_path = os.path.join(root, file)
            s3_file_path = os.path.join(s3_folder_path, local_file_path)
            s3_client.upload_file(local_file_path, bucket_name, s3_file_path)


def upload_folder_to_s3_by_tar(local_folder_path, bucket_name, s3_folder_path):
    tar_name = f"{os.path.basename(local_folder_path)}.tar"
    # os.system(f'tar cvf {tar_name} {local_folder_path}')
    tar(mode='c', archive=tar_name, sfiles=local_folder_path, verbose=True)
    # tar = tarfile.open(tar_path, "w:gz")
    # for root, dirs, files in os.walk(local_folder_path):
    #     for file in files:
    #         local_file_path = os.path.join(root, file)
    #         tar.add(local_file_path)
    # tar.close()
    s3_client = boto3.client('s3')
    s3_client.upload_file(tar_name, bucket_name, os.path.join(s3_folder_path, tar_name))
    # os.system(f"rm {tar_name}")
    rm(tar_name, recursive=True)


def upload_file_to_s3(file_name, bucket, directory=None, object_name=None):
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Add the directory to the object_name
    if directory:
        object_name = f"{directory}/{object_name}"

    # Upload the file
    try:
        s3_client = boto3.client('s3')
        s3_client.upload_file(file_name, bucket, object_name)
        print(f"File {file_name} uploaded to {bucket}/{object_name}")
    except Exception as e:
        print(f"Error occurred while uploading {file_name} to {bucket}/{object_name}: {e}")
        return False
    return True

def upload_file_to_s3_by_presign_url(local_path, s3_presign_url):
    response = requests.put(s3_presign_url, open(local_path, "rb"))
    response.raise_for_status()

def upload_multipart_files_to_s3_by_signed_url(local_path, signed_urls, part_size):
    integral_uploaded = False
    with open(local_path, "rb") as f:
        parts = []
        try:
            for i, signed_url in enumerate(signed_urls):
                file_data = f.read(part_size)
                response = requests.put(signed_url, data=file_data)
                response.raise_for_status()
                etag = response.headers['ETag']
                parts.append({
                    'ETag': etag,
                    'PartNumber': i + 1
                })
                print(f'model upload part {i+1}: {response}')

            integral_uploaded = True
            return parts
        except Exception as e:
            print(e)
            gr.Error(f'Upload file{local_path} failed, please try again. If still not work, contact your admin')
        finally:
            if not integral_uploaded:
                gr.Error(f'Upload file {local_path} not complete, please try again or create new one.')
                raise Exception('failed at multipart')


def download_folder_from_s3(bucket_name, s3_folder_path, local_folder_path):
    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(bucket_name)
    for obj in bucket.objects.filter(Prefix=s3_folder_path):
        obj_dirname = os.sep.join(os.path.dirname(obj.key).split("/")[1:])
        obj_basename = os.path.basename(obj.key)
        local_sub_folder_path = os.path.join(local_folder_path, obj_dirname)
        if not os.path.exists(local_sub_folder_path):
            os.makedirs(local_sub_folder_path)
        bucket.download_file(obj.key, os.path.join(local_sub_folder_path, obj_basename))  # save to same path


def download_folder_from_s3_by_tar(bucket_name, s3_tar_path, local_tar_path, target_dir="."):
    s3_client = boto3.client('s3')
    s3_client.download_file(bucket_name, s3_tar_path, local_tar_path)
    # tar_name = os.path.basename(s3_tar_path)
    # os.system(f"tar xvf {local_tar_path} -C {target_dir}")
    tar(mode='x', archive=local_tar_path, verbose=True, change_dir=target_dir)
    # tar = tarfile.open(local_tar_path, "r")
    # tar.extractall()
    # tar.close()
    # os.system(f"rm {local_tar_path}")
    rm(local_tar_path, recursive=True)


def download_file_from_s3(bucket_name, s3_file_path, local_file_path):
    s3_client = boto3.client('s3')
    s3_client.download_file(bucket_name, s3_file_path, local_file_path)


def get_bucket_name_from_s3_url(s3_path) -> str:
    o = urlparse(s3_path, allow_fragments=False)
    return o.netloc

def get_bucket_name_from_s3_path(s3_path) -> str:
    s3_path = s3_path.replace("s3://", "")
    return s3_path.split("/")[0]

def get_path_from_s3_path(s3_path) -> str:
    s3_path = s3_path.replace("s3://", "")
    return "/".join(s3_path.split("/")[1:])

def split_s3_path(s3_path):
    path_parts = s3_path.replace("s3://", "").split("/")
    bucket = path_parts.pop(0)
    key = "/".join(path_parts)
    return bucket, key


def read_from_s3(s3_path):
    s3 = boto3.client('s3')
    bucket, key = split_s3_path(s3_path)
    s3_resp = s3.get_object(
        Bucket=bucket,
        Key=key,
    )

    if s3_resp['ContentLength'] > 0:
        return s3_resp['Body'].read()

    raise Exception(f'no content for file {s3_path}')

def fast_upload(session, bucketname, s3dir, filelist, progress_func=None, workers=10):
    # timer = Timer()
    botocore_config = botocore.config.Config(max_pool_connections=workers)
    s3client = session.client('s3', config=botocore_config)
    transfer_config = s3transfer.TransferConfig(
        use_threads=True,
        max_concurrency=workers,
    )
    s3t = s3transfer.create_transfer_manager(s3client, transfer_config)
    # timer.record("init")
    for src in filelist:
        dst = os.path.join(s3dir, os.path.basename(src))
        s3t.upload(
            src, bucketname, dst,
            subscribers=[
                s3transfer.ProgressCallbackInvoker(progress_func),
            ] if progress_func else None,
        )
    s3t.shutdown()  # wait for all the upload tasks to finish
    # timer.record("upload")
    # print(timer.summary())

def save_variable_to_json(variable_name, variable_value, filename='sagemaker_ui.json'):
    data = {}

    if os.path.exists(filename):
        with open(filename, 'r') as json_file:
            data = json.load(json_file)

    data[variable_name] = variable_value

    with open(filename, 'w') as json_file:
        json.dump(data, json_file)

def get_variable_from_json(variable_name, filename='sagemaker_ui.json'):
    if not os.path.exists(filename):
        initial_data = {
            "api_gateway_url": "",
            "api_token": "",
            "username": ""
        }
        with open(filename, 'w') as json_file:
            json.dump(initial_data, json_file)

    with open(filename, 'r') as json_file:
        data = json.load(json_file)

    variable_value = data.get(variable_name)

    return variable_value


def host_url():
    return get_variable_from_json('api_gateway_url')


def api_key():
    return get_variable_from_json('api_token')


def is_gcr():
    api_url = get_variable_from_json('api_gateway_url')
    return api_url and '.execute-api.cn-' in api_url


def has_config():
    return host_url() and api_key()

"""
    Description: Below functions are used to replace existing shell command implementation with os.system method, which is not os agonostic and not recommended.
"""
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

def rm(path, force=False, recursive=False):
    """
    Description:
        Remove a file or directory.
    Args:
        path (str): Path of the file or directory to remove.
        force (bool): If True, ignore non-existent files and errors. Default is False.
        recursive (bool): If True, remove directories and their contents recursively. Default is False.
    Usage:
        # Remove the file
        rm(dst)
        # Remove a directory recursively
        rm("directory/path", recursive=True)
    """
    path_obj = Path(path)

    try:
        if path_obj.is_file() or (path_obj.is_symlink() and not path_obj.is_dir()):
            path_obj.unlink()
        elif path_obj.is_dir() and recursive:
            shutil.rmtree(path)
        elif path_obj.is_dir():
            raise ValueError("Cannot remove directory without recursive=True")
        else:
            raise ValueError("File or directory does not exist")
    except Exception as e:
        if not force:
            raise e

def cp(src, dst, recursive=False, dereference=False, preserve=True):
    """
    Description:
        Copy a file or directory from source path to destination path.
    Args:
        src (str): Source file or directory path.
        dst (str): Destination file or directory path.
        recursive (bool): If True, copy directory and its contents recursively. Default is False.
        dereference (bool): If True, always dereference symbolic links. Default is False.
        preserve (bool): If True, preserve file metadata. Default is True.
    Usage:
        src = "source/file/path.txt"
        dst = "destination/file/path.txt"

        # Copy the file
        cp(src, dst)

        # Copy a directory recursively and dereference symlinks
        cp("source/directory", "destination/directory", recursive=True, dereference=True)
    """
    src_path = Path(src)
    dst_path = Path(dst)
    try:
        if dereference:
            src_path = src_path.resolve()

        if src_path.is_dir() and recursive:
            if preserve:
                shutil.copytree(src_path, dst_path, copy_function=shutil.copy2, symlinks=not dereference)
            else:
                shutil.copytree(src_path, dst_path, symlinks=not dereference)
        elif src_path.is_file():
            if preserve:
                shutil.copy2(src_path, dst_path)
            else:
                shutil.copy(src_path, dst_path)
        else:
            raise ValueError("Source must be a file or a directory with recursive=True")
    except shutil.SameFileError:
        print("Source and destination represents the same file.")


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

def format_size(size, human_readable):
    if human_readable:
        for unit in ['B', 'K', 'M', 'G', 'T', 'P']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
    else:
        return str(size)

def df(show_all=False, human_readable=False):
    """
    Description:
        Get disk usage statistics.
    Args:
        show_all (bool): If True, include all filesystems. Default is False.
        human_readable (bool): If True, format sizes in human readable format. Default is False.
    Usage:
        filesystems = df(show_all=True, human_readable=True)
        for filesystem in filesystems:
            print(f"Filesystem: {filesystem['filesystem']}")
            print(f"Total: {filesystem['total']}")
            print(f"Used: {filesystem['used']}")
            print(f"Free: {filesystem['free']}")
            print(f"Percent: {filesystem['percent']}%")
            print(f"Mountpoint: {filesystem['mountpoint']}")
    """
    partitions = psutil.disk_partitions(all=show_all)
    result = []

    for partition in partitions:
        usage = psutil.disk_usage(partition.mountpoint)
        partition_info = {
            'filesystem': partition.device,
            'total': format_size(usage.total, human_readable),
            'used': format_size(usage.used, human_readable),
            'free': format_size(usage.free, human_readable),
            'percent': usage.percent,
            'mountpoint': partition.mountpoint,
        }
        result.append(partition_info)

    return result

if __name__ == '__main__':
    import sys

    # upload_file_to_s3(sys.argv[1], 'aws-gcr-csdc-atl-exp-us-west-2', sys.argv[2])
    # fast_upload(boto3.Session(), 'aws-gcr-csdc-atl-exp-us-west-2', sys.argv[2], [sys.argv[1]])
    download_folder_from_s3_by_tar('aws-gcr-csdc-atl-exp-us-west-2', 'aigc-webui-test-samples/samples.tar',
                                   'samples.tar')
