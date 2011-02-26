#!/usr/bin/python
from support.dbm import DBM
from support.cfg_manager import CfgManager
from support.policy import PolicyFactory
from support.ifolderws import iFolderWS
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

class pyFolder:
    def __init__ (self, cm):
        self.cm = cm
        self.__setup_logger ()
        self.__setup_ifolderws ()
        self.__setup_dbm ()
        self.__setup_policy ()
        self.__action ()

    def __setup_policy (self):
        self.policy = PolicyFactory.create (cm.get_policy (), self)

    def __setup_ifolderws (self):
        self.ifolderws = iFolderWS (self.cm)

    def __setup_dbm (self):
        self.dbm = DBM (self.cm.get_pathtodb ())
    
    def __setup_logger (self):
        self.logger = logging.getLogger ('pyFolder')
        self.logger.setLevel (logging.INFO)
        if self.cm.get_verbose ():
            self.handler = logging.StreamHandler ()
        else:
            self.handler = NullHandler ()
        formatter = logging.Formatter ('%(asctime)s [%(name)s] ' \
                                           '%(levelname)s ' \
                                           '%(module)s.%(funcName)s - ' \
                                           '%(message)s')
        self.handler.setFormatter (formatter)
        self.logger.addHandler (self.handler)

    def __action (self):
        pyFolder.__dict__[self.cm.get_action ()] (self)

    def remote_delete (self, iFolderID, iFolderEntryID, Path):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]
        return self.ifolderws.delete_entry \
            (iFolderID, iFolderEntryID, Name, iFolderEntryType.File)

    def remote_rmdir (self, iFolderID, iFolderEntryID, Path):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        return self.ifolderws.delete_entry \
            (iFolderID, iFolderEntryID, Path, iFolderEntryType.Directory)

    def remote_create_file (self, iFolderID, ParentID, Path):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]
        return self.ifolderws.create_entry \
            (iFolderID, ParentID, Name, iFolderEntryType.File)

    def remote_mkdir (self, iFolderID, ParentID, Path):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        return self.ifolderws.create_entry \
            (iFolderID, ParentID, Path, iFolderEntryType.Directory)

    def fetch (self, iFolderID, EntryID, Path):
        Path = self.__add_prefix (Path)
        Handle = self.ifolderws.open_file_read (iFolderID, EntryID)
        if Handle is not None:
            with open (Path, 'wb') as f:
                while True:
                    Base64Data = self.ifolderws.read_file (Handle)
                    if Base64Data is None:
                        break
                    f.write (base64.b64decode (Base64Data))
            return self.ifolderws.close_file (Handle)
        return False

    def remote_file_write (self, iFolderID, iFolderEntryID, Path):
        Size = self.getsize (Path)
        Handle = self.ifolderws.open_file_write \
            (iFolderID, iFolderEntryID, Size)
        if Handle is not None:
            Fine = True
            with open (self.__add_prefix (Path), 'rb') as f:
                while True:
                    Data = f.read (self.cm.get_soapbuflen ())
                    if len (Data) == 0:
                        break
                    Fine = Fine and self.ifolderws.write_file \
                        (Handle, base64.b64encode (Data))
            if Fine:
                self.logger.info ('File `{0}\' has been ' \
                                       'successfully updated'.format (Path))
            else:
                self.logger.warning ('Error while updating `{0}\''.format (Path))
            return self.ifolderws.close_file (Handle) and Fine
        return False

    def __add_ifolder (self, iFolderID):
        iFolderEntryID = None
        iFolderiFolderEntry = self.ifolderws.get_ifolder_entry_id (iFolderID)
        iFolder = self.ifolderws.get_ifolder (iFolderID)
        if iFolderiFolderEntry is not None and iFolder is not None:
            iFolderEntryID = iFolderiFolderEntry.ID
            mtime = iFolder.LastModified
            Name = iFolder.Name
            if self.policy.add_directory (iFolderID, iFolderEntryID, Name):
                self.dbm.add_ifolder (iFolderID, mtime, Name, iFolderEntryID)

    def __add_entries (self, iFolderID):
        ArrayOfiFolderEntry = \
            self.ifolderws.get_children_by_ifolder (iFolderID)
        if ArrayOfiFolderEntry is not None:
            for iFolderEntry in ArrayOfiFolderEntry:
                ChangeEntry = self.ifolderws.get_latest_change \
                    (iFolderID, iFolderEntry.ID)
                if ChangeEntry is not None:
                    self.__apply_change \
                        (iFolderID, iFolderEntry.ParentID, ChangeEntry, \
                             iFolderEntry.Name)

    def __apply_change (self, iFolderID, ParentID, ChangeEntry, Name):
        Updated = False
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        ChangeEntryAction = self.ifolderws.get_change_entry_action ()
        if ChangeEntry.Action == ChangeEntryAction.Add or \
                ChangeEntry.Action == ChangeEntryAction.Modify:
            if ChangeEntry.Type == iFolderEntryType.File:
                Updated = self.policy.add_file \
                    (iFolderID, ChangeEntry.ID, ChangeEntry.Name)
            elif ChangeEntry.Type == iFolderEntryType.Directory:
                Updated = self.policy.add_directory \
                    (iFolderID, ChangeEntry.ID, ChangeEntry.Name)
            if Updated:
                self.dbm.add_entry \
                    (iFolderID, ChangeEntry.ID, ChangeEntry.Time, \
                         self.__md5_hash (ChangeEntry.Name), ParentID, \
                         ChangeEntry.Name, Name)
        return Updated

    def checkout (self):
        self.dbm.create_schema ()
        ArrayOfiFolder = self.ifolderws.get_all_ifolders ()
        for iFolder in ArrayOfiFolder:
            self.__add_ifolder (iFolder.ID)
            self.__add_entries (iFolder.ID)

    def __ifolder_has_changes (self, iFolderID, mtime):
        iFolder = self.ifolderws.get_ifolder (iFolderID)
        if iFolder is not None:
            self.logger.debug ('Checking whether iFolder `{0}\' has remote ' \
                                   'changes'.format (iFolder.Name))
            if iFolder.LastModified > mtime:
                self.logger.debug ('iFolder `{0}\' has remote ' \
                                'changes'.format (iFolder.Name))
                self.logger.debug ('local_mtime={0}, remote_mtime={1}'.format \
                                       (mtime, iFolder.LastModified))
                return True
            else:
                self.logger.debug ('iFolder `{0}\' hasn\'t any remote ' \
                                       'changes'.format (iFolder.Name))
                return False
        return False

    def __get_change (self, iFolderID, EntryID, Path, mtime):
        ChangeEntry = self.ifolderws.get_latest_change (iFolderID, EntryID)
        if ChangeEntry is not None:
            if ChangeEntry.Time > mtime:
                self.logger.debug ('Entry {0} has remote ' \
                                       'changes'.format (Path))
                self.logger.debug ('local_mtime={0}, ' \
                                       'remote_mtime={1}'.format \
                                       (mtime, ChangeEntry.Time))
                return ChangeEntry
            else:
                self.logger.debug ('Entry {0} hasn\'t any remote ' \
                                       'changes'.format (Path))
        return None

    def __update_ifolder_in_dbm (self, iFolderID):
        iFolder = self.ifolderws.get_ifolder (iFolderID)
        if iFolder is not None:
            mtime = iFolder.LastModified
            self.dbm.update_mtime_by_ifolder (iFolderID, mtime)

    def __handle_add_action (self, iFolderID, EntryID, ChangeEntry):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Updated = False
        if ChangeEntry.Type == iFolderEntryType.Directory:
            Updated = self.policy.add_directory \
                (iFolderID, EntryID, ChangeEntry.Name)
        elif ChangeEntry.Type == iFolderEntryType.File:
            Updated = self.policy.add_file \
                (iFolderID, EntryID, ChangeEntry.Name)
        if Updated:
            self.__update_entry_in_dbm (iFolderID, EntryID, ChangeEntry)
        return Updated

    def __handle_modify_action (self, iFolderID, EntryID, ChangeEntry):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Updated = False
        if ChangeEntry.Type == iFolderEntryType.Directory:
            Updated = self.policy.modify_directory \
                (iFolderID, EntryID, ChangeEntry.Name)
        elif ChangeEntry.Type == iFolderEntryType.File:
            Updated = self.policy.modify_file \
                (iFolderID, EntryID, ChangeEntry.Name)
        if Updated:
            self.__update_entry_in_dbm (iFolderID, EntryID, ChangeEntry)
        return Updated

    def __handle_delete_action (self, iFolderID, EntryID, ChangeEntry):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Updated = False
        if ChangeEntry.Type == iFolderEntryType.Directory:
            Updated = self.policy.delete_directory \
                (iFolderID, EntryID, ChangeEntry.Name)
                # Optimization : delete also all the entries
                # from the DB that have EntryID as ParentID
        elif ChangeEntry.Type == iFolderEntryType.File:
            Updated = self.policy.delete_file \
                (iFolderID, EntryID, ChangeEntry.Name)
        if Updated:
            self.__delete_entry_from_dbm (iFolderID, EntryID)
        return Updated

    def __update_ifolder (self, iFolderID):
        entries_t = self.dbm.get_entries_by_ifolder (iFolderID)
        ChangeEntryAction = self.ifolderws.get_change_entry_action ()
        Updated = False
        for entry_t in entries_t:
            # Optimization : check for entries deleted from the
            # DB in the meanwhile and skip the checks about them 
            # (useful when removing a directory with many children)
            iFolderID = entry_t['ifolder']
            EntryID = entry_t['id']
            Path = entry_t['path']
            mtime = entry_t['mtime']
            ChangeEntry = self.__get_change (iFolderID, EntryID, Path, mtime)
            if ChangeEntry is not None:
                if ChangeEntry.Action == ChangeEntryAction.Add:
                    Updated = self.__handle_add_action \
                        (iFolderID, EntryID, ChangeEntry) or Updated
                elif ChangeEntry.Action == ChangeEntryAction.Modify:
                    Updated = self.__handle_modify_action \
                        (iFolderID, EntryID, ChangeEntry) or Updated
                elif ChangeEntry.Action == ChangeEntryAction.Delete:
                    Updated = self.__handle_delete_action \
                        (iFolderID, EntryID, ChangeEntry) or Updated
        return Updated

    def __add_new_entries (self, iFolderID):
        Updated = False
        ArrayOfiFolderEntry = \
            self.ifolderws.get_children_by_ifolder (iFolderID)
        if ArrayOfiFolderEntry is not None:
            for iFolderEntry in ArrayOfiFolderEntry:
                if self.dbm.get_entry (iFolderID, iFolderEntry.ID) is None:
                    ChangeEntry = self.ifolderws.get_latest_change \
                        (iFolderID, iFolderEntry.ID)
                    if ChangeEntry is not None:
                        Updated = self.__apply_change \
                            (iFolderID, \
                                 iFolderEntry.ParentID, \
                                 ChangeEntry, \
                                 iFolderEntry.Name) or Updated
        return Updated

    def __add_new_ifolders (self):
        ArrayOfiFolder = self.ifolderws.get_all_ifolders ()
        for iFolder in ArrayOfiFolder:
            if self.dbm.get_ifolder (iFolder.ID) is None:
                self.__add_ifolder (iFolder.ID)
                self.__add_entries (iFolder.ID)

    def __check_for_deleted_ifolder (self, ifolder_t):
        Updated = False
        iFolder = self.ifolderws.get_ifolder (ifolder_t['id'])
        if iFolder is None:
            Updated = self.policy.delete_directory \
                (ifolder_t['id'], ifolder_t['entry_id'], ifolder_t['name'])
            if Updated:
                self.dbm.delete_entries_by_ifolder (ifolder_t['id'])
                self.dbm.delete_ifolder (ifolder_t['id'])
        return Updated

    def __check_for_deleted_membership (self, ifolder_t):
        Updated = False
        iFolder = self.ifolderws.get_ifolder (ifolder_t['id'])
        if iFolder is None:
            Updated = self.policy.delete_directory \
                (ifolder_t['id'], ifolder_t['entry_id'], ifolder_t['name'])
            if Updated:
                self.dbm.delete_entries_by_ifolder (ifolder_t['id'])
                self.dbm.delete_ifolder (ifolder_t['id'])
            return Updated

    def __add_entry_to_dbm (self, iFolderID, Path):
        iFolderEntry = self.ifolderws.get_entry_by_path (iFolderID, Path)
        if iFolderEntry is not None:
            ChangeEntry = self.ifolderws.get_latest_change \
                (iFolderID, iFolderEntry.ID)
            if ChangeEntry is not None:
                self.dbm.add_entry (\
                    iFolderEntry.iFolderID, \
                        iFolderEntry.ID, \
                        ChangeEntry.Time, \
                        self.__md5_hash (ChangeEntry.Name), \
                        iFolderEntry.ParentID, \
                        iFolderEntry.Path, \
                        iFolderEntry.Name)
                return True
            return False
        return False

    def __add_prefix (self, path):
        if self.cm.get_prefix () != '':
            return os.path.join (self.cm.get_prefix (), path)
        return path

    def __remove_prefix (self, path):
        if self.cm.get_prefix () != '':
            prefix = os.path.join (self.cm.get_prefix (), '')
            return path.replace ('{0}'.format (prefix), '')
        return path

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
                self.logger.info ('Deleting local file `{0}\''.format (path))
                os.remove (path)
                return True
            except OSError, ose:
                self.logger.error (ose)
                return False
        return True

    def rmdir (self, path):
        if self.path_isdir (path):
            path = self.__add_prefix (path)
            try:
                self.logger.info ('Deleting local directory `{0}\''.format (path))
                shutil.rmtree (path)
                return True
            except OSError, ose:
                self.logger.error (ose)
                return False
        return True

    def mkdir (self, path):
        if not self.path_isdir (path):
            path = self.__add_prefix (path)
            try:
                self.logger.info ('Adding local directory `{0}\''.format (path))
                os.makedirs (path)
                return True
            except OSError, ose:
                self.logger.error (ose)
                return False
        return True

    def getsize (self, path):
        return os.path.getsize (self.__add_prefix (path))

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
                # Check the or's
                has_local_changes = self.directory_has_local_changes \
                    (entry['ifolder'], entry['id'], entry['path']) or \
                    has_local_changes
            else:
                has_local_changes = self.file_has_local_changes \
                    (entry['ifolder'], entry['id'], entry['path']) or \
                    has_local_changes
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
        
    def __update_entry_in_dbm (self, iFolderID, EntryID, ChangeEntry):
        self.dbm.update_mtime_and_digest_by_entry \
            (iFolderID, EntryID, ChangeEntry.Time, \
             self.__md5_hash (ChangeEntry.Name))

    def __delete_entry_from_dbm (self, iFolderID, EntryID):
        self.dbm.delete_entry (iFolderID, EntryID)

    def update (self):
        Updated = False
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
            iFolderID = ifolder_t['id']
            mtime = ifolder_t['mtime']
            if self.__ifolder_has_changes (iFolderID, mtime):
                Updated = self.__update_ifolder (iFolderID) or Updated
                Updated = self.__add_new_entries (iFolderID) or Updated
                if Updated:
                    self.__update_ifolder_in_dbm (iFolderID)
            self.__check_for_deleted_ifolder (ifolder_t)
            self.__check_for_deleted_membership (ifolder_t)
        self.__add_new_ifolders ()

    def __get_local_changes_on_entry (self, entry_t):
        self.logger.debug ('Checking for local changes ' \
                               'on entry `{0}\''.format \
                               (entry_t['path']))
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        ChangeEntryAction = self.ifolderws.get_change_entry_action ()
        Action = None
        Type = None
        if entry_t['digest'] == 'DIRECTORY':
            Type = iFolderEntryType.Directory
        else:
            Type = iFolderEntryType.File
        if not self.path_exists (entry_t['path']):
            Action = ChangeEntryAction.Delete
        else:
            if Type == iFolderEntryType.File:
                if self.file_has_local_changes \
                        (entry_t['ifolder'], entry_t['id'], entry_t['path']):
                    Action = ChangeEntryAction.Modify
            elif Type == iFolderEntryType.Directory:
                if self.directory_has_local_changes \
                        (entry_t['ifolder'], entry_t['id'], entry_t['path']):
                    Action = ChangeEntryAction.Modify
        if Action is not None:
            self.logger.debug ('{0} `{1}\', has local changes ' \
                                   'of type `{2}\''.format \
                                   (Type, entry_t['path'], Action))
        else:
            self.logger.debug ('{0} `{1}\', hasn\'t any ' \
                                   'local changes.'.format \
                                   (Type, entry_t['path']))
        return ChangeEntryAction, iFolderEntryType, Action, Type

    def __is_new_local_entry (self, iFolderID, Path, Isdir):
        entry_t = self.dbm.get_entry_by_ifolder_and_path (iFolderID, Path)
        if entry_t is None:
            if Isdir:
                self.logger.info ('Found new local directory `{0}\''.format (Path))
            else:
                self.logger.info ('Found new local file `{0}\''.format (Path))
            return True
        return False

    def __is_new_local_directory (self, iFolderID, Path):
        return self.__is_new_local_entry (iFolderID, Path, Isdir=True)

    def __is_new_local_file (self, iFolderID, Path):
        return self.__is_new_local_entry (iFolderID, Path, Isdir=False)

    def __find_parent (self, iFolderID, Path):
        self.logger.debug ('Finding parent for {0}'.format (Path))
        ParentPath = os.path.split (Path)[0]
        entry_t = self.dbm.get_entry_by_ifolder_and_path \
            (iFolderID, ParentPath)
        if entry_t is None:
            ifolder_t = self.dbm.get_ifolder (iFolderID)
            if ParentPath == ifolder_t['name']:
                self.logger.debug ('Parent is iFolder {0}'.format \
                                       (ifolder_t['name']))
                return ifolder_t['entry_id']
            else:
                self.logger.error ('Could not find parent for ' \
                                       '`{0}\''.format (Path))
                return None
        self.logger.debug ('Parent is iFolderEntry `{0}\''.format \
                               (entry_t['path']))
        return entry_t['id']

    def __commit_new_entries (self):
        known_ifolders_t = self.dbm.get_ifolders ()
        for ifolder_t in known_ifolders_t:
            iFolderID = ifolder_t['id']
            Name = ifolder_t['name']
            self.logger.debug \
                ('Searching for new entries in iFolder `{0}\''.format (Name))
            for Root, Dirs, Files in os.walk (self.__add_prefix (Name)):
                for Dir in Dirs:
                    Path = os.path.join (self.__remove_prefix (Root), Dir)
                    if self.__is_new_local_directory (iFolderID, Path):
                        ParentID = self.__find_parent (iFolderID, Path)
                        if ParentID is not None:
                            if self.policy.add_remote_directory \
                                    (iFolderID, ParentID, Path):
                                self.__add_entry_to_dbm (iFolderID, Path)

                for File in Files:
                    Path = os.path.join (self.__remove_prefix (Root), File)
                    if self.__is_new_local_file (iFolderID, Path):
                        ParentID = self.__find_parent (iFolderID, Path)
                        if ParentID is not None:
                            iFolderEntry = self.policy.add_remote_file \
                                (iFolderID, ParentID, Path)
                            if iFolderEntry is not None:
                                if self.policy.modify_remote_file \
                                            (iFolderEntry.iFolderID, \
                                                 iFolderEntry.ID, \
                                                 iFolderEntry.Path):
                                    self.__add_entry_to_dbm (iFolderID, Path)
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
                                self.policy.modify_remote_file \
                                (entry_t['ifolder'], entry_t['id'], entry_t['path'])
                        elif entry_type == iet.Directory:
                            update_entry_in_dbm = \
                                self.policy.modify_remote_directory \
                                (entry_t['ifolder'], entry_t['id'], entry_t['path'])
                        if update_entry_in_dbm:
                            ChangeEntry = self.__get_latest_change \
                                (entry_t['ifolder'], entry_t['id'])
                            if ChangeEntry is not None:
                                self.dbm.update_mtime_and_digest_by_entry \
                                    (entry_t['ifolder'], \
                                         ChangeEntry.ID, \
                                         ChangeEntry.Time, \
                                         self.__md5_hash (ChangeEntry.Name))
                    elif change_type == cea.Delete:
                        if entry_type == iet.File:
                            update_entry_in_dbm = \
                                self.policy.delete_remote_file \
                                (entry_t['ifolder'], entry_t['id'], entry_t['path'])
                        elif entry_type == iet.Directory:
                            update_entry_in_dbm = \
                                self.policy.delete_remote_directory \
                                (entry_t['ifolder'], entry_t['id'], entry_t['path'])
                            if update_entry_in_dbm:
                                self.dbm.delete_entries_by_parent \
                                    (entry_t['id'])
                        if update_entry_in_dbm:
                            self.dbm.delete_entry (entry_t['ifolder'], entry_t['id'])
                update_ifolder_in_dbm = update_ifolder_in_dbm or \
                    update_entry_in_dbm
            if update_ifolder_in_dbm:
                self.__update_ifolder_in_dbm (ifolder_t['id'])
        self.__commit_new_entries ()

if __name__ == '__main__':
    cm = CfgManager (DEFAULT_CONFIG_FILE, DEFAULT_SQLITE_FILE, \
                         DEFAULT_SOAP_BUFLEN)
    pf = pyFolder (cm)
