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

class TestCommit (unittest.TestCase):

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

    def testNoNewLocalDirectories (self):
        Name = 'foo'
        
        iFolderEntry = self.pyFolder.ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, Name, \
                self.iFolderEntryType.Directory)

        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)
        
        self.pyFolder.update ()
        
        self.assertFalse (self.pyFolder.is_new_local_directory (\
                iFolderEntry.iFolderID, os.path.normpath (iFolderEntry.Path)))
        
if __name__ == '__main__':
    unittest.main ()
