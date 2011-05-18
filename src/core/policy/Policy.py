# -*- coding: utf-8 -*-



import logging



from suds import WebFault



POLICY_LOGGER_NAME = '{0}.pyFolder.Policy'



## Abstract base class for all the policies.

class Policy:



    ## The constructor.
    #
    #  @param pyFolder A pyFolder instance.

    def __init__ (self, pyFolder):
        self.pyFolder = pyFolder
        self.logger = logging.getLogger (
            POLICY_LOGGER_NAME.format (pyFolder.cm.get_username ()))



    ## The destructor.

    def __del__ (self):
        self.pyFolder = None



    ## Define what to do when the client requests for the creation
    ## of a new directory locally.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   directory belongs to.
    #  @param EntryID The ID of the directory-entry.
    #  @param Path The path to the directory (without the pyFolder
    #              prefix added).

    def add_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the creation
    ## of a new file locally.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   file belongs to.
    #  @param EntryID The ID of the file-entry.
    #  @param Path The path to the file (without the pyFolder
    #              prefix added).

    def add_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the modification
    ## of an existing local directory.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   directory belongs to.
    #  @param EntryID The ID of the directory-entry.
    #  @param Path The path to the directory (without the pyFolder
    #              prefix added).

    def modify_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the modification
    ## of an existing local file.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   file belongs to.
    #  @param EntryID The ID of the file-entry.
    #  @param Path The path to the file (without the pyFolder
    #              prefix added).

    def modify_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the deletion
    ## of an existing local directory.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   directory belongs to.
    #  @param EntryID The ID of the directory-entry.
    #  @param Path The path to the directory (without the pyFolder
    #              prefix added).

    def delete_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the deletion
    ## of an existing local file.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   file belongs to.
    #  @param EntryID The ID of the file-entry.
    #  @param Path The path to the file (without the pyFolder
    #              prefix added).

    def delete_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the creation
    ## of a new remote directory.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   directory-entry will belong to.
    #  @param ParentID The ID of the parent-entry for the new directory.
    #  @param Path The path to the new directory (without the pyFolder
    #              prefix added).

    def add_remote_directory (self, iFolderID, ParentID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the creation
    ## of a new remote file.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   file-entry will belong to.
    #  @param ParentID The ID of the parent-entry for the new file.
    #  @param Path The path to the new file (without the pyFolder
    #              prefix added).

    def add_remote_file (self, iFolderID, ParentID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the modification
    ## of an existing remote directory.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   directory-entry belongs to.
    #  @param EntryID The ID for the directory-entry.
    #  @param Path The path to the directory (without the pyFolder
    #              prefix added).

    def modify_remote_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the modification
    ## of an existing remote file.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   file-entry belongs to.
    #  @param EntryID The ID of for the file-entry.
    #  @param Path The path to the file (without the pyFolder
    #              prefix added).

    def modify_remote_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the deletion
    ## of an existing remote directory.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   directory-entry belongs to.
    #  @param EntryID The ID for the directory-entry.
    #  @param Path The path to the directory (without the pyFolder
    #              prefix added).

    def delete_remote_directory (self, iFolderID, EntryID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the deletion
    ## of an existing remote file.
    #
    #  @param iFolderID The ID of the remote iFolder the 
    #                   file-entry belongs to.
    #  @param EntryID The ID for the file-entry.
    #  @param Path The path to the file (without the pyFolder
    #              prefix added).

    def delete_remote_file (self, iFolderID, EntryID, Path):
        raise NotImplementedError



    ## Define what to do when the client requests for the deletion
    ## of a local iFolder.
    #
    #  @param iFolderID The ID of the remote iFolder.
    #  @param Path The path to the iFolder (without the pyFolder
    #              prefix added).

    def delete_ifolder (self, iFolderID, Path):
        raise NotImplementedError
