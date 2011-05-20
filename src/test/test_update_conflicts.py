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



from setup import *



IFOLDER_NAME = 'TestUpdateConflicts'
TEST_CONFIG = Setup ()



class TestUpdateConflicts (unittest.TestCase):



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
            TEST_CONFIG.USERDATA[SECONDARY_USER]['username'], 0, 1)

        if UserList is not None:
            for User in UserList:
                self.pyFolder.ifolderws.add_member (\
                    self.iFolder.ID, User.ID, self.Rights.ReadWrite)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.checkout ()



    def tearDown (self):
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        self.pyFolder.finalize ()
        shutil.rmtree (TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'], True)



    def test_modify_on_conflict (self):
        Name = 'foo'
        RemoteContent = 'remote'
        LocalContent = 'local'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        Handle = self.ifolderws.open_file_write (
            self.iFolder.ID, Entry.ID, len (RemoteContent))

        self.ifolderws.write_file (Handle, base64.b64encode (RemoteContent))

        self.ifolderws.close_file (Handle)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        Path = os.path.join (IFOLDER_NAME, Name)
        self.pyFolder.write_file (Path, LocalContent)

        self.pyFolder.update ()

        ConflictedPath = self.pyFolder.add_conflicted_suffix (Path)

        self.assertTrue (self.pyFolder.path_isfile (Path))
        self.assertTrue (self.pyFolder.path_isfile (ConflictedPath))

        self.assertEqual (
            self.pyFolder.readlines (ConflictedPath)[0],
            LocalContent)

        self.assertEqual (
            self.pyFolder.readlines (Path)[0],
            RemoteContent)



    def test_add_on_conflict (self):
        Name = 'foo'
        RemoteContent = 'remote'
        LocalContent = 'local'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        Handle = self.ifolderws.open_file_write (
            self.iFolder.ID, Entry.ID, len (RemoteContent))

        self.ifolderws.write_file (Handle, base64.b64encode (RemoteContent))

        self.ifolderws.close_file (Handle)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.touch (Entry.Path)
        self.pyFolder.write_file (Entry.Path, LocalContent)

        self.pyFolder.update ()
        ConflictedPath = self.pyFolder.add_conflicted_suffix (Entry.Path)

        self.assertTrue (self.pyFolder.path_isfile (Entry.Path))
        self.assertTrue (self.pyFolder.path_isfile (ConflictedPath))

        self.assertEqual (
            self.pyFolder.readlines (ConflictedPath)[0], LocalContent)

        self.assertEqual (
            self.pyFolder.readlines (Entry.Path)[0], RemoteContent)



    def test_delete_on_conflict (self):
        Name = 'foo'
        Content = 'something'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.ifolderws.delete_entry (self.iFolder.ID, Entry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.write_file (Entry.Path, Content)

        self.pyFolder.update ()

        ConflictedPath = self.pyFolder.add_conflicted_suffix (Entry.Path)

        self.assertTrue (self.pyFolder.path_isfile (ConflictedPath))

        self.assertEqual (
            self.pyFolder.readlines (ConflictedPath)[0], Content)



    def test_delete_directory_on_local_changes (self):
        DirectoryName = 'foo'
        FileName = 'bar'
        Content = 'something'

        DirectoryEntry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            DirectoryName,
            self.Type.Directory)

        FileEntry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            DirectoryEntry.ID,
            FileName,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.pyFolder.write_file (FileEntry.Path, Content)

        self.pyFolder.ifolderws.delete_entry (
            self.iFolder.ID, DirectoryEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        ConflictedDirectoryPath = self.pyFolder.add_conflicted_suffix (
            DirectoryEntry.Path)
        ConflictedFilePath = os.path.join (ConflictedDirectoryPath, FileName)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedDirectoryPath))
        self.assertTrue (self.pyFolder.path_isfile (ConflictedFilePath))



    def test_delete_directory_on_new_local_entries (self):
        DirectoryName = 'foo'
        FileName = 'bar'
        Content = 'something'

        DirectoryEntry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            DirectoryName,
            self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (
            self.iFolder.ID, DirectoryEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        Path = os.path.join (DirectoryEntry.Path, FileName)

        self.pyFolder.touch (Path)

        self.pyFolder.write_file (Path, Content)

        self.pyFolder.update ()

        ConflictedDirectoryPath = self.pyFolder.add_conflicted_suffix (
            DirectoryEntry.Path)
        ConflictedFilePath = os.path.join (ConflictedDirectoryPath, FileName)

        self.assertTrue (self.pyFolder.path_isdir (ConflictedDirectoryPath))
        self.assertTrue (self.pyFolder.path_isfile (ConflictedFilePath))



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

        self.pyFolder.update ()

        ConflictediFolderPath = self.pyFolder.add_conflicted_suffix (
            iFolder.Name)

        ConflictedFilePath = os.path.join (ConflictediFolderPath, FileName)

        self.assertTrue (self.pyFolder.path_isdir (ConflictediFolderPath))
        self.assertTrue (self.pyFolder.path_isfile (ConflictedFilePath))



    def test_delete_ifolder_on_new_local_files (self):
        FileName = 'foo'
        iFolderName = 'bar'

        iFolder = self.pyFolder.ifolderws.create_ifolder (iFolderName)
        iFolderEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (
            iFolder.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.pyFolder.touch (os.path.join (iFolderName, FileName))

        self.pyFolder.ifolderws.delete_ifolder (iFolder.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        ConflictediFolderPath = self.pyFolder.add_conflicted_suffix (
            iFolder.Name)

        ConflictedFilePath = os.path.join (ConflictediFolderPath, FileName)

        self.assertTrue (self.pyFolder.path_isdir (ConflictediFolderPath))
        self.assertTrue (self.pyFolder.path_isfile (ConflictedFilePath))



    def test_read_on_read (self):

        EntryName = 'foo'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID, 
            self.iFolderEntry.ID,
            EntryName,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        Handle = self.ifolderws.open_file_read (
            self.iFolder.ID, 
            Entry.ID)

        self.pyFolder.update ()

        self.ifolderws.close_file (Handle)



    def test_read_on_write (self):

        EntryName = 'foo'
        Size = 100

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            EntryName,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        Handle = self.ifolderws.open_file_write (
            self.iFolder.ID,
            Entry.ID,
            Size)

        self.pyFolder.update ()

        self.ifolderws.close_file (Handle)



    def test_delete_file_within_locally_deleted_directory (self):
        Name = 'foo'

        Parent = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.Directory)

        Child = self.ifolderws.create_entry (
            self.iFolder.ID,
            Parent.ID,
            Name,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.pyFolder.rmdir (Parent.Path)

        self.ifolderws.delete_entry (
            Parent.iFolderID, Parent.ID)

        self.pyFolder.update ()

        self.assertEquals (self.pyFolder.dbm.get_entry (
                Parent.iFolderID, Parent.ID), None)



    def test_add_file_within_locally_deleted_directory (self):
        Name = 'foo'

        Parent = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.pyFolder.rmdir (Parent.Path)

        Child = self.ifolderws.create_entry (
            self.iFolder.ID,
            Parent.ID,
            Name,
            self.Type.File)

        self.pyFolder.update ()

        self.assertEqual (self.pyFolder.dbm.get_entry (
                Parent.iFolderID, Parent.ID), None)

        self.pyFolder.update ()

        self.assertNotEqual (self.pyFolder.dbm.get_entry (
                Parent.iFolderID, Parent.ID), None)

        self.assertNotEqual (self.pyFolder.dbm.get_entry (
                Child.iFolderID, Child.ID), None)



    def test_modify_file_on_locally_deleted_file (self):
        Name = 'foo'
        Content = 'something'

        Entry = self.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        Handle = self.ifolderws.open_file_write (
            Entry.iFolderID, Entry.ID, len (Content))

        self.ifolderws.write_file (Handle, base64.b64encode (Content))

        self.ifolderws.close_file (Handle)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.delete (Entry.Path)

        self.pyFolder.update ()

        Path = os.path.join (IFOLDER_NAME, Name)

        ExpectedDigest = self.pyFolder.md5_hash (Path)

        Digest = self.pyFolder.dbm.get_entry (
            Entry.iFolderID, Entry.ID)['digest']

        self.assertEqual (Digest, ExpectedDigest)



if __name__ == '__main__':
    unittest.main ()
