#!/usr/bin/python

from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds import WebFault

from dbm import DBM
from cfg_manager import CfgManager
import base64
import hashlib
import os
import shutil
import sys

DEFAULT_SOAP_BUFLEN = 65536
DEFAULT_CONFIG_FILE = os.path.expanduser (os.path.join ('~', '.ifolderrc'))
DEFAULT_SQLITE_FILE = os.path.expanduser (os.path.join ('~', '.ifolderdb'))

class pyFolder:
    def __init__ (self, cm):
        transport = HttpAuthenticated (username=cm.username (), \
                                           password=cm.password ())
        self.cm = cm
        self.client = Client (cm.ifolderws (), transport=transport)
        self.dbm = DBM (self.cm.pathtodb ())
        self.__action ()
    
    # Execute the chosen action
    def __action (self):
        pyFolder.__dict__[self.cm.action ()] (self)


    # Wrappers

    def __get_all_ifolders (self):
        return self.client.service.GetiFolders (0, 0)

    def __get_latest_change (self, entry):
        return self.client.service.GetChanges (entry.iFolderID, entry.ID, 0, 1)

    def __get_children_by_ifolder (self, ifolder):
        operation = self.client.factory.create ('SearchOperation')
        return self.client.service.GetEntriesByName ( \
            ifolder.ID, ifolder.ID, operation.Contains, '.', 0, 0)

    def __fetch (self, ifolder, change):
        self.__debug ('Fetching file \'{0}\' ...'.format (change.Name), False)
        handle = self.client.service.OpenFileRead (ifolder.ID, change.ID)
        with open (change.Name, 'wb') as f:
            while True:
                b64data = self.client.service.ReadFile \
                    (handle, cm.soapbuflen ())
                if b64data is None:
                    break
                f.write (base64.b64decode (b64data))
            self.client.service.CloseFile (handle)
        self.__debug ('done')

    # Wrappers end here

    def __add_ifolder (self, ifolder):
        self.dbm.ifolder_add (ifolder)
        self.__rmdir (ifolder.Name)
        self.__mkdir (ifolder.Name)

    # Create a local copy of the user's remote directory, overwriting an
    # eventual existing local tree
    def checkout (self):
        self.dbm.create_schema ()
        ifolders = self.__get_all_ifolders ()
        ifolders_count = ifolders.Total
        if ifolders_count > 0:
            for ifolder in ifolders.Items.iFolder:
                self.__add_ifolder (ifolder)
                entries = self.__get_children_by_ifolder (ifolder)
                entries_count = entries.Total
                if entries_count > 0:
                    for entry in entries.Items.iFolderEntry:
                        latest_change = self.__get_latest_change (entry)
                        if latest_change.Total > 0:
                            for change in latest_change.Items.ChangeEntry:
                                self.__apply_change (ifolder, change, True)
                                break
                    entries_count = entries_count - 1
                    if entries_count == 0:
                        break
                ifolders_count = ifolders_count - 1
                if ifolders_count == 0:
                    break

    # Update the user's local copy of the iFolder tree
    def update (self):
        ifolders = self.__get_all_ifolders ()
        ifolders_count = ifolders.Total
        if ifolders_count > 0:
            for ifolder in ifolders.Items.iFolder:
                self.__add_ifolder (ifolder)
                entries = self.__get_children_by_ifolder (ifolder)
                entries_count = entries.Total
                if entries_count > 0:
                    for entry in entries.Items.iFolderEntry:
                        latest_change = self.__get_latest_change (entry)
                        if latest_change.Total > 0:
                            for change in latest_change.Items.ChangeEntry:
                                self.__apply_change (ifolder, change, False)
                                break
                    entries_count = entries_count - 1
                    if entries_count == 0:
                        break
                ifolders_count = ifolders_count - 1
                if ifolders_count == 0:
                    break
    
    # Apply `change' to `ifolder'. If `force' is True, apply the change 
    # unconditionally
    def __apply_change (self, ifolder, change, force):
        cea = self.client.factory.create ('ChangeEntryAction')
        if change.Action == cea.Add:
            self.__apply_add_change (ifolder, change, force)
        elif change.Action == cea.Modify:
            self.__apply_modify_change (ifolder, change, force)
        elif change.Action == cea.Delete:
            self.__apply_delete_change (ifolder, change, force)

    def __apply_add_change (self, ifolder, change, force):
        iet = self.client.factory.create ('iFolderEntryType')
        if force:
            if change.Type == iet.File:
                self.__fetch (ifolder, change)
            elif change.Type == iet.Directory:
                self.__mkdir (change.Name)
            self.__dbm_update (ifolder, change)

    def __apply_modify_change (self, ifolder, change, force):
        iet = self.client.factory.create ('iFolderEntryType')
        if force:
            if change.Type == iet.File:
                self.__fetch (ifolder, change)
            elif change.Type == iet.Directory:
                self.__mkdir (change.Name)
            self.__dbm_update (ifolder, change)

    def __apply_delete_change (self, ifolder, change, force):
        iet = self.client.factory.create ('iFolderEntryType')
        if force:
            if change.Type == iet.File:
                self.__del (ifolder.ID, change.ID, change.Name)
            elif change.Type == iet.Directory:
                self.__rmdir (change.Name)
            self.__dbm_update (ifolder, change)

    def __del (self, path):
        if os.path.isfile (path):
            self.__debug ('Deleting file \'{0}\' ...'.format (path), False)
            os.remove (path)
            self.__debug ('done')

    def __rmdir (self, path):
        if os.path.isdir (path):
            self.__debug ('Removing directory \'{0}\' ...'.format (path), False)
            shutil.rmtree (path)
            self.__debug ('done')

    def __mkdir (self, path):
        if not os.path.isdir (path):
            self.__debug ('Adding directory \'{0}\' ...'.format (path), False)
            os.makedirs (path)
            self.__debug ('done')

    def __dbm_update (self, ifolder, change, force):
        pass

    # Utilities

    def __md5_hash (self, change):
        md5_hash = 'DIRECTORY'
        if os.path.isfile (change.Name):
            self.__debug ('Calculating MD5 hash for file \'{0}\''.format (change.Name), False)
            m = hashlib.md5 ()
            with open (change.Name, 'rb') as f:
                while True:
                    data = f.read ()
                    m.update (data)
                    if len (data) == 0:
                        break
                md5_hash = m.hexdigest ()
                self.__debug ('{0}'.format (m.hexdigest ()), True)
        return md5_hash

    def __debug (self, message, newline=True):
        if self.cm.verbose ():
            if newline:
                print >> sys.stderr, message
            else:
                print >> sys.stderr, message,

    # Utilities end here

if __name__ == '__main__':
    cm = CfgManager (DEFAULT_CONFIG_FILE, DEFAULT_SQLITE_FILE, \
                         DEFAULT_SOAP_BUFLEN)
    try:    
        pf = pyFolder (cm)
    except WebFault, wf:
        print wf
