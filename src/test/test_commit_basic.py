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

IFOLDER_NAME = 'TestCommitBasic'
TEST_CONFIG = Setup ()

class TestCommitBasic (unittest.TestCase):

    def setUp (self):
        os.makedirs (TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'])

        self.cm = ConfigManager (runfromtest=True, **TEST_CONFIG.USERDATA[PRIMARY_USER])
        self.pyFolder = pyFolder (self.cm, runfromtest=True)

        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.iFolderAsEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (\
            self.iFolder.ID)

        self.iFolderEntryType = \
            self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.ChangeEntryAction = \
            self.pyFolder.ifolderws.get_change_entry_action ()
        self.SearchOperation = self.pyFolder.ifolderws.get_search_operation ()

        self.pyFolder.checkout ()

    def tearDown (self):
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        self.pyFolder.finalize ()
        shutil.rmtree (TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'], True)

    def test_is_new_local_directory (self):
        DirectoryName = 'test_is_new_local_directory'
        
        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, DirectoryName, \
                self.iFolderEntryType.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        self.assertFalse (self.pyFolder.is_new_local_directory (\
                iFolderEntry.iFolderID, os.path.normpath (iFolderEntry.Path)))
        
    def test_get_local_changes_on_file (self):
        FileName = 'test_get_local_changes_on_file'
        FileData = 'test_get_local_changes_on_file'
        
        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, FileName, \
                self.iFolderEntryType.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        EntryTuple = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)

        iFolderID = EntryTuple['ifolder']
        iFolderEntryID = EntryTuple['id']
        LocalPath = EntryTuple['localpath']
        Digest = EntryTuple['digest']

        Action, Type = \
            self.pyFolder.get_local_changes_on_entry (\
            iFolderID, iFolderEntryID, LocalPath, Digest)
        
        self.assertEqual (Action, None)
        self.assertEqual (Type, self.iFolderEntryType.File)

        PrefixedLocalPath = os.path.join (\
            TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'], iFolderEntry.Path)

        with open (PrefixedLocalPath, 'wb') as File:
            File.write (FileData)
        
        Action, Type = \
            self.pyFolder.get_local_changes_on_entry (\
            iFolderID, iFolderEntryID, LocalPath, Digest)
        
        self.assertEqual (Action, self.ChangeEntryAction.Modify)
        self.assertEqual (Type, self.iFolderEntryType.File)
        
        os.remove (PrefixedLocalPath)
        
        Action, Type = \
            self.pyFolder.get_local_changes_on_entry (\
            iFolderID, iFolderEntryID, LocalPath, Digest)

        self.assertEqual (Action, self.ChangeEntryAction.Delete)
        self.assertEqual (Type, self.iFolderEntryType.File)
        
    def test_add_file (self):
        FileName = 'File'
        
        FileLocalPath = os.path.join (\
            TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'], self.iFolder.Name)
        FileLocalPath = os.path.join (FileLocalPath, FileName)
        
        with open (FileLocalPath, 'wb') as File:
            File.write (FileName)
            
        self.pyFolder.commit ()
        
        ArrayOfiFolderEntry = self.pyFolder.ifolderws.get_entries_by_name (\
            self.iFolder.ID, self.iFolderAsEntry.ID, \
                self.SearchOperation.Contains, FileName, 0, 1)
        
        if ArrayOfiFolderEntry is None:
            self.fail ('ArrayOfiFolderEntry can\'t be of `NoneType\'')
            return
        
        iFolderEntry = ArrayOfiFolderEntry[0]
        ChangeEntry = self.pyFolder.ifolderws.get_latest_change (\
            iFolderEntry.iFolderID, iFolderEntry.ID)

        if ChangeEntry is None:
            self.fail ('ChangeEntry can\'t be of `NoneType\'')
            return

        FileTuple = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        if FileTuple is None:
            self.fail ('FileTuple can\'t be of `NoneType\'')
            return

        self.assertEqual (ChangeEntry.Time, FileTuple['mtime'])
        
    def test_modify_file (self):
        FileName = 'File'
        
        FileLocalPath = os.path.join (\
            TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'], self.iFolder.Name)
        FileLocalPath = os.path.join (FileLocalPath, FileName)
        
        with open (FileLocalPath, 'wb') as File:
            File.write (FileName)
            
        self.pyFolder.commit ()

        ArrayOfiFolderEntry = self.pyFolder.ifolderws.get_entries_by_name (\
            self.iFolder.ID, self.iFolderAsEntry.ID, \
                self.SearchOperation.Contains, FileName, 0, 1)
        
        if ArrayOfiFolderEntry is None:
            self.fail ('ArrayOfiFolderEntry can\'t be of `NoneType\'')
            return
        
        iFolderEntry = ArrayOfiFolderEntry[0]

        FileTupleBeforeModify = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        if FileTupleBeforeModify is None:
            self.fail ('FileTupleBeforeModify can\'t be of `NoneType\'')
            return

        with open (FileLocalPath, 'wb') as File:
            File.write ('{0}{1}'.format (FileName, FileName))

        self.pyFolder.commit ()
        
        FileTupleAfterModify = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        if FileTupleAfterModify is None:
            self.fail ('FileTupleAfterModify can\'t be of `NoneType\'')
            return

        self.assertNotEqual (\
            FileTupleBeforeModify['mtime'], FileTupleAfterModify['mtime'])
        self.assertNotEqual (\
            FileTupleBeforeModify['digest'], FileTupleAfterModify['digest'])
        
    def test_find_closest_ancestor_remotely_alive (self):
        Ancestor = 'Ancestor'
        Parent = 'Parent'
        Child = 'Child'
        
        AncestoriFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, Ancestor, \
                self.iFolderEntryType.Directory)
        
        ParentiFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, AncestoriFolderEntry.ID, Parent, \
                self.iFolderEntryType.Directory)
        
        ChildiFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, ParentiFolderEntry.ID, Child, \
                self.iFolderEntryType.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        ChildEntryTuple = self.pyFolder.dbm.get_entry (\
            self.iFolder.ID, ChildiFolderEntry.ID)

        PathToRename, iFolderEntry = \
            self.pyFolder.find_closest_ancestor_remotely_alive (\
            self.iFolder.ID, ChildEntryTuple['localpath'])
        
        self.assertEqual (PathToRename, os.path.normpath (\
                'TestCommitBasic/Ancestor/Parent/Child'))
        self.assertEqual (iFolderEntry.ID, ParentiFolderEntry.ID)
        
        self.pyFolder.ifolderws.delete_entry (\
            self.iFolder.ID, ParentiFolderEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        PathToRename, iFolderEntry = \
            self.pyFolder.find_closest_ancestor_remotely_alive (\
            self.iFolder.ID, ChildEntryTuple['localpath'])

        self.assertEqual (PathToRename, os.path.normpath (\
                'TestCommitBasic/Ancestor/Parent'))
        self.assertEqual (iFolderEntry.ID, AncestoriFolderEntry.ID)
        
        self.pyFolder.ifolderws.delete_entry (\
            self.iFolder.ID, AncestoriFolderEntry.ID)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        PathToRename, iFolderEntry = \
            self.pyFolder.find_closest_ancestor_remotely_alive (\
            self.iFolder.ID, ChildEntryTuple['localpath'])
        self.assertEqual (PathToRename, os.path.normpath (\
                'TestCommitBasic/Ancestor'))
        self.assertEqual (self.iFolderAsEntry.ID, iFolderEntry.ID)
        
    def test_add_locked_file (self):
        LockedFile = '.DS_Store'

        LockedFilePath = self.pyFolder.add_prefix (self.iFolder.Name)
        LockedFilePath = os.path.join (LockedFilePath, LockedFile)
        
        with open (LockedFilePath, 'wb') as File:
            File.write ('aString')
            
        self.pyFolder.commit ()
        
        EntryTuple = self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (\
            self.iFolder.ID, self.pyFolder.remove_prefix (LockedFilePath))
        
        self.assertEqual (EntryTuple, None)

    def test_file_entry_invalid_characters (self):

        if sys.platform in [ 'win32', 'os2', 'os2emx' ]:
            return

        InvalidEntries = []
        BaseName = 'foo{0}'

        for Char in ENTRY_INVALID_CHARS:
            InvalidEntry = BaseName.format (Char)

            InvalidEntryLocalPath = self.pyFolder.add_prefix (IFOLDER_NAME)
            InvalidEntryLocalPath = os.path.join (\
                InvalidEntryLocalPath, InvalidEntry)

            InvalidEntries.append (InvalidEntryLocalPath)

            with open (InvalidEntryLocalPath, 'wb') as File:
                File.write ('something')
        
        self.pyFolder.commit ()
        
        for InvalidEntry in InvalidEntries:
            ValidEntry = self.pyFolder.strip_invalid_characters (InvalidEntry)
            self.assertTrue (os.path.isfile (ValidEntry))

    def test_directory_entry_invalid_characters (self):

        if sys.platform in [ 'win32', 'os2', 'os2emx' ]:
            return

        InvalidEntries = []
        BaseName = 'foo{0}'

        for Char in ENTRY_INVALID_CHARS:
            InvalidEntry = BaseName.format (Char)

            InvalidEntryLocalPath = self.pyFolder.add_prefix (IFOLDER_NAME)
            InvalidEntryLocalPath = os.path.join (\
                InvalidEntryLocalPath, InvalidEntry)

            InvalidEntries.append (InvalidEntryLocalPath)

            os.mkdir (InvalidEntryLocalPath)
        
        self.pyFolder.commit ()
        
        for InvalidEntry in InvalidEntries:
            ValidEntry = self.pyFolder.strip_invalid_characters (InvalidEntry)
            self.assertTrue (os.path.isdir (ValidEntry))

if __name__ == '__main__':
   unittest.main ()
