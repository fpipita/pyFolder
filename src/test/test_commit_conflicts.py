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

IFOLDER_NAME = 'TestCommitConflicts'
TEST_CONFIG = Setup ()

class TestCommitConflicts (unittest.TestCase):

    def setUp (self):
        os.makedirs (TEST_CONFIG.USERDATA_A['prefix'])
        
        self.cm_A = CfgManager (runfromtest=True, **TEST_CONFIG.USERDATA_A)
        self.cm_B = CfgManager (runfromtest=True, **TEST_CONFIG.USERDATA_B)

        self.pyFolder = pyFolder (self.cm_A, runfromtest=True)

        self.ifolderws = iFolderWS (self.cm_B)
        logging.getLogger ('suds.client').addHandler (NullHandler ())

        self.iFolderEntryType = \
            self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.ChangeEntryAction = \
            self.pyFolder.ifolderws.get_change_entry_action ()
        self.Rights = self.pyFolder.ifolderws.get_rights ()
        self.SearchOperation = self.pyFolder.ifolderws.get_search_operation ()
        self.SearchProperty = self.pyFolder.ifolderws.get_search_property ()

        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)

        time.sleep (TEST_CONFIG.WAIT_FOR_SIMIAS_TO_UPDATE)

        self.iFolderAsEntry = \
            self.pyFolder.ifolderws.get_ifolder_as_entry (self.iFolder.ID)

        ArrayOfiFolderUser = self.pyFolder.ifolderws.get_users_by_search (\
            self.SearchProperty.UserName, self.SearchOperation.Contains, \
                TEST_CONFIG.USERDATA_B['username'], 0, 1)

        if ArrayOfiFolderUser is not None:
            for iFolderUser in ArrayOfiFolderUser:
                self.pyFolder.ifolderws.add_member (\
                    self.iFolder.ID, iFolderUser.ID, self.Rights.ReadWrite)

        time.sleep (TEST_CONFIG.WAIT_FOR_SIMIAS_TO_UPDATE)

        self.pyFolder.checkout ()

    def tearDown (self):
        self.pyFolder.dbm = None
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        shutil.rmtree (TEST_CONFIG.USERDATA_A['prefix'], True)

    def test_add_directory_on_conflict (self):
        DirectoryName = 'test_add_directory_on_conflict'
        
        iFolderEntry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, DirectoryName, \
                self.iFolderEntryType.Directory)
        
        time.sleep (TEST_CONFIG.WAIT_FOR_SIMIAS_TO_UPDATE)

        LocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntry.Path)

        os.mkdir (LocalPath)

        self.pyFolder.commit ()
        
        time.sleep (TEST_CONFIG.WAIT_FOR_SIMIAS_TO_UPDATE)

        self.pyFolder.update ()

        ExpectedLocalPath = '{0}-{1}'.format (\
            LocalPath, TEST_CONFIG.USERDATA_A['username'])

        self.assertTrue (os.path.isdir (ExpectedLocalPath))
        self.assertTrue (os.path.isdir (LocalPath))

    def test_add_file_on_conflict (self):
        FileName = 'test_add_file_on_conflict'
        FileData = 'test_add_file_on_conflict'

        iFolderEntry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, FileName, \
                self.iFolderEntryType.File)
        
        time.sleep (TEST_CONFIG.WAIT_FOR_SIMIAS_TO_UPDATE)

        LocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntry.Path)

        with open (LocalPath, 'wb') as File:
            File.write (FileData)
            
        self.pyFolder.commit ()
        
        time.sleep (TEST_CONFIG.WAIT_FOR_SIMIAS_TO_UPDATE)

        self.pyFolder.update ()

        self.assertTrue (os.path.isfile ('{0}-{1}'.format (\
                    LocalPath, TEST_CONFIG.USERDATA_A['username'])))
        self.assertTrue (os.path.isfile (LocalPath))

if __name__ == '__main__':
    unittest.main ()
