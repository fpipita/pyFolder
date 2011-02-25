#!/usr/bin/python

from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds import WebFault
from support.dbm import DBM
from support.cfg_manager import CfgManager
from support.policy import PolicyFactory
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
        self.policy = PolicyFactory.create (cm.get_policy (), self)
        self.__action ()
    
    def __setup_suds_client (self):
        transport = HttpAuthenticated (username=self.cm.get_username (), \
                                           password=self.cm.get_password ())
        self.client = Client (self.cm.get_ifolderws (), transport=transport)
        logging.getLogger ('suds.client').addHandler (NullHandler ())

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

    def __get_all_ifolders (self):
        try:
            self.logger.debug ('Retrieving available ' \
                                   'iFolders for user ' \
                                   '`{0}\''.format (cm.get_username ()))
            iFolderSet = self.client.service.GetiFolders (0, 0)
            if iFolderSet.Total > 0:
                self.logger.debug ('{0} iFolder(s) found'.format \
                                       (iFolderSet.Total))
                return iFolderSet.Items.iFolder
            else:
                self.logger.debug ('No iFolders found')
            return None
        except WebFault, wf:
            self.logger.error (wf)
            return None

    def __get_ifolder_entry_id (self, iFolderID):
        try:
            self.logger.debug ('Getting iFolderEntryID for iFolder with ' \
                                   'ID={0}'.format (iFolderID))
            iFolderEntrySet = \
                self.client.service.GetEntries (iFolderID, iFolderID, 0, 1)
            if iFolderEntrySet.Total > 0:
                for iFolderEntry in iFolderEntrySet.Items.iFolderEntry:
                    self.logger.debug ('Success, got iFolderEntryID=' \
                                           '{0}'.format (iFolderEntry.ID))
                    return iFolderEntry
            return None
        except WebFault, wf:
            self.logger.error (wf)
            return None

    def __get_latest_change (self, iFolderID, iFolderEntryID):
        try:
            self.logger.debug ('Getting latest change ' \
                                   'for entry `{0}\''.format (iFolderEntryID))
            ChangeEntrySet = \
                self.client.service.GetChanges \
                (iFolderID, iFolderEntryID, 0, 1)
            if ChangeEntrySet.Total > 0:
                for ChangeEntry in ChangeEntrySet.Items.ChangeEntry:
                    self.logger.debug ('Latest Change for ' \
                                           'iFolderEntry `{0}\' ' \
                                           'is of Type `{1}\''.format \
                                           (ChangeEntry.Name, \
                                                ChangeEntry.Action))
                    return ChangeEntry
            return None
        except WebFault, wf:
            self.logger.error (wf)
            return None
        
    def __get_entry_by_path (self, iFolderID, Path):
        try:
            self.logger.debug ('Getting iFolderEntry `{0}\' '\
                                   'by iFolderID and Path'.format (Path))
            iFolderEntry = self.client.service.GetEntryByPath (iFolderID, Path)
            if iFolderEntry is not None:
                self.logger.debug ('Got iFolderEntry ' \
                                       'with ID={0}'.format (iFolderEntry.ID))
                return iFolderEntry
            else:
                self.logger.debug ('Could not get ' \
                                       'iFolderEntry `{0\''.format (Path))
            return None
        except WebFault, wf:
            self.logger.error (wf)
            return None

    def __get_children_by_ifolder (self, iFolderID):
        try:
            self.logger.debug ('Getting all the children for ' \
                                   'iFolder with ID={0}'.format (iFolderID))
            operation = self.client.factory.create ('SearchOperation')
            iFolderEntrySet = self.client.service.GetEntriesByName \
                (iFolderID, iFolderID, operation.Contains, '.', 0, 0)
            if iFolderEntrySet.Total > 0:
                iFolderEntry = iFolderEntrySet.Items.iFolderEntry
                self.logger.debug ('Found {0} ' \
                                       'children'.format (len (iFolderEntry)))
                return iFolderEntry
            else:
                self.logger.debug ('iFolder with ID={0} ' \
                                       'hasn\'t any children'.format \
                                       (iFolderID))
            return None
        except WebFault, wf:
            self.logger.error (wf)
            return None

    def __get_ifolder (self, iFolderID):
        try:
            self.logger.debug ('Getting iFolder with ID={0}'.format \
                                   (iFolderID))
            iFolder = self.client.service.GetiFolder (iFolderID)
            if iFolder is not None:
                self.logger.debug ('iFolder with ID={0} has ' \
                                       'name `{1}\''.format \
                                       (iFolder.ID, iFolder.Name))
                return iFolder
            else:
                self.logger.debug ('Could not get iFolder with ID={0}'.format \
                                       (iFolderID))
            return None
        except WebFault, wf:
            self.logger.error (wf)
            return None

    def __get_entry (self, iFolderID, iFolderEntryID):
        try:
            self.logger.debug ('Getting iFolderEntry with ID={0} ' \
                                   'and iFolderID={1}'.format \
                                   (iFolderID, iFolderEntryID))
            iFolderEntry = self.client.service.GetEntry \
                (iFolderID, iFolderEntryID)
            if iFolderEntry is not None:
                self.logger.debug ('Got iFolderEntry with ' \
                                       'name `{0}\' '.format \
                                       (iFolderEntry.Name))
                return iFolderEntry
            else:
                self.logger.debug ('Could not get iFolderEntry with ID={0} ' \
                                       'and iFolderID={1}'.format \
                                       (iFolderID, iFolderEntryID))
            return None
        except WebFault, wf:
            self.logger.error (wf)
            return None
        
    def __open_file_read (self, iFolderID, iFolderEntryID):
        try:
            self.logger.debug ('Opening remote file with iFolderID={0} ' \
                                   'and ID={0} for writing'.format \
                                   (iFolderID, iFolderEntryID))
            Handle = self.client.service.OpenFileRead \
                (iFolderID, iFolderEntryID)
            if Handle is not None:
                self.logger.debug ('Success, got handle={0}'.format (Handle))
                return Handle
            else:
                self.logger.debug ('Could not open remote file with ' \
                                       'iFolderID={0} ' \
                                       'and ID={0} for writing'.format \
                                       (iFolderID, iFolderEntryID))
            return None
        except WebFault, wf:
            self.logger.error (wf)
            return None

    def __read_file (self, Handle):
        try:
            return self.client.service.ReadFile \
                (Handle, self.cm.get_soapbuflen ())
        except WebFault, wf:
            self.logger.error (wf)
            return None

    def __open_file_write (self, iFolderID, iFolderEntryID, Path):
        try :
            self.logger.debug ('Opening remote file `{0}\' ' \
                                   'for writing'.format (Path))
            Handle = self.client.service.OpenFileWrite \
                (iFolderID, iFolderEntryID, self.getsize (Path))
            if Handle is not None:
                self.logger.debug ('Succes, got Handle={0}'.format (Handle))
                return Handle
            else:
                self.logger.debug ('Could not open remote file `{0}\' ' \
                                       'for writing'.format (Path))
            return None
        except WebFault, wf:
            self.logger.debug (wf)
            return None
    
    def __write_file (self, Handle, Data):
        try:
            self.client.service.WriteFile (Handle, base64.b64encode (Data))
            return True
        except WebFault, wf:
            self.logger.error (wf)
            return False

    def __close_file (self, Handle):
        try:
            self.logger.debug ('Closing file with handle={0}'.format (Handle))
            self.client.service.CloseFile (Handle)
            self.logger.debug ('File with handle={0} closed'.format (Handle))
            return True
        except WebFault, wf:
            self.logger.error (wf)
            return False

    def __create_entry (self, iFolderID, ParentID, Path, Type):
        Name = os.path.split (Path)[1]
        try:
            self.logger.debug ('Creating remote ' \
                                   'iFolderEntry `{0}\'' \
                                   'of Type `{1}\''.format (Name, Type))
            iFolderEntry = \
                self.client.service.CreateEntry \
                (iFolderID, ParentID, Type, Name)
            if iFolderEntry is not None:
                self.logger.debug ('Success, got id={0}'.format (iFolderEntry.ID))
                return iFolderEntry
            else:
                self.logger.debug ('Could not create ' \
                                       'iFolderEntry `{0}\''.format (Name))
            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def __delete_entry (self, iFolderID, iFolderEntryID, Path, Type):
        Name = os.path.split (Path)[1]
        try:
            self.logger.debug ('Deleting remote ' \
                                   'iFolderEntry `{0}\'' \
                                   'of Type `{1}\''.format (Name, Type))
            self.client.service.DeleteEntry (iFolderID, iFolderEntryID)
            self.logger.debug ('Remote iFolderEntry `{0}\' ' \
                                   'of Type `{1}\' ' \
                                   'has been deleted'.format (Name, Type))
            return True
        except WebFault, wf:
            self.logger.error (wf)
            return False

    def remote_delete (self, iFolderID, iFolderEntryID, Path):
        iFolderEntryType = self.client.factory.create ('iFolderEntryType')
        return self.__delete_entry (iFolderID, iFolderEntryID, Path, \
                                        iFolderEntryType.File)

    def remote_rmdir (self, iFolderID, iFolderEntryID, Path):
        iFolderEntryType = self.client.factory.create ('iFolderEntryType')
        return self.__delete_entry (iFolderID, iFolderEntryID, Path, \
                                        iFolderEntryType.Directory)

    def remote_create_file (self, iFolderID, ParentID, Path):
        iFolderEntryType = self.client.factory.create ('iFolderEntryType')
        return self.__create_entry (iFolderID, ParentID, Path, \
                                        iFolderEntryType.File)

    def remote_mkdir (self, iFolderID, ParentID, Path):
        iFolderEntryType = self.client.factory.create ('iFolderEntryType')
        return self.__create_entry (iFolderID, ParentID, Path, \
                                        iFolderEntryType.Directory)
    def __add_prefix (self, path):
        if self.cm.get_prefix () != '':
            return os.path.join (self.cm.get_prefix (), path)
        return path

    def fetch (self, iFolderID, EntryID, Path):
        Path = self.__add_prefix (Path)
        Handle = self.__open_file_read (iFolderID, EntryID)
        if Handle is not None:
            with open (Path, 'wb') as f:
                while True:
                    Base64Data = self.__read_file (Handle)
                    if Base64Data is None:
                        break
                    f.write (base64.b64decode (Base64Data))
            return self.__close_file (Handle)
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

    def remote_file_write (self, iFolderID, iFolderEntryID, Path):
        Handle = self.__open_file_write (iFolderID, iFolderEntryID, Path)
        if Handle is not None:
            Fine = True
            with open (self.__add_prefix (Path), 'rb') as f:
                while True:
                    Data = f.read (self.cm.get_soapbuflen ())
                    if len (Data) == 0:
                        break
                    Fine = Fine and self.__write_file (Handle, Data)
            if Fine:
                self.logger.info ('File `{0}\' has been ' \
                                       'successfully updated'.format (Path))
            else:
                self.logger.warning ('Error while updating `{0}\''.format (Path))
            return self.__close_file (Handle) and Fine
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
        
    def __add_ifolder (self, iFolderID):
        iFolderEntryID = None
        iFolderiFolderEntry = self.__get_ifolder_entry_id (iFolderID)
        iFolder = self.__get_ifolder (iFolderID)
        if iFolderiFolderEntry is not None and iFolder is not None:
            iFolderEntryID = iFolderiFolderEntry.ID
            mtime = iFolder.LastModified
            Name = iFolder.Name
            if self.policy.add_directory (iFolderID, iFolderEntryID, Name):
                self.dbm.add_ifolder (iFolderID, mtime, Name, iFolderEntryID)

    def __add_entries (self, iFolderID):
        ArrayOfiFolderEntry = self.__get_children_by_ifolder (iFolderID)
        if ArrayOfiFolderEntry is not None:
            for iFolderEntry in ArrayOfiFolderEntry:
                ChangeEntry = self.__get_latest_change (iFolderID, \
                                                            iFolderEntry.ID)
                if ChangeEntry is not None:
                    self.__apply_change (iFolderID, \
                                             iFolderEntry.ParentID, \
                                             ChangeEntry, \
                                             iFolderEntry.Name)

    def __apply_change (self, ifolder_id, parent_id, change, entry_name):
        update_dbm = False
        iet = self.client.factory.create ('iFolderEntryType')
        cea = self.client.factory.create ('ChangeEntryAction')
        if change.Action == cea.Add or change.Action == cea.Modify:
            if change.Type == iet.File:
                update_dbm = \
                    self.policy.add_file \
                    (ifolder_id, change.ID, change.Name)
            elif change.Type == iet.Directory:
                update_dbm = \
                    self.policy.add_directory \
                    (ifolder_id, change.ID, change.Name)
            if update_dbm:
                self.dbm.add_entry \
                    (ifolder_id, change.ID, change.Time, \
                         self.__md5_hash (change.Name), parent_id, \
                         change.Name, entry_name)
        return update_dbm
        
    def checkout (self):
        self.dbm.create_schema ()
        ArrayOfiFolder = self.__get_all_ifolders ()
        for iFolder in ArrayOfiFolder:
            self.__add_ifolder (iFolder.ID)
            self.__add_entries (iFolder.ID)

    def __ifolder_has_changes (self, iFolderID, mtime):
        iFolder = self.__get_ifolder (iFolderID)
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
        ChangeEntry = self.__get_latest_change (iFolderID, EntryID)
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

    def __update_entry_in_dbm (self, iFolderID, EntryID, ChangeEntry):
        self.dbm.update_mtime_and_digest_by_entry \
            (iFolderID, EntryID, ChangeEntry.Time, \
             self.__md5_hash (ChangeEntry.Name))

    def __update_ifolder_in_dbm (self, iFolderID):
        iFolder = self.__get_ifolder (iFolderID)
        if iFolder is not None:
            mtime = iFolder.LastModified
            self.dbm.update_mtime_by_ifolder (iFolderID, mtime)

    def __delete_entry_from_dbm (self, iFolderID, EntryID):
        self.dbm.delete_entry (iFolderID, EntryID)

    def __handle_add_action (self, iFolderID, EntryID, ChangeEntry):
        iFolderEntryType = self.client.factory.create ('iFolderEntryType')
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
        iFolderEntryType = self.client.factory.create ('iFolderEntryType')
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
        iFolderEntryType = self.client.factory.create ('iFolderEntryType')
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
        ChangeEntryAction = self.client.factory.create ('ChangeEntryAction')
        updated = False
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
                    updated = self.__handle_add_action \
                        (iFolderID, EntryID, ChangeEntry) or updated
                elif ChangeEntry.Action == ChangeEntryAction.Modify:
                    updated = self.__handle_modify_action \
                        (iFolderID, EntryID, ChangeEntry) or updated
                elif ChangeEntry.Action == ChangeEntryAction.Delete:
                    updated = self.__handle_delete_action \
                        (iFolderID, EntryID, ChangeEntry) or updated
        return updated

    def __add_new_entries (self, iFolderID):
        updated = False
        ArrayOfiFolderEntry = self.__get_children_by_ifolder (iFolderID)
        if ArrayOfiFolderEntry is not None:
            for iFolderEntry in ArrayOfiFolderEntry:
                if self.dbm.get_entry (iFolderID, iFolderEntry.ID) is None:
                    ChangeEntry = self.__get_latest_change \
                        (iFolderID, iFolderEntry.ID)
                    if ChangeEntry is not None:
                        updated = self.__apply_change \
                            (iFolderID, \
                                 iFolderEntry.ParentID, \
                                 ChangeEntry, \
                                 iFolderEntry.Name) or updated
        return updated

    def __add_new_ifolders (self):
        ArrayOfiFolder = self.__get_all_ifolders ()
        for iFolder in ArrayOfiFolder:
            if self.dbm.get_ifolder (iFolder.ID) is None:
                self.__add_ifolder (iFolder.ID)
                self.__add_entries (iFolder.ID)

    def __check_for_deleted_ifolder (self, ifolder_t):
        update_dbm = False
        iFolder = self.__get_ifolder (ifolder_t['id'])
        if iFolder is None:
            update_dbm = \
                self.policy.delete_directory \
                (ifolder_t['id'], ifolder_t['entry_id'], ifolder_t['name'])
            if update_dbm:
                self.dbm.delete_entries_by_ifolder (ifolder_t['id'])
                self.dbm.delete_ifolder (ifolder_t['id'])
        return update_dbm

    def __check_for_deleted_membership (self, ifolder_t):
        update_dbm = False
        iFolder = self.__get_ifolder (ifolder_t['id'])
        if iFolder is None:
            update_dbm = \
                self.policy.delete_directory \
                (ifolder_t['id'], ifolder_t['entry_id'], ifolder_t['name'])
            if update_dbm:
                self.dbm.delete_entries_by_ifolder (ifolder_t['id'])
                self.dbm.delete_ifolder (ifolder_t['id'])
            return update_dbm

    def update (self):
        updated = False
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
            if self.__ifolder_has_changes (ifolder_t['id'], \
                                               ifolder_t['mtime']):
                iFolderID = ifolder_t['id']
                updated = self.__update_ifolder (iFolderID) or updated
                updated = self.__add_new_entries (iFolderID) or updated
                if updated:
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

    def __add_to_dbm (self, iFolderID, Path):
        iFolderEntry = self.__get_entry_by_path (iFolderID, Path)
        if iFolderEntry is not None:
            ChangeEntry = self.__get_latest_change (iFolderID, iFolderEntry.ID)
            if ChangeEntry is not None:
                self.dbm.add_entry (iFolderEntry.iFolderID, \
                                        iFolderEntry.ID, \
                                        ChangeEntry.Time, \
                                        self.__md5_hash (ChangeEntry.Name), \
                                        iFolderEntry.ParentID, \
                                        iFolderEntry.Path, \
                                        iFolderEntry.Name)
                return True
            return False
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
                            if self.policy.add_remote_directory \
                                    (ifolder_t['id'], parent_id, path):
                                self.__add_to_dbm (ifolder_t['id'], path)

                for name in files:
                    path = os.path.join (self.__remove_prefix (root), name)
                    if self.__is_new_local_file (ifolder_t['id'], path):
                        parent_id = self.__find_parent (ifolder_t['id'], path)
                        if parent_id is not None:
                            iFolderEntry = self.policy.add_remote_file \
                                (ifolder_t['id'], parent_id, path)
                            if iFolderEntry is not None:
                                if self.policy.modify_remote_file \
                                            (iFolderEntry.iFolderID, \
                                                 iFolderEntry.ID, \
                                                 iFolderEntry.Path):
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
                iFolder = self.__get_ifolder (ifolder_t['id'])
                self.dbm.update_mtime_by_ifolder \
                    (ifolder_t['id'], iFolder.LastModified)
        self.__commit_new_entries ()

if __name__ == '__main__':
    cm = CfgManager (DEFAULT_CONFIG_FILE, DEFAULT_SQLITE_FILE, \
                         DEFAULT_SOAP_BUFLEN)
    pf = pyFolder (cm)
