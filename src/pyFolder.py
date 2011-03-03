#!/usr/bin/python
# -*- coding: utf-8 -*-

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
import time

DEFAULT_SOAP_BUFLEN = 65536
DEFAULT_CONFIG_FILE = os.path.expanduser (os.path.join ('~', '.ifolderrc'))
DEFAULT_SQLITE_FILE = os.path.expanduser (os.path.join ('~', '.ifolderdb'))
SIMIAS_SYNC = 5

class NullHandler (logging.Handler):
    def emit (self, record):
        pass

class pyFolder:
    def __init__ (self, cm, runfromtest=False):
        self.cm = cm
        self.__setup_logger ()
        self.__setup_ifolderws ()
        self.__setup_dbm ()
        self.__setup_policy ()

        if not runfromtest:
            self.__action ()

    def __setup_policy (self):
        self.policy = PolicyFactory.create (self.cm.get_policy (), self)

    def __setup_ifolderws (self):
        self.ifolderws = iFolderWS (self.cm)
        logging.getLogger ('suds.client').addHandler (NullHandler ())

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
        self.ifolderws.delete_entry (\
            iFolderID, iFolderEntryID, Name, iFolderEntryType.File)

    def remote_rmdir (self, iFolderID, iFolderEntryID, Path):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]
        self.ifolderws.delete_entry (\
            iFolderID, iFolderEntryID, Name, iFolderEntryType.Directory)

    def remote_create_file (self, iFolderID, ParentID, Path):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]
        return self.ifolderws.create_entry \
            (iFolderID, ParentID, Name, iFolderEntryType.File)

    def remote_mkdir (self, iFolderID, ParentID, Path):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]
        return self.ifolderws.create_entry \
            (iFolderID, ParentID, Name, iFolderEntryType.Directory)

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
            self.logger.info ('Local File `{0}\' ' \
                                  'successfully updated.'.format (Path))
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
                self.logger.info ('Remote File `{0}\' has been ' \
                                       'successfully updated'.format (Path))
            else:
                self.logger.warning ('Error while updating `{0}\''.format (Path))
            return self.ifolderws.close_file (Handle) and Fine
        return False

    def __add_ifolder (self, iFolderID):
        iFolderEntryID = None
        iFolderAsEntry = self.ifolderws.get_ifolder_as_entry (iFolderID)
        iFolder = self.ifolderws.get_ifolder (iFolderID)
        if iFolderAsEntry is not None and iFolder is not None:
            iFolderEntryID = iFolderAsEntry.ID
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
                    self.__add_entry_locally (\
                        iFolderID, iFolderEntry.ParentID, ChangeEntry)

    def __add_entry_locally (self, iFolderID, ParentID, ChangeEntry):
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
                self.__add_entry_to_dbm (\
                    None, \
                        iFolderID, \
                        ChangeEntry.ID, \
                        ChangeEntry.Time, \
                        ParentID, \
                        ChangeEntry.Name)
        return Updated
    
    def add_entry_locally (self, iFolderID, ParentID, Path):
        SearchOperation = self.ifolderws.get_search_operation ()
        Name = os.path.split (Path)[1]

        iFolderEntry = None
        ArrayOfiFolderEntry = self.ifolderws.get_entries_by_name (\
            iFolderID, ParentID, SearchOperation.Contains, Name, \
                0, 1)
        
        if ArrayOfiFolderEntry is not None:
            for _iFolderEntry in ArrayOfiFolderEntry:
                iFolderEntry = _iFolderEntry
                ChangeEntry = self.ifolderws.get_latest_change (\
                    iFolderEntry.iFolderID, iFolderEntry.ID)
                if ChangeEntry is not None:
                    self.__add_entry_locally (\
                        iFolderEntry.iFolderID, \
                            iFolderEntry.ParentID, \
                            ChangeEntry)
                break
        return iFolderEntry
            
    def add_hierarchy_locally (self, iFolderID, ParentID, Path):
        SearchOperation = self.ifolderws.get_search_operation ()

        iFolderEntry = self.add_entry_locally (iFolderID, ParentID, Path)

        ArrayOfiFolderEntry = self.ifolderws.get_entries_by_name (\
            iFolderEntry.iFolderID, iFolderEntry.ID, \
                SearchOperation.Contains, '.', 0, 0)

        if ArrayOfiFolderEntry is not None:
            for _iFolderEntry in ArrayOfiFolderEntry:
                ChangeEntry = self.ifolderws.get_latest_change (\
                    _iFolderEntry.iFolderID, _iFolderEntry.ID)
                if ChangeEntry is not None:
                    self.__add_entry_locally (\
                        _iFolderEntry.iFolderID, _iFolderEntry.ParentID, \
                            ChangeEntry)
                break

    def checkout (self):
        self.dbm.create_schema ()
        ArrayOfiFolder = self.ifolderws.get_all_ifolders ()
        if ArrayOfiFolder is not None:
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

    def __handle_add_action (self, iFolderID, iFolderEntryID, ChangeEntry):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Updated = False
        if ChangeEntry.Type == iFolderEntryType.Directory:
            Updated = self.policy.add_directory \
                (iFolderID, iFolderEntryID, ChangeEntry.Name)
        elif ChangeEntry.Type == iFolderEntryType.File:
            Updated = self.policy.add_file \
                (iFolderID, iFolderEntryID, ChangeEntry.Name)
        if Updated:
            self.__update_entry_in_dbm (iFolderID, iFolderEntryID)
        return Updated

    def __handle_modify_action (self, iFolderID, iFolderEntryID, ChangeEntry):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Updated = False
        if ChangeEntry.Type == iFolderEntryType.Directory:
            Updated = self.policy.modify_directory \
                (iFolderID, iFolderEntryID, ChangeEntry.Name)
        elif ChangeEntry.Type == iFolderEntryType.File:
            Updated = self.policy.modify_file \
                (iFolderID, iFolderEntryID, ChangeEntry.Name)
        if Updated:
            self.__update_entry_in_dbm (iFolderID, iFolderEntryID)
        return Updated

    def __handle_delete_action (self, iFolderID, iFolderEntryID, ChangeEntry):
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Updated = False
        if ChangeEntry.Type == iFolderEntryType.File:
            Updated = self.policy.delete_file (\
                iFolderID, iFolderEntryID, ChangeEntry.Name)
        elif ChangeEntry.Type == iFolderEntryType.Directory:
            Updated = self.policy.delete_directory (\
                iFolderID, iFolderEntryID, ChangeEntry.Name)
            if Updated:
                self.__delete_hierarchy_from_dbm (iFolderID, iFolderEntryID)
        if Updated:
            self.__delete_entry_from_dbm (iFolderID, iFolderEntryID)
        return Updated

    def __update_ifolder (self, iFolderID):
        ListOfEntryTuple = self.dbm.get_entries_by_ifolder (iFolderID)
        ChangeEntryAction = self.ifolderws.get_change_entry_action ()
        Updated = False

        for EntryTuple in ListOfEntryTuple:
            iFolderID = EntryTuple['ifolder']
            iFolderEntryID = EntryTuple['id']
            Path = EntryTuple['path']
            mtime = EntryTuple['mtime']

            if self.dbm.get_entry (iFolderID, iFolderEntryID) is None:
                continue
            
            ChangeEntry = self.__get_change (\
                iFolderID, iFolderEntryID, Path, mtime)
            if ChangeEntry is not None:
                if ChangeEntry.Action == ChangeEntryAction.Add:
                    Updated = self.__handle_add_action \
                        (iFolderID, iFolderEntryID, ChangeEntry) or Updated
                elif ChangeEntry.Action == ChangeEntryAction.Modify:
                    Updated = self.__handle_modify_action \
                        (iFolderID, iFolderEntryID, ChangeEntry) or Updated
                elif ChangeEntry.Action == ChangeEntryAction.Delete:
                    Updated = self.__handle_delete_action \
                        (iFolderID, iFolderEntryID, ChangeEntry) or Updated
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
                        Updated = self.__add_entry_locally (\
                            iFolderID, iFolderEntry.ParentID, \
                                ChangeEntry) or Updated
        return Updated

    def __add_new_ifolders (self):
        ArrayOfiFolder = self.ifolderws.get_all_ifolders ()
        if ArrayOfiFolder is not None:
            for iFolder in ArrayOfiFolder:
                if self.dbm.get_ifolder (iFolder.ID) is None:
                    self.__add_ifolder (iFolder.ID)
                    self.__add_entries (iFolder.ID)

    def __check_for_deleted_ifolder (self, iFolderTuple):
        Updated = False
        iFolderID = iFolderTuple['id']
        iFolderAsEntryID = iFolderTuple['entry_id']
        Name = iFolderTuple['name']

        iFolder = self.ifolderws.get_ifolder (iFolderID)

        if iFolder is None:
            Updated = self.policy.delete_directory (\
                iFolderID, iFolderAsEntryID, Name)
            if Updated:
                self.dbm.delete_entries_by_ifolder (iFolderID)
                self.dbm.delete_ifolder (iFolderID)
        return Updated

    def __check_for_deleted_membership (self, iFolderTuple):
        Updated = False
        iFolderID = iFolderTuple['id']
        iFolderAsEntryID = iFolderTuple['entry_id']
        Name = iFolderTuple['name']

        iFolder = self.ifolderws.get_ifolder (iFolderID)

        if iFolder is None:
            Updated = self.policy.delete_directory \
                (iFolderID, iFolderAsEntryID, Name)
            if Updated:
                self.dbm.delete_entries_by_ifolder (iFolderID)
                self.dbm.delete_ifolder (iFolderID)
        return Updated

    # *args = (iFolderID, iFolderEntryID, ChangeTime, ParentID, Path)
    def __add_entry_to_dbm (self, iFolderEntry, *args):

        iFolderID = None
        iFolderEntryID = None
        ChangeTime = None
        ParentID = None
        Path = None

        if iFolderEntry is None:
            iFolderID, iFolderEntryID, ChangeTime, ParentID, Path = args
        else:
            ChangeEntry = self.ifolderws.get_latest_change \
                (iFolderEntry.iFolderID, iFolderEntry.ID)
            if ChangeEntry is not None:
                iFolderID = iFolderEntry.iFolderID
                iFolderEntryID = iFolderEntry.ID
                ChangeTime = ChangeEntry.Time
                ParentID = iFolderEntry.ParentID
                Path = iFolderEntry.Path

        Hash = self.__md5_hash (Path)
        LocalPath = os.path.normpath (Path)            
        self.dbm.add_entry (\
            iFolderID, iFolderEntryID, ChangeTime, Hash, ParentID, \
                Path, LocalPath)

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
    
    def rename (self, src, dst):
        src = self.__add_prefix (src)
        dst = self.__add_prefix (dst)
        try:
            os.rename (src, dst)
            self.logger.info ('Renamed `{0}\' to `{1}\''.format (src, dst))
        except OSError, ose:
            self.logger.error (ose)
            raise

    def delete (self, path):
        path = self.__add_prefix (path)
        try:
            os.remove (path)
            self.logger.info ('Deleted local file `{0}\''.format (path))
        except OSError, ose:
            self.logger.error (ose)
            raise

    def rmdir (self, path):
        path = self.__add_prefix (path)
        try:
            shutil.rmtree (path)
            self.logger.info ('Deleted local directory `{0}\''.format (path))
        except OSError, ose:
            self.logger.error (ose)
            raise

    def mkdir (self, path):
        path = self.__add_prefix (path)
        try:
            os.makedirs (path)
            self.logger.info ('Added local directory `{0}\''.format (path))
        except OSError, ose:
            self.logger.error (ose)
            raise

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

    def directory_has_local_changes (self, iFolderID, iFolderEntryID, \
                                         LocalPath):
        Changed = False
        ListOfEntryTuple = self.dbm.get_entries_by_parent (iFolderEntryID)

        for EntryTuple in ListOfEntryTuple:
            _iFolderID = EntryTuple['ifolder']
            _iFolderEntryID = EntryTuple['id']
            _LocalPath = EntryTuple['localpath']
            Digest = EntryTuple['digest']

            if Digest == 'DIRECTORY':
                Changed = self.directory_has_local_changes (\
                    _iFolderID, _iFolderEntryID, _LocalPath) or Changed
            else:
                Changed = self.file_has_local_changes (\
                    _iFolderID, _iFolderEntryID, _LocalPath) or Changed
                if Changed:
                    return Changed
        return Changed

    def file_has_local_changes (self, iFolderID, iFolderEntryID, LocalPath):
        EntryTuple = self.dbm.get_entry (iFolderID, iFolderEntryID)
        if not self.path_exists (LocalPath):
            if EntryTuple is None:
                return False
            else:
                return True
        else:
            if EntryTuple is None:
                return True
            else:

                OldDigest = EntryTuple['digest']
                NewDigest = self.__md5_hash (LocalPath)

                if OldDigest != NewDigest:
                    self.logger.info ('File `{0}\' has local ' \
                                          'changes'.format (LocalPath))
                    return True
                else:
                    return False
        
    def __update_entry_in_dbm (self, iFolderID, iFolderEntryID):
        iFolderEntryTuple = self.dbm.get_entry (\
            iFolderID, iFolderEntryID)
        ChangeEntry = None

        while True:
            ChangeEntry = self.ifolderws.get_latest_change (\
                iFolderID, iFolderEntryID)
            if ChangeEntry is not None and \
                    ChangeEntry.Time != iFolderEntryTuple['mtime']:
                break
            time.sleep (SIMIAS_SYNC)

        if ChangeEntry is not None:
            self.dbm.update_mtime_and_digest_by_entry (\
                iFolderID, iFolderEntryID, ChangeEntry.Time, \
                    self.__md5_hash (ChangeEntry.Name))

    def __delete_entry_from_dbm (self, iFolderID, iFolderEntryID):
        self.dbm.delete_entry (iFolderID, iFolderEntryID)

    def update (self):
        try:
            ListOfiFolderTuple = self.dbm.get_ifolders ()
        except sqlite3.OperationalError:
            print >> sys.stderr, 'Could not open the local database. '
            'Please, ' \
                'run the `checkout\' action first ' \
                'or provide a valid path to the local ' \
                'database using the `--pathtodb\' ' \
                'command line switch.'
            sys.exit ()
        for iFolderTuple in ListOfiFolderTuple:
            iFolderID = iFolderTuple['id']
            mtime = iFolderTuple['mtime']

            Updated = False

            if self.__ifolder_has_changes (iFolderID, mtime):
                Updated = self.__update_ifolder (iFolderID) or Updated
                Updated = self.__add_new_entries (iFolderID) or Updated

            if Updated:
                self.__update_ifolder_in_dbm (iFolderID)

            self.__check_for_deleted_ifolder (iFolderTuple)
            self.__check_for_deleted_membership (iFolderTuple)
        self.__add_new_ifolders ()

    def get_local_changes_on_entry (self, iFolderID, iFolderEntryID, \
                                          LocalPath, Digest, \
                                        iFolderEntryType, \
                                        ChangeEntryAction):
        Action = None
        Type = None
        if Digest == 'DIRECTORY':
            Type = iFolderEntryType.Directory
        else:
            Type = iFolderEntryType.File
        if not self.path_exists (LocalPath):
            Action = ChangeEntryAction.Delete
        else:
            if Type == iFolderEntryType.File:
                if self.file_has_local_changes (\
                    iFolderID, iFolderEntryID, LocalPath):
                    Action = ChangeEntryAction.Modify
            elif Type == iFolderEntryType.Directory:
                if self.directory_has_local_changes (\
                    iFolderID, iFolderEntryID, LocalPath):
                    Action = ChangeEntryAction.Modify
        return Action, Type

    def __is_new_local_entry (self, iFolderID, Path, Isdir):
        entry_t = self.dbm.get_entry_by_ifolder_and_localpath (iFolderID, Path)
        if entry_t is None:
            if Isdir:
                self.logger.info ('Found new local ' \
                                      'directory `{0}\''.format (Path))
            else:
                self.logger.info ('Found new local file `{0}\''.format (Path))
            return True
        return False

    def is_new_local_directory (self, iFolderID, Path):
        return self.__is_new_local_entry (iFolderID, Path, Isdir=True)

    def __is_new_local_file (self, iFolderID, Path):
        return self.__is_new_local_entry (iFolderID, Path, Isdir=False)

    def __find_parent (self, iFolderID, Path):
        self.logger.debug ('Finding parent for {0}'.format (Path))
        ParentPath = os.path.split (Path)[0]
        entry_t = self.dbm.get_entry_by_ifolder_and_localpath (\
            iFolderID, ParentPath)
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

    def __commit_added_directories (self, Root, Dirs, iFolderID):
        Updated = False
        for Dir in Dirs:
            Path = os.path.join (self.__remove_prefix (Root), Dir)
            if self.is_new_local_directory (iFolderID, Path):
                ParentID = self.__find_parent (iFolderID, Path)
                if ParentID is not None:
                    iFolderEntry = self.policy.add_remote_directory (\
                        iFolderID, ParentID, Path)
                    if iFolderEntry is not None:
                        Updated = True
                        self.__add_entry_to_dbm (iFolderEntry)
        return Updated

    def __commit_added_files (self, Root, Files, iFolderID):
        Updated = False
        for File in Files:
            Path = os.path.join (self.__remove_prefix (Root), File)
            if self.__is_new_local_file (iFolderID, Path):
                ParentID = self.__find_parent (iFolderID, Path)
                if ParentID is not None:
                    iFolderEntry = self.policy.add_remote_file \
                        (iFolderID, ParentID, Path)
                    if iFolderEntry is not None:
                        self.__add_entry_to_dbm (iFolderEntry)
                        Updated = True
                        if self.policy.modify_remote_file \
                                (iFolderEntry.iFolderID, \
                                     iFolderEntry.ID, \
                                     iFolderEntry.Path):
                            self.__update_entry_in_dbm (\
                                iFolderEntry.iFolderID, iFolderEntry.ID)
        return Updated

    def __commit_added_entries (self, iFolderID, Name):
        Updated = False
        for Root, Dirs, Files in os.walk (self.__add_prefix (Name)):
            Updated = self.__commit_added_directories (\
                Root, Dirs, iFolderID) or Updated
            Updated = self.__commit_added_files (\
                Root, Files, iFolderID) or Updated
        return Updated
                
    def __commit_modified_entry (self, iFolderID, iFolderEntryID, \
                                     Path, EntryType, iFolderEntryType):
        Updated = False
        if EntryType == iFolderEntryType.File:
            Updated = self.policy.modify_remote_file (\
                iFolderID, iFolderEntryID, Path)
        elif EntryType == iFolderEntryType.Directory:
            Updated = self.policy.modify_remote_directory (\
                iFolderID, iFolderEntryID, Path)
        if Updated:
            self.__update_entry_in_dbm (iFolderID, iFolderEntryID)
        return Updated

    def __delete_hierarchy_from_dbm (self, iFolderID, iFolderEntryID):
        ListOfEntryTuple = self.dbm.get_entries_by_parent (iFolderEntryID)
        if len (ListOfEntryTuple) == 0:
            self.dbm.delete_entry (iFolderID, iFolderEntryID)
            return
        for EntryTuple in ListOfEntryTuple:
            ChildrenID = EntryTuple['id']
            if EntryTuple['digest'] == 'DIRECTORY':
                self.__delete_hierarchy_from_dbm (iFolderID, ChildrenID)
            self.dbm.delete_entry (iFolderID, ChildrenID)
    
    def __commit_deleted_entry (self, iFolderID, iFolderEntryID, \
                                    Path, EntryType, iFolderEntryType):
        Updated = False
        if EntryType == iFolderEntryType.File:
            Updated = self.policy.delete_remote_file (\
                iFolderID, iFolderEntryID, Path)
        elif EntryType == iFolderEntryType.Directory:
            Updated = self.policy.delete_remote_directory (\
                iFolderID, iFolderEntryID, Path)
            if Updated:
                self.__delete_hierarchy_from_dbm (iFolderID, iFolderEntryID)
        if Updated:
            self.__delete_entry_from_dbm (iFolderID, iFolderEntryID)
        return Updated
    
    def __commit_existing_entries (self, iFolderID):
        ChangeEntryAction = self.ifolderws.get_change_entry_action ()
        iFolderEntryType = self.ifolderws.get_ifolder_entry_type ()
        Updated = False

        ListOfEntryTuple = self.dbm.get_entries_by_ifolder (iFolderID)

        for EntryTuple in ListOfEntryTuple:
            iFolderEntryID = EntryTuple['id']
            Path = EntryTuple['path']
            LocalPath = EntryTuple['localpath']
            Digest = EntryTuple['digest']

            if self.dbm.get_entry (iFolderID, iFolderEntryID) is None:
                continue
            
            self.logger.debug ('Checking entry `{0}\''.format (LocalPath))

            ChangeType, EntryType = self.get_local_changes_on_entry (\
                iFolderID, iFolderEntryID, LocalPath, Digest, \
                    iFolderEntryType, ChangeEntryAction)

            if ChangeType is not None:
                if ChangeType == ChangeEntryAction.Modify:
                    Updated = self.__commit_modified_entry (\
                        iFolderID, \
                            iFolderEntryID, \
                            Path, \
                            EntryType, \
                            iFolderEntryType) or Updated

                elif ChangeType == ChangeEntryAction.Delete:
                    Updated = self.__commit_deleted_entry (\
                        iFolderID, \
                            iFolderEntryID, \
                            Path, \
                            EntryType, \
                            iFolderEntryType) or Updated
        return Updated

    def commit (self):
        try:
            ListOfiFolderTuple = self.dbm.get_ifolders ()
        except sqlite3.OperationalError:
            print >> sys.stderr, 'Could not open the local database. Please, ' \
                'run the `checkout\' action first or ' \
                'provide a valid path to the local ' \
                'database using the `--pathtodb\' ' \
                'command line switch.'
            sys.exit ()

        # We assume that the pyFolder user isn't allowed to add/delete
        # iFolders, so we are going to check just the entries
        for iFolderTuple in ListOfiFolderTuple:
            iFolderID = iFolderTuple['id']
            Name = iFolderTuple['name']
            
            Updated = False

            Updated = self.__commit_existing_entries (iFolderID) or Updated
            Updated = self.__commit_added_entries (iFolderID, Name) or Updated
            
            if Updated:
                self.__update_ifolder_in_dbm (iFolderID)

if __name__ == '__main__':
    cm = CfgManager (DEFAULT_CONFIG_FILE, DEFAULT_SQLITE_FILE, \
                         DEFAULT_SOAP_BUFLEN)
    pf = pyFolder (cm)
