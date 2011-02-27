# -*- coding: utf-8 -*-

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
        return self.pyFolder.mkdir (path)

    def add_file (self, ifolder_id, entry_id, path):
        return self.pyFolder.fetch (ifolder_id, entry_id, path)

    def modify_directory (self, ifolder_id, entry_id, path):
        return True

    def modify_file (self, ifolder_id, entry_id, path):
        return self.pyFolder.fetch (ifolder_id, entry_id, path)
    
    def delete_directory (self, ifolder_id, entry_id, path):
        return self.pyFolder.rmdir (path)

    def delete_file (self, ifolder_id, entry_id, path):
        return self.pyFolder.delete (path)

    def add_remote_directory (self, ifolder_id, parent_id, path):
        return self.pyFolder.remote_mkdir (ifolder_id, parent_id, path)
    
    def add_remote_file (self, ifolder_id, parent_id, path):
        return self.pyFolder.remote_create_file (ifolder_id, parent_id, path)

    def modify_remote_directory (self, ifolder_id, entry_id, path):
        return False
    
    def modify_remote_file (self, ifolder_id, entry_id, path):
        return self.pyFolder.remote_file_write (ifolder_id, entry_id, path)
    
    def delete_remote_directory (self, ifolder_id, entry_id, path):
        return self.pyFolder.remote_rmdir (ifolder_id, entry_id, path)

    def delete_remote_file (self, ifolder_id, entry_id, path):
        return self.pyFolder.remote_delete (ifolder_id, entry_id, path)

class PolicyFactory:
    @staticmethod
    def create (policy, pyFolder):
        if policy == 'DEFAULT':
            return DEFAULT (pyFolder)
    
    @staticmethod
    def get_factories ():
        return ['DEFAULT', ]
