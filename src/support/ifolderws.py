# -*- coding: utf-8 -*-

import logging
from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds import WebFault

class iFolderWS:
    def __init__ (self, cm):
        self.cm = cm
        self.__setup_suds_client ()
        self.__setup_logger ()

    def __setup_logger (self):
        self.logger = logging.getLogger ('pyFolder.iFolderWS')

    def __setup_suds_client (self):
        transport = HttpAuthenticated (username=self.cm.get_username (), \
                                           password=self.cm.get_password ())
        self.client = Client (self.cm.get_ifolderws (), transport=transport)
        
    def create_ifolder (self, Name, Description='', SSL=False, \
                            EncryptionAlgorithm='', PassPhrase=''):
        try:

            return self.client.service.CreateiFolder (\
                Name, Description, SSL, EncryptionAlgorithm, PassPhrase)

        except WebFault, wf:
            self.logger.error (wf)
            raise

    def delete_ifolder (self, iFolderID):
        try:

            self.client.service.DeleteiFolder (iFolderID)

        except WebFault, wf:
            self.logger.error (wf)
            raise
    
    def get_all_ifolders (self):
        try:
            iFolderSet = self.client.service.GetiFolders (0, 0)

            if iFolderSet.Total > 0:
                return iFolderSet.Items.iFolder

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_ifolder_as_entry (self, iFolderID):
        try:
            iFolderEntrySet = \
                self.client.service.GetEntries (iFolderID, iFolderID, 0, 1)

            if iFolderEntrySet.Total > 0:
                for iFolderEntry in iFolderEntrySet.Items.iFolderEntry:
                    return iFolderEntry

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_latest_change (self, iFolderID, EntryID):
        try:
            ChangeEntrySet = \
                self.client.service.GetChanges (iFolderID, EntryID, 0, 1)

            if ChangeEntrySet.Total > 0:
                for Change in ChangeEntrySet.Items.ChangeEntry:
                    return Change

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise
        
    def get_entry_by_path (self, iFolderID, Path):
        try:
            iFolderEntry = self.client.service.GetEntryByPath (iFolderID, Path)

            if iFolderEntry is not None:
                return iFolderEntry

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise
        
    def get_entries_by_name (self, iFolderID, ParentID, Operation, Pattern, \
                                 Index, Max):
        try:
            iFolderEntrySet = \
                self.client.service.GetEntriesByName (\
                iFolderID, ParentID, Operation, Pattern, \
                                 Index, Max)

            if iFolderEntrySet.Total > 0:
                return iFolderEntrySet.Items.iFolderEntry

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_children_by_ifolder (self, iFolderID):
        try:
            Operation = self.get_search_operation ()
            iFolderEntrySet = self.client.service.GetEntriesByName \
                (iFolderID, iFolderID, Operation.Contains, '.', 0, 0)

            if iFolderEntrySet.Total > 0:
                return iFolderEntrySet.Items.iFolderEntry

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_ifolder (self, iFolderID):
        try:
            iFolder = self.client.service.GetiFolder (iFolderID)

            if iFolder is not None:
                return iFolder

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_entry (self, iFolderID, EntryID):
        try:

            Entry = self.client.service.GetEntry (iFolderID, EntryID)

            if Entry is not None:
                return Entry

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise
        
    def open_file_read (self, iFolderID, EntryID):
        try:
            Handle = self.client.service.OpenFileRead (iFolderID, EntryID)

            if Handle is not None:
                return Handle

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def read_file (self, Handle):
        try:

            return self.client.service.ReadFile (\
                Handle, self.cm.get_soapbuflen ())

        except WebFault, wf:
            self.logger.error (wf)
            raise

    def open_file_write (self, iFolderID, EntryID, Size):
        try :
            Handle = self.client.service.OpenFileWrite (\
                iFolderID, EntryID, Size)

            if Handle is not None:
                return Handle

            return None
        except WebFault, wf:
            self.logger.debug (wf)
            raise
    
    def write_file (self, Handle, Data):
        try:

            self.client.service.WriteFile (Handle, Data)

        except WebFault, wf:
            self.logger.error (wf)
            raise

    def close_file (self, Handle):
        try:

            self.client.service.CloseFile (Handle)

        except WebFault, wf:
            self.logger.error (wf)
            raise

    def create_entry (self, iFolderID, ParentID, Name, Type):
        try:
            Entry = self.client.service.CreateEntry (\
                iFolderID, ParentID, Type, Name)

            if Entry is not None:
                return Entry

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def delete_entry (self, iFolderID, EntryID, Name, Type):
        try:

            self.client.service.DeleteEntry (iFolderID, EntryID)

        except WebFault, wf:
            self.logger.error (wf)
            raise
        
    def add_member (self, iFolderID, UserID, Rights):
        try:

            self.client.service.AddMember (iFolderID, UserID, Rights)

        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_users_by_search (self, Property, Operation, Pattern, \
                                 Index, Max):
        try:
            iFolderUserSet = self.client.service.GetUsersBySearch (\
                Property, Operation, Pattern, Index, Max)

            if iFolderUserSet.Total > 0:
                return iFolderUserSet.Items.iFolderUser

            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_ifolder_entry_type (self):
        return self.client.factory.create ('iFolderEntryType')
        
    def get_change_entry_action (self):
        return self.client.factory.create ('ChangeEntryAction')
    
    def get_rights (self):
        return self.client.factory.create ('Rights')

    def get_search_property (self):
        return self.client.factory.create ('SearchProperty')
    
    def get_search_operation (self):
        return self.client.factory.create ('SearchOperation')
