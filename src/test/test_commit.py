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

class TestCommit (unittest.TestCase):

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
        self.iFolderEntry = self.pyFolder.ifolderws.get_ifolder_entry_id (\
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
        
    def test_add_directory_on_conflict (self):
        DirectoryName = 'test_add_directory_on_conflict'

        _USERNAME = 'mario'
        _PASSWORD = 'foo'
        _PATHTODB = os.path.join (PREFIX, '.test_add_directory_on_conflict')

        Rights = self.pyFolder.ifolderws.get_rights ()
        SearchOperation = self.pyFolder.ifolderws.get_search_operation ()
        SearchProperty = self.pyFolder.ifolderws.get_search_property ()

        ArrayOfiFolderUser = self.pyFolder.ifolderws.get_users_by_search (\
            SearchProperty.UserName, SearchOperation.Contains, _USERNAME, \
                0, 1)

        if ArrayOfiFolderUser is not None:
            for iFolderUser in ArrayOfiFolderUser:
                self.pyFolder.ifolderws.add_member (\
                    self.iFolder.ID, iFolderUser.ID, Rights.ReadWrite)
        else:
            self.fail ()
            return

        _cm = CfgManager (soapbuflen=DEFAULT_SOAP_BUFLEN, runfromtest=True)
        _cm.options.username = _USERNAME
        _cm.options.password = _PASSWORD
        _cm.options.ifolderws = IFOLDERWS
        _ifolderws = iFolderWS (_cm)
        
        logging.getLogger ('suds.client').addHandler (NullHandler ())
        
        iFolderEntry = _ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, DirectoryName, \
                self.iFolderEntryType.Directory)
        
        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)

        LocalPath = os.path.join (PREFIX, iFolderEntry.Path)

        os.mkdir (LocalPath)

        self.pyFolder.commit ()
        
        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)

        self.pyFolder.update ()

        self.assertTrue (os.path.isdir ('{0}-{1}'.format (LocalPath, USERNAME)))
        self.assertTrue (os.path.isdir (LocalPath))

    def test_add_file_on_conflict (self):
        FileName = 'test_add_file_on_conflict'
        FileData = 'test_add_file_on_conflict'

        _USERNAME = 'mario'
        _PASSWORD = 'foo'
        _PATHTODB = os.path.join (PREFIX, '.test_add_file_on_conflict')

        Rights = self.pyFolder.ifolderws.get_rights ()
        SearchOperation = self.pyFolder.ifolderws.get_search_operation ()
        SearchProperty = self.pyFolder.ifolderws.get_search_property ()

        ArrayOfiFolderUser = self.pyFolder.ifolderws.get_users_by_search (\
            SearchProperty.UserName, SearchOperation.Contains, _USERNAME, \
                0, 1)

        if ArrayOfiFolderUser is not None:
            for iFolderUser in ArrayOfiFolderUser:
                self.pyFolder.ifolderws.add_member (\
                    self.iFolder.ID, iFolderUser.ID, Rights.ReadWrite)
        else:
            self.fail ()
            return

        _cm = CfgManager (soapbuflen=DEFAULT_SOAP_BUFLEN, runfromtest=True)
        _cm.options.username = _USERNAME
        _cm.options.password = _PASSWORD
        _cm.options.ifolderws = IFOLDERWS
        _ifolderws = iFolderWS (_cm)

        logging.getLogger ('suds.client').addHandler (NullHandler ())

        iFolderEntry = _ifolderws.create_entry (\
            self.iFolder.ID, self.iFolderEntry.ID, FileName, \
                self.iFolderEntryType.File)
        
        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)

        LocalPath = os.path.join (PREFIX, iFolderEntry.Path)

        with open (LocalPath, 'wb') as File:
            File.write (FileData)
            
        self.pyFolder.commit ()
        
        time.sleep (WAIT_FOR_SIMIAS_TO_UPDATE)

        self.pyFolder.update ()

        self.assertTrue (os.path.isfile ('{0}-{1}'.format (LocalPath, USERNAME)))
        self.assertTrue (os.path.isfile (LocalPath))
        
if __name__ == '__main__':
    unittest.main ()
