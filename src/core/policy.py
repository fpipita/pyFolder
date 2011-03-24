# -*- coding: utf-8 -*-

from suds import WebFault
import logging

class Policy:
    def __init__ (self, pyFolder):
        self.pyFolder = pyFolder
        self.logger = logging.getLogger ('pyFolder.Policy')

    def __del__ (self):
        self.pyFolder = None
    
    def add_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError

    def add_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError

    def modify_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError

    def modify_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError
    
    def delete_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError

    def delete_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError

    def add_remote_directory (self, iFolderID, ParentID, Path):
        raise NotImplementedError
    
    def add_remote_file (self, iFolderID, ParentID, Path):
        raise NotImplementedError

    def modify_remote_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError
    
    def modify_remote_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError

    def delete_remote_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError

    def delete_remote_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError
    
    def delete_ifolder (self, iFolderID, Path):
        raise NotImplementedError

class DEFAULT (Policy):
    """
    The DEFAULT Policy has the following features:

    [ UPDATE behavior ]
    - If an entry has any kind of remote changes, the changes are also applied
      locally. If the entry has also local changes, it is renamed.
    - If a new entry is added remotely, it is also added to the local
      repository. If, in the meanwhile, a local entry (with the same path)
      is added locally, it is renamed.
    - If an entry has remotely been deleted, it is deleted also locally. If
      the local copy has any changes, it is renamed.
    - If an iFolder has been remotely deleted at the time (or during) the
      update, it is locally removed. If the local copy contained any local
      change (modifies/new files/deletions), the iFolder will be renamed and 
      just removed from the local dbm.

    [ COMMIT behavior ]
    - If an entry has local changes (modify, deletion), changes are committed.
    - New locally added entries are committed. If, at the time of the commit,
      a remote entry having the same path and name of the one that is being
      committed has been added, then the entry being committed is renamed, 
      so that both the copies are saved on the server and they will be 
      available for all the users at the next update.
    """
    def delete_ifolder (self, iFolderID, Path):
        if self.pyFolder.ifolder_has_local_changes (iFolderID):
            self.pyFolder.handle_name_conflict (Path)

        try:

            self.pyFolder.delete_ifolder (iFolderID, Path)
            
        except OSError, ose:
            pass
    
    def add_directory (self, iFolderID, EntryID, Path):
        try:

            self.pyFolder.mkdir (Path)

        except OSError:
            pass
        return True

    def add_file (self, iFolderID, EntryID, Path):
        try:

            if self.pyFolder.file_has_local_changes (\
                iFolderID, EntryID, Path, Localize=True):
                self.pyFolder.handle_name_conflict (Path)

            self.pyFolder.fetch (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type
            
            if OriginalException == \
                    'iFolder.WebService.EntryDoesNotExistException':
                return False
            
            else:
                raise

    def modify_directory (self, iFolderID, EntryID, Path):
        return True

    def modify_file (self, iFolderID, EntryID, Path):
        try:

            if self.pyFolder.file_has_local_changes (\
                iFolderID, EntryID, Path, Localize=True):
                self.pyFolder.handle_name_conflict (Path)

            self.pyFolder.fetch (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type
            
            if OriginalException == \
                    'iFolder.WebService.EntryDoesNotExistException':
                return False
            
            else:
                raise

    def delete_directory (self, iFolderID, EntryID, Path):
        if self.pyFolder.directory_has_local_changes (\
            iFolderID, EntryID) or \
            self.pyFolder.directory_has_new_entries (iFolderID, Path):
            self.pyFolder.handle_name_conflict (Path)

        try:
            
            self.pyFolder.rmdir (Path)

        except OSError:
            pass

        return True

    def delete_file (self, iFolderID, EntryID, Path):
        try:

            if self.pyFolder.file_has_local_changes (\
                iFolderID, EntryID, Path, Localize=True):
                self.pyFolder.handle_name_conflict (Path)

            self.pyFolder.delete (Path)
            
        except OSError:
            pass
        return True

    def add_remote_directory (self, iFolderID, ParentID, Path):
        try:

            Entry = self.pyFolder.remote_mkdir (iFolderID, ParentID, Path)
            self.pyFolder.add_entry_to_dbm (Entry)
            return Entry

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == \
                    'iFolder.WebService.EntryAlreadyExistException':
                self.pyFolder.handle_name_conflict (Path)
                return None
            
            elif OriginalException == \
                    'iFolder.WebService.EntryInvalidCharactersException':
                self.pyFolder.handle_name_conflict (Path, InvalidChars=True)
                return None

            elif OriginalException == \
                    'iFolder.WebService.FileTypeException':
                self.pyFolder.ignore_locked (Path)
                return None

            elif OriginalException == 'System.NullReferenceException' or \
                    OriginalException == \
                    'System.IO.DirectoryNotFoundException':
                self.pyFolder.rollback (iFolderID, Path)
                return None
            
            elif OriginalException == 'Simias.Storage.AccessException':
                self.pyFolder.ignore_no_rights (Path)
                return None

            else:
                raise
    
    def add_remote_file (self, iFolderID, ParentID, Path):
        try:

            Entry = self.pyFolder.remote_create_file (\
                iFolderID, ParentID, Path)

            self.pyFolder.add_entry_to_dbm (Entry)

            return Entry

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == \
                    'iFolder.WebService.EntryAlreadyExistException':
                self.pyFolder.handle_name_conflict (Path)
                return None
            
            elif OriginalException == \
                    'iFolder.WebService.EntryInvalidCharactersException':
                self.pyFolder.handle_name_conflict (Path, InvalidChars=True)
                return None
            
            elif OriginalException == \
                    'iFolder.WebService.FileTypeException':
                self.pyFolder.ignore_locked (Path)
                return None

            elif OriginalException == 'System.NullReferenceException' or \
                    OriginalException == \
                    'System.IO.DirectoryNotFoundException':
                self.pyFolder.rollback (iFolderID, Path)
                return None
            
            elif OriginalException == 'Simias.Storage.AccessException':
                self.pyFolder.ignore_no_rights (Path)
                return None
                
            else:
                raise

    def modify_remote_directory (self, iFolderID, EntryID, Path):
        return True
    
    def modify_remote_file (self, iFolderID, EntryID, Path):
        try:

            self.pyFolder.remote_file_write (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type
            
            if OriginalException == 'System.IO.IOException':
                self.pyFolder.ignore_in_use (Path)
                return False

            elif OriginalException == 'Simias.Storage.AccessException':
                self.pyFolder.ignore_no_rights (Path)
                return False

            elif OriginalException == \
                    'iFolder.WebService.MemberDoesNotExistException' or \
                    OriginalException == \
                    'iFolder.WebService.iFolderDoesNotExistException':
                raise

            else:
                raise
    
    def delete_remote_directory (self, iFolderID, EntryID, Path):
        try:

            self.pyFolder.remote_rmdir (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type
            
            if OriginalException == 'System.IO.IOException':
                self.pyFolder.ignore_in_use (Path)
                return False

            elif OriginalException == 'Simias.Storage.AccessException':
                self.pyFolder.ignore_no_rights (Path)
                return False

            elif OriginalException == \
                    'iFolder.WebService.MemberDoesNotExistException' or \
                    OriginalException == \
                    'iFolder.WebService.iFolderDoesNotExistException':
                raise

            else:
                raise

    def delete_remote_file (self, iFolderID, EntryID, Path):
        try:

            self.pyFolder.remote_delete (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == 'System.IO.IOException':
                self.pyFolder.ignore_in_use (Path)
                return False

            elif OriginalException == 'Simias.Storage.AccessException':
                self.pyFolder.ignore_no_rights (Path)
                return False
            
            elif OriginalException == \
                    'iFolder.WebService.MemberDoesNotExistException' or \
                    OriginalException == \
                    'iFolder.WebService.iFolderDoesNotExistException':
                raise

            else:
                raise

class PolicyFactory:
    @staticmethod
    def create (policy, pyFolder):
        if policy == 'DEFAULT':
            return DEFAULT (pyFolder)
    
    @staticmethod
    def get_factories ():
        return ['DEFAULT', ]
