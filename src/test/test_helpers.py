#-*- coding: utf-8 -*-

import base64
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
        self.cm = ConfigManager (runfromtest=True, **TEST_CONFIG.USERDATA[PRIMARY_USER])
        self.pyFolder = pyFolder (self.cm, runfromtest=True)
        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.iFolderEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (\
            self.iFolder.ID)

        self.Type = self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.Action = self.pyFolder.ifolderws.get_change_entry_action ()

        self.pyFolder.checkout ()
        
    def tearDown (self):
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        self.pyFolder.finalize ()
        shutil.rmtree (TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'], True)

    def test_add_conflicted_suffix (self):
        aFile = '/lol\\foo/bar/baz/file.exe.lol'
        aDirectory = '/lol\\bar'
        Suffix = 'conflicted'

        self.assertEqual (\
            self.pyFolder.add_conflicted_suffix (aFile, Suffix), \
                '/lol\\foo/bar/baz/file.exe-{0}.lol'.format (Suffix))
        
        self.assertEqual (\
            self.pyFolder.add_conflicted_suffix (aDirectory, Suffix), \
                '/lol\\bar-{0}'.format (Suffix))
        
        aFile = '/lol/.bar'
        
        self.assertEqual (\
            self.pyFolder.add_conflicted_suffix (aFile, Suffix), \
                '/lol/.bar-{0}'.format (Suffix))
        
        aFile = '/lol/.bar.exe'
        
        self.assertEqual (\
            self.pyFolder.add_conflicted_suffix (aFile, Suffix), \
                '/lol/.bar-{0}.exe'.format (Suffix))
        
    def test_strip_invalid_characters (self):

        if sys.platform in [ 'win32', 'os2', 'os2emx' ]:
            return
        
        InvalidCharacters = [ '\\', ':', '*', '?', '\"', '<', '>', '|' ]
        Replacement = 'foo'
        InvalidPath = '/foo/bar/lol/{0}'
        ValidPath = InvalidPath.format (Replacement)
        
        for Char in InvalidCharacters:
            
            self.assertEqual (\
                self.pyFolder.strip_invalid_characters (\
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

if __name__ == '__main__':
    unittest.main ()
