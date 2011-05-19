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



from setup import *



IFOLDER_NAME = 'TestUpdateBasic'
TEST_CONFIG = Setup ()



class TestUpdateBasic (unittest.TestCase):



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

        self.pyFolder.checkout ()



    def tearDown (self):
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        self.pyFolder.finalize ()
        shutil.rmtree (TEST_CONFIG.USERDATA[PRIMARY_USER]['prefix'], True)



    def test_add_file (self):
        Name = 'foo'

        Entry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)

        self.assertEqual (EntryTuple['id'], Entry.ID)
        self.assertEqual (EntryTuple['ifolder'], Entry.iFolderID)
        self.assertNotEqual (EntryTuple['digest'], 'DIRECTORY')

        self.assertTrue (self.pyFolder.path_isfile (Entry.Path))



    def test_modify_file (self):
        Name = 'foo'
        Content = 'something'

        Entry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        Handle = self.pyFolder.ifolderws.open_file_write (
            Entry.iFolderID, Entry.ID, len (Content))

        self.pyFolder.ifolderws.write_file (
            Handle, base64.b64encode (Content))

        self.pyFolder.ifolderws.close_file (Handle)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)

        Change = self.pyFolder.ifolderws.get_latest_change (
            Entry.iFolderID, Entry.ID)

        self.assertEqual (EntryTuple['mtime'], Change.Time)

        self.assertTrue (self.pyFolder.path_isfile (Entry.Path))

        self.assertEqual (self.pyFolder.readlines (Entry.Path)[0], Content)



    def test_delete_file (self):
        Name = 'foo'

        Entry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (Entry.iFolderID, Entry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)

        self.assertEqual (EntryTuple, None)

        self.assertFalse (self.pyFolder.path_isfile (Entry.Path))



    def test_add_directory (self):
        Name = 'foo'

        Entry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)

        self.assertEqual (EntryTuple['id'], Entry.ID)
        self.assertEqual (EntryTuple['ifolder'], Entry.iFolderID)
        self.assertEqual (EntryTuple['digest'], 'DIRECTORY')

        self.assertTrue (self.pyFolder.path_isdir (Entry.Path))



    def test_delete_directory (self):
        Name = 'foo'

        Entry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Name,
            self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (Entry.iFolderID, Entry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        EntryTuple = self.pyFolder.dbm.get_entry (Entry.iFolderID, Entry.ID)

        self.assertEqual (EntryTuple, None)

        self.assertFalse (self.pyFolder.path_isdir (Entry.Path))



    def test_update_entry_on_parent_deletion (self):
        Parent = 'Parent'
        Child = 'Child'
        Content = 'something'

        ParentEntry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID,
            self.iFolderEntry.ID,
            Parent,
            self.Type.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        ChildEntry = self.pyFolder.ifolderws.create_entry (
            self.iFolder.ID, ParentEntry.ID, Child, self.Type.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.update ()

        Handle = self.pyFolder.ifolderws.open_file_write (
            self.iFolder.ID, ChildEntry.ID, len (Content))

        self.pyFolder.ifolderws.write_file (Handle, base64.b64encode (Content))
        self.pyFolder.ifolderws.close_file (Handle)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.pyFolder.ifolderws.delete_entry (self.iFolder.ID, ParentEntry.ID)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        ChildEntryTuple = self.pyFolder.dbm.get_entry (
            self.iFolder.ID, ChildEntry.ID)

        self.pyFolder.update_entry (
            self.iFolder.ID, ChildEntryTuple['id'], ChildEntryTuple['mtime'])

        self.assertFalse (self.pyFolder.path_isfile (ChildEntry.Path))



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
