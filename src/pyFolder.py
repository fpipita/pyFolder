#!/usr/bin/python

from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds import WebFault
from support.dbm import DBM
from support.cfg_manager import CfgManager
from support.conflicts_handler import ConflictsHandlerFactory
import base64
import hashlib
import logging
import os
import shutil
import sqlite3
import sys

DEFAULT_SOAP_BUFLEN = 65536
DEFAULT_CONFIG_FILE = os.path.expanduser (os.path.join ('~', '.ifolderrc'))
DEFAULT_SQLITE_FILE = os.path.expanduser (os.path.join ('~', '.ifolderdb'))

class NullHandler (logging.Handler):
    def emit (self, record):
        pass

class pyFolder:
    def __init__ (self, cm):
        self.cm = cm
        self.__setup_logger ()
        self.__setup_suds_client ()

        self.dbm = DBM (self.cm.get_pathtodb ())
        self.conflicts_handler = ConflictsHandlerFactory.create \
            (cm.get_conflicts (), self)
        self.__action ()
    
    def __setup_suds_client (self):
        transport = HttpAuthenticated (username=self.cm.get_username (), \
                                           password=self.cm.get_password ())
        self.client = Client (self.cm.get_ifolderws (), transport=transport)
        logging.getLogger ('suds.client').addHandler (NullHandler ())

    def __setup_logger (self):
        self.logger = logging.getLogger ('pyFolder')
        self.logger.setLevel (logging.DEBUG)
        if self.cm.get_verbose ():
            self.handler = logging.StreamHandler ()
        else:
            self.handler = NullHandler ()
        self.handler.setLevel (logging.DEBUG)
        formatter = logging.Formatter ('%(asctime)s [%(name)s] ' \
                                           '%(levelname)s ' \
                                           '%(module)s.%(funcName)s - ' \
                                           '%(message)s')
        self.handler.setFormatter (formatter)
        self.logger.addHandler (self.handler)

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

    def __get_entry (self, ifolder_id, entry_id):
        return self.client.service.GetEntry (ifolder_id, entry_id)

    def __get_entry_by_path (self, ifolder_id, path):
        try:
            self.logger.debug ('Getting remote entry `{0}\' '\
                                   'by iFolderID and Path'.format (path))
            entry = self.client.service.GetEntryByPath (ifolder_id, path)
            self.logger.debug ('Got entry with ID={0}'.format (entry.ID))
            return entry
        except WebFault, wf:
            self.logger.error (wf)
            return None

    def __add_prefix (self, path):
        if self.cm.get_prefix () != '':
            return os.path.join (self.cm.get_prefix (), path)
        return path

    def fetch (self, ifolder_id, entry_id, path):
        path = self.__add_prefix (path)
        try:
            self.logger.debug ('Fetching remote file `{0}\''.format (path))
            handle = self.client.service.OpenFileRead (ifolder_id, entry_id)
            with open (path, 'wb') as f:
                while True:
                    b64data = self.client.service.ReadFile \
                        (handle, cm.get_soapbuflen ())
                    if b64data is None:
                        break
                    f.write (base64.b64decode (b64data))
                self.client.service.CloseFile (handle)
            self.logger.debug ('Done')
            return True
        except WebFault, wf:
            self.logger.error (wf)
            return False

    def path_exists (self, path):
        return os.path.exists (self.__add_prefix (path))

    def path_isfile (self, path):
        return os.path.isfile (self.__add_prefix (path))

    def path_isdir (self, path):
        return os.path.isdir (self.__add_prefix (path))

    def delete (self, path):
        if self.path_isfile (path):
            path = self.__add_prefix (path)
            try:
                self.logger.debug ('Deleting local file `{0}\''.format (path))
                os.remove (path)
                self.logger.debug ('Done')
                return True
            except OSError, ose:
                self.logger.error (ose)
                return False

    def rmdir (self, path):
        if self.path_isdir (path):
            path = self.__add_prefix (path)
            try:
                self.logger.debug ('Deleting local directory `{0}\''.format (path))
                shutil.rmtree (path)
                self.logger.debug ('Done')
                return True
            except OSError, ose:
                self.logger.error (ose)
                return False

    def mkdir (self, path):
        if not self.path_isdir (path):
            path = self.__add_prefix (path)
            try:
                self.logger.debug ('Adding local directory `{0}\''.format (path))
                os.makedirs (path)
                self.logger.debug ('Done')
                return True
            except OSError, ose:
                self.logger.error (ose)
                return False
        else:
            return True

    def getsize (self, path):
        return os.path.getsize (self.__add_prefix (path))

    def remote_delete (self, ifolder_id, entry_id, path):
        try:
            self.logger.debug ('Deleting remote file `{0}\''.format (path))
            self.client.service.DeleteEntry (ifolder_id, entry_id)
            self.logger.debug ('Done')
            return True
        except WebFault, wf:
            self.logger.warning (wf)
            return False

    def remote_file_write (self, ifolder_id, entry_id, path):
        try:
            self.logger.debug ('Updating remote file `{0}\''.format (path))
            handle = self.client.service.OpenFileWrite \
                (ifolder_id, entry_id, self.getsize (path))
            with open (self.__add_prefix (path), 'rb') as f:
                while True:
                    data = f.read ()
                    self.client.service.WriteFile (handle, base64.b64encode (data))
                    if len (data) == 0:
                        break
                self.client.service.CloseFile (handle)
                self.logger.debug ('Done')
            return True
        except WebFault, wf:
            self.logger.error (wf)
            return False

    def remote_mkdir (self, ifolder_id, parent_id, path):
        iet = self.client.factory.create ('iFolderEntryType')
        name = os.path.split (path)[1]
        try:
            self.logger.debug ('Creating remote directory `{0}\''.format (name))
            self.client.service.CreateEntry (ifolder_id, parent_id, \
                                                 iet.Directory, name)
            self.logger.debug ('Done')
            return True
        except WebFault, wf:
            self.logger.error (wf)
            return False

    def remote_rmdir (self, ifolder_id, entry_id, path):
        try:
            self.logger.debug ('Deleting remote directory `{0}\''.format (path))
            self.client.service.DeleteEntry (ifolder_id, entry_id)
            self.logger.debug ('Done')
            return True
        except WebFault, wf:
            self.logger.error (wf)
            return False

    def remote_create_file (self, ifolder_id, parent_id, path):
        iet = self.client.factory.create ('iFolderEntryType')
        name = os.path.split (path)[1]
        try:
            self.logger.debug ('Creating remote file `{0}\''.format (name))
            self.client.service.CreateEntry (ifolder_id, parent_id, \
                                                 iet.File, name)
            self.logger.debug ('Done')
            return True
        except WebFault, wf:
            self.logger.error (wf)
            return False

    def __md5_hash (self, path):
        path = self.__add_prefix (path)
        md5_hash = 'DIRECTORY'
        if os.path.isfile (path):
            m = hashlib.md5 ()
            with open (path, 'rb') as f:
                while True:
                    data = f.read ()
                    m.update (data)
                    if len (data) == 0:
                        break
                md5_hash = m.hexdigest ()
        return md5_hash

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
                self.logger.debug ('Comparing MD5 sums for file `{0}\''.format (path))
                old_digest = entry['digest']
                new_digest = self.__md5_hash (path)
                self.logger.debug ('old_digest={0}, new_digest={1}'.format \
                                       (old_digest, new_digest))
                if old_digest != new_digest:
                    self.logger.debug ('MD5 sums differ, file `{0}\' ' \
                                           'has local changes'.format (path))
                    return True
                else:
                    self.logger.debug ('MD5 sums coincide, file `{0}\' ' \
                                           'hasn\'t any local changes'.format (path))
                    return False
        
    def __add_ifolder (self, ifolder_id):
        entry_id = None
        ifolder_as_entry = self.client.service.GetEntries \
            (ifolder_id, ifolder_id, 0, 1)
        ifolder = self.__get_ifolder (ifolder_id)
        if ifolder_as_entry.Total > 0 and ifolder is not None:
            for ifolder_entry in ifolder_as_entry.Items.iFolderEntry:
                entry_id = ifolder_entry.ID
                break
            mtime = ifolder.LastModified
            name = ifolder.Name
            update_dbm = self.conflicts_handler.add_directory \
                (ifolder_id, entry_id, name)
            if update_dbm:
                self.dbm.add_ifolder \
                    (ifolder_id, mtime, name, entry_id)

    def __add_entries (self, ifolder_id):
        entries = self.__get_children_by_ifolder (ifolder_id)
        entries_count = entries.Total
        if entries_count > 0:
            for entry in entries.Items.iFolderEntry:
                latest_change = self.__get_latest_change (ifolder_id, entry.ID)
                if latest_change.Total > 0:
                    for change in latest_change.Items.ChangeEntry:
                        self.__apply_change \
                            (ifolder_id, entry.ParentID, change, entry.Name)
                        break
                entries_count = entries_count - 1
                if entries_count == 0:
                    break

    def __apply_change (self, ifolder_id, parent_id, change, entry_name):
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
                         change.Name, entry_name)
        return update_dbm
        
    def checkout (self):
        self.dbm.create_schema ()
        ifolders = self.__get_all_ifolders ()
        ifolders_count = ifolders.Total
        if ifolders_count > 0:
            for ifolder in ifolders.Items.iFolder:
                self.__add_ifolder (ifolder.ID)
                self.__add_entries (ifolder.ID)
                ifolders_count = ifolders_count - 1
                if ifolders_count == 0:
                    break

    def __ifolder_has_changes (self, ifolder_t):
        self.logger.debug ('Checking whether iFolder `{0}\' has remote ' \
                               'changes'.format (ifolder_t['name']))
        remote_ifolder = None
        try:
            remote_ifolder = self.__get_ifolder (ifolder_t['id'])
        except WebFault, wf:
            self.logger.warning (wf)
            return False
        if remote_ifolder is not None:
            if remote_ifolder.LastModified > ifolder_t['mtime']:
                self.logger.debug ('iFolder `{0}\' has remote ' \
                                'changes'.format (ifolder_t['name']))
                self.logger.debug ('local_mtime={0}, remote_mtime={1}'.format \
                                       (ifolder_t['mtime'], \
                                            remote_ifolder.LastModified))
                return True
            else:
                self.logger.debug ('iFolder `{0}\' hasn\'t any remote ' \
                                       'changes'.format (ifolder_t['name']))
                return False
        return False

    def __entry_has_changes (self, entry_t):
        self.logger.debug ('Checking for remote changes in entry `{0}\''.format \
                               (entry_t['path']))
        latest_change = self.__get_latest_change (entry_t['ifolder'], entry_t['id'])
        if latest_change.Total > 0:
            for change in latest_change.Items.ChangeEntry:
                if change.Time > entry_t['mtime']:
                    self.logger.debug ('Entry {0} has remote ' \
                                           'changes'.format (entry_t['path']))
                    self.logger.debug ('local_mtime={0}, remote_mtime={1}'.format \
                                           (entry_t['mtime'], change.Time))
                    return True
                else:
                    self.logger.debug ('Entry {0} hasn\'t any remote ' \
                                           'changes'.format (entry_t['path']))
                    return False

    def __update_ifolder (self, ifolder_t):
        entries_t = self.dbm.get_entries_by_ifolder (ifolder_t['id'])
        update_dbm = False
        for entry_t in entries_t:
            if self.__entry_has_changes (entry_t):
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
                                (ifolder_t['id'], entry.ParentID, change, entry.Name)
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
                    self.__add_ifolder (ifolder.ID)
                    self.__add_entries (ifolder.ID)
                ifolders_count = ifolders_count - 1
                if ifolders_count == 0:
                    break

    def __check_for_deleted_ifolder (self, ifolder_t):
        update_dbm = False
        remote_ifolder = None
        try:
            remote_ifolder = self.__get_ifolder (ifolder_t['id'])
        except WebFault, wf:
            self.logger.warning (wf)
            return update_dbm
        if remote_ifolder is None:
            update_dbm = \
                self.conflicts_handler.delete_directory \
                (ifolder_t['id'], ifolder_t['entry_id'], ifolder_t['name'])
            if update_dbm:
                self.dbm.delete_entries_by_ifolder (ifolder_t['id'])
                self.dbm.delete_ifolder (ifolder_t['id'])
        return update_dbm

    def __check_for_deleted_membership (self, ifolder_t):
        update_dbm = False
        remote_ifolder = None
        try:
            remote_ifolder = self.__get_ifolder (ifolder_t['id'])
        except WebFault, wf:
            self.logger.warning (wf)
            update_dbm = \
                self.conflicts_handler.delete_directory \
                (ifolder_t['id'], ifolder_t['entry_id'], ifolder_t['name'])
            if update_dbm:
                self.dbm.delete_entries_by_ifolder (ifolder_t['id'])
                self.dbm.delete_ifolder (ifolder_t['id'])
            return update_dbm

    def update (self):
        update_dbm = False
        try:
            known_ifolders_t = self.dbm.get_ifolders ()
        except sqlite3.OperationalError:
            self.logger.error ('Could not open the local database. Please, ' \
                                   'run the `checkout\' action first ' \
                                   'or provide a valid path to the local ' \
                                   'database using the `--pathtodb\' ' \
                                   'command line switch.')
            sys.exit ()
        for ifolder_t in known_ifolders_t:
            if self.__ifolder_has_changes (ifolder_t):
                update_dbm = update_dbm or self.__update_ifolder (ifolder_t)
                update_dbm = update_dbm or self.__add_new_entries (ifolder_t)
                if update_dbm:
                    self.dbm.update_mtime_by_ifolder \
                        (ifolder_t['id'], self.__get_ifolder \
                             (ifolder_t['id']).LastModified)
            self.__check_for_deleted_ifolder (ifolder_t)
            self.__check_for_deleted_membership (ifolder_t)
        self.__add_new_ifolders ()

    def __get_local_changes_on_entry (self, entry_t):
        self.logger.debug ('Checking for local changes on entry `{0}\''.format \
                               (entry_t['path']))
        iet = self.client.factory.create ('iFolderEntryType')
        cea = self.client.factory.create ('ChangeEntryAction')
        change_type = None
        entry_type = None
        if entry_t['digest'] == 'DIRECTORY':
            entry_type = iet.Directory
        else:
            entry_type = iet.File
        if not self.path_exists (entry_t['path']):
            change_type = cea.Delete
        else:
            if entry_type == iet.File:
                if self.file_has_local_changes \
                        (entry_t['ifolder'], entry_t['id'], entry_t['path']):
                    change_type = cea.Modify
            elif entry_type == iet.Directory:
                if self.directory_has_local_changes \
                        (entry_t['ifolder'], entry_t['id'], entry_t['path']):
                    change_type = cea.Modify
        if change_type is not None:
            self.logger.debug ('Entry `{0}\', ' \
                                   'of type `{1}\', has local ' \
                                   'changes of type `{2}\''.format \
                                   (entry_t['path'], entry_type, change_type))
        else:
            self.logger.debug ('Entry `{0}\', ' \
                                   'of type `{1}\', hasn\'t any local ' \
                                   'changes'.format \
                                   (entry_t['path'], entry_type, change_type))
        return cea, iet, change_type, entry_type

    def __remove_prefix (self, path):
        if self.cm.get_prefix () != '':
            prefix = os.path.join (self.cm.get_prefix (), '')
            return path.replace ('{0}'.format (prefix), '')
        return path

    def __is_new_local_entry (self, ifolder_id, path, isdir):
        entry_t = self.dbm.get_entry_by_ifolder_and_path (ifolder_id, path)
        if entry_t is None:
            if isdir:
                self.logger.debug ('Found new local directory `{0}\''.format (path))
            else:
                self.logger.debug ('Found new local file `{0}\''.format (path))
            return True
        return False

    def __is_new_local_directory (self, ifolder_id, path):
        return self.__is_new_local_entry (ifolder_id, path, isdir=True)

    def __is_new_local_file (self, ifolder_id, path):
        return self.__is_new_local_entry (ifolder_id, path, isdir=False)

    def __find_parent (self, ifolder_id, path):
        parent_path = os.path.split (path)[0]
        entry_t = self.dbm.get_entry_by_ifolder_and_path (ifolder_id, parent_path)
        if entry_t is None:
            ifolder_t = self.dbm.get_ifolder (ifolder_id)
            if parent_path == ifolder_t['name']:
                self.logger.debug ('Entry `{0}\' has ' \
                                       'parent iFolder ' \
                                       '`{1}\''.format (path, ifolder_t['name']))
                return ifolder_t['entry_id']
            else:
                self.logger.error ('Could not find parent for ' \
                                       'entry `{0}\''.format (path))
                return None
        self.logger.debug ('Entry `{0}\' has ' \
                               'parent entry `{1}\''.format (path, entry_t['path']))
        return entry_t['id']

    def __add_to_dbm (self, ifolder_id, path):
        try:
            self.logger.debug ('Getting remote entry `{0}\' '\
                                   'by iFolderID and Path'.format (path))
            entry = self.client.service.GetEntryByPath (ifolder_id, path)
            self.logger.debug ('Got entry with ID={0}'.format (entry.ID))
            latest_change = self.__get_latest_change (ifolder_id, entry.ID)
            if latest_change.Total > 0:
                for change in latest_change.Items.ChangeEntry:
                    self.dbm.add_entry (entry.iFolderID, entry.ID, \
                                            change.Time, \
                                            self.__md5_hash (change.Name), \
                                            entry.ParentID, \
                                            entry.Path, \
                                            entry.Name)
                    break
            return True
        except WebFault, wf:
            self.logger.error (wf)
            return False
    
    def __commit_new_entries (self):
        known_ifolders_t = self.dbm.get_ifolders ()
        for ifolder_t in known_ifolders_t:
            self.logger.debug ('Searching for new entries in iFolder `{0}\''.format \
                                   (ifolder_t['name']))
            for root, dirs, files in os.walk (self.__add_prefix (ifolder_t['name'])):
                for name in dirs:
                    path = os.path.join (self.__remove_prefix (root), name)
                    if self.__is_new_local_directory (ifolder_t['id'], path):
                        parent_id = self.__find_parent (ifolder_t['id'], path)
                        if parent_id is not None:
                            if self.conflicts_handler.add_remote_directory \
                                    (ifolder_t['id'], parent_id, path):
                                self.__add_to_dbm (ifolder_t['id'], path)

                for name in files:
                    path = os.path.join (self.__remove_prefix (root), name)
                    if self.__is_new_local_file (ifolder_t['id'], path):
                        parent_id = self.__find_parent (ifolder_t['id'], path)
                        if parent_id is not None:
                            if self.conflicts_handler.add_remote_file \
                                    (ifolder_t['id'], parent_id, path):
                                entry = self.__get_entry_by_path \
                                    (ifolder_t['id'], path)
                                if entry is not None:
                                    if self.conflicts_handler.modify_remote_file \
                                            (ifolder_t['id'], entry.ID, path):
                                        self.__add_to_dbm (ifolder_t['id'], path)
            # Remember to update the iFolder in the database if any new
            # entry is committed

    def commit (self):
        try:
            known_ifolders_t = self.dbm.get_ifolders ()
        except sqlite3.OperationalError:
            self.logger.error ('Could not open the local database. Please, ' \
                                   'run the `checkout\' action first or ' \
                                   'provide a valid path to the local ' \
                                   'database using the `--pathtodb\' ' \
                                   'command line switch.')
            sys.exit ()
        # We assume that the pyFolder user isn't allowed to add/delete
        # iFolders, so we are going to check just the entries
        for ifolder_t in known_ifolders_t:
            self.logger.debug ('Searching for local changes in iFolder ' \
                                   '`{0}\''.format (ifolder_t['name']))
            update_ifolder_in_dbm = False
            entries_t = self.dbm.get_entries_by_ifolder (ifolder_t['id'])
            for entry_t in entries_t:
                self.logger.debug ('Checking entry `{0}\''.format (entry_t['path']))
                update_entry_in_dbm = False
                cea, iet, change_type, entry_type = \
                    self.__get_local_changes_on_entry (entry_t)
                if change_type is not None:
                    if change_type == cea.Modify:
                        if entry_type == iet.File:
                            update_entry_in_dbm = \
                                self.conflicts_handler.modify_remote_file \
                                (entry_t['ifolder'], entry_t['id'], entry_t['path'])
                        elif entry_type == iet.Directory:
                            update_entry_in_dbm = \
                                self.conflicts_handler.modify_remote_directory \
                                (entry_t['ifolder'], entry_t['id'], entry_t['path'])
                        if update_entry_in_dbm:
                            latest_change = self.__get_latest_change \
                                (entry_t['ifolder'], entry_t['id'])
                            if latest_change.Total > 0:
                                for change in latest_change.Items.ChangeEntry:
                                    self.dbm.update_mtime_and_digest_by_entry \
                                        (entry_t['ifolder'], change.ID, change.Time, \
                                             self.__md5_hash (change.Name))
                                    break
                    elif change_type == cea.Delete:
                        if entry_type == iet.File:
                            update_entry_in_dbm = \
                                self.conflicts_handler.delete_remote_file \
                                (entry_t['ifolder'], entry_t['id'], entry_t['path'])
                        elif entry_type == iet.Directory:
                            update_entry_in_dbm = \
                                self.conflicts_handler.delete_remote_directory \
                                (entry_t['ifolder'], entry_t['id'], entry_t['path'])
                            if update_entry_in_dbm:
                                self.dbm.delete_entries_by_parent \
                                    (entry_t['id'])
                        if update_entry_in_dbm:
                            self.dbm.delete_entry (entry_t['ifolder'], entry_t['id'])
                update_ifolder_in_dbm = update_ifolder_in_dbm or \
                    update_entry_in_dbm
            if update_ifolder_in_dbm:
                ifolder = self.__get_ifolder (ifolder_t['id'])
                self.dbm.update_mtime_by_ifolder \
                    (ifolder_t['id'], ifolder.LastModified)
        self.__commit_new_entries ()

if __name__ == '__main__':
    cm = CfgManager (DEFAULT_CONFIG_FILE, DEFAULT_SQLITE_FILE, \
                         DEFAULT_SOAP_BUFLEN)
    pf = pyFolder (cm)
