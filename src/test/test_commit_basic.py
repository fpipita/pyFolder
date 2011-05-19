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

        self.cm = ConfigManager (
            runfromtest=True, **TEST_CONFIG.USERDATA[PRIMARY_USER])

        self.pyFolder = pyFolder (self.cm, runmode=RUN_FROM_TEST)

        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.iFolderEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (
            self.iFolder.ID)

        self.Type = self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.Action = self.pyFolder.ifolderws.get_change_entry_action ()
        self.SearchOperation = self.pyFolder.ifolderws.get_search_operation ()

        self.pyFolder.checkout ()



    def tearDown (self):
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        self.pyFolder.finalize ()
        shutil.rmtree (TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'], True)



    def test_is_new_local_directory (self):
        Name = 'foo'

        Entry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.assertFalse (self.pyFolder.is_new_local_directory (
                Entry.iFolderID, Entry.Path))



    def test_get_local_changes_on_file (self):
        Name = 'foo'
        Content = 'something'

        Entry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)

        iFolderID = EntryTuple['ifolder']
        iFolderEntryID = EntryTuple['id']
        LocalPath = EntryTuple['localpath']
        Digest = EntryTuple['digest']

        Action, Type = self.pyFolder.get_local_changes_on_entry (
            iFolderID, iFolderEntryID, LocalPath, Digest)

        self.assertEqual (Action, None)
        self.assertEqual (Type, self.Type.File)

        self.pyFolder.write_file (Entry.Path, Content)

        Action, Type = self.pyFolder.get_local_changes_on_entry (
            iFolderID, iFolderEntryID, LocalPath, Digest)

        self.assertEqual (Action, self.Action.Modify)
        self.assertEqual (Type, self.Type.File)

        self.pyFolder.delete (Entry.Path)

        Action, Type = self.pyFolder.get_local_changes_on_entry (
            iFolderID, iFolderEntryID, LocalPath, Digest)

        self.assertEqual (Action, self.Action.Delete)
        self.assertEqual (Type, self.Type.File)



    def test_add_file (self):
        Name = 'foo'
        Content = 'something'
        Path = os.path.join (IFOLDER_NAME, Name)

        self.pyFolder.touch (Path)
        self.pyFolder.write_file (Path, Content)

        self.pyFolder.commit ()

        EntryList = self.pyFolder.ifolderws.get_entries_by_name (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            self.SearchOperation.Contains,
            Name, 0, 1)

        self.assertNotEqual (EntryList, None)

        Entry = EntryList[0]
        Change = self.pyFolder.ifolderws.get_latest_change (
            Entry.iFolderID, Entry.ID)

        self.assertNotEqual (Change, None)

        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)

        self.assertNotEqual (EntryTuple, None)

        self.assertEqual (Change.Time, EntryTuple['mtime'])



    def test_modify_file (self):
        Name = 'foo'
        Content = 'something'
        Path = os.path.join (IFOLDER_NAME, Name)

        self.pyFolder.touch (Path)
        self.pyFolder.write_file (Path, Content)

        self.pyFolder.commit ()

        EntryList = self.pyFolder.ifolderws.get_entries_by_name (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            self.SearchOperation.Contains,
            Name, 0, 1)

        self.assertNotEqual (EntryList, None)

        Entry = EntryList[0]

        EntryTupleBeforeModify = self.pyFolder.dbm.get_entry (
            Entry.iFolderID, Entry.ID)

        self.assertNotEqual (EntryTupleBeforeModify, None)

        self.pyFolder.write_file (Path, Content * 2)

        self.pyFolder.commit ()

        EntryTupleAfterModify = self.pyFolder.dbm.get_entry (
            Entry.iFolderID, Entry.ID)

        self.assertNotEqual (EntryTupleAfterModify, None)

        self.assertNotEqual (
            EntryTupleBeforeModify['mtime'], EntryTupleAfterModify['mtime'])

        self.assertNotEqual (
            EntryTupleBeforeModify['digest'], EntryTupleAfterModify['digest'])



    def test_find_closest_ancestor_remotely_alive (self):
        Ancestor = 'Ancestor'
        Parent = 'Parent'
        Child = 'Child'

        AncestorEntry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Ancestor,
            self.Type.Directory)

        ParentEntry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            AncestorEntry.ID,
            Parent,
            self.Type.Directory)

        ChildEntry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            ParentEntry.ID,
            Child,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        ChildTuple = self.pyFolder.dbm.get_entry (
            self.iFolder.ID, ChildEntry.ID)

        PathToRename, Entry = \
            self.pyFolder.find_closest_ancestor_remotely_alive (
            self.iFolder.ID, ChildTuple['localpath'])

        self.assertEqual (PathToRename, os.path.normpath (
                'TestCommitBasic/Ancestor/Parent/Child'))

        self.assertEqual (Entry.ID, ParentEntry.ID)

        self.pyFolder.ifolderws.delete_entry (self.iFolder.ID, ParentEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        PathToRename, Entry = \
            self.pyFolder.find_closest_ancestor_remotely_alive (
            self.iFolder.ID, ChildTuple['localpath'])

        self.assertEqual (PathToRename, os.path.normpath (
                'TestCommitBasic/Ancestor/Parent'))

        self.assertEqual (Entry.ID, AncestorEntry.ID)

        self.pyFolder.ifolderws.delete_entry (
            self.iFolder.ID, AncestorEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        PathToRename, Entry = \
            self.pyFolder.find_closest_ancestor_remotely_alive (
            self.iFolder.ID, ChildTuple['localpath'])

        self.assertEqual (PathToRename, os.path.normpath (
                'TestCommitBasic/Ancestor'))

        self.assertEqual (self.iFolderEntry.ID, Entry.ID)



    def test_add_locked_file (self):
        Name = '.DS_Store'
        Path = os.path.join (IFOLDER_NAME, Name)

        self.pyFolder.touch (Path)

        self.pyFolder.commit ()

        EntryTuple = self.pyFolder.dbm.get_entry_by_ifolder_and_localpath (
            self.iFolder.ID, Path)

        self.assertEqual (EntryTuple, None)



    def test_file_entry_invalid_characters (self):

        if sys.platform in [ 'win32', 'os2', 'os2emx' ]:
            return

        InvalidEntries = []
        BaseName = 'foo{0}'

        for Char in ENTRY_INVALID_CHARS:
            InvalidEntry = BaseName.format (Char)

            Path = os.path.join (IFOLDER_NAME, InvalidEntry)

            InvalidEntries.append (Path)

            self.pyFolder.touch (Path)

        self.pyFolder.commit ()

        for Entry in InvalidEntries:
            ValidEntry = self.pyFolder.strip_invalid_characters (Entry)
            self.assertTrue (self.pyFolder.path_isfile (ValidEntry))



    def test_directory_entry_invalid_characters (self):

        if sys.platform in [ 'win32', 'os2', 'os2emx' ]:
            return

        InvalidEntries = []
        BaseName = 'foo{0}'

        for Char in ENTRY_INVALID_CHARS:
            InvalidEntry = BaseName.format (Char)

            Path = os.path.join (IFOLDER_NAME, InvalidEntry)

            InvalidEntries.append (Path)

            self.pyFolder.mkdir (Path)

        self.pyFolder.commit ()

        for Entry in InvalidEntries:
            ValidEntry = self.pyFolder.strip_invalid_characters (Entry)
            self.assertTrue (self.pyFolder.path_isdir (ValidEntry))



if __name__ == '__main__':
   unittest.main ()
