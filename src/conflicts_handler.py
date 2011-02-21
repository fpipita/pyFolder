class Policy:
    def __init__ (self, pyFolder):
        self.pyFolder = pyFolder
    
    def add_directory (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def add_file (self, ifolder_id, entry_id, name):
        raise NotImplementedError

    def modify_directory (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def modify_file (self, ifolder_id, entry_id, name):
        raise NotImplementedError
    
    def delete_directory (self, ifolder_id, entry_id, path):
        raise NotImplementedError

    def delete_file (self, ifolder_id, entry_id, path):
        raise NotImplementedError

class AlwaysAcceptRemoteChanges (Policy):
    def add_directory (self, ifolder_id, entry_id, path):
        self.pyFolder.mkdir (path)
        return True

    def add_file (self, ifolder_id, entry_id, name):
        self.pyFolder.fetch (ifolder_id, entry_id, name)
        return True

    def modify_directory (self, ifolder_id, entry_id, path):
        return True

    def modify_file (self, ifolder_id, entry_id, name):
        self.pyFolder.fetch (ifolder_id, entry_id, name)
        return True
    
    def delete_directory (self, ifolder_id, entry_id, path):
        self.pyFolder.rmdir (path)
        return True

    def delete_file (self, ifolder_id, entry_id, path):
        self.pyFolder.delete (path)
        return True

class ConflictsHandlerFactory:
    @staticmethod
    def create (policy, pyFolder):
        if policy == 'AlwaysAcceptRemoteChanges':
            return AlwaysAcceptRemoteChanges (pyFolder)
