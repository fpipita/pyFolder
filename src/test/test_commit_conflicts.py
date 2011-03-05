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
from support.policy import CONFLICTED_SUFFIX

from suds import WebFault
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

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.iFolderAsEntry = \
            self.pyFolder.ifolderws.get_ifolder_as_entry (self.iFolder.ID)

        ArrayOfiFolderUser = self.pyFolder.ifolderws.get_users_by_search (\
            self.SearchProperty.UserName, self.SearchOperation.Contains, \
                TEST_CONFIG.USERDATA_B['username'], 0, 1)

        if ArrayOfiFolderUser is not None:
            for iFolderUser in ArrayOfiFolderUser:
                self.pyFolder.ifolderws.add_member (\
                    self.iFolder.ID, iFolderUser.ID, self.Rights.ReadWrite)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

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
        
        LocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntry.Path)

        os.mkdir (LocalPath)

        self.pyFolder.commit ()
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
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
        
        LocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntry.Path)

        with open (LocalPath, 'wb') as File:
            File.write (FileData)
            
        self.pyFolder.commit ()

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)        
        self.pyFolder.update ()

        self.assertTrue (os.path.isfile ('{0}-{1}'.format (\
                    LocalPath, TEST_CONFIG.USERDATA_A['username'])))
        self.assertTrue (os.path.isfile (LocalPath))
        
    def test_modify_file_on_update (self):
        FileA = 'FileA'
        FileB = 'FileB'

        iFolderEntryA = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, FileA, \
                self.iFolderEntryType.File)

        iFolderEntryB = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, FileB, \
                self.iFolderEntryType.File)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        TupleAbeforeCommit = self.pyFolder.dbm.get_entry (\
            iFolderEntryA.iFolderID, iFolderEntryA.ID)
        self.assertNotEqual (TupleAbeforeCommit, None)

        TupleBbeforeCommit = self.pyFolder.dbm.get_entry (\
            iFolderEntryB.iFolderID, iFolderEntryB.ID)
        self.assertNotEqual (TupleBbeforeCommit, None)

        Handle = self.ifolderws.open_file_read (\
            iFolderEntryA.iFolderID, iFolderEntryA.ID)
        
        FileALocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntryA.Path)
        FileBLocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntryB.Path)

        with open (FileALocalPath, 'wb') as File:
            File.write (FileA)
            
        with open (FileBLocalPath, 'wb') as File:
            File.write (FileB)
            
        self.pyFolder.commit ()

        TupleAafterCommit = self.pyFolder.dbm.get_entry (\
            iFolderEntryA.iFolderID, iFolderEntryA.ID)
        TupleBafterCommit = self.pyFolder.dbm.get_entry (\
            iFolderEntryB.iFolderID, iFolderEntryB.ID)
        
        self.assertEqual (\
            TupleAbeforeCommit['mtime'], TupleAafterCommit['mtime'])
        self.assertNotEqual (\
            TupleBbeforeCommit['mtime'], TupleBafterCommit['mtime'])
        
        self.ifolderws.close_file (Handle)
        
        self.pyFolder.commit ()
        
        TupleAafterCommit = self.pyFolder.dbm.get_entry (\
            iFolderEntryA.iFolderID, iFolderEntryA.ID)
        
        self.assertNotEqual (\
            TupleAbeforeCommit['mtime'], TupleAafterCommit['mtime'])
    
    def test_add_file_on_parent_deletion (self):
        Parent = 'Parent'
        Child = 'Child'
        
        iFolderEntryDirectory = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, Parent, \
                self.iFolderEntryType.Directory)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        ChildPath = os.path.join (os.path.join (IFOLDER_NAME, Parent), Child)
        ChildPath = os.path.join (TEST_CONFIG.USERDATA_A['prefix'], ChildPath)
        with open (ChildPath, 'wb') as File:
            File.write (Child)
        
        self.ifolderws.delete_entry (\
            iFolderEntryDirectory.iFolderID, \
                iFolderEntryDirectory.ID, None, None)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        self.pyFolder.commit ()

        ConflictedParentPath = os.path.join (IFOLDER_NAME, Parent)
        ConflictedParentPath = \
            '{0}-{1}'.format (ConflictedParentPath, CONFLICTED_SUFFIX)
        
        ConflictedChildPath = os.path.join (ConflictedParentPath, Child)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedParentPath))
        self.assertTrue (self.pyFolder.path_isfile (ConflictedChildPath))
        
        iFolderEntryTuple = \
            self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, ConflictedChildPath)
        
        self.assertNotEqual (iFolderEntryTuple, None)

        Head, Tail = os.path.split (ConflictedParentPath)

        ArrayOfiFolderEntry = self.pyFolder.ifolderws.get_entries_by_name (\
            self.iFolder.ID, self.iFolderAsEntry.ID, \
                self.SearchOperation.Contains, Tail, 0, 1)
        
        self.assertNotEqual (ArrayOfiFolderEntry, None)

        ConflictedParentEntry = ArrayOfiFolderEntry[0]

        Head, Tail = os.path.split (ConflictedChildPath)

        ArrayOfiFolderEntry = self.pyFolder.ifolderws.get_entries_by_name (\
            self.iFolder.ID, ConflictedParentEntry.ID, \
                self.SearchOperation.Contains, Tail, 0, 1)
        
        self.assertNotEqual (ArrayOfiFolderEntry, None)

    def test_add_directory_on_parent_deletion (self):
        Parent= 'Parent'
        Child = 'Child'
        
        ParentEntry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, Parent, \
                self.iFolderEntryType.Directory)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        self.ifolderws.delete_entry (\
            ParentEntry.iFolderID, \
                ParentEntry.ID, None, None)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        ChildPath = os.path.join (os.path.join (IFOLDER_NAME, Parent), Child)
        self.pyFolder.mkdir (ChildPath)
        
        self.pyFolder.commit ()

        ConflictedParentPath = os.path.join (IFOLDER_NAME, Parent)
        ConflictedParentPath = '{0}-{1}'.format (\
            ConflictedParentPath, CONFLICTED_SUFFIX)
        
        ConflictedChildPath = os.path.join (ConflictedParentPath, Child)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedParentPath))
        self.assertTrue (self.pyFolder.path_isdir (ConflictedChildPath))
        
        iFolderEntryTuple = \
            self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, ConflictedChildPath)
        
        self.assertNotEqual (iFolderEntryTuple, None)

        Head, Tail = os.path.split (ConflictedParentPath)
        
        ArrayOfiFolderEntry = self.pyFolder.ifolderws.get_entries_by_name (\
            self.iFolder.ID, self.iFolderAsEntry.ID, \
                self.SearchOperation.Contains, Tail, 0, 1)
        
        self.assertNotEqual (ArrayOfiFolderEntry, None)

        ConflictedParentEntry = ArrayOfiFolderEntry[0]
        
        Head, Tail = os.path.split (ConflictedChildPath)

        ArrayOfiFolderEntry = self.pyFolder.ifolderws.get_entries_by_name (\
            self.iFolder.ID, ConflictedParentEntry.ID, \
                self.SearchOperation.Contains, Tail, 0, 1)
        
        self.assertNotEqual (ArrayOfiFolderEntry, None)
        
if __name__ == '__main__':
    unittest.main ()
