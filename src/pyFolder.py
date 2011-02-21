#!/usr/bin/python

from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds import WebFault
from dbm import DBM
from cfg_manager import CfgManager
from conflicts_handler import ConflictsHandlerFactory
import base64
import hashlib
import os
import shutil
import sqlite3
import sys

DEFAULT_SOAP_BUFLEN = 65536
DEFAULT_CONFIG_FILE = os.path.expanduser (os.path.join ('~', '.ifolderrc'))
DEFAULT_SQLITE_FILE = os.path.expanduser (os.path.join ('~', '.ifolderdb'))

class pyFolder:
    def __init__ (self, cm):
        transport = HttpAuthenticated (username=cm.get_username (), \
                                           password=cm.get_password ())
        self.cm = cm
        self.client = Client (cm.get_ifolderws (), transport=transport)
        self.dbm = DBM (self.cm.get_pathtodb ())
        self.conflicts_handler = ConflictsHandlerFactory.create \
            (cm.get_conflicts (), self)
        self.__action ()
    
    def __action (self):
        pyFolder.__dict__[self.cm.get_action ()] (self)

    def __get_all_ifolders (self):
        return self.client.service.GetiFolders (0, 0)

    def __get_latest_change (self, ifolder_id, entry_id):
        return self.client.service.GetChanges (ifolder_id, entry_id, 0, 1)

    def __get_children_by_ifolder (self, ifolder_id):
        operation = self.client.factory.create ('SearchOperation')
        return self.client.service.GetEntriesByName ( \
            ifolder_id, ifolder_id, operation.Contains, '.', 0, 0)

    def __get_ifolder (self, ifolder_id):
        return self.client.service.GetiFolder (ifolder_id)

    def fetch (self, ifolder_id, entry_id, path):
        self.__debug ('Fetching file \'{0}\' ...'.format (path), False)
        handle = self.client.service.OpenFileRead (ifolder_id, entry_id)
        with open (path, 'wb') as f:
            while True:
                b64data = self.client.service.ReadFile \
                    (handle, cm.get_soapbuflen ())
                if b64data is None:
                    break
                f.write (base64.b64decode (b64data))
            self.client.service.CloseFile (handle)
        self.__debug ('done')

    def delete (self, path):
        if os.path.isfile (path):
            self.__debug ('Deleting file \'{0}\' ...'.format (path), False)
            os.remove (path)
            self.__debug ('done')

    def rmdir (self, path):
        if os.path.isdir (path):
            self.__debug ('Removing directory \'{0}\' ...'.format (path), False)
            shutil.rmtree (path)
            self.__debug ('done')

    def mkdir (self, path):
        if not os.path.isdir (path):
            self.__debug ('Adding directory \'{0}\' ...'.format (path), False)
            os.makedirs (path)
            self.__debug ('done')

    def __add_ifolder (self, ifolder_id, mtime, name):
        update_dbm = self.conflicts_handler.add_directory (None, None, name)
        if update_dbm:
            self.dbm.add_ifolder (ifolder_id, mtime, name)

    def __add_entries (self, ifolder_id):
        entries = self.__get_children_by_ifolder (ifolder_id)
        entries_count = entries.Total
        if entries_count > 0:
            for entry in entries.Items.iFolderEntry:
                latest_change = self.__get_latest_change (ifolder_id, entry.ID)
                if latest_change.Total > 0:
                    for change in latest_change.Items.ChangeEntry:
                        self.__apply_change (ifolder_id, change)
                        break
                entries_count = entries_count - 1
                if entries_count == 0:
                    break

    def __apply_change (self, ifolder_id, change):
        update_dbm = False
        iet = self.client.factory.create ('iFolderEntryType')
        cea = self.client.factory.create ('ChangeEntryAction')
        if change.Action == cea.Add or change.Action == cea.Modify:
            if change.Type == iet.File:
                update_dbm = \
                    self.conflicts_handler.add_file \
                    (ifolder_id, change.ID, change.Name)
            elif change.Type == iet.Directory:
                update_dbm = \
                    self.conflicts_handler.add_directory \
                    (ifolder_id, change.ID, change.Name)
            if update_dbm:
                self.dbm.add_entry \
                    (ifolder_id, change, self.__md5_hash (change))
        return update_dbm
        
    def checkout (self):
        self.dbm.create_schema ()
        ifolders = self.__get_all_ifolders ()
        ifolders_count = ifolders.Total
        if ifolders_count > 0:
            for ifolder in ifolders.Items.iFolder:
                self.__add_ifolder (ifolder.ID, ifolder.LastModified, ifolder.Name)
                self.__add_entries (ifolder.ID)
                ifolders_count = ifolders_count - 1
                if ifolders_count == 0:
                    break

    def __ifolder_has_changes (self, ifolder_t):
        remote_ifolder = None
        try:
            remote_ifolder = self.__get_ifolder (ifolder_t[0])
        except WebFault, wf:
            return False
        if remote_ifolder is not None:
            if remote_ifolder.LastModified > ifolder_t[1]:
                return True
            else:
                return False
        return False

    def __entry_has_changes (self, entry_t):
        latest_change = self.__get_latest_change (entry_t[0], entry_t[1])
        if latest_change.Total > 0:
            for change in latest_change.Items.ChangeEntry:
                if change.Time > entry_t[2]:
                    return True
                else:
                    return False

    def __update_ifolder (self, ifolder_t):
        entries_t = self.dbm.get_entries_by_ifolder (ifolder_t[0])
        update_dbm = False
        for entry_t in entries_t:
            if self.__entry_has_changes (entry_t):
                self.__debug ('Entry {0} has remote changes'.format (entry_t[1]))
                iet = self.client.factory.create ('iFolderEntryType')
                cea = self.client.factory.create ('ChangeEntryAction')
                latest_change = self.__get_latest_change \
                    (entry_t[0], entry_t[1])
                if latest_change.Total > 0:
                    for change in latest_change.Items.ChangeEntry:
                        if change.Action == cea.Add:
                            if change.Type == iet.Directory:
                                update_dbm = \
                                    self.conflicts_handler.add_directory \
                                    (entry_t[0], entry_t[1], change.Name)
                            elif change.Type == iet.File:
                                update_dbm = \
                                    self.conflicts_handler.add_file \
                                    (entry_t[0], entry_t[1], change.Name)
                        elif change.Action == cea.Modify:
                            if change.Type == iet.Directory:
                                update_dbm = \
                                    self.conflict_handler.modify_directory \
                                    (entry_t[0], entry_t[1], change.Name)
                            elif change.Type == iet.File:
                                update_dbm = \
                                    self.conflicts_handler.modify_file \
                                    (entry_t[0], entry_t[1], change.Name)
                        elif change.Action == cea.Delete:
                            if change.Type == iet.Directory:
                                update_dbm = \
                                    self.conflicts_handler.delete_directory \
                                    (entry_t[0], entry_t[1], change.Name)
                            elif change.Type == iet.File:
                                update_dbm = \
                                    self.conflicts_handler.delete_file \
                                    (entry_t[0], entry_t[1], change.Name)
                    if update_dbm:
                        if change.Action == cea.Add or \
                                change.Action == cea.Modify:
                            self.dbm.update_mtime_and_digest_by_entry (\
                                ifolder_t[0], change, \
                                    self.__md5_hash (change))
                        elif change.Action == cea.Delete:
                            self.dbm.delete_entry (ifolder_t[0], change.ID)
        return update_dbm

    def __add_new_entries (self, ifolder_t):
        update_dbm = False
        entries = self.__get_children_by_ifolder (ifolder_t[0])
        entries_count = entries.Total
        if entries_count > 0:
            for entry in entries.Items.iFolderEntry:
                if self.dbm.get_entry (ifolder_t[0], entry.ID) is None:
                    latest_change = self.__get_latest_change (ifolder_t[0], entry.ID)
                    if latest_change.Total > 0:
                        for change in latest_change.Items.ChangeEntry:
                            update_dbm = self.__apply_change (ifolder_t[0], change)
                            break
                entries_count = entries_count - 1
                if entries_count == 0:
                    break
        return update_dbm

    def __add_new_ifolders (self):
        ifolders = self.__get_all_ifolders ()
        ifolders_count = ifolders.Total
        if ifolders_count > 0:
            for ifolder in ifolders.Items.iFolder:
                if self.dbm.get_ifolder (ifolder.ID) is None:
                    self.__add_ifolder (ifolder.ID, ifolder.LastModified, ifolder.Name)
                    self.__add_entries (ifolder.ID)
                ifolders_count = ifolders_count - 1
                if ifolders_count == 0:
                    break

    def __check_for_deleted_ifolder (self, ifolder_t):
        update_dbm = False
        remote_ifolder = None
        try:
            remote_ifolder = self.__get_ifolder (ifolder_t[0])
        except WebFault:
            return update_dbm
        if remote_ifolder is None:
            update_dbm = \
                self.conflicts_handler.delete_directory \
                (ifolder_t[0], ifolder_t[1], ifolder_t[2])
            if update_dbm:
                self.dbm.delete_ifolder (ifolder_t[0])
        return update_dbm

    def __check_for_deleted_membership (self, ifolder_t):
        update_dbm = False
        remote_ifolder = None
        try:
            remote_ifolder = self.__get_ifolder (ifolder_t[0])
        except WebFault:
            update_dbm = \
                self.conflicts_handler.delete_directory \
                (ifolder_t[0], ifolder_t[1], ifolder_t[2])
            if update_dbm:
                self.dbm.delete_ifolder (ifolder_t[0])
            return update_dbm

    def update (self):
        update_dbm = False
        known_ifolders_t = self.dbm.get_ifolders ()
        for ifolder_t in known_ifolders_t:
            if self.__ifolder_has_changes (ifolder_t):
                self.__debug ('iFolder {0} has remote changes'.format (ifolder_t[0]))
                update_dbm = update_dbm or self.__update_ifolder (ifolder_t)
                update_dbm = update_dbm or self.__add_new_entries (ifolder_t)
                if update_dbm:
                    self.dbm.update_mtime_by_ifolder \
                        (ifolder_t[0], self.__get_ifolder \
                             (ifolder_t[0]).LastModified)
            self.__check_for_deleted_ifolder (ifolder_t)
            self.__check_for_deleted_membership (ifolder_t)
        self.__add_new_ifolders ()

    def __md5_hash (self, change):
        md5_hash = 'DIRECTORY'
        if os.path.isfile (change.Name):
            self.__debug ('MD5SUM (\'{0}\') ->'.format (change.Name), False)
            m = hashlib.md5 ()
            with open (change.Name, 'rb') as f:
                while True:
                    data = f.read ()
                    m.update (data)
                    if len (data) == 0:
                        break
                md5_hash = m.hexdigest ()
                self.__debug ('{0}'.format (md5_hash, True))
        return md5_hash

    def __debug (self, message, newline=True):
        if self.cm.get_verbose ():
            if newline:
                print >> sys.stderr, message
            else:
                print >> sys.stderr, message,

if __name__ == '__main__':
    cm = CfgManager (DEFAULT_CONFIG_FILE, DEFAULT_SQLITE_FILE, \
                         DEFAULT_SOAP_BUFLEN)
    pf = pyFolder (cm)
