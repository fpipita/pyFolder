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
from core.config import ConfigManager



from suds import WebFault



from setup import *



IFOLDER_NAME = 'TestCommitConflicts'
TEST_CONFIG = Setup ()



class TestCommitConflicts (unittest.TestCase):



    def setUp (self):
        os.makedirs (TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'])

        self.cm_A = ConfigManager (
            runfromtest=True, **TEST_CONFIG.USERDATA[PRIMARY_USER])

        self.cm_B = ConfigManager (
            runfromtest=True, **TEST_CONFIG.USERDATA[SECONDARY_USER])

        self.pyFolder = pyFolder (self.cm_A, runmode=RUN_FROM_TEST)

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

        UserList = self.pyFolder.ifolderws.get_users_by_search (
            self.SearchProperty.UserName,
            self.SearchOperation.Contains,
            TEST_CONFIG.USERDATA[SECONDARY_USER]['username'], 
            0, 1)

        if UserList is not None:
            for User in UserList:
                self.pyFolder.ifolderws.add_member (
                    self.iFolder.ID,
                    User.ID,
                    self.Rights.ReadWrite)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.checkout ()



    def tearDown (self):
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        self.pyFolder.finalize ()
        shutil.rmtree (TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'], True)



    def test_add_directory_on_conflict (self):
        Name = 'foo'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.Directory)

        self.pyFolder.mkdir (Entry.Path)

        self.pyFolder.commit ()

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        ConflictedPath = self.pyFolder.add_conflicted_suffix (
            Entry.Path)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedPath))
        self.assertTrue (self.pyFolder.path_isdir (Entry.Path))



    def test_add_file_on_conflict (self):
        Name = 'foo'
        Content = 'something'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        self.pyFolder.touch (Entry.Path)
        self.pyFolder.write_file (Entry.Path, Content)

        self.pyFolder.commit ()

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)        

        self.pyFolder.update ()

        ConflictedPath = self.pyFolder.add_conflicted_suffix (Entry.Path)

        self.assertTrue (self.pyFolder.path_isfile (ConflictedPath))
        self.assertTrue (self.pyFolder.path_isfile (Entry.Path))



    def test_modify_file_on_update (self):
        FileA = 'FileA'
        FileB = 'FileB'
        Content = 'something'

        EntryA = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            FileA,
            self.Type.File)

        EntryB = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            FileB,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        TupleAbeforeCommit = self.pyFolder.dbm.get_entry (
            EntryA.iFolderID, EntryA.ID)

        TupleBbeforeCommit = self.pyFolder.dbm.get_entry (
            EntryB.iFolderID, EntryB.ID)

        Handle = self.ifolderws.open_file_read (EntryA.iFolderID, EntryA.ID)

        self.pyFolder.write_file (EntryA.Path, Content)
        self.pyFolder.write_file (EntryB.Path, Content)

        self.pyFolder.commit ()

        TupleAafterCommit = self.pyFolder.dbm.get_entry (
            EntryA.iFolderID, EntryA.ID)

        TupleBafterCommit = self.pyFolder.dbm.get_entry (
            EntryB.iFolderID, EntryB.ID)

        self.assertEqual (
            TupleAbeforeCommit['mtime'], TupleAafterCommit['mtime'])

        self.assertNotEqual (
            TupleBbeforeCommit['mtime'], TupleBafterCommit['mtime'])

        self.ifolderws.close_file (Handle)

        self.pyFolder.commit ()

        TupleAafterCommit = self.pyFolder.dbm.get_entry (
            EntryA.iFolderID, EntryA.ID)

        self.assertNotEqual (
            TupleAbeforeCommit['mtime'], TupleAafterCommit['mtime'])



    def test_add_file_on_parent_deletion (self):
        Parent = 'Parent'
        Child = 'Child'

        ParentEntry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Parent,
            self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        Path = os.path.join (ParentEntry.Path, Child)

        self.pyFolder.touch (Path)

        self.ifolderws.delete_entry (ParentEntry.iFolderID, ParentEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.commit ()

        ConflictedPath = self.pyFolder.add_conflicted_suffix (
            ParentEntry.Path)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedPath))

        ConflictedPath = os.path.join (ConflictedPath, Child)

        self.assertTrue (self.pyFolder.path_isfile (ConflictedPath))



    def test_add_directory_on_parent_deletion (self):
        Parent= 'Parent'
        Child = 'Child'

        ParentEntry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Parent,
            self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.ifolderws.delete_entry (ParentEntry.iFolderID, ParentEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        Path = os.path.join (ParentEntry.Path, Child)

        self.pyFolder.mkdir (Path)

        self.pyFolder.commit ()

        ConflictedPath = self.pyFolder.add_conflicted_suffix (
            ParentEntry.Path)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedPath))

        ConflictedPath = os.path.join (ConflictedPath, Child)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedPath))



    def test_delete_ifolder_on_local_changes (self):
        FileName = 'foo'
        iFolderName = 'bar'
        Content = 'something'

        iFolder = self.pyFolder.ifolderws.create_ifolder (iFolderName)

        iFolderEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (
            iFolder.ID)

        FileEntry = self.pyFolder.ifolderws.create_entry (
            iFolder.ID, iFolderEntry.ID, FileName, self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.pyFolder.write_file (FileEntry.Path, Content)

        self.pyFolder.ifolderws.delete_ifolder (iFolder.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.commit ()

        ConflictedPath = self.pyFolder.add_conflicted_suffix (
            iFolderName)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedPath))

        ConflictedPath = os.path.join (ConflictedPath, FileName)

        self.assertTrue (self.pyFolder.path_isfile (ConflictedPath))



    def test_delete_ifolder_on_new_local_files (self):
        FileName = 'foo'
        iFolderName = 'bar'

        iFolder = self.pyFolder.ifolderws.create_ifolder (iFolderName)

        iFolderEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (
            iFolder.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        Path = os.path.join (iFolderName, FileName)

        self.pyFolder.touch (Path)

        self.pyFolder.ifolderws.delete_ifolder (iFolder.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.commit ()

        ConflictedPath = self.pyFolder.add_conflicted_suffix (
            iFolderName)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedPath))

        ConflictedPath = os.path.join (ConflictedPath, FileName)

        self.assertTrue (self.pyFolder.path_isfile (ConflictedaPath))



    def test_write_on_read (self):
        EntryName = 'foo'
        Content = 'something'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            EntryName,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        Handle = self.ifolderws.open_file_read (
            self.iFolder.ID,
            Entry.ID)

        self.pyFolder.write_file (Entry.Path, Content)

        self.pyFolder.commit ()
        self.ifolderws.close_file (Handle)



    def test_write_on_write (self):
        EntryName = 'foo'
        Content = 'something'
        Size = 100

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            EntryName,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        Handle = self.ifolderws.open_file_write (
            self.iFolder.ID,
            Entry.ID,
            Size)

        self.pyFolder.write_file (Entry.Path, Content)

        self.pyFolder.commit ()
        self.ifolderws.close_file (Handle)



    def test_delete_nonexistent_file (self):
        Name = 'foo'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.ifolderws.delete_entry (
            Entry.iFolderID, Entry.ID)

        self.pyFolder.delete (Entry.Path)

        self.pyFolder.commit ()

        self.assertEquals (self.pyFolder.dbm.get_entry (
                Entry.iFolderID, Entry.ID), None)



    def test_delete_nonexistent_directory (self):
        Name = 'foo'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.ifolderws.delete_entry (
            Entry.iFolderID, Entry.ID)

        self.pyFolder.rmdir (Entry.Path)

        self.pyFolder.commit ()

        self.assertEquals (self.pyFolder.dbm.get_entry (
                Entry.iFolderID, Entry.ID), None)



    def test_modify_file_on_nonexistent_file (self):
        Name = 'foo'
        Content = 'something'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.ifolderws.delete_entry (
            Entry.iFolderID, Entry.ID)

        self.pyFolder.write_file (Entry.Path, Content)

        self.pyFolder.commit ()

        self.assertEquals (self.pyFolder.dbm.get_entry (
                Entry.iFolderID, Entry.ID), None)

        Path = self.pyFolder.add_conflicted_suffix (Entry.Path)

        self.assertTrue (self.pyFolder.path_isfile (Path))



if __name__ == '__main__':
    unittest.main ()
