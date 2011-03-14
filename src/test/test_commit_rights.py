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
from core.cfg_manager import CfgManager

from suds import WebFault

from setup import Setup

IFOLDER_NAME = 'TestCommitRights'
TEST_CONFIG = Setup ()

class TestCommitRights (unittest.TestCase):

    def setUp (self):
        os.makedirs (TEST_CONFIG.USERDATA_A['prefix'])
        
        self.cm_A = CfgManager (runfromtest=True, **TEST_CONFIG.USERDATA_A)
        self.cm_B = CfgManager (runfromtest=True, **TEST_CONFIG.USERDATA_B)

        self.pyFolder = pyFolder (self.cm_A, runfromtest=True)

        self.ifolderws = iFolderWS (self.cm_B)
        logging.getLogger ('suds.client').addHandler (NullHandler ())

        self.Type = self.ifolderws.get_ifolder_entry_type ()
        self.Action = self.ifolderws.get_change_entry_action ()
        self.Rights = self.ifolderws.get_rights ()
        self.SearchOperation = self.ifolderws.get_search_operation ()
        self.SearchProperty = self.ifolderws.get_search_property ()

        self.iFolder = self.ifolderws.create_ifolder (IFOLDER_NAME)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.iFolderEntry = self.ifolderws.get_ifolder_as_entry (\
            self.iFolder.ID)

        UserList = self.pyFolder.ifolderws.get_users_by_search (\
            self.SearchProperty.UserName, self.SearchOperation.Contains, \
                TEST_CONFIG.USERDATA_A['username'], 0, 1)

        self.USER_A = None

        if UserList is not None:
            for User in UserList:
                self.USER_A = User
                self.ifolderws.add_member (\
                    self.iFolder.ID, User.ID, self.Rights.ReadWrite)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.checkout ()

    def tearDown (self):
        self.pyFolder.dbm = None
        self.ifolderws.delete_ifolder (self.iFolder.ID)
        shutil.rmtree (TEST_CONFIG.USERDATA_A['prefix'], True)
        
    def test_add_file_on_read_only_rights (self):
        aFile = 'aFile'
        
        aFileLocalPath = self.pyFolder.add_prefix (IFOLDER_NAME)
        aFileLocalPath = os.path.join (aFileLocalPath, aFile)
        
        with open (aFileLocalPath, 'wb') as File:
            File.write ('something')
            
        self.ifolderws.set_member_rights (\
            self.iFolder.ID, self.USER_A.ID, self.Rights.ReadOnly)
            
        self.pyFolder.commit ()
        
        aFileEntry = self.ifolderws.get_entries_by_name (\
            self.iFolder.ID, self.iFolderEntry.ID, \
                self.SearchOperation.Contains, aFile, 0, 1)
        
        self.assertEqual (aFileEntry, None)
        
        aFileTuple = \
            self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (aFileLocalPath))
        
        self.assertEqual (aFileTuple, None)
        
    def test_add_directory_on_read_only_rights (self):
        aDirectory = 'aDirectory'
        
        aDirectoryLocalPath = self.pyFolder.add_prefix (IFOLDER_NAME)
        aDirectoryLocalPath = os.path.join (aDirectoryLocalPath, aDirectory)
        
        os.mkdir (aDirectoryLocalPath)
            
        self.ifolderws.set_member_rights (\
            self.iFolder.ID, self.USER_A.ID, self.Rights.ReadOnly)
            
        self.pyFolder.commit ()
        
        aDirectoryEntry = self.ifolderws.get_entries_by_name (\
            self.iFolder.ID, self.iFolderEntry.ID, \
                self.SearchOperation.Contains, aDirectory, 0, 1)
        
        self.assertEqual (aDirectoryEntry, None)
        
        aDirectoryTuple = \
            self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (aDirectoryLocalPath))
        
        self.assertEqual (aDirectoryTuple, None)
        
    def test_modify_file_on_read_only_rights (self):
        aFile = 'aFile'

        aFileEntry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, aFile, self.Type.File)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        self.pyFolder.update ()
        
        aFileLocalPath = self.pyFolder.add_prefix (IFOLDER_NAME)
        aFileLocalPath = os.path.join (aFileLocalPath, aFile)
        
        with open (aFileLocalPath, 'wb') as File:
            File.write ('something')
            
        self.ifolderws.set_member_rights (\
            self.iFolder.ID, self.USER_A.ID, self.Rights.ReadOnly)
            
        aFileTupleBeforeCommit = \
            self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (aFileLocalPath))

        self.pyFolder.commit ()
        
        aFileTupleAfterCommit = \
            self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (aFileLocalPath))
        
        self.assertEqual (aFileTupleBeforeCommit, aFileTupleAfterCommit)
        
    def test_modify_directory_on_read_only_rights (self):
        pass
    
    def test_delete_file_on_read_only_rights (self):
        aFile = 'aFile'

        aFileEntry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, aFile, self.Type.File)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        self.pyFolder.update ()
        
        aFileLocalPath = self.pyFolder.add_prefix (IFOLDER_NAME)
        aFileLocalPath = os.path.join (aFileLocalPath, aFile)
        
        os.remove (aFileLocalPath)
            
        self.ifolderws.set_member_rights (\
            self.iFolder.ID, self.USER_A.ID, self.Rights.ReadOnly)
            
        aFileTupleBeforeCommit = \
            self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (aFileLocalPath))

        self.pyFolder.commit ()
        
        aFileTupleAfterCommit = \
            self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (aFileLocalPath))
        
        self.assertEqual (aFileTupleBeforeCommit, aFileTupleAfterCommit)
        
    def test_delete_directory_on_read_only_rights (self):
        aDirectory = 'aDirectory'

        aDirectoryEntry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, aDirectory, self.Type.Directory)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        self.pyFolder.update ()
        
        aDirectoryLocalPath = self.pyFolder.add_prefix (IFOLDER_NAME)
        aDirectoryLocalPath = os.path.join (aDirectoryLocalPath, aDirectory)
        
        shutil.rmtree (aDirectoryLocalPath)
            
        self.ifolderws.set_member_rights (\
            self.iFolder.ID, self.USER_A.ID, self.Rights.ReadOnly)
            
        aDirectoryTupleBeforeCommit = \
            self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (aDirectoryLocalPath))

        self.pyFolder.commit ()
        
        aDirectoryTupleAfterCommit = \
            self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (aDirectoryLocalPath))
        
        self.assertEqual (\
            aDirectoryTupleBeforeCommit, aDirectoryTupleAfterCommit)

if __name__ == '__main__':
    unittest.main ()
