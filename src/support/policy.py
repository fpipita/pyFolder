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
      locally.
    - If a new entry is added remotely, it is also added to the local
      repository.

    [ COMMIT behavior ]
    - If an entry has local changes (modify, deletion), changes are committed.
    - New locally added entries are committed. If, at the time of the commit,
      a remote entry having the same path and name of the one that is being
      committed has been added, then the entries are renamed, adding a suffix
      with the `OwnerUserName' and both the copies are saved on the server, so
      that they will be available for all the users at the next update.
    """
    def add_directory (self, ifolder_id, entry_id, path):
        try:
            self.pyFolder.mkdir (path)
        except OSError:
            pass
        return True

    def add_file (self, ifolder_id, entry_id, path):
        self.pyFolder.fetch (ifolder_id, entry_id, path)
        return True

    def modify_directory (self, ifolder_id, entry_id, path):
        return True

    def modify_file (self, ifolder_id, entry_id, path):
        self.pyFolder.fetch (ifolder_id, entry_id, path)
        return True
    
    def delete_directory (self, ifolder_id, entry_id, path):
        try:
            self.pyFolder.rmdir (path)
        except OSError:
            pass
        return True

    def delete_file (self, ifolder_id, entry_id, path):
        try:
            self.pyFolder.delete (path)
        except OSError:
            pass
        return True

    def add_remote_directory (self, iFolderID, ParentID, Path):
        try:
            iFolderEntry = \
                self.pyFolder.remote_mkdir (iFolderID, ParentID, Path)
            return iFolderEntry
        except WebFault, wf:
            NewPath = '{0}-{1}'.format (Path, self.pyFolder.cm.get_username ())
            self.pyFolder.rename (Path, NewPath)
            self.pyFolder.add_hierarchy_locally (iFolderID, ParentID, Path)
            iFolderEntry = \
                self.pyFolder.remote_mkdir (iFolderID, ParentID, NewPath)
            return iFolderEntry
    
    def add_remote_file (self, iFolderID, ParentID, Path):
        try:
            iFolderEntry = \
                self.pyFolder.remote_create_file (iFolderID, ParentID, Path)
            return iFolderEntry
        except WebFault, wf:
            NewPath = '{0}-{1}'.format (Path, self.pyFolder.cm.get_username ())
            self.pyFolder.rename (Path, NewPath)
            self.pyFolder.add_entry_locally (iFolderID, ParentID, Path)
            iFolderEntry = \
                self.pyFolder.remote_create_file (\
                iFolderID, ParentID, NewPath)
            return iFolderEntry

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
