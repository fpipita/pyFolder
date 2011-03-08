# -*- coding: utf-8 -*-

from suds import WebFault
import logging

class Policy:
    def __init__ (self, pyFolder):
        self.pyFolder = pyFolder
        self.logger = logging.getLogger ('pyFolder.Policy')
    
    def add_directory (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def add_file (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def modify_directory (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def modify_file (self, ifolder_id, entry_id, path):
        raise NotImplementedError
    
    def delete_directory (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def delete_file (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def add_remote_directory (self, ifolder_id, parent_id, path):
        raise NotImplementedError
    
    def add_remote_file (self, ifolder_id, parent_id, path):
        raise NotImplementedError

    def modify_remote_directory (self, ifolder_id, entry_id, path):
        raise NotImplementedError
    
    def modify_remote_file (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def delete_remote_directory (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def delete_remote_file (self, ifolder_id, entry_id, path):
        raise NotImplementedError

class DEFAULT (Policy):
    """
    The DEFAULT Policy has the following features:

    [ UPDATE behavior ]
    - If an entry has any kind of remote change, the changes are also applied
      locally. If the entry has also local changes, it is renamed.
    - If a new entry is added remotely, it is also added to the local
      repository. If, in the meanwhile, a local entry (with the same path)
      is added locally, it is renamed.
    - If an entry has remotely been deleted, it is deleted also locally. If
      the local copy has any changes, it is renamed.

    [ COMMIT behavior ]
    - If an entry has local changes (modify, deletion), changes are committed.
    - New locally added entries are committed. If, at the time of the commit,
      a remote entry having the same path and name of the one that is being
      committed has been added, then the entry being committed is renamed, 
      so that both the copies are saved on the server and they will be 
      available for all the users at the next update.
    """
    def add_directory (self, ifolder_id, entry_id, path):
        try:

            self.pyFolder.mkdir (path)

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

    def modify_directory (self, ifolder_id, entry_id, path):
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
                    'iFolder.WebService.FileTypeException':
                self.pyFolder.ignore_locked (Path)
                return None

            elif OriginalException == 'System.NullReferenceException' or \
                    'System.IO.DirectoryNotFoundException':
                self.pyFolder.rollback (iFolderID, Path)
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
                    'iFolder.WebService.FileTypeException':
                self.pyFolder.ignore_locked (Path)
                return None

            elif OriginalException == 'System.NullReferenceException' or \
                    'System.IO.DirectoryNotFoundException':
                self.pyFolder.rollback (iFolderID, Path)
                return None

            else:
                raise

    def modify_remote_directory (self, ifolder_id, entry_id, path):
        return True
    
    def modify_remote_file (self, iFolderID, EntryID, Path):
        try:

            self.pyFolder.remote_file_write (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            return False
    
    def delete_remote_directory (self, iFolderID, iFolderEntryID, Path):
        try:

            self.pyFolder.remote_rmdir (iFolderID, iFolderEntryID, Path)

        except WebFault, wf:
            pass
        return True

    def delete_remote_file (self, iFolderID, iFolderEntryID, Path):
        try:

            self.pyFolder.remote_delete (iFolderID, iFolderEntryID, Path)

        except WebFault, wf:
            pass
        return True

class PolicyFactory:
    @staticmethod
    def create (policy, pyFolder):
        if policy == 'DEFAULT':
            return DEFAULT (pyFolder)
    
    @staticmethod
    def get_factories ():
        return ['DEFAULT', ]
