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

from setup import Setup

IFOLDER_NAME = 'TestUpdateBasic'
TEST_CONFIG = Setup ()

class TestUpdateBasic (unittest.TestCase):

    def setUp (self):
        os.makedirs (TEST_CONFIG.USERDATA_A['prefix'])

        self.cm = ConfigManager (runfromtest=True, **TEST_CONFIG.USERDATA_A)
        self.pyFolder = pyFolder (self.cm, runfromtest=True)

        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.iFolderEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (\
            self.iFolder.ID)

        self.Type = self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.Action = self.pyFolder.ifolderws.get_change_entry_action ()

        self.pyFolder.checkout ()

    def tearDown (self):
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        self.pyFolder.finalize ()
        shutil.rmtree (TEST_CONFIG.USERDATA_A['prefix'], True)

    def test_add_file (self):
        FileName = 'test_add_file'

        Entry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, FileName, \
                self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)
        
        self.assertEqual (EntryTuple['id'], Entry.ID)
        self.assertEqual (EntryTuple['ifolder'], Entry.iFolderID)
        self.assertNotEqual (EntryTuple['digest'], 'DIRECTORY')
        
        LocalPath = os.path.join (TEST_CONFIG.USERDATA_A['prefix'], Entry.Path)

        self.assertTrue (os.path.isfile (LocalPath))

    def test_modify_file (self):
        FileName = 'test_modify_file'
        FileData = 'test_modify_file'

        Entry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, FileName, \
                self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        Handle = self.pyFolder.ifolderws.open_file_write (\
            Entry.iFolderID, Entry.ID, len (FileData))
        self.pyFolder.ifolderws.write_file (\
            Handle, base64.b64encode (FileData))
        self.pyFolder.ifolderws.close_file (Handle)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)
        
        Change = self.pyFolder.ifolderws.get_latest_change (\
            Entry.iFolderID, Entry.ID)
        
        self.assertEqual (EntryTuple['mtime'], Change.Time)

        LocalPath = os.path.join (TEST_CONFIG.USERDATA_A['prefix'], Entry.Path)
        
        self.assertTrue (os.path.isfile (LocalPath))
        
        with open (LocalPath, 'rb') as File:
            self.assertEqual (File.readlines ()[0], FileData)

    def test_delete_file (self):
        FileName = 'test_delete_file'

        Entry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, FileName, \
                self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (Entry.iFolderID, Entry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)
        
        self.assertEqual (EntryTuple, None)
        
        LocalPath = os.path.join (TEST_CONFIG.USERDATA_A['prefix'], Entry.Path)
        
        self.assertFalse (os.path.isfile (LocalPath))

    def test_add_directory (self):
        DirectoryName = 'test_add_directory'

        Entry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, DirectoryName, \
                self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)
        
        self.assertEqual (EntryTuple['id'], Entry.ID)
        self.assertEqual (EntryTuple['ifolder'], Entry.iFolderID)
        self.assertEqual (EntryTuple['digest'], 'DIRECTORY')
        
        LocalPath = os.path.join (TEST_CONFIG.USERDATA_A['prefix'], Entry.Path)
        
        self.assertTrue (os.path.isdir (LocalPath))

    def testModifyDirectory (self):
        pass

    def test_delete_directory (self):
        DirectoryName = 'test_delete_directory'

        Entry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, DirectoryName, \
                self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (Entry.iFolderID, Entry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)
        
        self.assertEqual (EntryTuple, None)

        LocalPath = os.path.join (TEST_CONFIG.USERDATA_A['prefix'], Entry.Path)
        
        self.assertFalse (os.path.isdir (LocalPath))

    def test_update_entry_on_parent_deletion (self):
        Parent = 'Parent'
        Child = 'Child'
        aString = 'aString'
        
        ParentEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, Parent, self.Type.Directory)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        ChildEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, ParentEntry.ID, Child, self.Type.File)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        self.pyFolder.update ()
        
        Handle = self.pyFolder.ifolderws.open_file_write (\
            self.iFolder.ID, ChildEntry.ID, len (aString))
        
        self.pyFolder.ifolderws.write_file (Handle, base64.b64encode (aString))
        self.pyFolder.ifolderws.close_file (Handle)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        
        self.pyFolder.ifolderws.delete_entry (self.iFolder.ID, ParentEntry.ID)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        ChildEntryTuple = self.pyFolder.dbm.get_entry (\
            self.iFolder.ID, ChildEntry.ID)
 
        self.pyFolder.update_entry (\
            self.iFolder.ID, ChildEntryTuple['id'], ChildEntryTuple['mtime'])

        ChildLocalPath = os.path.normpath (ChildEntry.Path)
        ChildLocalPath = self.pyFolder.add_prefix (ChildLocalPath)

        self.assertFalse (self.pyFolder.path_isfile (ChildLocalPath))

    def test_delete_nested_hierarchy (self):
        Hierarchy = {
            'Ancestor':None,
            'Parent':'Ancestor',
            'Child':'Parent'}

        for Key in Hierarchy.keys ():
            Current = Hierarchy[Key]
            ParentID = self.iFolderEntry.ID

            if Current is not None:
                ParentID = Hierarchy[Current].ID

            Hierarchy[Key] = self.pyFolder.ifolderws.create_entry (
                self.iFolder.ID,
                ParentID,
                Key,
                self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (
            Hierarchy['Ancestor'].iFolderID, Hierarchy['Ancestor'].ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        Content = os.listdir (self.pyFolder.add_prefix (IFOLDER_NAME))
        self.assertEquals (len (Content), 0)
        
if __name__ == '__main__':
   unittest.main ()
