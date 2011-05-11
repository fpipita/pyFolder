# -*- coding: utf-8 -*-



from Policy import *



## The default Policy used by pyFolder.

class DefaultPolicy (Policy):



    def add_directory (self, iFolderID, EntryID, Path):
        try:

            self.pyFolder.mkdir (Path)

        except OSError:
            pass
        return True



    def add_file (self, iFolderID, EntryID, Path):
        try:

            if self.pyFolder.file_has_local_changes (\
                iFolderID, EntryID, Path, Localize=True):
                self.pyFolder.handle_name_conflict (Path)

            self.pyFolder.fetch (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == \
                    'iFolder.WebService.EntryDoesNotExistException':
                return False

            elif OriginalException == 'System.IO.IOException':
                self.pyFolder.ignore_in_use (Path)
                return False

            else:
                raise

        except IOError:

            # BUG #0000 - Closed.
            # It happened when, at the update time, parth of path
            # to Path had been deleted locally.

            self.pyFolder.handle_ioerror (iFolderID, Path)
            return False



    def modify_directory (self, iFolderID, EntryID, Path):
        return True



    def modify_file (self, iFolderID, EntryID, Path):
        try:

            if self.pyFolder.file_has_local_changes (\
                iFolderID, EntryID, Path, Localize=True):
                self.pyFolder.handle_name_conflict (Path)

            self.pyFolder.fetch (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == \
                    'iFolder.WebService.EntryDoesNotExistException':
                return False

            elif OriginalException == 'System.IO.IOException':
                self.pyFolder.ignore_in_use (Path)
                return False

            else:
                raise

        except IOError:

            self.pyFolder.handle_ioerror (iFolderID, Path)
            return False



    def delete_directory (self, iFolderID, EntryID, Path):
        if self.pyFolder.directory_has_local_changes (\
            iFolderID, EntryID) or \
            self.pyFolder.directory_has_new_entries (iFolderID, Path):
            self.pyFolder.handle_name_conflict (Path)

        try:

            self.pyFolder.rmdir (Path)

        except OSError:
            pass

        return True



    def delete_file (self, iFolderID, EntryID, Path):
        try:

            if self.pyFolder.file_has_local_changes (\
                iFolderID, EntryID, Path, Localize=True):
                self.pyFolder.handle_name_conflict (Path)

            self.pyFolder.delete (Path)

        except OSError:
            pass
        return True



    def add_remote_directory (self, iFolderID, ParentID, Path):
        try:

            Entry = self.pyFolder.remote_mkdir (iFolderID, ParentID, Path)
            self.pyFolder.add_entry_to_dbm (Entry)
            return Entry

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == \
                    'iFolder.WebService.EntryAlreadyExistException':
                self.pyFolder.handle_name_conflict (Path)
                return None

            elif OriginalException == \
                    'iFolder.WebService.EntryInvalidCharactersException':
                self.pyFolder.handle_name_conflict (Path, InvalidChars=True)
                return None

            elif OriginalException == \
                    'iFolder.WebService.FileTypeException':
                self.pyFolder.ignore_locked (Path)
                return None

            elif OriginalException == 'System.NullReferenceException' or \
                    OriginalException == \
                    'System.IO.DirectoryNotFoundException':
                self.pyFolder.rollback (iFolderID, Path)
                return None

            elif OriginalException == 'Simias.Storage.AccessException':
                self.pyFolder.ignore_no_rights (Path)
                return None

            else:
                raise



    def add_remote_file (self, iFolderID, ParentID, Path):
        try:

            Entry = self.pyFolder.remote_create_file (\
                iFolderID, ParentID, Path)

            self.pyFolder.add_entry_to_dbm (Entry)

            return Entry

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == \
                    'iFolder.WebService.EntryAlreadyExistException':
                self.pyFolder.handle_name_conflict (Path)
                return None

            elif OriginalException == \
                    'iFolder.WebService.EntryInvalidCharactersException':
                self.pyFolder.handle_name_conflict (Path, InvalidChars=True)
                return None

            elif OriginalException == \
                    'iFolder.WebService.FileTypeException':
                self.pyFolder.ignore_locked (Path)
                return None

            elif OriginalException == 'System.NullReferenceException' or \
                    OriginalException == \
                    'System.IO.DirectoryNotFoundException':
                self.pyFolder.rollback (iFolderID, Path)
                return None

            elif OriginalException == 'Simias.Storage.AccessException':
                self.pyFolder.ignore_no_rights (Path)
                return None

            else:
                raise



    def modify_remote_directory (self, iFolderID, EntryID, Path):
        return True



    def modify_remote_file (self, iFolderID, EntryID, Path):
        try:

            self.pyFolder.remote_file_write (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == 'System.IO.IOException':
                self.pyFolder.ignore_in_use (Path)
                return False

            elif OriginalException == 'Simias.Storage.AccessException':
                self.pyFolder.ignore_no_rights (Path)
                return False

            elif OriginalException == \
                    'iFolder.WebService.EntryDoesNotExistException':

                # BUG #0001 - Closed.
                # It happened when we were going to modify a shared
                # file which, at the time of the commit, has been remotely
                # deleted by anybody else.

                self.pyFolder.rollback (iFolderID, Path)
                return False

            elif OriginalException == \
                    'iFolder.WebService.MemberDoesNotExistException' or \
                    OriginalException == \
                    'iFolder.WebService.iFolderDoesNotExistException':
                raise

            else:
                raise



    def delete_remote_directory (self, iFolderID, EntryID, Path):
        try:

            self.pyFolder.remote_rmdir (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == 'System.IO.IOException':
                self.pyFolder.ignore_in_use (Path)
                return False

            elif OriginalException == 'Simias.Storage.AccessException':
                self.pyFolder.ignore_no_rights (Path)
                return False

            elif OriginalException == \
                    'iFolder.WebService.EntryDoesNotExistException':
                return True

            elif OriginalException == \
                    'iFolder.WebService.MemberDoesNotExistException' or \
                    OriginalException == \
                    'iFolder.WebService.iFolderDoesNotExistException':
                raise

            else:
                raise



    def delete_remote_file (self, iFolderID, EntryID, Path):
        try:

            self.pyFolder.remote_delete (iFolderID, EntryID, Path)
            return True

        except WebFault, wf:
            OriginalException = wf.fault.detail.detail.OriginalException._type

            if OriginalException == 'System.IO.IOException':
                self.pyFolder.ignore_in_use (Path)
                return False

            elif OriginalException == 'Simias.Storage.AccessException':
                self.pyFolder.ignore_no_rights (Path)
                return False

            elif OriginalException == \
                    'iFolder.WebService.EntryDoesNotExistException':
                return True

            elif OriginalException == \
                    'iFolder.WebService.MemberDoesNotExistException' or \
                    OriginalException == \
                    'iFolder.WebService.iFolderDoesNotExistException':
                raise

            else:
                raise



    def delete_ifolder (self, iFolderID, Path):
        if self.pyFolder.ifolder_has_local_changes (iFolderID):
            self.pyFolder.handle_name_conflict (Path)

        try:

            self.pyFolder.delete_ifolder (iFolderID, Path)

        except OSError, ose:
            pass
