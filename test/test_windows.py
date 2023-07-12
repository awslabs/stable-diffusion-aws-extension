import os
import shutil
import filecmp
import unittest
import errno
import stat
import psutil
import sys

# append the path to the utils module
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from windows import tar, rm, cp, mv, df

class TestTarFunction(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'test_tar_function'
        try:
            os.makedirs(self.test_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        os.chdir(self.test_dir)

        with open('file1.txt', 'w') as f:
            f.write('This is file1.')
        with open('file2.txt', 'w') as f:
            f.write('This is file2.')

    def tearDown(self):
        os.chdir('..')
        shutil.rmtree(self.test_dir)

    def test_tar_function(self):
        # Test creating a new archive with file list as input
        tar(mode='c', archive='archive.tar', sfiles=['file1.txt', 'file2.txt'])

        # Verify the archive was created
        self.assertTrue(os.path.exists('archive.tar'))

        # Create a folder for extracted files
        try:
            os.makedirs('extracted')
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # Test extracting files from the archive in test
        # assemble the path to the archive
        archive_path = os.path.join(os.getcwd(), 'archive.tar')
        tar(mode='x', archive=archive_path, change_dir='extracted')

        # Verify the files were extracted
        self.assertTrue(os.path.exists('extracted/file1.txt'))
        self.assertTrue(os.path.exists('extracted/file2.txt'))

        # Compare the original and extracted files
        self.assertTrue(filecmp.cmp('file1.txt', 'extracted/file1.txt'))
        self.assertTrue(filecmp.cmp('file2.txt', 'extracted/file2.txt'))

        # Test creating a folder name as input
        tar(mode='c', archive='archive2.tar', sfiles='extracted')

        # Verify the archive was created
        self.assertTrue(os.path.exists('archive2.tar'))

        # Create a folder for extracted files
        try:
            os.makedirs('extracted2')
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # Test extracting files from the archive in test
        # assemble the path to the archive
        archive_path = os.path.join(os.getcwd(), 'archive2.tar')
        tar(mode='x', archive=archive_path, change_dir='extracted2')

        # Verify the files were extracted
        self.assertTrue(os.path.exists('extracted2/extracted/file1.txt'))
        self.assertTrue(os.path.exists('extracted2/extracted/file2.txt'))

        # Compare the original and extracted files
        self.assertTrue(filecmp.cmp('file1.txt', 'extracted2/extracted/file1.txt'))
        self.assertTrue(filecmp.cmp('file2.txt', 'extracted2/extracted/file2.txt'))

class TestRmFunction(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'test_rm_function'
        os.makedirs(self.test_dir)
        os.chdir(self.test_dir)

        with open('file1.txt', 'w') as f:
            f.write('This is file1.')

        os.makedirs('dir1')
        with open('dir1/file2.txt', 'w') as f:
            f.write('This is file2 inside dir1.')

    def tearDown(self):
        os.chdir('..')
        shutil.rmtree(self.test_dir)

    def test_rm_file(self):
        rm('file1.txt')
        self.assertFalse(os.path.exists('file1.txt'))

    def test_rm_directory_without_recursive(self):
        with self.assertRaises(ValueError):
            rm('dir1')

    def test_rm_directory_with_recursive(self):
        rm('dir1', recursive=True)
        self.assertFalse(os.path.exists('dir1'))

    def test_rm_nonexistent_file_without_force(self):
        with self.assertRaises(ValueError):
            rm('nonexistent_file.txt')

    def test_rm_nonexistent_file_with_force(self):
        try:
            rm('nonexistent_file.txt', force=True)
        except ValueError:
            self.fail("rm() raised ValueError unexpectedly with force=True")

class TestCpFunction(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'test_cp_function'
        os.makedirs(self.test_dir)
        os.chdir(self.test_dir)

        with open('file1.txt', 'w') as f:
            f.write('This is file1.')

        os.makedirs('dir1')
        with open('dir1/file2.txt', 'w') as f:
            f.write('This is file2 inside dir1.')

    def tearDown(self):
        os.chdir('..')
        shutil.rmtree(self.test_dir)

    def test_cp_file(self):
        cp('file1.txt', 'file1_copy.txt')
        self.assertTrue(os.path.exists('file1_copy.txt'))

    def test_cp_directory_without_recursive(self):
        with self.assertRaises(ValueError):
            cp('dir1', 'dir1_copy')

    def test_cp_directory_with_recursive(self):
        cp('dir1', 'dir1_copy', recursive=True)
        self.assertTrue(os.path.exists('dir1_copy'))
        self.assertTrue(os.path.exists('dir1_copy/file2.txt'))

    def test_cp_dereference_symlink(self):
        os.symlink('file1.txt', 'file1_symlink.txt')
        cp('file1_symlink.txt', 'file1_dereferenced.txt', dereference=True)
        self.assertTrue(os.path.exists('file1_dereferenced.txt'))

    def test_cp_preserve_file_metadata(self):
        os.chmod('file1.txt', stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        cp('file1.txt', 'file1_preserved.txt', preserve=True)
        src_stat = os.stat('file1.txt')
        dst_stat = os.stat('file1_preserved.txt')
        self.assertEqual(src_stat.st_mode, dst_stat.st_mode)

    def test_cp_not_preserve_file_metadata(self):
        os.chmod('file1.txt', stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        cp('file1.txt', 'file1_not_preserved.txt', preserve=False)

        # Modify the file mode of the destination file
        os.chmod('file1_not_preserved.txt', stat.S_IRUSR | stat.S_IWUSR)

        src_stat = os.stat('file1.txt')
        dst_stat = os.stat('file1_not_preserved.txt')
        self.assertNotEqual(src_stat.st_mode, dst_stat.st_mode)

class TestMvFunction(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'test_mv_function'
        os.makedirs(self.test_dir)
        os.chdir(self.test_dir)

        with open('file1.txt', 'w') as f:
            f.write('This is file1.')

        os.makedirs('dir1')
        with open('dir1/file2.txt', 'w') as f:
            f.write('This is file2 inside dir1.')

    def tearDown(self):
        os.chdir('..')
        shutil.rmtree(self.test_dir)

    def test_rename_file(self):
        mv('file1.txt', 'file1_renamed.txt')
        self.assertFalse(os.path.exists('file1.txt'))
        self.assertTrue(os.path.exists('file1_renamed.txt'))

    def test_move_file_to_new_directory(self):
        os.makedirs('new_directory')
        mv('file1.txt', 'new_directory/file1.txt')
        self.assertFalse(os.path.exists('file1.txt'))
        self.assertTrue(os.path.exists('new_directory/file1.txt'))

    def test_move_directory(self):
        os.makedirs('destination_directory')
        mv('dir1', 'destination_directory/dir1')
        self.assertFalse(os.path.exists('dir1'))
        self.assertTrue(os.path.exists('destination_directory/dir1'))

    def test_force_move_overwrite_file(self):
        with open('existing_destination_file.txt', 'w') as f:
            f.write('This is the existing destination file.')

        mv('file1.txt', 'existing_destination_file.txt', force=True)
        self.assertFalse(os.path.exists('file1.txt'))
        self.assertTrue(os.path.exists('existing_destination_file.txt'))

    def test_force_move_overwrite_directory(self):
        os.makedirs('existing_destination_directory')
        with open('existing_destination_directory/file3.txt', 'w') as f:
            f.write('This is file3 inside the existing destination directory.')

        mv('dir1', 'existing_destination_directory', force=True)
        self.assertFalse(os.path.exists('dir1'))
        self.assertTrue(os.path.exists('existing_destination_directory'))
        self.assertTrue(os.path.exists('existing_destination_directory/file2.txt'))
        self.assertFalse(os.path.exists('existing_destination_directory/file3.txt'))

    def test_move_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            mv('nonexistent_file.txt', 'some_destination.txt')

    def test_move_file_to_existing_destination_without_force(self):
        with open('existing_destination_file.txt', 'w') as f:
            f.write('This is the existing destination file.')

        with self.assertRaises(FileExistsError):
            mv('file1.txt', 'existing_destination_file.txt')

class TestDfFunction(unittest.TestCase):
    def test_df_default_options(self):
        filesystems = df()
        for filesystem in filesystems:
            self.assertIsInstance(filesystem['filesystem'], str)
            self.assertIsInstance(filesystem['total'], str)
            self.assertIsInstance(filesystem['used'], str)
            self.assertIsInstance(filesystem['free'], str)
            self.assertIsInstance(filesystem['percent'], float)
            self.assertIsInstance(filesystem['mountpoint'], str)

    def test_df_show_all(self):
        filesystems_all = df(show_all=True)
        filesystems_default = df()
        self.assertGreaterEqual(len(filesystems_all), len(filesystems_default))

    def test_df_human_readable(self):
        filesystems = df(human_readable=True)
        for filesystem in filesystems:
            self.assertIsInstance(filesystem['filesystem'], str)
            self.assertIsInstance(filesystem['total'], str)
            self.assertIsInstance(filesystem['used'], str)
            self.assertIsInstance(filesystem['free'], str)
            self.assertIsInstance(filesystem['percent'], float)
            self.assertIsInstance(filesystem['mountpoint'], str)
            self.assertTrue(filesystem['total'][-1] in ['B', 'K', 'M', 'G', 'T', 'P'])
            self.assertTrue(filesystem['used'][-1] in ['B', 'K', 'M', 'G', 'T', 'P'])
            self.assertTrue(filesystem['free'][-1] in ['B', 'K', 'M', 'G', 'T', 'P'])

if __name__ == '__main__':
    unittest.main()