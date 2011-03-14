# -*- coding: utf-8 -*-

import base64
import os
import shutil
import sys
import time
import unittest

sys.path.append ('../')

from pyFolder import *
from core.dbm import DBM
from core.config import CfgManager

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

        self.Type = self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.Action = self.pyFolder.ifolderws.get_change_entry_action ()
        self.Rights = self.pyFolder.ifolderws.get_rights ()
        self.SearchOperation = self.pyFolder.ifolderws.get_search_operation ()
        self.SearchProperty = self.pyFolder.ifolderws.get_search_property ()

        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.iFolderEntry = \
            self.pyFolder.ifolderws.get_ifolder_as_entry (self.iFolder.ID)

        UserList = self.pyFolder.ifolderws.get_users_by_search (\
            self.SearchProperty.UserName, self.SearchOperation.Contains, \
                TEST_CONFIG.USERDATA_B['username'], 0, 1)

        if UserList is not None:
            for User in UserList:
                self.pyFolder.ifolderws.add_member (\
                    self.iFolder.ID, User.ID, self.Rights.ReadWrite)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.checkout ()

    def tearDown (self):
        self.pyFolder.dbm = None
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        shutil.rmtree (TEST_CONFIG.USERDATA_A['prefix'], True)

    def test_add_directory_on_conflict (self):
        DirectoryName = 'test_add_directory_on_conflict'
        
        Entry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, DirectoryName, \
                self.Type.Directory)
        
        LocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], Entry.Path)

        os.mkdir (LocalPath)

        self.pyFolder.commit ()
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        ExpectedLocalPath = self.pyFolder.add_conflicted_suffix (\
            LocalPath)

        self.assertTrue (os.path.isdir (ExpectedLocalPath))
        self.assertTrue (os.path.isdir (LocalPath))

    def test_add_file_on_conflict (self):
        FileName = 'test_add_file_on_conflict'
        FileData = 'test_add_file_on_conflict'

        Entry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, FileName, self.Type.File)
        
        LocalPath = os.path.join (TEST_CONFIG.USERDATA_A['prefix'], Entry.Path)

        with open (LocalPath, 'wb') as File:
            File.write (FileData)
            
        self.pyFolder.commit ()

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)        
        self.pyFolder.update ()

        ConflictedLocalPath = self.pyFolder.add_conflicted_suffix (\
            LocalPath)
        
        self.assertTrue (os.path.isfile (ConflictedLocalPath))
        self.assertTrue (os.path.isfile (LocalPath))
        
    def test_modify_file_on_update (self):
        FileA = 'FileA'
        FileB = 'FileB'

        EntryA = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, FileA, self.Type.File)

        EntryB = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, FileB, self.Type.File)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        TupleAbeforeCommit = self.pyFolder.dbm.get_entry (\
            EntryA.iFolderID, EntryA.ID)
        self.assertNotEqual (TupleAbeforeCommit, None)

        TupleBbeforeCommit = self.pyFolder.dbm.get_entry (\
            EntryB.iFolderID, EntryB.ID)
        self.assertNotEqual (TupleBbeforeCommit, None)

        Handle = self.ifolderws.open_file_read (EntryA.iFolderID, EntryA.ID)
        
        FileALocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], EntryA.Path)
        FileBLocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], EntryB.Path)

        with open (FileALocalPath, 'wb') as File:
            File.write (FileA)
            
        with open (FileBLocalPath, 'wb') as File:
            File.write (FileB)
            
        self.pyFolder.commit ()

        TupleAafterCommit = self.pyFolder.dbm.get_entry (\
            EntryA.iFolderID, EntryA.ID)
        TupleBafterCommit = self.pyFolder.dbm.get_entry (\
            EntryB.iFolderID, EntryB.ID)
        
        self.assertEqual (\
            TupleAbeforeCommit['mtime'], TupleAafterCommit['mtime'])
        self.assertNotEqual (\
            TupleBbeforeCommit['mtime'], TupleBafterCommit['mtime'])
        
        self.ifolderws.close_file (Handle)
        
        self.pyFolder.commit ()
        
        TupleAafterCommit = self.pyFolder.dbm.get_entry (\
            EntryA.iFolderID, EntryA.ID)
        
        self.assertNotEqual (\
            TupleAbeforeCommit['mtime'], TupleAafterCommit['mtime'])
    
    def test_add_file_on_parent_deletion (self):
        Parent = 'Parent'
        Child = 'Child'
        
        ParentEntry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, Parent, \
                self.Type.Directory)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        ParentPath = os.path.join (\
            self.pyFolder.add_prefix (IFOLDER_NAME), Parent)

        ChildPath = os.path.join (ParentPath, Child)

        with open (ChildPath, 'wb') as File:
            File.write (Child)
        
        self.ifolderws.delete_entry (ParentEntry.iFolderID, ParentEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        self.pyFolder.commit ()
        
        self.pyFolder.commit ()

        ConflictedParentPath = self.pyFolder.add_conflicted_suffix (ParentPath)
        ConflictedChildPath = os.path.join (ConflictedParentPath, Child)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedParentPath))
        self.assertTrue (self.pyFolder.path_isfile (ConflictedChildPath))
        
        EntryTuple = self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (ConflictedChildPath))
        
        self.assertNotEqual (EntryTuple, None)

        Head, Tail = os.path.split (ConflictedParentPath)

        EntryList = self.pyFolder.ifolderws.get_entries_by_name (\
            self.iFolder.ID, self.iFolderEntry.ID, \
                self.SearchOperation.Contains, Tail, 0, 1)
        
        self.assertNotEqual (EntryList, None)

        ConflictedParentEntry = EntryList[0]

        Head, Tail = os.path.split (ConflictedChildPath)

        EntryList = self.pyFolder.ifolderws.get_entries_by_name (\
            self.iFolder.ID, ConflictedParentEntry.ID, \
                self.SearchOperation.Contains, Tail, 0, 1)
        
        self.assertNotEqual (EntryList, None)

    def test_add_directory_on_parent_deletion (self):
        Parent= 'Parent'
        Child = 'Child'
        
        ParentEntry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, Parent, \
                self.Type.Directory)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        self.ifolderws.delete_entry (ParentEntry.iFolderID, ParentEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        ParentPath = os.path.join (\
            self.pyFolder.add_prefix (IFOLDER_NAME), Parent)

        ChildPath = os.path.join (ParentPath, Child)

        self.pyFolder.mkdir (ChildPath)
        
        self.pyFolder.commit ()
        
        self.pyFolder.commit ()

        ConflictedParentPath = self.pyFolder.add_conflicted_suffix (ParentPath)
        ConflictedChildPath = os.path.join (ConflictedParentPath, Child)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedParentPath))
        self.assertTrue (self.pyFolder.path_isdir (ConflictedChildPath))
        
        EntryTuple = self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (ConflictedChildPath))
        
        self.assertNotEqual (EntryTuple, None)

        Head, Tail = os.path.split (ConflictedParentPath)
        
        EntryList = self.pyFolder.ifolderws.get_entries_by_name (\
            self.iFolder.ID, self.iFolderEntry.ID, \
                self.SearchOperation.Contains, Tail, 0, 1)
        
        self.assertNotEqual (EntryList, None)

        ConflictedParentEntry = EntryList[0]
        
        Head, Tail = os.path.split (ConflictedChildPath)

        EntryList = self.pyFolder.ifolderws.get_entries_by_name (\
            self.iFolder.ID, ConflictedParentEntry.ID, \
                self.SearchOperation.Contains, Tail, 0, 1)
        
        self.assertNotEqual (EntryList, None)

    def test_delete_ifolder_on_local_changes (self):
        aFile = 'aFile'
        iFolderName = 'anIfolder'
        
        aniFolder = self.pyFolder.ifolderws.create_ifolder (iFolderName)
        aniFolderEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (\
            aniFolder.ID)
        
        aFileEntry = self.pyFolder.ifolderws.create_entry (\
            aniFolder.ID, aniFolderEntry.ID, aFile, self.Type.File)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        aniFolderLocalPath = self.pyFolder.add_prefix (aniFolder.Name)
        aFileLocalPath = os.path.join (aniFolderLocalPath, aFile)
        
        with open (aFileLocalPath, 'wb') as File:
            File.write ('aString')
            
        self.pyFolder.ifolderws.delete_ifolder (aniFolder.ID)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        self.pyFolder.commit ()
        
        ConflictedaniFolderLocalPath = self.pyFolder.add_conflicted_suffix (\
            aniFolderLocalPath)
        
        ConflictedaFileLocalPath = os.path.join (\
            ConflictedaniFolderLocalPath, aFile)

        self.assertTrue (os.path.isdir (ConflictedaniFolderLocalPath))
        self.assertTrue (os.path.isfile (ConflictedaFileLocalPath))
        
    def test_delete_ifolder_on_new_local_files (self):
        aFile = 'aFile'
        iFolderName = 'anIfolder'
        
        aniFolder = self.pyFolder.ifolderws.create_ifolder (iFolderName)
        aniFolderEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (\
            aniFolder.ID)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()
        
        aniFolderLocalPath = self.pyFolder.add_prefix (aniFolder.Name)
        aFileLocalPath = os.path.join (aniFolderLocalPath, aFile)
        
        with open (aFileLocalPath, 'wb') as File:
            File.write ('aString')

        self.pyFolder.ifolderws.delete_ifolder (aniFolder.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        self.pyFolder.commit ()
        
        ConflictedaniFolderLocalPath = self.pyFolder.add_conflicted_suffix (\
            aniFolderLocalPath)
        
        ConflictedaFileLocalPath = os.path.join (\
            ConflictedaniFolderLocalPath, aFile)

        self.assertTrue (os.path.isdir (ConflictedaniFolderLocalPath))
        self.assertTrue (os.path.isfile (ConflictedaFileLocalPath))
        
if __name__ == '__main__':
    unittest.main ()
