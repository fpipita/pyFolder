#-*- coding: utf-8 -*-



import base64
import datetime
import os
import shutil
import sys
import time
import unittest



sys.path.append ('../')



from pyFolder import *
from core.dbm import DBM
from core.config import ConfigManager



from suds import WebFault



from setup import *



IFOLDER_NAME = 'TestHelpers'
TEST_CONFIG = Setup ()



class TestHelpers (unittest.TestCase):



    def setUp (self):
        os.makedirs (TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'])

        self.cm = ConfigManager (
            runfromtest=True, **TEST_CONFIG.USERDATA[PRIMARY_USER])

        self.pyFolder = pyFolder (self.cm, runmode=RUN_FROM_TEST)
        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.iFolderEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (
            self.iFolder.ID)

        self.Type = self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.Action = self.pyFolder.ifolderws.get_change_entry_action ()

        self.pyFolder.checkout ()



    def tearDown (self):
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        self.pyFolder.finalize ()
        shutil.rmtree (TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'], True)



    def test_conflicted_suffix (self):
        Name = '/lol\\foo/bar/baz/file.exe.lol'
        Conflicted = self.pyFolder.add_conflicted_suffix (Name)

        self.assertTrue (self.pyFolder.is_conflicted_entry (Conflicted))
        self.assertFalse (self.pyFolder.is_conflicted_entry (Name))

        self.assertFalse (
            self.pyFolder.is_conflicted_entry (
                os.path.join (Conflicted, 'bar')))



    def test_has_conflicted_ancestors (self):
        Name = '/lol\\foo/bar/baz/file.exe.lol'
        Conflicted = self.pyFolder.add_conflicted_suffix (Name)

        self.assertTrue (
            self.pyFolder.has_conflicted_ancestors (
                os.path.join (Conflicted, 'bar')))



    def test_strip_invalid_characters (self):

        if sys.platform in [ 'win32', 'os2', 'os2emx' ]:
            return

        InvalidCharacters = [ '\\', ':', '*', '?', '\"', '<', '>', '|' ]
        Replacement = 'foo'
        InvalidPath = '/foo/bar/lol/{0}'
        ValidPath = InvalidPath.format (Replacement)

        for Char in InvalidCharacters:

            self.assertEqual (
                self.pyFolder.strip_invalid_characters (
                    InvalidPath.format (Char), Replacement), ValidPath)



    def test_get_directories (self):

        x = self.pyFolder.get_directories ()

        self.assertTrue (IFOLDER_NAME in x)

        x = self.pyFolder.get_directories (ExcludeiFolders=True)

        self.assertTrue (IFOLDER_NAME not in x)



    def test_get_files (self):

        x = self.pyFolder.get_files ()

        self.assertTrue (not len (x))

        FilePath = os.path.join (IFOLDER_NAME, 'bar')

        self.pyFolder.touch (FilePath)

        x = self.pyFolder.get_files ()

        self.assertTrue (FilePath in x)



    def test_add_prefix (self):
        ExpectedPath = self.pyFolder.add_prefix (IFOLDER_NAME)

        Path = self.pyFolder.add_prefix (IFOLDER_NAME)
        Path = self.pyFolder.add_prefix (Path)

        self.assertTrue (ExpectedPath, Path)




    def test_get_conflicted_entries (self):
        Plain = [os.path.join (IFOLDER_NAME, i) for i in ['a', 'b', 'c', 'd']]
        Conflicted = [self.pyFolder.add_conflicted_suffix (
                os.path.join (IFOLDER_NAME, i)) for i in ['e', 'f', 'g', 'h']]

        Dir = False

        for List in [Plain, Conflicted]:
            for Entry in List:

                if Dir:
                    self.pyFolder.mkdir (Entry)
                    Dir = False

                else:
                    self.pyFolder.touch (Entry)
                    Dir = True

        self.assertEqual (
            self.pyFolder.get_conflicted_entries ().sort (),
            Conflicted.sort ())

        ConflictedDir = os.path.join (IFOLDER_NAME, 'foo')
        ConflictedDir = self.pyFolder.add_conflicted_suffix (ConflictedDir)
        File = os.path.join (ConflictedDir, 'bar')

        self.pyFolder.mkdir (ConflictedDir)

        self.pyFolder.touch (File)

        self.assertTrue (File not in self.pyFolder.get_conflicted_entries ())


    def test_strip_conflicted_suffix (self):
        Name = 'bar.exe'
        ConflictedName = self.pyFolder.add_conflicted_suffix (Name)

        self.assertEquals (
            Name,
            self.pyFolder.strip_conflicted_suffix (ConflictedName))



    def test_should_method_be_logged (self):
        self.assertTrue (self.pyFolder.should_method_be_logged ('write_file'))
        self.assertFalse (self.pyFolder.should_method_be_logged ('write_file'))
        self.assertTrue (self.pyFolder.should_method_be_logged ('read_file'))
        self.assertFalse (self.pyFolder.should_method_be_logged ('read_file'))

        self.assertTrue (self.pyFolder.should_method_be_logged ('foo'))
        self.assertTrue (self.pyFolder.should_method_be_logged ('foo'))
        self.assertTrue (self.pyFolder.should_method_be_logged ('read_file'))
        self.assertFalse (self.pyFolder.should_method_be_logged ('read_file'))
        self.assertTrue (self.pyFolder.should_method_be_logged ('write_file'))
        self.assertFalse (self.pyFolder.should_method_be_logged ('write_file'))



    def test_filter_args (self):
        args = ['lol', 'fooooooooooooooooooooooooooooooooooa']
        printable_args = self.pyFolder.filter_args ('write_file', args)

        self.assertTrue (
            len (printable_args[1]) <= WRITE_FILE_PRINTABLE_ARGS_LIMIT)



if __name__ == '__main__':
    unittest.main ()
