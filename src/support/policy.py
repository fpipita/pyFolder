# -*- coding: utf-8 -*-

from suds import WebFault
import logging

class Policy:
    def __init__ (self, pyFolder):
        self.pyFolder = pyFolder
        self.logger = logging.getLogger ('pyFolder.Policy')
    
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

    def add_remote_directory (self, iFolderID, parent_id, Path):
        raise NotImplementedError
    
    def add_remote_file (self, iFolderID, parent_id, Path):
        raise NotImplementedError

    def modify_remote_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError
    
    def modify_remote_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError

    def delete_remote_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError

    def delete_remote_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError
    
    def delete_ifolder (self, iFolderID, Name):
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
    def delete_ifolder (self, iFolderID, Name):
        if self.pyFolder.ifolder_has_local_changes (iFolderID):
            ConflictedName = self.pyFolder.add_conflicted_suffix (Name)
            self.pyFolder.rename (Name, ConflictedName)

        try:

            self.pyFolder.delete_ifolder (iFolderID, Name)
            
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
                ConflictedPath = self.pyFolder.add_conflicted_suffix (Path)
                self.pyFolder.rename (Path, ConflictedPath)

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
                ConflictedPath = self.pyFolder.add_conflicted_suffix (Path)
                self.pyFolder.rename (Path, ConflictedPath)

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
            ConflictedPath = self.pyFolder.add_conflicted_suffix (Path)
            self.pyFolder.rename (Path, ConflictedPath)

        try:
            
            self.pyFolder.rmdir (Path)

        except OSError:
            pass

        return True

    def delete_file (self, iFolderID, EntryID, Path):
        try:

            if self.pyFolder.file_has_local_changes (\
                iFolderID, EntryID, Path, Localize=True):
                ConflictedPath = self.pyFolder.add_conflicted_suffix (Path)
                self.pyFolder.rename (Path, ConflictedPath)

            self.pyFolder.delete (Path)
            
        except OSError:
            pass
        return True

    def add_remote_directory (self, iFolderID, ParentID, Path):
        try:

            iFolderEntry = \
                self.pyFolder.remote_mkdir (iFolderID, ParentID, Path)
            self.pyFolder.add_entry_to_dbm (iFolderEntry)
            return iFolderEntry

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == \
                    'iFolder.WebService.EntryAlreadyExistException':
                ConflictedPath = self.pyFolder.add_conflicted_suffix (Path)
                self.pyFolder.rename (Path, ConflictedPath)
                return None
            
            elif OriginalException == \
                    'iFolder.WebService.EntryInvalidCharactersException':
                ValidPath = self.pyFolder.strip_invalid_characters (Path)
                self.pyFolder.rename (Path, ValidPath)
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

            iFolderEntry = \
                self.pyFolder.remote_create_file (iFolderID, ParentID, Path)
            self.pyFolder.add_entry_to_dbm (iFolderEntry)
            return iFolderEntry

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == \
                    'iFolder.WebService.EntryAlreadyExistException':
                ConflictedPath = self.pyFolder.add_conflicted_suffix (Path)
                self.pyFolder.rename (Path, ConflictedPath)
                return None
            
            elif OriginalException == \
                    'iFolder.WebService.EntryInvalidCharactersException':
                ValidPath = self.pyFolder.strip_invalid_characters (Path)
                self.pyFolder.rename (Path, ValidPath)
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
    
    def delete_remote_directory (self, iFolderID, iFolderEntryID, Path):
        try:

            self.pyFolder.remote_rmdir (iFolderID, iFolderEntryID, Path)
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

    def delete_remote_file (self, iFolderID, iFolderEntryID, Path):
        try:

            self.pyFolder.remote_delete (iFolderID, iFolderEntryID, Path)
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
