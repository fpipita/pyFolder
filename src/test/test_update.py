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
IFOLDER_NAME = 'TestUpdate'
PREFIX = '/tmp/pyFolder'

WAIT_FOR_SIMIAS_TO_UPDATE = 5

class TestUpdate (unittest.TestCase):

    def setUp (self):
        self.cm = CfgManager (\
            pathtodb=':memory:', \
            soapbuflen=DEFAULT_SOAP_BUFLEN, \
                runfromtest=True)
        self.cm.options.username = USERNAME
        self.cm.options.password = PASSWORD
        self.cm.options.ifolderws = IFOLDERWS
        self.cm.options.prefix = PREFIX
        self.cm.options.verbose = False
        self.pyFolder = pyFolder (self.cm, runfromtest=True)
        self.iFolder = self.pyFolder.ifolderws.create_ifolder (IFOLDER_NAME)
        self.iFolderEntry = self.pyFolder.ifolderws.get_ifolder_entry_id (\
            self.iFolder.ID)
        self.iFolderEntryType = \
            self.pyFolder.ifolderws.get_ifolder_entry_type ()
        self.ChangeEntryAction = \
            self.pyFolder.ifolderws.get_change_entry_action ()
        self.pyFolder.checkout ()

    def tearDown (self):
        shutil.rmtree (PREFIX)
        self.pyFolder.ifolderws.delete_ifolder (self.iFolder.ID)

    def test_add_file (self):
        Name = 'foo'

        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, Name, \
                self.iFolderEntryType.File)

        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)

        self.pyFolder.update ()
        
        entry_t = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        self.assertEqual (entry_t['id'], iFolderEntry.ID)
        self.assertEqual (entry_t['ifolder'], iFolderEntry.iFolderID)
        self.assertNotEqual (entry_t['digest'], 'DIRECTORY')
        
        LocalPath = os.path.join (PREFIX, iFolderEntry.Path)

        self.assertTrue (os.path.isfile (LocalPath))

        iFolder = self.pyFolder.ifolderws.get_ifolder (\
            iFolderEntry.iFolderID)
        
        ifolder_t = self.pyFolder.dbm.get_ifolder (\
            iFolderEntry.iFolderID)
        
        self.assertEqual (ifolder_t['mtime'], iFolder.LastModified)
    
    def test_modify_file (self):
        Name = 'foo'
        Data = 'bar'

        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, Name, \
                self.iFolderEntryType.File)

        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)

        self.pyFolder.update ()

        Handle = self.pyFolder.ifolderws.open_file_write (\
            iFolderEntry.iFolderID, iFolderEntry.ID, len (Data))
        self.pyFolder.ifolderws.write_file (Handle, base64.b64encode (Data))
        self.pyFolder.ifolderws.close_file (Handle)
        
        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)

        self.pyFolder.update ()
        
        entry_t = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        ChangeEntry = self.pyFolder.ifolderws.get_latest_change (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        self.assertEqual (entry_t['mtime'], ChangeEntry.Time)

        LocalPath = os.path.join (PREFIX, iFolderEntry.Path)
        
        self.assertTrue (os.path.isfile (LocalPath))
        
        with open (LocalPath, 'rb') as File:
            self.assertEqual (File.readlines ()[0], Data)

        iFolder = self.pyFolder.ifolderws.get_ifolder (\
            iFolderEntry.iFolderID)
        
        ifolder_t = self.pyFolder.dbm.get_ifolder (\
            iFolderEntry.iFolderID)
        
        self.assertEqual (ifolder_t['mtime'], iFolder.LastModified)
        
    def test_delete_file (self):
        Name = 'foo'

        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, Name, \
                self.iFolderEntryType.File)

        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)
        
        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID, None, None)

        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)

        self.pyFolder.update ()
        
        entry_t = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        self.assertEqual (entry_t, None)
        
        LocalPath = os.path.join (PREFIX, iFolderEntry.Path)
        
        self.assertFalse (os.path.isfile (LocalPath))

        iFolder = self.pyFolder.ifolderws.get_ifolder (\
            iFolderEntry.iFolderID)
        
        ifolder_t = self.pyFolder.dbm.get_ifolder (\
            iFolderEntry.iFolderID)
        
        self.assertEqual (ifolder_t['mtime'], iFolder.LastModified)

    def test_add_directory (self):
        Name = 'foo'

        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, Name, \
                self.iFolderEntryType.Directory)

        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)
        
        self.pyFolder.update ()

        entry_t = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        self.assertEqual (entry_t['id'], iFolderEntry.ID)
        self.assertEqual (entry_t['ifolder'], iFolderEntry.iFolderID)
        self.assertEqual (entry_t['digest'], 'DIRECTORY')
        
        LocalPath = os.path.join (PREFIX, iFolderEntry.Path)
        
        self.assertTrue (os.path.isdir (LocalPath))

        iFolder = self.pyFolder.ifolderws.get_ifolder (\
            iFolderEntry.iFolderID)
        
        ifolder_t = self.pyFolder.dbm.get_ifolder (\
            iFolderEntry.iFolderID)
        
        self.assertEqual (ifolder_t['mtime'], iFolder.LastModified)
    
    # def testModifyDirectory (self):
    #     pass

    def test_delete_directory (self):
        Name = 'foo'

        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, Name, \
                self.iFolderEntryType.Directory)

        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)
        
        self.pyFolder.update ()

        self.pyFolder.ifolderws.delete_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID, None, None)

        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)

        self.pyFolder.update ()

        entry_t = self.pyFolder.dbm.get_entry (\
            iFolderEntry.iFolderID, iFolderEntry.ID)
        
        self.assertEqual (entry_t, None)

        LocalPath = os.path.join (PREFIX, iFolderEntry.Path)
        
        self.assertFalse (os.path.isdir (LocalPath))

        iFolder = self.pyFolder.ifolderws.get_ifolder (\
            iFolderEntry.iFolderID)
        
        ifolder_t = self.pyFolder.dbm.get_ifolder (\
            iFolderEntry.iFolderID)
        
        self.assertEqual (ifolder_t['mtime'], iFolder.LastModified)
        
if __name__ == '__main__':
    unittest.main ()
