import os
import tarfile
import shutil
from pathlib import Path
import psutil

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

    