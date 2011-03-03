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

from setup import Setup

IFOLDER_NAME = 'TestUpdate'
TEST_CONFIG = Setup ()

class TestUpdate (unittest.TestCase):

    def setUp (self):
        os.makedirs (TEST_CONFIG.USERDATA_A['prefix'])

        self.cm = CfgManager (runfromtest=True, **TEST_CONFIG.USERDATA_A)
        self.pyFolder = pyFolder (self.cm, runfromtest=True)

        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)

        self.iFolderAsEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (\
            self.iFolder.ID)

        self.iFolderEntryType = \
            self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.ChangeEntryAction = \
            self.pyFolder.ifolderws.get_change_entry_action ()

        self.pyFolder.checkout ()

    def tearDown (self):
        self.pyFolder.dbm = None
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)
        shutil.rmtree (TEST_CONFIG.USERDATA_A['prefix'], True)

    def test_add_file (self):
        FileName = 'test_add_file'

        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, FileName, \
                self.iFolderEntryType.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        EntryTuple = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        self.assertEqual (EntryTuple['id'], iFolderEntry.ID)
        self.assertEqual (EntryTuple['ifolder'], iFolderEntry.iFolderID)
        self.assertNotEqual (EntryTuple['digest'], 'DIRECTORY')
        
        LocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntry.Path)

        self.assertTrue (os.path.isfile (LocalPath))

        iFolder = self.pyFolder.ifolderws.get_ifolder (\
            iFolderEntry.iFolderID)
        
        iFolderTuple = self.pyFolder.dbm.get_ifolder (\
            iFolderEntry.iFolderID)
        
        self.assertEqual (iFolderTuple['mtime'], iFolder.LastModified)
    
    def test_modify_file (self):
        FileName = 'test_modify_file'
        FileData = 'test_modify_file'

        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, FileName, \
                self.iFolderEntryType.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        Handle = self.pyFolder.ifolderws.open_file_write (\
            iFolderEntry.iFolderID, iFolderEntry.ID, len (FileData))
        self.pyFolder.ifolderws.write_file (\
            Handle, base64.b64encode (FileData))
        self.pyFolder.ifolderws.close_file (Handle)
        
        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        EntryTuple = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        ChangeEntry = self.pyFolder.ifolderws.get_latest_change (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        self.assertEqual (EntryTuple['mtime'], ChangeEntry.Time)

        LocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntry.Path)
        
        self.assertTrue (os.path.isfile (LocalPath))
        
        with open (LocalPath, 'rb') as File:
            self.assertEqual (File.readlines ()[0], FileData)

        iFolder = self.pyFolder.ifolderws.get_ifolder (\
            iFolderEntry.iFolderID)
        
        iFolderTuple = self.pyFolder.dbm.get_ifolder (\
            iFolderEntry.iFolderID)
        
        self.assertEqual (iFolderTuple['mtime'], iFolder.LastModified)
        
    def test_delete_file (self):
        FileName = 'test_delete_file'

        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, FileName, \
                self.iFolderEntryType.File)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID, None, None)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()
        
        EntryTuple = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        self.assertEqual (EntryTuple, None)
        
        LocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntry.Path)
        
        self.assertFalse (os.path.isfile (LocalPath))

        iFolder = self.pyFolder.ifolderws.get_ifolder (\
            iFolderEntry.iFolderID)
        
        iFolderTuple = self.pyFolder.dbm.get_ifolder (\
            iFolderEntry.iFolderID)
        
        self.assertEqual (iFolderTuple['mtime'], iFolder.LastModified)

    def test_add_directory (self):
        DirectoryName = 'test_add_directory'

        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, DirectoryName, \
                self.iFolderEntryType.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        EntryTuple = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        self.assertEqual (EntryTuple['id'], iFolderEntry.ID)
        self.assertEqual (EntryTuple['ifolder'], iFolderEntry.iFolderID)
        self.assertEqual (EntryTuple['digest'], 'DIRECTORY')
        
        LocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntry.Path)
        
        self.assertTrue (os.path.isdir (LocalPath))

        iFolder = self.pyFolder.ifolderws.get_ifolder (\
            iFolderEntry.iFolderID)
        
        iFolderTuple = self.pyFolder.dbm.get_ifolder (\
            iFolderEntry.iFolderID)
        
        self.assertEqual (iFolderTuple['mtime'], iFolder.LastModified)
    
    # def testModifyDirectory (self):
    #     pass

    def test_delete_directory (self):
        DirectoryName = 'test_delete_directory'

        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderAsEntry.ID, DirectoryName, \
                self.iFolderEntryType.Directory)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID, None, None)

        time.sleep (TEST_CONFIG.SIMIAS_REFRESH)
        self.pyFolder.update ()

        EntryTuple = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        self.assertEqual (EntryTuple, None)

        LocalPath = os.path.join (\
            TEST_CONFIG.USERDATA_A['prefix'], iFolderEntry.Path)
        
        self.assertFalse (os.path.isdir (LocalPath))

        iFolder = self.pyFolder.ifolderws.get_ifolder (\
            iFolderEntry.iFolderID)
        
        iFolderTuple = self.pyFolder.dbm.get_ifolder (\
            iFolderEntry.iFolderID)
        
        self.assertEqual (iFolderTuple['mtime'], iFolder.LastModified)
        
if __name__ == '__main__':
    unittest.main ()
