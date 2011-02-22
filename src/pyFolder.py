#!/usr/bin/python

from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds import WebFault
from support.dbm import DBM
from support.cfg_manager import CfgManager
from support.conflicts_handler import ConflictsHandlerFactory
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

    def __add_prefix (self, path):
        if self.cm.get_prefix () != '':
            return os.path.join (self.cm.get_prefix (), path)
        return path

    def fetch (self, ifolder_id, entry_id, path):
        path = self.__add_prefix (path)
        self.debug ('Fetching file \'{0}\' ...'.format (path), False)
        handle = self.client.service.OpenFileRead (ifolder_id, entry_id)
        with open (path, 'wb') as f:
            while True:
                b64data = self.client.service.ReadFile \
                    (handle, cm.get_soapbuflen ())
                if b64data is None:
                    break
                f.write (base64.b64decode (b64data))
            self.client.service.CloseFile (handle)
        self.debug ('done')
    
    def path_exists (self, path):
        return os.path.exists (self.__add_prefix (path))

    def path_isfile (self, path):
        return os.path.isfile (self.__add_prefix (path))

    def path_is_dir (self, path):
        return os.path.isdir (self.__add_prefix (path))

    def delete (self, path):
        if self.path_isfile (path):
            self.debug ('Deleting file \'{0}\' ...'.format (path), False)
            os.remove (path)
            self.debug ('done')

    def rmdir (self, path):
        if self.path_isdir (path):
            self.debug ('Removing directory \'{0}\' ...'.format (path), False)
            shutil.rmtree (path)
            self.debug ('done')

    def mkdir (self, path):
        if not self.path_isdir (path):
            self.debug ('Adding directory \'{0}\' ...'.format (path), False)
            os.makedirs (path)
            self.debug ('done')

    def directory_has_local_changes (self, ifolder_id, entry_id, path):
        has_local_changes = False
        entries = self.dbm.get_entries_by_parent (entry_id)
        for entry in entries:
            if entry['digest'] == 'DIRECTORY':
                has_local_changes = has_local_changes or \
                    self.directory_has_local_changes \
                    (entry['ifolder'], entry['id'], entry['path'])
            else:
                has_local_changes = has_local_changes or \
                    self.file_has_local_changes \
                    (entry['ifolder'], entry['id'], entry['path'])
                if has_local_changes:
                    return True
        return has_local_changes

    def file_has_local_changes (self, ifolder_id, entry_id, path):
        entry = self.dbm.get_entry (ifolder_id, entry_id)
        if not self.path_exists (path):
            if entry is None:
                return False
            else:
                return True
        else:
            if entry is None:
                return True
            else:
                old_digest = entry['digest']
                new_digest = self.__md5_hash (path)
                if old_digest != new_digest:
                    return True
                else:
                    return False
        return True
        
    def __add_ifolder (self, ifolder_id, mtime, name):
        ifolder_as_entry = self.client.service.GetEntries \
            (ifolder_id, ifolder_id, 0, 1)
        if ifolder_as_entry.Total > 0:
            for ifolder_entry in ifolder_as_entry.Items.iFolderEntry:
                update_dbm = self.conflicts_handler.add_directory \
                    (ifolder_entry.iFolderID, ifolder_entry.ID, name)
                if update_dbm:
                    self.dbm.add_ifolder \
                        (ifolder_id, mtime, name, ifolder_entry.ID)

    def __add_entries (self, ifolder_id):
        entries = self.__get_children_by_ifolder (ifolder_id)
        entries_count = entries.Total
        if entries_count > 0:
            for entry in entries.Items.iFolderEntry:
                latest_change = self.__get_latest_change (ifolder_id, entry.ID)
                if latest_change.Total > 0:
                    for change in latest_change.Items.ChangeEntry:
                        self.__apply_change \
                            (ifolder_id, entry.ParentID, change)
                        break
                entries_count = entries_count - 1
                if entries_count == 0:
                    break

    def __apply_change (self, ifolder_id, parent_id, change):
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
                    (ifolder_id, change.ID, change.Time, \
                         self.__md5_hash (change.Name), parent_id, \
                         change.Name)
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
            remote_ifolder = self.__get_ifolder (ifolder_t['id'])
        except WebFault, wf:
            return False
        if remote_ifolder is not None:
            if remote_ifolder.LastModified > ifolder_t['mtime']:
                return True
            else:
                return False
        return False

    def __entry_has_changes (self, entry_t):
        latest_change = self.__get_latest_change (entry_t['ifolder'], entry_t['id'])
        if latest_change.Total > 0:
            for change in latest_change.Items.ChangeEntry:
                if change.Time > entry_t['mtime']:
                    return True
                else:
                    return False

    def __update_ifolder (self, ifolder_t):
        entries_t = self.dbm.get_entries_by_ifolder (ifolder_t['id'])
        update_dbm = False
        for entry_t in entries_t:
            if self.__entry_has_changes (entry_t):
                self.debug ('Entry {0} has remote changes'.format (entry_t['id']))
                iet = self.client.factory.create ('iFolderEntryType')
                cea = self.client.factory.create ('ChangeEntryAction')
                latest_change = self.__get_latest_change \
                    (entry_t['ifolder'], entry_t['id'])
                if latest_change.Total > 0:
                    for change in latest_change.Items.ChangeEntry:
                        if change.Action == cea.Add:
                            if change.Type == iet.Directory:
                                update_dbm = \
                                    self.conflicts_handler.add_directory \
                                    (entry_t['ifolder'], entry_t['id'], change.Name)
                            elif change.Type == iet.File:
                                update_dbm = \
                                    self.conflicts_handler.add_file \
                                    (entry_t['ifolder'], entry_t['id'], change.Name)
                        elif change.Action == cea.Modify:
                            if change.Type == iet.Directory:
                                update_dbm = \
                                    self.conflict_handler.modify_directory \
                                    (entry_t['ifolder'], entry_t['id'], change.Name)
                            elif change.Type == iet.File:
                                update_dbm = \
                                    self.conflicts_handler.modify_file \
                                    (entry_t['ifolder'], entry_t['id'], change.Name)
                        elif change.Action == cea.Delete:
                            if change.Type == iet.Directory:
                                update_dbm = \
                                    self.conflicts_handler.delete_directory \
                                    (entry_t['ifolder'], entry_t['id'], change.Name)
                            elif change.Type == iet.File:
                                update_dbm = \
                                    self.conflicts_handler.delete_file \
                                    (entry_t['ifolder'], entry_t['id'], change.Name)
                    if update_dbm:
                        if change.Action == cea.Add or \
                                change.Action == cea.Modify:
                            self.dbm.update_mtime_and_digest_by_entry (\
                                ifolder_t['id'], change.ID, \
                                    change.Time, \
                                    self.__md5_hash (change.Name))
                        elif change.Action == cea.Delete:
                            self.dbm.delete_entry (ifolder_t['id'], change.ID)
        return update_dbm

    def __add_new_entries (self, ifolder_t):
        update_dbm = False
        entries = self.__get_children_by_ifolder (ifolder_t['id'])
        entries_count = entries.Total
        if entries_count > 0:
            for entry in entries.Items.iFolderEntry:
                if self.dbm.get_entry (ifolder_t['id'], entry.ID) is None:
                    latest_change = self.__get_latest_change (ifolder_t['id'], entry.ID)
                    if latest_change.Total > 0:
                        for change in latest_change.Items.ChangeEntry:
                            update_dbm = self.__apply_change \
                                (ifolder_t['id'], entry.ParentID, change)
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
            remote_ifolder = self.__get_ifolder (ifolder_t['id'])
        except WebFault:
            return update_dbm
        if remote_ifolder is None:
            update_dbm = \
                self.conflicts_handler.delete_directory \
                (ifolder_t['id'], ifolder_t['entry_id'], ifolder_t['name'])
            if update_dbm:
                self.dbm.delete_ifolder (ifolder_t['id'])
        return update_dbm

    def __check_for_deleted_membership (self, ifolder_t):
        update_dbm = False
        remote_ifolder = None
        try:
            remote_ifolder = self.__get_ifolder (ifolder_t['id'])
        except WebFault:
            update_dbm = \
                self.conflicts_handler.delete_directory \
                (ifolder_t['id'], ifolder_t['entry_id'], ifolder_t['name'])
            if update_dbm:
                self.dbm.delete_ifolder (ifolder_t['id'])
            return update_dbm

    def update (self):
        update_dbm = False
        try:
            known_ifolders_t = self.dbm.get_ifolders ()
        except sqlite3.OperationalError:
            print 'Could not open the local database. Please, ' \
                'run the `checkout\' action first or provide a valid ' \
                'path to the local database using the `--pathtodb\' ' \
                'command line switch.'
            sys.exit ()
        for ifolder_t in known_ifolders_t:
            if self.__ifolder_has_changes (ifolder_t):
                self.debug ('iFolder {0} has remote changes'.format (ifolder_t['name']))
                update_dbm = update_dbm or self.__update_ifolder (ifolder_t)
                update_dbm = update_dbm or self.__add_new_entries (ifolder_t)
                if update_dbm:
                    self.dbm.update_mtime_by_ifolder \
                        (ifolder_t['id'], self.__get_ifolder \
                             (ifolder_t['id']).LastModified)
            self.__check_for_deleted_ifolder (ifolder_t)
            self.__check_for_deleted_membership (ifolder_t)
        self.__add_new_ifolders ()

    def __md5_hash (self, path):
        path = self.__add_prefix (path)
        md5_hash = 'DIRECTORY'
        if os.path.isfile (path):
            self.debug ('MD5SUM (\'{0}\') ->'.format (path), False)
            m = hashlib.md5 ()
            with open (path, 'rb') as f:
                while True:
                    data = f.read ()
                    m.update (data)
                    if len (data) == 0:
                        break
                md5_hash = m.hexdigest ()
                self.debug ('{0}'.format (md5_hash, True))
        return md5_hash

    def debug (self, message, newline=True):
        if self.cm.get_verbose ():
            if newline:
                print >> sys.stderr, message
            else:
                print >> sys.stderr, message,

    def commit (self):
        try:
            known_ifolders_t = self.dbm.get_ifolders ()
        except sqlite3.OperationalError:
            print 'Could not open the local database. Please, ' \
                'run the `checkout\' action first or provide a valid ' \
                'path to the local database using the `--pathtodb\' ' \
                'command line switch.'
            sys.exit ()
        # We first check for changes made to the entries which were already
        # present in the repository
        # for ifolder_t in known_ifolders_t:
        #     update_ifolder_in_dbm = False
        #     entries_t = self.dbm.get_entries_by_parent (ifolder_t['entry_id'])
        #     for entry_t in entries_t:
        #         update_entry_in_dbm = False
        #         if self.__entry_has_changes (entry_t):
        #             update_entry_in_dbm = \
        #                 self.conflicts_handler.add_remote_entry (entry_t)
        #             update_ifolder_in_dbm = update_ifolder_in_dbm or \
        #                 update_entry_in_dbm
        #             if update_entry_in_dbm:
        #                 latest_change = self.__get_latest_change (\
        #                     entry_t['ifolder'], \
        #                         entry_t['id'])
        #                 if latest_change.Total > 0:
        #                     for change in latest_change.Items.ChangeEntry:
        #                         self.dbm.update_entry (entry_t['ifolder'], \
        #                                                    entry_t['id'], \
        #                                                    change.Time, \
        #                                                    self.__md5_hash ())
                                                   

if __name__ == '__main__':
    cm = CfgManager (DEFAULT_CONFIG_FILE, DEFAULT_SQLITE_FILE, \
                         DEFAULT_SOAP_BUFLEN)
    pf = pyFolder (cm)
