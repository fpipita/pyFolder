#!/usr/bin/python
# -*- coding: utf-8 -*-

## @package pyFolder
#  Documentation for the pyFolder module.
#
#  This module, contains the basic functions used by the client,
#  the checkout, update and commit ones, plus various helper methods.

from core.dbm import DBM
from core.config import ConfigManager
from core.policy import PolicyFactory
from core.ifolderws import iFolderWS
from core.notify.NotifierFactory import NotifierFactory

import base64
import datetime
import hashlib
import logging
import os
import shutil
import sqlite3
import sys
import time
import threading

from suds import WebFault

DEFAULT_SOAP_BUFLEN = 65536
DEFAULT_CONFIG_FILE = os.path.expanduser (os.path.join ('~', '.ifolderrc'))
DEFAULT_SQLITE_FILE = os.path.expanduser (os.path.join ('~', '.ifolderdb'))
SIMIAS_SYNC_INTERVAL = 5
PYFOLDER_SYNC_INTERVAL = 60
CONFLICTED_SUFFIX = 'conflicted'
ENTRY_INVALID_CHARS = [ '\\', ':', '*', '?', '\"', '<', '>', '|' ]
DEFAULT_INVALID_CHAR_REPLACEMENT = ''



class NullHandler (logging.Handler):
    def emit (self, record):
        pass



class pyFolder (threading.Thread):



    ## The constructor.
    #  @param cm A core.config.ConfigManager instance.
    #  @param runfromtest Tells pyFolder whether it 
    #         should run an action or not.

    def __init__ (self, cm, runfromtest=False):
        threading.Thread.__init__ (self)
        self.cm = cm
        self.__setup_logger ()
        self.__setup_ifolderws ()

        if self.cm.get_action () != 'noninteractive':
            self.__setup_dbm ()

        self.__setup_policy ()
        self.__setup_notifier ()

        if not runfromtest:
            self.__action ()



    ## The destructor.

    def __del__ (self):
        self.dbm = None
        self.notifier = None



    ## Handle a local name-conflict, by renaming the conflicted entry.
    #
    #  @param Path The path to rename (without the pyFolder prefix added).
    #  @param InvalidChars If True, just strip forbidden characters from
    #                      the tail of `Path'.

    def handle_name_conflict (self, Path, InvalidChars=False):
        NewPath = None

        if InvalidChars:
            NewPath = self.strip_invalid_characters (Path)

        else:
            NewPath = self.add_conflicted_suffix (Path)

        self.rename (Path, NewPath)

        self.notifier.info (\
            u'Name conflict detected', \
                u'Renamed {0} to {1}'.format (\
                Path.encode ('utf-8'), NewPath.encode ('utf-8')))



    ## Creates a suitable notifier for the host operating system.

    def __setup_notifier (self):
        self.notifier = NotifierFactory.create (sys.platform)



    ## Helper method. 

    def __setup_policy (self):
        self.policy = PolicyFactory.create (self.cm.get_policy (), self)



    ## Helper method. 

    def __setup_ifolderws (self):
        self.ifolderws = iFolderWS (self.cm)
        logging.getLogger ('suds.client').addHandler (NullHandler ())



    ## Helper method. 

    def __setup_dbm (self):
        self.dbm = DBM (self.cm.get_pathtodb ())
    


    ## Helper method. 

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



    ## The action that pyFolder will execute by default.
    #
    #  The action to be executed, can be either specified through 
    #  the configuration file or provided as a command line option.

    def __action (self):
        pyFolder.__dict__[self.cm.get_action ()] (self)



    ## Invoke the iFolder WEB Service.
    #
    #  All the calls to the Web Service, should be done through this method.
    #  It handles the `System.NullReferenceException' raised by Simias when
    #  there is an upgrade in progress on its internal data structures.
    #        
    #  @param method A callable object from an instance of the 
    #                core.ifolderws.iFolderWS class.
    #  @param args   The arguments list to pass to the callable object.
    #
    #  @return The return type expected by the invoked Web Service.

    def __invoke (self, method, *args):

        if not callable (method):
            raise TypeError
        
        self.logger.info ('Invoking webmethod `{0}\''.format (method.__name__))

        SyncInterval = 0
        while True:
            
            try:

                return method (*args)

            except WebFault, wf:

                self.logger.error (wf)
                
                OriginalException = \
                    wf.fault.detail.detail.OriginalException._type
                
                if OriginalException == 'System.NullReferenceException':

                    SyncInterval = (SyncInterval + 1) % SIMIAS_SYNC_INTERVAL
                    time.sleep (SyncInterval)

                    continue

                else:
                    raise
    


    def ignore_locked (self, Path):
        self.logger.info ('Ignoring locked entry `{0}\''.format (\
                Path.encode ('utf-8')))
        


    def ignore_no_rights (self, Path):
        self.logger.info ('Could not commit entry `{0}\' ' \
                              'because of not sufficient ' \
                              'rights'.format (Path.encode ('utf-8')))



    ## Replace invalid characters in the given path.
    #
    #  The method just fixes the leaf node of the path.
    #
    #  @param Path The path to fix.
    #  @param Replacement The string to use as replacement for
    #                     the invalid characters.
    #
    #  @return A valid version of the path.

    def strip_invalid_characters (\
        self, Path, Replacement=DEFAULT_INVALID_CHAR_REPLACEMENT):

        Head, Tail = os.path.split (Path)
        Name = Tail

        for Char in ENTRY_INVALID_CHARS:

            if Char in Name:
                Name = Name.replace (Char, Replacement)

        return Path.replace (Tail, Name)



    def ignore_in_use (self, Path):
        self.logger.info ('Could not commit entry `{0}\' ' \
                              'because it is already ' \
                              'in use'.format (Path.encode ('utf-8')))



    ## Delete a remote file.
    #
    #  @param iFolderID The ID of the iFolder to which the file
    #         belongs.
    #  @param EntryID The ID of the file seen as an iFolderEntry.
    #  @param Path The path to the file (no matters whether it is 
    #              a local path or a remote one, because of only 
    #              the tail will be used).

    def remote_delete (self, iFolderID, EntryID, Path):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]

        self.__invoke (self.ifolderws.delete_entry, iFolderID, EntryID)



    ## Delete a remote directory.
    #
    #  @param iFolderID The ID of the iFolder to which the directory
    #         belongs.
    #  @param EntryID The ID of the directory seen as an iFolderEntry.
    #  @param Path The path to the directory (no matters whether it 
    #              is a local path or a remote one, because of, only 
    #              the tail will be used).

    def remote_rmdir (self, iFolderID, EntryID, Path):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]

        self.__invoke (self.ifolderws.delete_entry, iFolderID, EntryID)



    ## Create a remote file.
    #
    #  @param iFolderID the ID of the iFolder to which the new file will 
    #                   belong.
    #  @param ParentID the ID of the iFolderEntry which will act as
    #                  parent for the new file.
    #  @param Path The path (it can be either a local or a remote one, only
    #              its tail is going to be used) to the new file.
    #
    #  @return The remote file's iFolderEntry.

    def remote_create_file (self, iFolderID, ParentID, Path):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]
        
        return self.ifolderws.create_entry (iFolderID, ParentID, \
                                                Name, Type.File)



    ## Create a remote directory.
    #
    #  @param iFolderID the ID of the iFolder to which the new directory
    #                   will belong.
    #  @param ParentID the ID of the iFolderEntry which will act as
    #                  parent for the new directory.
    #  @param Path The path (it can be either a local or a remote one, only
    #              its tail is going to be used) to the new directory.
    #
    #  @return The remote directory's iFolderEntry.

    def remote_mkdir (self, iFolderID, ParentID, Path):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Name = os.path.split (Path)[1]

        return self.ifolderws.create_entry (iFolderID, ParentID, \
                                                Name, Type.Directory)



    ## Download a remote file.
    #
    #  @param iFolderID The ID of the iFolder to which the file belongs.
    #  @param EntryID The ID of the file seen as an iFolderEntry.
    #  @param LocalPath The local path on which the remote file will be saved.

    def fetch (self, iFolderID, EntryID, LocalPath):
        LocalPath = self.add_prefix (LocalPath)
        Handle = self.__invoke (\
            self.ifolderws.open_file_read, iFolderID, EntryID)

        if Handle is not None:
            with open (LocalPath, 'wb') as File:
                while True:
                    Base64Data = self.__invoke (self.ifolderws.read_file, \
                                                    Handle)
                    if Base64Data is None:
                        break

                    File.write (base64.b64decode (Base64Data))
                self.__invoke (self.ifolderws.close_file, Handle)



    ## Write the content of a local file to an existing remote one.
    #
    #  @param iFolderID the ID of the iFolder the remote file belongs to.
    #  @param EntryID the ID of the remote file seen as an iFolderEntry.
    #  @param LocalPath The path to the local file that is going to be 
    #                   uploaded.

    def remote_file_write (self, iFolderID, EntryID, LocalPath):
        Size = self.getsize (LocalPath)
        Handle = self.__invoke (self.ifolderws.open_file_write, \
                                    iFolderID, EntryID, Size)
        if Handle is not None:
            with open (self.add_prefix (LocalPath), 'rb') as File:
                while True:
                    Data = File.read (self.cm.get_soapbuflen ())

                    if len (Data) == 0:
                        break

                    self.__invoke (self.ifolderws.write_file, \
                                       Handle, base64.b64encode (Data))
            self.__invoke (self.ifolderws.close_file, Handle)



    ## Add an iFolder to the local database and create its local directory.
    #
    #  @param iFolderID The ID of the iFolder to add.
 
    def __add_ifolder (self, iFolderID):
        iFolderEntry = self.__invoke (self.ifolderws.get_ifolder_as_entry, \
                                          iFolderID)
        iFolder = self.__invoke (self.ifolderws.get_ifolder, iFolderID)

        if iFolderEntry is not None and iFolder is not None:
            iFolderEntryID = iFolderEntry.ID
            mtime = iFolder.LastModified
            Name = iFolder.Name

            if self.policy.add_directory (iFolderID, iFolderEntryID, Name):
                self.dbm.add_ifolder (iFolderID, mtime, Name, iFolderEntryID)



    ## Add all the entries which belong to an iFolder locally.
    #
    #  @param iFolderID The ID of the iFolder whose entries need to be
    #                   added locally.

    def __add_entries (self, iFolderID):
        EntryList = self.__invoke (self.ifolderws.get_children_by_ifolder, \
                                       iFolderID)
        if EntryList is not None:
            for Entry in EntryList:
                ParentID = Entry.ParentID

                Change = self.__invoke (self.ifolderws.get_latest_change, \
                                            iFolderID, Entry.ID)
                if Change is not None:
                    self.__add_entry_locally (iFolderID, ParentID, Change)



    ## Helper method, add a single entry locally.
    #
    #  @param iFolderID The ID of the iFolder to which the entry belongs.
    #  @param ParentID The ID of its parent entry.
    #  @param Change A ChangeEntry instance. 
    #
    #  @return True whether the entry was successfully added.
    #
    #  @sa The iFolder Web Service description.

    def __add_entry_locally (self, iFolderID, ParentID, Change):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Action = self.ifolderws.get_change_entry_action ()
        EntryID = Change.ID
        Name = Change.Name
        Time = Change.Time
        Updated = False

        if Change.Action == Action.Add or Change.Action == Action.Modify:

            if Change.Type == Type.File:
                Updated = self.policy.add_file (iFolderID, EntryID, Name)

            elif Change.Type == Type.Directory:
                Updated = self.policy.add_directory (iFolderID, EntryID, Name)

            if Updated:
                self.add_entry_to_dbm (\
                    None, iFolderID, EntryID, Time, ParentID, Name)

        return Updated



    ## Public method, add a single entry locally.
    #
    #  @param iFolderID The ID of the iFolder to which the entry belongs.
    #  @param ParentID The ID of the entry which acts as parent to the entry
    #                  which is going to be added.
    #  @param Path Can be any path pointing to the entry. Just its tail is
    #              going to be used.
    #
    #  @return The iFolderEntry just added on success, None else.

    def add_entry_locally (self, iFolderID, ParentID, Path):
        Operation = self.ifolderws.get_search_operation ()
        Name = os.path.split (Path)[1]

        EntryList = self.__invoke (self.ifolderws.get_entries_by_name, \
                                       iFolderID, ParentID, \
                                       Operation.Contains, Name, 0, 1)
        if EntryList is not None:
            for Entry in EntryList:
                EntryID = Entry.ID
                ParentID = Entry.ParentID

                Change = self.__invoke (self.ifolderws.get_latest_change, \
                                            iFolderID, EntryID)

                if Change is not None:
                    self.__add_entry_locally (iFolderID, ParentID, Change)

                return Entry
        return None



    ## Public method, add a remote directory-hierarchy locally.
    #
    #  @param iFolderID The ID of the iFolder to which the entry belong.
    #  @param ParentID The ID of the entry which acts as parent to
    #                  the hierarchy that is going to be added.
    #  @param Path Can be any path pointing to the entry. Just its tail is
    #              going to be used.

    def add_hierarchy_locally (self, iFolderID, ParentID, Path):
        Operation = self.ifolderws.get_search_operation ()

        ParentEntry = self.add_entry_locally (iFolderID, ParentID, Path)

        EntryList = self.__invoke (self.ifolderws.get_entries_by_name, \
                                       iFolderID, ParentEntry.ID, \
                                       Operation.Contains, '.', 0, 0)

        if EntryList is not None:
            for Entry in EntryList:
                Change = self.__invoke (self.ifolderws.get_latest_change, \
                                            iFolderID, Entry.ID)
                if Change is not None:
                    ParentID = Entry.ParentID
                    self.__add_entry_locally (iFolderID, ParentID, Change)
                return



    ## Build an initial local copy of the user's remote iFolders.
    #
            
    def checkout (self):
        self.dbm.create_schema ()
        
        iFolderList = self.__invoke (self.ifolderws.get_all_ifolders)

        iFolderID = None
        Name = None
        
        if iFolderList is not None:

            try:

                for iFolder in iFolderList:
                    iFolderID = iFolder.ID
                    Name = iFolder.Name

                    self.__add_ifolder (iFolder.ID)
                    self.__add_entries (iFolder.ID)

            except WebFault, wf:

                OriginalException = \
                    wf.fault.detail.detail.OriginalException._type

                if OriginalException == \
                        'iFolder.WebService.MemberDoesNotExistException' or \
                        OriginalException == \
                        'iFolder.WebService.iFolderDoesNotExistException':
                    self.policy.delete_ifolder (iFolderID, Name)

                else:
                    raise



    ## Check whether new local directories were added to the given one.
    #
    #  @param Root The full path (with added prefix) to the directory
    #              to check.
    #  @param Dirs A list of directories whose parent is Root.
    #  @param iFolderID The ID of the iFolder Root belongs to.
    #
    #  @return True whether new directories were found.

    def directory_has_new_directories (self, Root, Dirs, iFolderID):
        Changed = False
        
        for Dir in Dirs:
            Path = os.path.join (self.remove_prefix (Root), Dir)
            if self.is_new_local_directory (iFolderID, Path):
                Changed = True
                
        return Changed        
    


    ## Check whether new local files were added to the given directory.
    #
    #  @param Root The full path (with added prefix) to the directory 
    #              to check.
    #  @param Files A list of files whose parent is Root.
    #  @param iFolderID The ID of the iFolder Root belongs to.
    #
    #  @return True whether new files were found.

    def directory_has_new_files (self, Root, Files, iFolderID):
        Changed = False
        
        for File in Files:
            Path = os.path.join (self.remove_prefix (Root), File)
            if self.__is_new_local_file (iFolderID, Path):
                Changed = True
                
        return Changed



    ## Check whether new local entries were added to the given directory.
    #
    #  @param iFolderID The ID of the iFolder Root belongs to.
    #  @param LocalPath The path (without prefix) to the directory to check.
    #
    #  @return True whether new entries (files or directories) were found.

    def directory_has_new_entries (self, iFolderID, LocalPath):
        Changed = False
        
        for Root, Dirs, Files in os.walk (self.add_prefix (LocalPath)):

            Changed = self.directory_has_new_directories (\
                Root, Dirs, iFolderID) or Changed

            Changed = self.directory_has_new_files (\
                Root, Files, iFolderID) or Changed
            
        return Changed



    ## Check whether the given iFolder has any local changes.
    #
    #  @param iFolderID The ID of the iFolder to check.
    #
    #  @return True if the iFolder has any kind (modify, deletion,
    #          addition) of local change.

    def ifolder_has_local_changes (self, iFolderID):
        iFolderTuple = self.dbm.get_ifolder (iFolderID)
        
        if iFolderTuple is not None:
            iFolderEntryID = iFolderTuple['entry_id']
            Name = iFolderTuple['name']

            return self.directory_has_local_changes (\
                iFolderID, iFolderEntryID) or \
                self.directory_has_new_entries (iFolderID, Name)

        return False



    ## Check whether the given iFolder has any remote changes.
    #
    #  @param iFolderID The ID of the iFolder to check.
    #  @param mtime The timestamp of the last modification made to the iFolder
    #               currently stored in the local database.
    #               
    #  @return True whether the iFolder's remote LastModified
    #          attribute is newer than the mtime local one.
    
    def __ifolder_has_changes (self, iFolderID, mtime):
        iFolder = self.__invoke (self.ifolderws.get_ifolder, iFolderID)

        if iFolder is not None:

            if iFolder.LastModified > mtime:
                return True

            else:
                return False

        return True



    ## Get the latest remote change made to the given entry, if any.
    #
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param EntryID The ID of the given entry.
    #  @param mtime The timestamp of the last change made to the entry
    #               currently stored in the local database.
    #
    #  @return A ChangeEntry instance if a new remote change was found,
    #          None else.
    #
    #  @sa The iFolder Web Service description.

    def __get_change (self, iFolderID, EntryID, mtime):
        Change = self.__invoke (self.ifolderws.get_latest_change, \
                                    iFolderID, EntryID)

        if Change is not None:

            if Change.Time > mtime:
                return Change

        return None



    ## Synchronize the local mtime for the given iFolder with the remote one.
    #
    #  @param iFolderID The ID of the iFolder whose mtime needs to be updated.
    
    def __update_ifolder_in_dbm (self, iFolderID):
        iFolder = self.__invoke (self.ifolderws.get_ifolder, iFolderID)

        if iFolder is not None:
            mtime = iFolder.LastModified
            self.dbm.update_mtime_by_ifolder (iFolderID, mtime)



    ## Apply the addition of a remote entry locally.
    #
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param EntryID The ID of the entry.
    #  @param Change A ChangeEntry instance. 
    #
    #  @return True if Change was successfully applied.
    #
    #  @sa The iFolder Web Service description.
            
    def __handle_add_action (self, iFolderID, EntryID, Change):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Name = Change.Name
        Updated = False

        if Change.Type == Type.Directory:
            Updated = self.policy.add_directory (iFolderID, EntryID, Name)

        elif Change.Type == Type.File:
            Updated = self.policy.add_file (iFolderID, EntryID, Name)

        if Updated:
            self.__update_entry_in_dbm (iFolderID, EntryID)

        return Updated



    ## Apply the motification of a remote entry locally.
    #
    #  @param iFolderID The ID of the iFolder entry belongs to.
    #  @param EntryID The ID of the entry.
    #  @param Change A ChangeEntry instance. 
    #
    #  @return True if Change was successfully applied.
    #
    #  @sa The iFolder Web Service description.

    def __handle_modify_action (self, iFolderID, EntryID, Change):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Updated = False
        Name = Change.Name

        if Change.Type == Type.Directory:
            Updated = self.policy.modify_directory (iFolderID, EntryID, Name)

        elif Change.Type == Type.File:
            Updated = self.policy.modify_file (iFolderID, EntryID, Name)

        if Updated:
            self.__update_entry_in_dbm (iFolderID, EntryID)

        return Updated



    ## Apply the deletion of a remote entry locally.
    #
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param EntryID The ID of the entry.
    #  @param Change A ChangeEntry instance. 
    #
    #  @return True if Change was successfully applied.
    #
    #  @sa The iFolder Web Service description.

    def __handle_delete_action (self, iFolderID, EntryID, Change):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Updated = False
        Name = Change.Name

        if Change.Type == Type.File:
            Updated = self.policy.delete_file (iFolderID, EntryID, Name)

        elif Change.Type == Type.Directory:
            Updated = self.policy.delete_directory (iFolderID, EntryID, Name)

            if Updated:
                self.__delete_hierarchy_from_dbm (iFolderID, EntryID)

        if Updated:
            self.__delete_entry_from_dbm (iFolderID, EntryID)

        return Updated



    ## Check if an entry has any kind of remote change and handle it.
    #
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param EntryID The ID of the entry.
    #  @param mtime The timestamp of the latest change made to the entry
    #               currently stored in the local database.
    #
    #  @return True if any change was successfully applied to the entry.

    def update_entry (self, iFolderID, EntryID, mtime):
        Action = self.ifolderws.get_change_entry_action ()        
        Change = self.__get_change (iFolderID, EntryID, mtime)
        Updated = False
        
        if Change is not None:

            if Change.Action == Action.Add:
                Updated = self.__handle_add_action (iFolderID, EntryID, Change)

            elif Change.Action == Action.Modify:
                Updated = self.__handle_modify_action (\
                    iFolderID, EntryID, Change)

            elif Change.Action == Action.Delete:
                Updated = self.__handle_delete_action (\
                    iFolderID, EntryID, Change)
                
        return Updated



    ## Update the local copy of given iFolder, by applying eventual
    ## remote changes.
    #
    #  @param iFolderID The ID of the iFolder to update.
    #
    #  @return True if all of the changes were successfully applied.

    def __update_ifolder (self, iFolderID):
        EntryTupleList = self.dbm.get_entries_by_ifolder (iFolderID)
        Updated = False

        for EntryTuple in EntryTupleList:
            iFolderID = EntryTuple['ifolder']
            EntryID = EntryTuple['id']
            mtime = EntryTuple['mtime']

            if self.dbm.get_entry (iFolderID, EntryID) is None:
                continue
            
            Updated = self.update_entry (iFolderID, EntryID, mtime) and \
                Updated

        return Updated



    ## Add new remote entries to local copy of the given iFolder.
    #  
    #  @param iFolderID The ID of the iFolder to check.
    #
    #  @return True if all of the new entries were successfully merged
    #          within the local copy.

    def __add_new_entries (self, iFolderID):
        Updated = False
        
        EntryList = self.__invoke (self.ifolderws.get_children_by_ifolder, \
                                       iFolderID)
        if EntryList is not None:
            for Entry in EntryList:
                ParentID = Entry.ParentID
                
                if self.dbm.get_entry (iFolderID, Entry.ID) is None:
                    Change = self.__invoke (self.ifolderws.get_latest_change, \
                                                iFolderID, Entry.ID)

                    if Change is not None:
                        Updated = self.__add_entry_locally (\
                            iFolderID, ParentID, Change) and Updated

        return Updated



    ## Add eventual new iFolders to the user's local repository.

    def __add_new_ifolders (self):
        iFolderList = self.__invoke (self.ifolderws.get_all_ifolders)

        if iFolderList is not None:
            for iFolder in iFolderList:
                if self.dbm.get_ifolder (iFolder.ID) is None:
                    self.__add_ifolder (iFolder.ID)
                    self.__add_entries (iFolder.ID)



    ## Add the given entry to the local database.
    #  
    #  @param Entry an iFolderEntry instance. 
    #  @param args A list containing ALL of the following parameters: 
    #              iFolderID, EntryID, Time, ParentID, Path. The list
    #              is checked IFF Entry is None.
    #
    #  @sa The iFolder Web Service description.

    def add_entry_to_dbm (self, Entry, *args):

        iFolderID = None
        EntryID = None
        Time = None
        ParentID = None
        Path = None

        if Entry is None:
            iFolderID, EntryID, Time, ParentID, Path = args

        else:
            Change = self.__invoke (self.ifolderws.get_latest_change, \
                                        Entry.iFolderID, Entry.ID)

            if Change is not None:
                iFolderID = Entry.iFolderID
                EntryID = Entry.ID
                Time = Change.Time
                ParentID = Entry.ParentID
                Path = Entry.Path

        Hash = self.__md5_hash (Path)
        LocalPath = os.path.normpath (Path)

        self.dbm.add_entry (iFolderID, EntryID, Time, Hash, ParentID, \
                                Path, LocalPath)



    ## Add the pyFolder prefix (if any) to the given Path.
    #
    #  @param Path The path to modify.
    #
    #  @return The modified path if a prefix was given, the original one else.

    def add_prefix (self, Path):

        if self.cm.get_prefix () != '':
            return os.path.join (self.cm.get_prefix (), Path)

        return Path



    ## Remove the pyFolder prefix (if any) previously added with 
    #  pyFolder.add_prefix.
    #
    #  @param Path The path to modify.
    #
    #  @return The path with the prefix removed.

    def remove_prefix (self, Path):

        if self.cm.get_prefix () != '':
            prefix = os.path.join (self.cm.get_prefix (), '')
            return Path.replace ('{0}'.format (prefix), '')

        return Path



    ## Add a conflicted suffix to the given local path.
    #  
    #  @param Path The path that needs to be renamed.
    #  @param Suffix The conflicted suffix to append to Path.
    #
    #  @return The modified path.

    def add_conflicted_suffix (self, Path, Suffix=None):

        BaseName, Extension = os.path.splitext (Path)

        if Suffix == None:
            Suffix = '{0}_{1}'.format (\
                CONFLICTED_SUFFIX, datetime.date.today ())

        if Extension == '':
            return '{0}-{1}'.format (\
                BaseName.encode ('utf-8'), Suffix.encode ('utf-8'))

        else:
            return '{0}-{1}{2}'.format (\
                BaseName.encode ('utf-8'), Suffix, Extension.encode ('utf-8'))



    ## Check whether the given local path exists.
    #
    #  @param Path The path to check, it must be provided without the pyFolder 
    #              prefix.
    #
    #  @return True whether the prefixed version of path exists.

    def path_exists (self, Path):
        return os.path.exists (self.add_prefix (Path))



    ## Check whether the given local path is a file.
    #
    #  @param Path The path to check, it must be provided without the pyFolder 
    #              prefix.
    #
    #  @return True whether the prefixed version of path is a file.

    def path_isfile (self, Path):
        return os.path.isfile (self.add_prefix (Path))



    ## Check whether the given local path is a directory.
    #
    #  @param Path The path to check, it must be provided without the pyFolder 
    #              prefix.
    #
    #  @return True whether the prefixed version of path is a directory.

    def path_isdir (self, Path):
        return os.path.isdir (self.add_prefix (Path))



    ## Rename a local path.
    #
    #  @param Src The path that needs to be renamed. It must be 
    #             provided without the pyFolder prefix.
    #  @param Dst The new path. It must be provided without the pyFolder 
    #             prefix.

    def rename (self, Src, Dst):
        Src = self.add_prefix (Src)
        Dst = self.add_prefix (Dst)

        try:

            os.rename (Src, Dst)
            self.logger.info ('Renamed `{0}\' to `{1}\''.format (\
                    Src.encode ('utf-8'), Dst.encode ('utf-8')))

        except OSError, ose:

            self.logger.error (ose)
            raise



    ## Delete a local file.
    #
    #  @param Path The file to delete. It must be provided without the
    #              pyFolder prefix.

    def delete (self, Path):
        Path = self.add_prefix (Path)

        try:

            os.remove (Path)
            self.logger.info ('Deleted local file `{0}\''.format (\
                    Path.encode ('utf-8')))

        except OSError, ose:

            self.logger.error (ose)
            raise



    ## Delete a local directory tree recursively.
    #
    #  @param Path The directory tree to remove. It must be provided 
    #              without the pyFolder prefix.

    def rmdir (self, Path):
        Path = self.add_prefix (Path)

        try:

            shutil.rmtree (Path)
            self.logger.info ('Deleted local directory `{0}\''.format (\
                    Path.encode ('utf-8')))

        except OSError, ose:

            self.logger.error (ose)
            raise



    ## Create a local directory tree, adding eventual intermediate 
    ## directories.
    #
    #  @param Path The directory tree to create. It must be provided 
    #              without the pyFolder prefix.

    def mkdir (self, Path):
        Path = self.add_prefix (Path)

        try:

            os.makedirs (Path)
            self.logger.info ('Added local directory `{0}\''.format (\
                    Path.encode ('utf-8')))

        except OSError, ose:

            self.logger.error (ose)
            raise



    ## Delete the given iFolder and all of its children from the local 
    ## repository and from the local database.
    #
    #  @param iFolderID The ID of the iFolder to remove.
    #  @param Name the name of the iFolder.

    def delete_ifolder (self, iFolderID, Name):
        self.rmdir (Name)
        self.dbm.delete_entries_by_ifolder (iFolderID)
        self.dbm.delete_ifolder (iFolderID)



    ## Get the size of the given file in bytes.
    #
    #  @param Path The path to the file. It must be provided without
    #              the pyFolder prefix added.
    #
    #  @return The size in bytes of the given file.

    def getsize (self, Path):
        return os.path.getsize (self.add_prefix (Path))



    ## Calculate the MD5 digest for the given entry.
    #
    #  This method will return the string 'DIRECTORY' if Path
    #  points to a directory.
    # 
    #  @param Path The path to the given entry, without the pyFolder prefix.
    #
    #  @return The MD5 digest for the given path.
    
    def __md5_hash (self, Path):
        Path = self.add_prefix (Path)
        Hash = 'DIRECTORY'

        if os.path.isfile (Path):
            m = hashlib.md5 ()

            with open (Path, 'rb') as File:

                while True:
                    Data = File.read ()
                    m.update (Data)

                    if len (Data) == 0:
                        break

                Hash = m.hexdigest ()

        return Hash



    ## Check for local changes in the given entry-directory.
    #
    #  @param iFolderID The ID of the iFolder the directory-entry belongs to.
    #  @param EntryID The ID of the directory-entry.
    #
    #  @return True whether at least one file in the directory
    #          has been locally modified or deleted.
    
    def directory_has_local_changes (self, iFolderID, EntryID):
        Changed = False
        EntryTupleList = self.dbm.get_entries_by_parent (EntryID)

        for EntryTuple in EntryTupleList:
            ChildEntryID = EntryTuple['id']
            ChildLocalPath = EntryTuple['localpath']
            Digest = EntryTuple['digest']

            if Digest == 'DIRECTORY':
                Changed = self.directory_has_local_changes (\
                    iFolderID, ChildEntryID) or Changed

            else:
                Changed = self.file_has_local_changes (\
                    iFolderID, ChildEntryID, ChildLocalPath) or Changed

                if Changed:
                    return Changed

        return Changed



    ## Detect local changes on the given file-entry.
    #
    #  @param iFolderID The ID of the iFolder the file-entry belongs to.
    #  @param EntryID The ID of the file-entry.
    #  @param LocalPath The path to the file to check. It can be either
    #                   a pyFolder-prefixed path or not.
    #  @param Localize If a path without the pyFolder-prefix is provided,
    #                  make sure this is set to True, or the method will
    #                  fail.
    #
    #  @return True whether the file has been locally modified or deleted.

    def file_has_local_changes (\
        self, iFolderID, EntryID, LocalPath, Localize=False):

        EntryTuple = self.dbm.get_entry (iFolderID, EntryID)
        
        if Localize:
            LocalPath = self.add_prefix (os.path.normpath (LocalPath))

        if not self.path_exists (LocalPath):
            if EntryTuple is None:
                return False

            else:
                return True

        else:
            if EntryTuple is None:
                return True

            else:
                OldDigest = EntryTuple['digest']
                NewDigest = self.__md5_hash (LocalPath)

                if OldDigest != NewDigest:
                    return True

                else:
                    return False



    ## Synchronize the entry's local mtime with its remote one.
    #
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param EntryID The ID of the entry.
    
    def __update_entry_in_dbm (self, iFolderID, EntryID):
        EntryTuple = self.dbm.get_entry (iFolderID, EntryID)

        Count = 5
        SyncInterval = 0
        while Count > 0:
            Change = self.__invoke (\
                self.ifolderws.get_latest_change, iFolderID, EntryID)

            if Change is not None and Change.Time != EntryTuple['mtime']:
                break

            Count = Count - 1
            SyncInterval = (SyncInterval + 1) % SIMIAS_SYNC_INTERVAL
            time.sleep (SyncInterval)

        if Change is not None:
            Hash = self.__md5_hash (Change.Name)
            self.dbm.update_mtime_and_digest_by_entry (\
                iFolderID, EntryID, Change.Time, Hash)



    ## Delete the given entry from the local database.
    # 
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param EntryID The ID of the entry.

    def __delete_entry_from_dbm (self, iFolderID, EntryID):
        self.dbm.delete_entry (iFolderID, EntryID)



    ## Synchronize the local copy of the repository with the remote one,
    ## by applying remote changes locally.

    def update (self):
        iFolderTupleList = None
        
        try:

            iFolderTupleList = self.dbm.get_ifolders ()

        except sqlite3.OperationalError:

            print >> sys.stderr, 'Could not open the local database. '
            'Please, ' \
                'run the `checkout\' action first ' \
                'or provide a valid path to the local ' \
                'database using the `--pathtodb\' ' \
                'command line switch.'
            sys.exit ()

        for iFolderTuple in iFolderTupleList:
            iFolderID = iFolderTuple['id']
            mtime = iFolderTuple['mtime']
            Name = iFolderTuple['name']

            Updated = True

            try:

                if self.__ifolder_has_changes (iFolderID, mtime):
                    Updated = self.__update_ifolder (iFolderID) and Updated
                    Updated = self.__add_new_entries (iFolderID) and Updated

                    if Updated:
                        self.__update_ifolder_in_dbm (iFolderID)

            except WebFault, wf:

                OriginalException = \
                    wf.fault.detail.detail.OriginalException._type

                if OriginalException == \
                        'iFolder.WebService.MemberDoesNotExistException' or \
                        OriginalException == \
                        'iFolder.WebService.iFolderDoesNotExistException':
                    self.policy.delete_ifolder (iFolderID, Name)

                else:
                    raise
                
        self.__add_new_ifolders ()



    ## Detect eventual local changes on the given entry.
    #
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param EntryID The ID of the entry.
    #  @param LocalPath The local path to the entry that is going to be
    #                   checked, without the pyFolder prefix added.
    #  @param Digest The digest of the given entry.
    #
    #  @return A tuple (ChangeAction, ChangeType), with the kind of action
    #          made on the entry and the type of the entry.
    #
    #  @sa The iFolder Web Service description.

    def get_local_changes_on_entry (\
        self, iFolderID, EntryID, LocalPath, Digest):

        Action = self.ifolderws.get_change_entry_action ()
        Type = self.ifolderws.get_ifolder_entry_type ()
        ChangeAction = None
        ChangeType = None

        if Digest == 'DIRECTORY':
            ChangeType = Type.Directory

        else:
            ChangeType = Type.File

        if not self.path_exists (LocalPath):
            ChangeAction = Action.Delete

        else:
            if ChangeType == Type.File:
                if self.file_has_local_changes (iFolderID, EntryID, LocalPath):
                    ChangeAction = Action.Modify

            elif ChangeType == Type.Directory:
                if self.directory_has_local_changes (iFolderID, EntryID):
                    ChangeAction = Action.Modify

        return ChangeAction, ChangeType



    ## Check whether the given entry already exists in the local database.
    #
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param Path The local path of the entry, without the pyFolder prefix
    #              added.
    #
    #  @return True whether the entry does not exist in the local database.

    def __is_new_local_entry (self, iFolderID, Path):
        EntryTuple = \
            self.dbm.get_entry_by_ifolder_and_localpath (iFolderID, Path)

        if EntryTuple is None:
            return True

        return False



    ## Check whether the given directory-entry already exists locally.
    #
    #  @param iFolderID The ID of the iFolder the directory-entry belongs to.
    #  @param Path The local path of the directory-entry, without the
    #              pyFolder prefix added.
    #
    #  @return True whether the directory-entry does not already exist locally.

    def is_new_local_directory (self, iFolderID, Path):
        return self.path_isdir (Path) and \
            self.__is_new_local_entry (iFolderID, Path)



    ## Check whether the given file-entry already exists locally.
    #
    #  @param iFolderID The ID of the iFolder the file-entry belongs to.
    #  @param Path The local path of the file-entry, without the pyFolder 
    #              prefix added.
    #
    #  @return True whether the file-entry does not already exist locally.

    def __is_new_local_file (self, iFolderID, Path):
        return self.path_isfile (Path) and \
            self.__is_new_local_entry (iFolderID, Path)



    ## Search for the given entry's parent entry.
    #
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param Path The local path of the entry, without the pyFolder 
    #              prefix added.
    #
    #  @return The ID of the parent entry or None if the entry has been
    #          orphaned.
    
    def __find_parent (self, iFolderID, Path):
        ParentPath = os.path.split (Path)[0]

        EntryTuple = \
            self.dbm.get_entry_by_ifolder_and_localpath (iFolderID, ParentPath)

        if EntryTuple is None:
            iFolderTuple = self.dbm.get_ifolder (iFolderID)

            if ParentPath == iFolderTuple['name']:
                return iFolderTuple['entry_id']

            else:
                return None

        return EntryTuple['id']



    ## Find the closest ancestor-entry which is still remotely existing.
    #
    #  @param iFolderID The ID of the iFolder the orphaned entry belongs to.
    #  @param LocalPath The local path to the orphaned entry. It has to
    #                   be deprived of the pyFolder prefix.
    #
    #  @return A tuple (Path, Entry). Path is the path to the direct
    #          descendant of the closest ancestor of LocalPath which
    #          is still remotely alive in the LocalPath hierarchy. Entry
    #          is the ancestor entry.

    def find_closest_ancestor_remotely_alive (self, iFolderID, LocalPath):
        Operation = self.ifolderws.get_search_operation ()
        Head, Tail = os.path.split (LocalPath)

        EntryTuple = self.dbm.get_entry_by_ifolder_and_localpath (\
            iFolderID, Head)

        if EntryTuple == None:
            iFolderEntry = self.__invoke (\
                self.ifolderws.get_ifolder_as_entry, iFolderID)
            return LocalPath, iFolderEntry

        ParentID = EntryTuple['id']
        
        try:

            Entry = self.__invoke (self.ifolderws.get_entry, \
                                       iFolderID, ParentID)
            return LocalPath, Entry

        except WebFault, wf:

            self.logger.error (wf)
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == \
                    'iFolder.WebService.EntryDoesNotExistException' or \
                    OriginalException == \
                    'System.IO.DirectoryNotFoundException':
                return self.find_closest_ancestor_remotely_alive (\
                    iFolderID, Head)

            else:
                raise



    ## Commit eventual new locally-added directories.
    #
    #  @param Root The root path where to check for new directories.
    #  @param Dirs A list of directory names, whose parent is Root.
    #  @param iFolderID The ID of the iFolder to which Root belongs.
    #
    #  @return True whether at least a new directory was committed.

    def __commit_added_directories (self, Root, Dirs, iFolderID):
        Updated = False

        for Dir in Dirs:
            Path = os.path.join (self.remove_prefix (Root), Dir)
            if self.is_new_local_directory (iFolderID, Path):
                ParentID = self.__find_parent (iFolderID, Path)
                if ParentID is not None:
                    Entry = self.policy.add_remote_directory (\
                        iFolderID, ParentID, Path)
                    if Entry is not None:
                        Updated = True

        return Updated



    ## Commit eventual new locally-added files.
    #
    #  @param Root The root path where to check for new files.
    #  @param Files A list of file-names, whose parent is Root.
    #  @param iFolderID The ID of the iFolder to which Root belongs.
    #
    #  @return True if at least one new file was committed.

    def __commit_added_files (self, Root, Files, iFolderID):
        Updated = False

        for File in Files:
            Path = os.path.join (self.remove_prefix (Root), File)
            if self.__is_new_local_file (iFolderID, Path):
                ParentID = self.__find_parent (iFolderID, Path)
                if ParentID is not None:
                    Entry = self.policy.add_remote_file \
                        (iFolderID, ParentID, Path)
                    if Entry is not None:
                        Updated = True
                        if self.policy.modify_remote_file (\
                            iFolderID, Entry.ID, Entry.Path):
                            self.__update_entry_in_dbm (\
                                Entry.iFolderID, Entry.ID)

        return Updated



    ## Commit eventual new local entries.
    #
    #  @param iFolderID The ID of the iFolder the new entries will be 
    #                   merged with.
    #  @param Name The name of the iFolder that needs to be checked for
    #              new locally-added entries.
    #
    #  @return True whether at least one new entry (of any kind) was
    #               committed.

    def __commit_added_entries (self, iFolderID, Name):
        Updated = False

        for Root, Dirs, Files in os.walk (self.add_prefix (Name)):
            Updated = self.__commit_added_directories (\
                Root, Dirs, iFolderID) or Updated
            Updated = self.__commit_added_files (\
                Root, Files, iFolderID) or Updated

        return Updated



    ## Commit an existing entry that has been locally modified.
    #
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param EntryID The ID of the entry.
    #  @param LocalPath The local path to the entry, deprived of the
    #                   pyFolder prefix.
    #  @param EntryType The type of the entry.
    #  
    #  @return True whether the entry has been successfully committed.
    # 
    #  @sa The iFolder Web Service description.

    def __commit_modified_entry (self, iFolderID, EntryID, LocalPath, \
                                     EntryType):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Updated = False

        if EntryType == Type.File:
            Updated = self.policy.modify_remote_file (\
                iFolderID, EntryID, LocalPath)

        elif EntryType == Type.Directory:
            Updated = self.policy.modify_remote_directory (\
                iFolderID, EntryID, LocalPath)

        if Updated:
            self.__update_entry_in_dbm (iFolderID, EntryID)

        return Updated

    def rollback (self, iFolderID, Path):
        PathToRename, AncestorEntry = \
            self.find_closest_ancestor_remotely_alive (iFolderID, Path)

        self.handle_name_conflict (PathToRename)
        
        DeadAncestorEntryTuple = self.dbm.get_entry_by_ifolder_and_localpath (\
            iFolderID, PathToRename)

        EntryID = DeadAncestorEntryTuple['id']

        self.__delete_hierarchy_from_dbm (iFolderID, EntryID)
        self.dbm.delete_entry (iFolderID, EntryID)



    ## Delete a whole hierarchy from the local database.
    #
    #  @param iFolderID The ID of the iFolder the ancestor
    #                   entry of the hierarchy belongs to.
    #  @param EntryID The ID of the ancestor entry.

    def __delete_hierarchy_from_dbm (self, iFolderID, EntryID):
        EntryTupleList = self.dbm.get_entries_by_parent (EntryID)

        if len (EntryTupleList) == 0:
            self.dbm.delete_entry (iFolderID, EntryID)
            return

        for EntryTuple in EntryTupleList:
            ChildrenID = EntryTuple['id']

            if EntryTuple['digest'] == 'DIRECTORY':
                self.__delete_hierarchy_from_dbm (iFolderID, ChildrenID)

            self.dbm.delete_entry (iFolderID, ChildrenID)
    


    ## Commit a locally deleted entry.
    #
    #  @param iFolderID The ID of the iFolder the entry belongs to.
    #  @param EntryID The ID of the entry.
    #  @param LocalPath The local path to the entry, deprived of the
    #                   pyFolder prefix.
    #  @param EntryType The type of the entry.
    #
    #  @return True whether the deletion change has been successfully 
    #          committed.
    # 
    #  @sa The iFolder Web Service description.

    def __commit_deleted_entry (self, iFolderID, EntryID, LocalPath, \
                                    EntryType):
        Type = self.ifolderws.get_ifolder_entry_type ()
        Updated = False

        if EntryType == Type.File:
            Updated = self.policy.delete_remote_file (\
                iFolderID, EntryID, LocalPath)

        elif EntryType == Type.Directory:
            Updated = self.policy.delete_remote_directory (\
                iFolderID, EntryID, LocalPath)
            if Updated:
                self.__delete_hierarchy_from_dbm (iFolderID, EntryID)

        if Updated:
            self.__delete_entry_from_dbm (iFolderID, EntryID)

        return Updated
    


    ## Commit any local change made on existing entries.
    #
    #  @param iFolderID The ID of the iFolder the entries
    #                   belong to.
    #
    #  @return True if at least one entry has been successfully committed.

    def __commit_existing_entries (self, iFolderID):
        Action = self.ifolderws.get_change_entry_action ()
        Type = self.ifolderws.get_ifolder_entry_type ()
        Updated = False

        EntryTupleList = self.dbm.get_entries_by_ifolder (iFolderID)

        for EntryTuple in EntryTupleList:
            EntryID = EntryTuple['id']
            Path = EntryTuple['path']
            LocalPath = EntryTuple['localpath']
            Digest = EntryTuple['digest']

            if self.dbm.get_entry (iFolderID, EntryID) is None:
                continue
            
            self.logger.debug ('Checking entry `{0}\''.format (\
                    LocalPath.encode ('utf-8')))

            ChangeType, EntryType = self.get_local_changes_on_entry (\
                iFolderID, EntryID, LocalPath, Digest)

            if ChangeType is not None:
                if ChangeType == Action.Modify:
                    Updated = self.__commit_modified_entry (\
                        iFolderID, EntryID, Path, EntryType) or Updated

                elif ChangeType == Action.Delete:
                    Updated = self.__commit_deleted_entry (\
                        iFolderID, EntryID, Path, EntryType) or Updated

        return Updated



    ## Synchronize the remote repository with the local one.

    def commit (self):
        iFolderTupleList = None

        try:

            iFolderTupleList = self.dbm.get_ifolders ()

        except sqlite3.OperationalError:

            print >> sys.stderr, 'Could not open the local database. ' \
                'Please, ' \
                'run the `checkout\' action first or ' \
                'provide a valid path to the local ' \
                'database using the `--pathtodb\' ' \
                'command line switch.'
            sys.exit ()



        # We assume that the pyFolder user isn't allowed to add/delete
        # iFolders, so we are going to check just the entries

        for iFolderTuple in iFolderTupleList:
            iFolderID = iFolderTuple['id']
            Name = iFolderTuple['name']
            
            Updated = False

            try:

                Updated = self.__commit_existing_entries (iFolderID) \
                    or Updated
                Updated = self.__commit_added_entries (iFolderID, Name) \
                    or Updated

            except WebFault, wf:

                OriginalException = \
                    wf.fault.detail.detail.OriginalException._type

                if OriginalException == \
                        'iFolder.WebService.MemberDoesNotExistException' or \
                        OriginalException == \
                        'iFolder.WebService.iFolderDoesNotExistException':
                    self.policy.delete_ifolder (iFolderID, Name)

                else:
                    raise
            
            if Updated:
                self.__update_ifolder_in_dbm (iFolderID)
                
    def run (self):
        self.__setup_dbm ()

        while True:
            self.update ()
            time.sleep (SIMIAS_SYNC_INTERVAL)
            self.commit ()
            time.sleep (PYFOLDER_SYNC_INTERVAL)

    def noninteractive (self):
        self.start ()

if __name__ == '__main__':
    cm = ConfigManager (DEFAULT_CONFIG_FILE, DEFAULT_SQLITE_FILE, \
                         DEFAULT_SOAP_BUFLEN)
    pf = pyFolder (cm)
