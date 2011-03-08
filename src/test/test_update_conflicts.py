#-*- coding: utf-8 -*-

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

IFOLDER_NAME = 'TestUpdateConflicts'
TEST_CONFIG = Setup ()

class TestUpdateConflicts (unittest.TestCase):

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
            
if __name__ == '__main__':
    unittest.main ()
