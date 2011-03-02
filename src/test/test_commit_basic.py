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

USERNAME = 'francesco'
PASSWORD = 'foo'
IFOLDERWS = 'http://192.168.56.3/simias10/iFolderWeb.asmx?wsdl=0'
IFOLDER_NAME = 'TestCommit'
PREFIX = '/tmp/pyFolder'

WAIT_FOR_SIMIAS_TO_UPDATE = 5

class TestCommitBasic (unittest.TestCase):

    def setUp (self):
        self.cm = CfgManager (soapbuflen=DEFAULT_SOAP_BUFLEN, \
                                  pathtodb=':memory:', runfromtest=True)
        self.cm.options.username = USERNAME
        self.cm.options.password = PASSWORD
        self.cm.options.ifolderws = IFOLDERWS
        self.cm.options.prefix = PREFIX
        self.cm.options.verbose = False
        self.pyFolder = pyFolder (self.cm, runfromtest=True)
        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)
        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)
        self.iFolderEntry = self.pyFolder.ifolderws.get_ifolder_as_entry (\
            self.iFolder.ID)
        self.iFolderEntryType = \
            self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.ChangeEntryAction = \
            self.pyFolder.ifolderws.get_change_entry_action ()
        self.pyFolder.checkout ()

    def tearDown (self):
        shutil.rmtree (PREFIX, True)
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)

    def test_is_new_local_directory (self):
        DirectoryName = 'test_is_new_local_directory'
        
        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, DirectoryName, \
                self.iFolderEntryType.Directory)

        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)
        
        self.pyFolder.update ()
        
        self.assertFalse (self.pyFolder.is_new_local_directory (\
                iFolderEntry.iFolderID, os.path.normpath (iFolderEntry.Path)))
        
    def test_get_local_changes_on_file (self):
        FileName = 'test_get_local_changes_on_file'
        FileData = 'test_get_local_changes_on_file'
        
        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, FileName, \
                self.iFolderEntryType.File)
        
        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)
        
        self.pyFolder.update ()
        
        EntryTuple = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)

        iFolderID = EntryTuple['ifolder']
        iFolderEntryID = EntryTuple['id']
        LocalPath = EntryTuple['localpath']
        Digest = EntryTuple['digest']

        Action, Type = \
            self.pyFolder.get_local_changes_on_entry (\
            iFolderID, iFolderEntryID, LocalPath, Digest, \
                self.iFolderEntryType, self.ChangeEntryAction)
        
        self.assertEqual (Action, None)
        self.assertEqual (Type, self.iFolderEntryType.File)

        _LocalPath = os.path.join (PREFIX, iFolderEntry.Path)

        with open (_LocalPath, 'wb') as File:
            File.write (FileData)
        
        Action, Type = \
            self.pyFolder.get_local_changes_on_entry (\
            iFolderID, iFolderEntryID, LocalPath, Digest, \
                self.iFolderEntryType, self.ChangeEntryAction)
        
        self.assertEqual (Action, self.ChangeEntryAction.Modify)
        self.assertEqual (Type, self.iFolderEntryType.File)
        
        os.remove (_LocalPath)
        
        Action, Type = \
            self.pyFolder.get_local_changes_on_entry (\
            iFolderID, iFolderEntryID, LocalPath, Digest, \
                self.iFolderEntryType, self.ChangeEntryAction)

        self.assertEqual (Action, self.ChangeEntryAction.Delete)
        self.assertEqual (Type, self.iFolderEntryType.File)
        
if __name__ == '__main__':
    unittest.main ()
