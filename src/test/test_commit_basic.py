# -*- coding: utf-8 -*-

import base64
import os
import shutil
import sys
import time
import unittest

sys.path.append ('../')

from pyFolder import *
from support.dbm import DBM
from support.cfg_manager import CfgManager

from setup import Setup

IFOLDER_NAME = 'TestCommitBasic'
TEST_CONFIG = Setup ()

class TestCommitBasic (unittest.TestCase):

    def setUp (self):
        os.makedirs (TEST_CONFIG.USERDATA_A['prefix'])

        self.cm = CfgManager (runfromtest=True, **TEST_CONFIG.USERDATA_A)
        self.pyFolder = pyFolder (self.cm, runfromtest=True)

        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)

        time.sleep (TEST_CONFIG.WAIT_FOR_SIMIAS_TO_UPDATE)

        self.iFolderAsEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (\
            self.iFolder.ID)

        self.iFolderEntryType = \
            self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.ChangeEntryAction = \
            self.pyFolder.ifolderws.get_change_entry_action ()

        self.pyFolder.checkout ()

    def tearDown (self):
        self.pyFolder.dbm = None
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        shutil.rmtree (TEST_CONFIG.USERDATA_A['prefix'], True)

    def test_is_new_local_directory (self):
        DirectoryName = 'test_is_new_local_directory'
        
        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, DirectoryName, \
                self.iFolderEntryType.Directory)

        time.sleep (TEST_CONFIG.WAIT_FOR_SIMIAS_TO_UPDATE)
        
        self.pyFolder.update ()
        
        self.assertFalse (self.pyFolder.is_new_local_directory (\
                iFolderEntry.iFolderID, os.path.normpath (iFolderEntry.Path)))
        
    def test_get_local_changes_on_file (self):
        FileName = 'test_get_local_changes_on_file'
        FileData = 'test_get_local_changes_on_file'
        
        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, FileName, \
                self.iFolderEntryType.File)
        
        time.sleep (TEST_CONFIG.WAIT_FOR_SIMIAS_TO_UPDATE)
        
        self.pyFolder.update ()
        
        EntryTuple = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)

        iFolderID = EntryTuple['ifolder']
        iFolderEntryID = EntryTuple['id']
        LocalPath = EntryTuple['localpath']
        Digest = EntryTuple['digest']

        Action, Type = \
            self.pyFolder.get_local_changes_on_entry (\
            iFolderID, iFolderEntryID, LocalPath, Digest, \
                self.iFolderEntryType, self.ChangeEntryAction)
        
        self.assertEqual (Action, None)
        self.assertEqual (Type, self.iFolderEntryType.File)

        PrefixedLocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntry.Path)

        with open (PrefixedLocalPath, 'wb') as File:
            File.write (FileData)
        
        Action, Type = \
            self.pyFolder.get_local_changes_on_entry (\
            iFolderID, iFolderEntryID, LocalPath, Digest, \
                self.iFolderEntryType, self.ChangeEntryAction)
        
        self.assertEqual (Action, self.ChangeEntryAction.Modify)
        self.assertEqual (Type, self.iFolderEntryType.File)
        
        os.remove (PrefixedLocalPath)
        
        Action, Type = \
            self.pyFolder.get_local_changes_on_entry (\
            iFolderID, iFolderEntryID, LocalPath, Digest, \
                self.iFolderEntryType, self.ChangeEntryAction)

        self.assertEqual (Action, self.ChangeEntryAction.Delete)
        self.assertEqual (Type, self.iFolderEntryType.File)
        
if __name__ == '__main__':
    unittest.main ()
