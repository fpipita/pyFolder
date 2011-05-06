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

        self.cm_A = ConfigManager (runfromtest=True, **TEST_CONFIG.USERDATA[PRIMARY_USER])
        self.cm_B = ConfigManager (runfromtest=True, **TEST_CONFIG.USERDATA[SECONDARY_USER])

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
        EntryName = 'aFile'
        RemoteContent = 'something'
        LocalContent = '{0} else'.format (RemoteContent)

        Entry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, EntryName, self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        Handle = self.ifolderws.open_file_write (\
            self.iFolder.ID, Entry.ID, len (RemoteContent))

        self.ifolderws.write_file (Handle, base64.b64encode (RemoteContent))

        self.ifolderws.close_file (Handle)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        EntryLocalPath = self.pyFolder.add_prefix (\
            os.path.normpath (Entry.Path))

        with open (EntryLocalPath, 'wb') as File:
            File.write (LocalContent)

        self.pyFolder.update ()

        ConflictedEntryLocalPath = self.pyFolder.add_conflicted_suffix (\
            EntryLocalPath)

        self.assertTrue (os.path.isfile (EntryLocalPath))
        self.assertTrue (os.path.isfile (ConflictedEntryLocalPath))

        with open (ConflictedEntryLocalPath, 'rb') as File:
            self.assertEqual (File.readlines ()[0], LocalContent)

        with open (EntryLocalPath, 'rb') as File:
            self.assertEqual (File.readlines ()[0], RemoteContent)



    def test_add_on_conflict (self):
        EntryName = 'aFile'
        RemoteContent = 'something'
        LocalContent = '{0} else'.format (RemoteContent)

        Entry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, EntryName, self.Type.File)

        Handle = self.ifolderws.open_file_write (\
            self.iFolder.ID, Entry.ID, len (RemoteContent))

        self.ifolderws.write_file (Handle, base64.b64encode (RemoteContent))

        self.ifolderws.close_file (Handle)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        EntryLocalPath = self.pyFolder.add_prefix (\
            os.path.normpath (Entry.Path))

        with open (EntryLocalPath, 'wb') as File:
            File.write (LocalContent)

        self.pyFolder.update ()

        ConflictedEntryLocalPath = self.pyFolder.add_conflicted_suffix (\
            EntryLocalPath)

        self.assertTrue (os.path.isfile (EntryLocalPath))
        self.assertTrue (os.path.isfile (ConflictedEntryLocalPath))

        with open (ConflictedEntryLocalPath, 'rb') as File:
            self.assertEqual (File.readlines ()[0], LocalContent)

        with open (EntryLocalPath, 'rb') as File:
            self.assertEqual (File.readlines ()[0], RemoteContent)



    def test_delete_on_conflict (self):
        EntryName = 'aFile'
        LocalContent = 'something'

        Entry = self.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, EntryName, self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.ifolderws.delete_entry (self.iFolder.ID, Entry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        EntryLocalPath = self.pyFolder.add_prefix (\
            os.path.normpath (Entry.Path))

        with open (EntryLocalPath, 'wb') as File:
            File.write (LocalContent)

        self.pyFolder.update ()

        ConflictedEntryLocalPath = self.pyFolder.add_conflicted_suffix (\
            EntryLocalPath)

        self.assertTrue (os.path.isfile (ConflictedEntryLocalPath))

        with open (ConflictedEntryLocalPath, 'rb') as File:
            self.assertEqual (File.readlines ()[0], LocalContent)



    def test_delete_directory_on_local_changes (self):
        aDirectory = 'aDirectory'
        aFile = 'aFile'

        aDirectoryEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, aDirectory, \
                self.Type.Directory)

        aFileEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, aFile, \
                self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (\
            self.iFolder.ID, aDirectoryEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        aDirectoryPath = self.pyFolder.add_prefix (\
            os.path.normpath (aDirectoryEntry.Path))

        aFilePath = os.path.join (aDirectoryPath, aFile)

        with open (aFilePath, 'wb') as File:
            File.write ('something')

        self.pyFolder.update ()

        ConflictedaDirectoryPath = self.pyFolder.add_conflicted_suffix (\
            aDirectoryPath)
        ConflictedaFilePath = os.path.join (ConflictedaDirectoryPath, aFile)

        self.assertTrue (os.path.isdir (ConflictedaDirectoryPath))
        self.assertTrue (os.path.isfile (ConflictedaFilePath))



    def test_delete_directory_on_new_local_entries (self):
        aDirectory = 'aDirectory'
        aFile = 'aFile'

        aDirectoryEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, aDirectory, \
                self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (\
            self.iFolder.ID, aDirectoryEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        aDirectoryPath = self.pyFolder.add_prefix (\
            os.path.normpath (aDirectoryEntry.Path))

        aFilePath = os.path.join (aDirectoryPath, aFile)

        with open (aFilePath, 'wb') as File:
            File.write ('something')

        self.pyFolder.update ()

        ConflictedaDirectoryPath = self.pyFolder.add_conflicted_suffix (\
            aDirectoryPath)
        ConflictedaFilePath = os.path.join (ConflictedaDirectoryPath, aFile)

        self.assertTrue (os.path.isdir (ConflictedaDirectoryPath))
        self.assertTrue (os.path.isfile (ConflictedaFilePath))



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

        self.pyFolder.update ()

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

        self.pyFolder.update ()

        ConflictedaniFolderLocalPath = self.pyFolder.add_conflicted_suffix (\
            aniFolderLocalPath)

        ConflictedaFileLocalPath = os.path.join (\
            ConflictedaniFolderLocalPath, aFile)

        self.assertTrue (os.path.isdir (ConflictedaniFolderLocalPath))
        self.assertTrue (os.path.isfile (ConflictedaFileLocalPath))



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
