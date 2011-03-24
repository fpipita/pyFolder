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
