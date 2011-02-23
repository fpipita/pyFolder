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

    def modify_remote_directory (self, ifolder_id, entry_id, path):
        raise NotImplementedError
    
    def modify_remote_file (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def delete_remote_directory (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def delete_remote_file (self, ifolder_id, entry_id, path):
        raise NotImplementedError

class AlwaysAcceptRemoteChanges (Policy):
    def add_directory (self, ifolder_id, entry_id, path):
        self.pyFolder.mkdir (path)
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
        self.pyFolder.rmdir (path)
        return True

    def delete_file (self, ifolder_id, entry_id, path):
        self.pyFolder.delete (path)
        return True

    def modify_remote_directory (self, ifolder_id, entry_id, path):
        return False
    
    def modify_remote_file (self, ifolder_id, entry_id, path):
        return False
    
    def delete_remote_directory (self, ifolder_id, entry_id, path):
        return False

    def delete_remote_file (self, ifolder_id, entry_id, path):
        return False

class AlwaysKeepLocalChanges (Policy):
    def add_directory (self, ifolder_id, entry_id, path):
        if self.pyFolder.directory_has_local_changes (ifolder_id, entry_id, path):
            return False
        else:
            self.pyFolder.mkdir (path)
            return True

    def add_file (self, ifolder_id, entry_id, path):
        if self.pyFolder.file_has_local_changes (ifolder_id, entry_id, path):
            return False
        else:
            self.pyFolder.fetch (ifolder_id, entry_id, path)
            return True

    def modify_directory (self, ifolder_id, entry_id, path):
        if self.pyFolder.directory_has_local_changes (ifolder_id, entry_id, path):
            return False
        else:
            return True

    def modify_file (self, ifolder_id, entry_id, path):
        if self.pyFolder.file_has_local_changes (ifolder_id, entry_id, path):
            return False
        else:
            self.pyFolder.fetch (ifolder_id, entry_id, path)
            return True
    
    def delete_directory (self, ifolder_id, entry_id, path):
        if self.pyFolder.directory_has_local_changes (ifolder_id, entry_id, path):
            return False
        else:
            self.pyFolder.rmdir (path)
            return True

    def delete_file (self, ifolder_id, entry_id, path):
        if self.pyFolder.file_has_local_changes (ifolder_id, entry_id, path):
            return False
        else:
            self.pyFolder.delete (path)
            return True

    def modify_remote_directory (self, ifolder_id, entry_id, path):
        return False
    
    def modify_remote_file (self, ifolder_id, entry_id, path):
        self.pyFolder.remote_file_write (ifolder_id, entry_id, path)
        return True
    
    def delete_remote_directory (self, ifolder_id, entry_id, path):
        self.pyFolder.remote_rmdir (ifolder_id, entry_id, path)
        return True

    def delete_remote_file (self, ifolder_id, entry_id, path):
        self.pyFolder.remote_delete (ifolder_id, entry_id, path)
        return True

class ConflictsHandlerFactory:
    @staticmethod
    def create (policy, pyFolder):
        if policy == 'AlwaysAcceptRemoteChanges':
            return AlwaysAcceptRemoteChanges (pyFolder)
        elif policy == 'AlwaysKeepLocalChanges':
            return AlwaysKeepLocalChanges (pyFolder)
    
    @staticmethod
    def get_factories ():
        return [\
            'AlwaysAcceptRemoteChanges', \
                'AlwaysKeepLocalChanges' \
                ]
