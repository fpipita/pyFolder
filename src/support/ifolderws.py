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

    def get_all_ifolders (self):
        try:
            self.logger.debug ('Retrieving available ' \
                                   'iFolders for user ' \
                                   '`{0}\''.format (self.cm.get_username ()))
            iFolderSet = self.client.service.GetiFolders (0, 0)
            if iFolderSet.Total > 0:
                self.logger.debug ('{0} iFolder(s) found'.format \
                                       (iFolderSet.Total))
                return iFolderSet.Items.iFolder
            else:
                self.logger.debug ('No iFolders found')
            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_ifolder_entry_id (self, iFolderID):
        try:
            self.logger.debug ('Getting iFolderEntryID for iFolder with ' \
                                   'ID={0}'.format (iFolderID))
            iFolderEntrySet = \
                self.client.service.GetEntries (iFolderID, iFolderID, 0, 1)
            if iFolderEntrySet.Total > 0:
                for iFolderEntry in iFolderEntrySet.Items.iFolderEntry:
                    self.logger.debug ('Success, got iFolderEntryID=' \
                                           '{0}'.format (iFolderEntry.ID))
                    return iFolderEntry
            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_latest_change (self, iFolderID, iFolderEntryID):
        try:
            self.logger.debug ('Getting latest change ' \
                                   'for entry `{0}\''.format (iFolderEntryID))
            ChangeEntrySet = \
                self.client.service.GetChanges \
                (iFolderID, iFolderEntryID, 0, 1)
            if ChangeEntrySet.Total > 0:
                for ChangeEntry in ChangeEntrySet.Items.ChangeEntry:
                    self.logger.debug ('Latest Change for ' \
                                           'iFolderEntry `{0}\' ' \
                                           'is of Type `{1}\''.format \
                                           (ChangeEntry.Name, \
                                                ChangeEntry.Action))
                    return ChangeEntry
            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise
        
    def get_entry_by_path (self, iFolderID, Path):
        try:
            self.logger.debug ('Getting iFolderEntry `{0}\' '\
                                   'by iFolderID and Path'.format (Path))
            iFolderEntry = self.client.service.GetEntryByPath (iFolderID, Path)
            if iFolderEntry is not None:
                self.logger.debug ('Got iFolderEntry ' \
                                       'with ID={0}'.format (iFolderEntry.ID))
                return iFolderEntry
            else:
                self.logger.debug ('Could not get ' \
                                       'iFolderEntry `{0\''.format (Path))
            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_children_by_ifolder (self, iFolderID):
        try:
            self.logger.debug ('Getting all the children for ' \
                                   'iFolder with ID={0}'.format (iFolderID))
            operation = self.client.factory.create ('SearchOperation')
            iFolderEntrySet = self.client.service.GetEntriesByName \
                (iFolderID, iFolderID, operation.Contains, '.', 0, 0)
            if iFolderEntrySet.Total > 0:
                iFolderEntry = iFolderEntrySet.Items.iFolderEntry
                self.logger.debug ('Found {0} ' \
                                       'children'.format (len (iFolderEntry)))
                return iFolderEntry
            else:
                self.logger.debug ('iFolder with ID={0} ' \
                                       'hasn\'t any children'.format \
                                       (iFolderID))
            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_ifolder (self, iFolderID):
        try:
            self.logger.debug ('Getting iFolder with ID={0}'.format \
                                   (iFolderID))
            iFolder = self.client.service.GetiFolder (iFolderID)
            if iFolder is not None:
                self.logger.debug ('iFolder with ID={0} has ' \
                                       'name `{1}\''.format \
                                       (iFolder.ID, iFolder.Name))
                return iFolder
            else:
                self.logger.debug ('Could not get iFolder with ID={0}'.format \
                                       (iFolderID))
            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def get_entry (self, iFolderID, iFolderEntryID):
        try:
            self.logger.debug ('Getting iFolderEntry with ID={0} ' \
                                   'and iFolderID={1}'.format \
                                   (iFolderID, iFolderEntryID))
            iFolderEntry = self.client.service.GetEntry \
                (iFolderID, iFolderEntryID)
            if iFolderEntry is not None:
                self.logger.debug ('Got iFolderEntry with ' \
                                       'name `{0}\' '.format \
                                       (iFolderEntry.Name))
                return iFolderEntry
            else:
                self.logger.debug ('Could not get iFolderEntry')
            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise
        
    def open_file_read (self, iFolderID, iFolderEntryID):
        try:
            Handle = self.client.service.OpenFileRead \
                (iFolderID, iFolderEntryID)
            if Handle is not None:
                self.logger.info (\
                    'Remote File has been successfully ' \
                        'opened for reading')
                return Handle
            else:
                self.logger.warning (\
                    'Could not open remote File for reading')
            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def read_file (self, Handle):
        try:
            return self.client.service.ReadFile \
                (Handle, self.cm.get_soapbuflen ())
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def open_file_write (self, iFolderID, iFolderEntryID, Size):
        try :
            Handle = self.client.service.OpenFileWrite \
                (iFolderID, iFolderEntryID, Size)
            if Handle is not None:
                self.logger.info (\
                    'Remote File has beend successfully ' \
                        'opened for writing')
                return Handle
            else:
                self.logger.warning (\
                    'Could not open remote File for writing')
            return None
        except WebFault, wf:
            self.logger.debug (wf)
            raise
    
    def write_file (self, Handle, Data):
        try:
            self.client.service.WriteFile (Handle, Data)
            return True
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def close_file (self, Handle):
        try:
            self.logger.debug ('Closing file with handle={0}'.format (Handle))
            self.client.service.CloseFile (Handle)
            self.logger.info ('File with handle={0} closed'.format (Handle))
            return True
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def create_entry (self, iFolderID, ParentID, Name, Type):
        try:
            iFolderEntry = \
                self.client.service.CreateEntry \
                (iFolderID, ParentID, Type, Name)
            if iFolderEntry is not None:
                self.logger.info ('{0} `{1}\', ' \
                                      'has been remotely ' \
                                      'created'.format (Type, Name))
                return iFolderEntry
            else:
                self.logger.warning ('Could not create ' \
                                         '`{0}\' remotely'.format (Name))
            return None
        except WebFault, wf:
            self.logger.error (wf)
            raise

    def delete_entry (self, iFolderID, iFolderEntryID, Name, Type):
        try:
            self.client.service.DeleteEntry (iFolderID, iFolderEntryID)
            self.logger.info ('{0} `{1}\', ' \
                                  'has been remotely ' \
                                  'deleted'.format (Type, Name))
            return True
        except WebFault, wf:
            self.logger.error (wf)
            raise
        
    def get_ifolder_entry_type (self):
        return self.client.factory.create ('iFolderEntryType')
        
    def get_change_entry_action (self):
        return self.client.factory.create ('ChangeEntryAction')
