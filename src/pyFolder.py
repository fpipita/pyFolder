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
import threading

from suds import WebFault

DEFAULT_SOAP_BUFLEN = 65536
DEFAULT_CONFIG_FILE = os.path.expanduser (os.path.join ('~', '.ifolderrc'))
DEFAULT_SQLITE_FILE = os.path.expanduser (os.path.join ('~', '.ifolderdb'))
SIMIAS_SYNC = 5
PYFOLDER_SYNC_INTERVAL = 60
CONFLICTED_SUFFIX = 'conflicted'

class NullHandler (logging.Handler):
    def emit (self, record):
        pass

class pyFolder (threading.Thread):
    def __init__ (self, cm, runfromtest=False):
        threading.Thread.__init__ (self)
        self.cm = cm
        self.__setup_logger ()
        self.__setup_ifolderws ()

        if self.cm.get_action () != 'noninteractive':
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

    def remote_delete (self, iFolderID, EntryID, Path):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]

        try:
            self.ifolderws.delete_entry (iFolderID, EntryID, Name, Type.File)
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def remote_rmdir (self, iFolderID, EntryID, Path):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]

        try:
            self.ifolderws.delete_entry (\
                iFolderID, EntryID, Name, Type.Directory)
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def remote_create_file (self, iFolderID, ParentID, Path):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]

        try:
            return self.ifolderws.create_entry (\
                iFolderID, ParentID, Name, Type.File)
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def remote_mkdir (self, iFolderID, ParentID, Path):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]

        try:
            return self.ifolderws.create_entry (\
                iFolderID, ParentID, Name, Type.Directory)
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def fetch (self, iFolderID, EntryID, Path):
        Path = self.__add_prefix (Path)
        Handle = None

        try:
            Handle = self.ifolderws.open_file_read (iFolderID, EntryID)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if Handle is not None:
            with open (Path, 'wb') as File:
                while True:
                    Base64Data = None

                    try:
                        Base64Data = self.ifolderws.read_file (Handle)
                    except WebFault, wf:
                        self.logger.error (wf)
                        raise

                    if Base64Data is None:
                        break
                    File.write (base64.b64decode (Base64Data))
            try:
                self.ifolderws.close_file (Handle)
            except WebFault, wf:
                self.logger.error (wf)
                raise

    def remote_file_write (self, iFolderID, EntryID, Path):
        Size = self.getsize (Path)
        Handle = None

        try:
            Handle = self.ifolderws.open_file_write (iFolderID, EntryID, Size)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if Handle is not None:
            with open (self.__add_prefix (Path), 'rb') as File:
                while True:
                    Data = File.read (self.cm.get_soapbuflen ())
                    if len (Data) == 0:
                        break

                    try:
                        self.ifolderws.write_file (\
                            Handle, base64.b64encode (Data))
                    except WebFault, wf:
                        self.logger.error (wf)
                        raise

            try:
                self.ifolderws.close_file (Handle)
            except WebFault, wf:
                self.logger.error (wf)
                raise

    def __add_ifolder (self, iFolderID):
        iFolderEntryID = None
        iFolderEntry = None
        iFolder = None

        try:
            iFolderEntry = self.ifolderws.get_ifolder_as_entry (iFolderID)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        try:
            iFolder = self.ifolderws.get_ifolder (iFolderID)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if iFolderEntry is not None and iFolder is not None:
            iFolderEntryID = iFolderEntry.ID
            mtime = iFolder.LastModified
            Name = iFolder.Name

            if self.policy.add_directory (iFolderID, iFolderEntryID, Name):
                self.dbm.add_ifolder (iFolderID, mtime, Name, iFolderEntryID)

    def __add_entries (self, iFolderID):
        EntryList = None

        try:
            EntryList = self.ifolderws.get_children_by_ifolder (iFolderID)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if EntryList is not None:
            for Entry in EntryList:
                ParentID = Entry.ParentID
                Change = None

                try:
                    Change = \
                        self.ifolderws.get_latest_change (iFolderID, Entry.ID)
                except WebFault, wf:
                    self.logger.error (wf)
                    raise

                if Change is not None:
                    self.__add_entry_locally (iFolderID, ParentID, Change)

    def __add_entry_locally (self, iFolderID, ParentID, Change):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Action = self.ifolderws.get_change_entry_action ()
        EntryID = Change.ID
        Name = Change.Name
        Time = Change.Time
        Updated = False

        if Change.Action == Action.Add or Change.Action == Action.Modify:

            if Change.Type == Type.File:
                Updated = self.policy.add_file (iFolderID, EntryID, Name)

            elif Change.Type == Type.Directory:
                Updated = self.policy.add_directory (iFolderID, EntryID, Name)

            if Updated:
                self.add_entry_to_dbm (\
                    None, iFolderID, EntryID, Time, ParentID, Name)

        return Updated
    
    def add_entry_locally (self, iFolderID, ParentID, Path):
        Operation = self.ifolderws.get_search_operation ()
        Name = os.path.split (Path)[1]

        EntryList = None
        
        try:
            EntryList = self.ifolderws.get_entries_by_name (\
                iFolderID, ParentID, Operation.Contains, Name, 0, 1)
        except WebFault, wf:
            self.logger.error (wf)
            raise
        
        if EntryList is not None:
            for Entry in EntryList:
                EntryID = Entry.ID
                ParentID = Entry.ParentID
                Change = None

                try:
                    Change = \
                        self.ifolderws.get_latest_change (iFolderID, EntryID)
                except WebFault, wf:
                    self.logger.error (wf)
                    raise

                if Change is not None:
                    self.__add_entry_locally (iFolderID, ParentID, Change)

                return Entry
        return None
            
    def add_hierarchy_locally (self, iFolderID, ParentID, Path):
        Operation = self.ifolderws.get_search_operation ()

        ParentEntry = self.add_entry_locally (iFolderID, ParentID, Path)
        EntryList = None

        try:
            EntryList = self.ifolderws.get_entries_by_name (\
                iFolderID, ParentEntry.ID, Operation.Contains, '.', 0, 0)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if EntryList is not None:
            for Entry in EntryList:
                Change = None

                try:
                    Change = \
                        self.ifolderws.get_latest_change (iFolderID, Entry.ID)
                except WebFault, wf:
                    self.logger.error (wf)
                    raise

                if Change is not None:
                    ParentID = Entry.ParentID
                    self.__add_entry_locally (iFolderID, ParentID, Change)
                return

    def checkout (self):
        self.dbm.create_schema ()
        iFolderList = None

        try:
            iFolderList = self.ifolderws.get_all_ifolders ()
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if iFolderList is not None:
            for iFolder in iFolderList:
                self.__add_ifolder (iFolder.ID)
                self.__add_entries (iFolder.ID)

    def __ifolder_has_changes (self, iFolderID, mtime):
        iFolder = None

        try:
            iFolder = self.ifolderws.get_ifolder (iFolderID)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if iFolder is not None:
            if iFolder.LastModified > mtime:
                return True
            else:
                return False
        return False

    def __get_change (self, iFolderID, EntryID, Path, mtime):
        Change = None

        try:
            Change = self.ifolderws.get_latest_change (iFolderID, EntryID)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if Change is not None:
            if Change.Time > mtime:
                return Change
        return None

    def __update_ifolder_in_dbm (self, iFolderID):
        iFolder = None
        
        try:
            iFolder = self.ifolderws.get_ifolder (iFolderID)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if iFolder is not None:
            mtime = iFolder.LastModified
            self.dbm.update_mtime_by_ifolder (iFolderID, mtime)

    def __handle_add_action (self, iFolderID, EntryID, Change):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Name = Change.Name
        Updated = False

        if Change.Type == Type.Directory:
            Updated = self.policy.add_directory (iFolderID, EntryID, Name)

        elif Change.Type == Type.File:
            Updated = self.policy.add_file (iFolderID, EntryID, Name)

        if Updated:
            self.__update_entry_in_dbm (iFolderID, EntryID)

        return Updated

    def __handle_modify_action (self, iFolderID, EntryID, Change):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Updated = False
        Name = Change.Name

        if Change.Type == Type.Directory:
            Updated = self.policy.modify_directory (iFolderID, EntryID, Name)

        elif Change.Type == Type.File:
            Updated = self.policy.modify_file (iFolderID, EntryID, Name)

        if Updated:
            self.__update_entry_in_dbm (iFolderID, EntryID)

        return Updated

    def __handle_delete_action (self, iFolderID, EntryID, Change):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Updated = False
        Name = Change.Name

        if Change.Type == Type.File:
            Updated = self.policy.delete_file (iFolderID, EntryID, Name)

        elif Change.Type == Type.Directory:
            Updated = self.policy.delete_directory (iFolderID, EntryID, Name)

            if Updated:
                self.__delete_hierarchy_from_dbm (iFolderID, EntryID)

        if Updated:
            self.__delete_entry_from_dbm (iFolderID, EntryID)

        return Updated

    def __update_ifolder (self, iFolderID):
        EntryTupleList = self.dbm.get_entries_by_ifolder (iFolderID)
        Action = self.ifolderws.get_change_entry_action ()
        Updated = False

        for EntryTuple in EntryTupleList:
            iFolderID = EntryTuple['ifolder']
            EntryID = EntryTuple['id']
            Path = EntryTuple['path']
            mtime = EntryTuple['mtime']

            if self.dbm.get_entry (iFolderID, EntryID) is None:
                continue
            
            Change = self.__get_change (iFolderID, EntryID, Path, mtime)

            if Change is not None:

                if Change.Action == Action.Add:
                    Updated = self.__handle_add_action (\
                        iFolderID, EntryID, Change) or Updated

                elif Change.Action == Action.Modify:
                    Updated = self.__handle_modify_action (\
                        iFolderID, EntryID, Change) or Updated

                elif Change.Action == Action.Delete:
                    Updated = self.__handle_delete_action (\
                        iFolderID, EntryID, Change) or Updated

        return Updated

    def __add_new_entries (self, iFolderID):
        Updated = False
        EntryList = None
        
        try:
            EntryList = self.ifolderws.get_children_by_ifolder (iFolderID)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if EntryList is not None:
            for Entry in EntryList:
                ParentID = Entry.ParentID
                
                if self.dbm.get_entry (iFolderID, Entry.ID) is None:
                    Change = None

                    try:
                        Change = self.ifolderws.get_latest_change (\
                            iFolderID, Entry.ID)
                    except WebFault, wf:
                        self.logger.error (wf)
                        raise

                    if Change is not None:
                        Updated = self.__add_entry_locally (\
                            iFolderID, ParentID, Change) or Updated

        return Updated

    def __add_new_ifolders (self):
        iFolderList = None
        
        try:
            iFolderList = self.ifolderws.get_all_ifolders ()
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if iFolderList is not None:
            for iFolder in iFolderList:
                if self.dbm.get_ifolder (iFolder.ID) is None:
                    self.__add_ifolder (iFolder.ID)
                    self.__add_entries (iFolder.ID)

    def __check_for_deleted_ifolder (self, iFolderTuple):
        Updated = False
        iFolderID = iFolderTuple['id']
        iFolderEntryID = iFolderTuple['entry_id']
        Name = iFolderTuple['name']

        iFolder = None
        try:
            iFolder = self.ifolderws.get_ifolder (iFolderID)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if iFolder is None:

            Updated = self.policy.delete_directory (\
                iFolderID, iFolderEntryID, Name)

            if Updated:
                self.dbm.delete_entries_by_ifolder (iFolderID)
                self.dbm.delete_ifolder (iFolderID)

        return Updated

    def __check_for_deleted_membership (self, iFolderTuple):
        Updated = False
        iFolderID = iFolderTuple['id']
        iFolderEntryID = iFolderTuple['entry_id']
        Name = iFolderTuple['name']

        iFolder = None
        try:
            iFolder = self.ifolderws.get_ifolder (iFolderID)
        except WebFault, wf:
            self.logger.error (wf)
            raise

        if iFolder is None:

            Updated = self.policy.delete_directory \
                (iFolderID, iFolderEntryID, Name)

            if Updated:
                self.dbm.delete_entries_by_ifolder (iFolderID)
                self.dbm.delete_ifolder (iFolderID)

        return Updated

    # *args = (iFolderID, EntryID, Time, ParentID, Path)
    def add_entry_to_dbm (self, Entry, *args):

        iFolderID = None
        EntryID = None
        Time = None
        ParentID = None
        Path = None

        if Entry is None:
            iFolderID, EntryID, Time, ParentID, Path = args
        else:
            
            Change = None
            try:
                Change = self.ifolderws.get_latest_change (\
                    Entry.iFolderID, Entry.ID)
            except WebFault, wf:
                self.logger.error (wf)
                raise

            if Change is not None:
                iFolderID = Entry.iFolderID
                EntryID = Entry.ID
                Time = Change.Time
                ParentID = Entry.ParentID
                Path = Entry.Path

        Hash = self.__md5_hash (Path)
        LocalPath = os.path.normpath (Path)

        self.dbm.add_entry (iFolderID, EntryID, Time, Hash, ParentID, \
                                Path, LocalPath)

    def __add_prefix (self, Path):
        if self.cm.get_prefix () != '':
            return os.path.join (self.cm.get_prefix (), Path)
        return Path

    def __remove_prefix (self, Path):
        if self.cm.get_prefix () != '':
            prefix = os.path.join (self.cm.get_prefix (), '')
            return Path.replace ('{0}'.format (prefix), '')
        return Path

    def path_exists (self, Path):
        return os.path.exists (self.__add_prefix (Path))

    def path_isfile (self, Path):
        return os.path.isfile (self.__add_prefix (Path))

    def path_isdir (self, Path):
        return os.path.isdir (self.__add_prefix (Path))
    
    def rename (self, Src, Dst):
        Src = self.__add_prefix (Src)
        Dst = self.__add_prefix (Dst)
        try:
            os.rename (Src, Dst)
            self.logger.info ('Renamed `{0}\' to `{1}\''.format (Src, Dst))
        except OSError, ose:
            self.logger.error (ose)
            raise

    def delete (self, Path):
        Path = self.__add_prefix (Path)
        try:
            os.remove (Path)
            self.logger.info ('Deleted local file `{0}\''.format (Path))
        except OSError, ose:
            self.logger.error (ose)
            raise

    def rmdir (self, Path):
        Path = self.__add_prefix (Path)
        try:
            shutil.rmtree (Path)
            self.logger.info ('Deleted local directory `{0}\''.format (Path))
        except OSError, ose:
            self.logger.error (ose)
            raise

    def mkdir (self, Path):
        Path = self.__add_prefix (Path)
        try:
            os.makedirs (Path)
            self.logger.info ('Added local directory `{0}\''.format (Path))
        except OSError, ose:
            self.logger.error (ose)
            raise

    def getsize (self, Path):
        return os.path.getsize (self.__add_prefix (Path))

    def __md5_hash (self, Path):
        Path = self.__add_prefix (Path)
        Hash = 'DIRECTORY'
        if os.path.isfile (Path):
            m = hashlib.md5 ()
            with open (Path, 'rb') as File:
                while True:
                    Data = File.read ()
                    m.update (Data)
                    if len (Data) == 0:
                        break
                Hash = m.hexdigest ()
        return Hash

    def directory_has_local_changes (self, iFolderID, EntryID, LocalPath):
        Changed = False

        EntryTupleList = self.dbm.get_entries_by_parent (EntryID)

        for EntryTuple in EntryTupleList:
            ChildEntryID = EntryTuple['id']
            ChildLocalPath = EntryTuple['localpath']
            Digest = EntryTuple['digest']

            if Digest == 'DIRECTORY':
                Changed = self.directory_has_local_changes (\
                    iFolderID, ChildEntryID, ChildLocalPath) or Changed

            else:
                Changed = self.file_has_local_changes (\
                    iFolderID, ChildEntryID, ChildLocalPath) or Changed

                if Changed:
                    return Changed

        return Changed

    def file_has_local_changes (self, iFolderID, EntryID, LocalPath):
        EntryTuple = self.dbm.get_entry (iFolderID, EntryID)

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
        
    def __update_entry_in_dbm (self, iFolderID, EntryID):
        EntryTuple = self.dbm.get_entry (iFolderID, EntryID)

        ChangeEntry = None
        Count = 5

        while Count > 0:
            try:
                Change = self.ifolderws.get_latest_change (iFolderID, EntryID)
            except WebFault, wf:
                self.logger.error (wf)
                raise

            if Change is not None and Change.Time != EntryTuple['mtime']:
                break

            Count = Count - 1
            time.sleep (SIMIAS_SYNC)

        if Change is not None:
            Hash = self.__md5_hash (Change.Name)
            self.dbm.update_mtime_and_digest_by_entry (\
                iFolderID, EntryID, Change.Time, Hash)

    def __delete_entry_from_dbm (self, iFolderID, EntryID):
        self.dbm.delete_entry (iFolderID, EntryID)

    def update (self):
        try:
            iFolderTupleList = self.dbm.get_ifolders ()
        except sqlite3.OperationalError:
            print >> sys.stderr, 'Could not open the local database. '
            'Please, ' \
                'run the `checkout\' action first ' \
                'or provide a valid path to the local ' \
                'database using the `--pathtodb\' ' \
                'command line switch.'
            sys.exit ()
        for iFolderTuple in iFolderTupleList:
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

    def get_local_changes_on_entry (\
        self, iFolderID, EntryID, LocalPath, Digest, Type, Action):
        ChangeAction = None
        ChangeType = None

        if Digest == 'DIRECTORY':
            ChangeType = Type.Directory

        else:
            ChangeType = Type.File

        if not self.path_exists (LocalPath):
            ChangeAction = Action.Delete

        else:
            if ChangeType == Type.File:
                if self.file_has_local_changes (iFolderID, EntryID, LocalPath):
                    ChangeAction = Action.Modify

            elif ChangeType == Type.Directory:
                if self.directory_has_local_changes (\
                    iFolderID, EntryID, LocalPath):
                    ChangeAction = Action.Modify

        return ChangeAction, ChangeType

    def __is_new_local_entry (self, iFolderID, Path, Isdir):
        EntryTuple = \
            self.dbm.get_entry_by_ifolder_and_localpath (iFolderID, Path)

        if EntryTuple is None:
            return True

        return False

    def is_new_local_directory (self, iFolderID, Path):
        return self.path_isdir (Path) and \
            self.__is_new_local_entry (iFolderID, Path, Isdir=True)

    def __is_new_local_file (self, iFolderID, Path):
        return self.path_isfile (Path) and \
            self.__is_new_local_entry (iFolderID, Path, Isdir=False)

    def __find_parent (self, iFolderID, Path):
        ParentPath = os.path.split (Path)[0]

        EntryTuple = \
            self.dbm.get_entry_by_ifolder_and_localpath (iFolderID, ParentPath)

        if EntryTuple is None:
            iFolderTuple = self.dbm.get_ifolder (iFolderID)

            if ParentPath == iFolderTuple['name']:
                return iFolderTuple['entry_id']

            else:
                return None

        return EntryTuple['id']

    def add_remote_hierarchy (self, AncestoriEntry, NewParentPath):
        Head, Tail = os.path.split (NewParentPath)
        iFolderID = AncestoriEntry.iFolderID

        self.__commit_added_directories (Head, [Tail,], iFolderID)
        self.__commit_added_entries (iFolderID, NewParentPath)
    
    def find_closest_ancestor_remotely_alive (self, iFolderID, LocalPath):
        Operation = self.ifolderws.get_search_operation ()
        Head, Tail = os.path.split (LocalPath)

        EntryTuple = self.dbm.get_entry_by_ifolder_and_localpath (\
            iFolderID, Head)

        if EntryTuple == None:
            return LocalPath, self.ifolderws.get_ifolder_as_entry (iFolderID)

        ParentID = EntryTuple['id']
        
        Entry = None
        Done = False

        while not Done:
            try:
                Entry = self.ifolderws.get_entry (iFolderID, ParentID)
                Done = True
                return LocalPath, Entry
            except WebFault, wf:
                self.logger.error (wf)
                OriginalException = wf.fault.detail.detail.OriginalException._type

                if OriginalException == \
                        'iFolder.WebService.EntryDoesNotExistException':
                    Done = True
                    return self.find_closest_ancestor_remotely_alive (\
                        iFolderID, Head)

                elif OriginalException == 'System.NullReferenceException':
                    time.sleep (SIMIAS_SYNC)
                    continue
    
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

    def rollback (self, iFolderID, Path):
        PathToRename, AncestoriFolderEntry = \
            self.find_closest_ancestor_remotely_alive (\
            iFolderID, Path)

        NewParentPath = '{0}-{1}'.format (PathToRename, CONFLICTED_SUFFIX)
        self.rename (PathToRename, NewParentPath)
        
        DeadAncestorEntryTuple = self.dbm.get_entry_by_ifolder_and_localpath (\
            iFolderID, PathToRename)

        iFolderEntryID = DeadAncestorEntryTuple['id']

        self.__delete_hierarchy_from_dbm (iFolderID, iFolderEntryID)
        self.dbm.delete_entry (iFolderID, iFolderEntryID)

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
                
    def run (self):
        self.__setup_dbm ()
        while True:
            self.update ()
            time.sleep (SIMIAS_SYNC)
            self.commit ()
            time.sleep (PYFOLDER_SYNC_INTERVAL)

    def noninteractive (self):
        self.start ()

if __name__ == '__main__':
    cm = CfgManager (DEFAULT_CONFIG_FILE, DEFAULT_SQLITE_FILE, \
                         DEFAULT_SOAP_BUFLEN)
    pf = pyFolder (cm)
