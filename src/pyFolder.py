#!/usr/bin/python

from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds import WebFault
from optparse import OptionParser
from datetime import *

import base64
import os
import sqlite3
import sys

DEFAULT_SOAP_BUFLEN = 65536
DEFAULT_CONFIG_FILE = os.path.expanduser (os.path.join ('~', '.ifolderrc'))
DEFAULT_SQLITE_FILE = os.path.expanduser (os.path.join ('~', '.ifolderdb'))

class pyFolderConfigManager ():
    class pyFolderConfigFile:
        def __init__ (self, ifcm):
            pass

    def __init__ (self):

        # Try to read the configuration file
        pyFolderConfigManager.pyFolderConfigFile (self)
        
        # If the user provides any command line option, just overwrite the 
        # settings previously read from the configuration file
        self.parser = OptionParser ()

        self.parser.add_option ('--username', \
                                    action='store', \
                                    type='string', \
                                    dest='username', \
                                    help='The username that you use to ' \
                                    'login into your iFolder account')

        self.parser.add_option ('--password', \
                                    action='store', \
                                    type='string', \
                                    dest='password', \
                                    help='The password that you use to ' \
                                    'login into your iFolder account')

        self.parser.add_option ('--ifolderws', \
                                    action='store', \
                                    type='string', \
                                    dest='ifolderws', \
                                    help='The iFolder Web Service URI')

        self.parser.add_option ('--soapbuflen', \
                                    action='store', \
                                    type='int', \
                                    dest='soapbuflen', \
                                    help='Bufferize up to SOAPBUFLEN bytes ' \
                                    'before to flush [ default : %default ]', \
                                    default=DEFAULT_SOAP_BUFLEN)

        self.parser.add_option ('--config', \
                                    action='store', \
                                    type='string', \
                                    dest='configfile', \
                                    help='Read the configuration from ' \
                                    'CONFIGFILE [ default : %default ]', \
                                    default=DEFAULT_CONFIG_FILE)

        self.parser.add_option ('--pathtodb', \
                                    action='store', \
                                    type='string', \
                                    dest='pathtodb', \
                                    help='The path to a local sqlite ' \
                                    'database containing the mapping ' \
                                    'between the entry-IDs and their ' \
                                    'modification times [ default : ' \
                                    '%default ]', \
                                    default=DEFAULT_SQLITE_FILE)

        self.parser.add_option ('--action', \
                                    action='store', \
                                    type='choice', \
                                    dest='action', \
                                    help='The action that will be done by ' \
                                    'pyFolder [ default: %default ]', \
                                    choices=self.actions (), \
                                    default=self.actions ()[0])

        self.parser.add_option ('--verbose', '-v', \
                                    action='store_true', \
                                    dest='verbose', \
                                    help='Starts pyFolder in verbose mode, ' \
                                    'printing debug/error messages ' \
                                    'on the stderr [ default : %default ]', \
                                    default=False)
                                    
        (self.options, self.args) = self.parser.parse_args ()
        if self.options.username is None or self.options.password is None \
                or self.options.ifolderws is None:
            self.parser.print_help ()
            sys.exit ()

    def actions (self):
        return [\
            'checkout', \
             'update' \
                ]

    def action (self):
        return self.options.action

    def username (self):
        return self.options.username

    def password (self):
        return self.options.password

    def ifolderws (self):
        return self.options.ifolderws
    
    def soapbuflen (self):
        return self.options.soapbuflen

    def pathtodb (self):
        return self.options.pathtodb

    def verbose (self):
        return self.options.verbose

class pyFolderDBManager:
    def __init__ (self, pathtodb):
        self.cx = sqlite3.connect (pathtodb)

    def create_schema (self):
        cu = self.cx.cursor ()
        try:
            # If the schema already exists ...
            cu.execute ('CREATE TABLE iFolder (iFolderID TEXT, ' \
                            'entryID TEXT, mtime DATETIME, ' \
                            'PRIMARY KEY (iFolderID, entryID))')
        except sqlite3.OperationalError, oe:
            # ... just remove all the tuples
            cu.execute ('DELETE FROM iFolder')
        finally:
            self.cx.commit ()

    # Add a new tuple (iFolderID, entryID, mtime) to the local
    # database or do nothing if it already exists
    def add (self, iFolderID, entryID, mtime):
        cu = self.cx.cursor ()
        try:
            cu.execute ('INSERT INTO iFolder VALUES (?, ?, ?)', \
                            (iFolderID, entryID, mtime))
            self.cx.commit ()
        except sqlite3.IntegrityError:
            pass

    # Update the tuple (iFolderID, entryID, mtime) or insert it if
    # it does not already exist
    def update (self, iFolderID, entryID, mtime):
        cu = self.cx.cursor ()

        if self.mtime (iFolderID, entryID) > \
                datetime (MINYEAR, 1, 1, 0, 0, 0, 0):
            cu.execute ('UPDATE iFolder SET mtime=(?) ' \
                            'WHERE iFolderID=(?) AND ' \
                            'entryID=(?)', (mtime, iFolderID, entryID))
            self.cx.commit ()
        else:
            self.add (iFolderID, entryID, mtime)
    
    # Get a datetime.datetime object representing the timestamp of
    # the last modification made to the entry identified by the composite
    # key (iFolderID, entryID)
    def mtime (self, iFolderID, entryID):
        cu = self.cx.cursor ()
        try:
            cu.execute ('SELECT i.mtime FROM iFolder AS i ' \
                            'WHERE i.iFolderID=? AND i.entryID=?', \
                            (iFolderID, entryID))
            mtime = cu.fetchone ()
            if mtime is not None:
                # The entry exists in the local copy, so just return its mtime
                mtime = datetime.strptime (mtime[0], '%Y-%m-%d %H:%M:%S.%f')
            else:
                # The db is empty or the entry does not 
                # exist yet in the local copy, let's create a 'mock' mtime
                mtime = datetime (MINYEAR, 1, 1, 0, 0, 0, 0)
        except sqlite3.OperationalError, oe:
            # We are probably running the 'update' action without 
            # having ever run the 'checkout' action first, so we
            # create the schema and then we return a 'mock' mtime
            self.create_schema ()
            mtime = datetime (MINYEAR, 1, 1, 0, 0, 0, 0)
        return mtime

    # The object destructor, to make sure that the connection to the db
    # gets properly closed and all the modifies made committed
    def __del__ (self):
        self.cx.commit ()
        self.cx.close ()

class pyFolder:
    def __init__ (self, icm):
        transport = HttpAuthenticated (username=icm.username (), \
                                           password=icm.password ())
        self.icm = icm
        self.client = Client (icm.ifolderws (), transport=transport)
        self.dbm = pyFolderDBManager (self.icm.pathtodb ())
        self.__action ()
    
    # Execute the chosen action
    def __action (self):
        pyFolder.__dict__[self.icm.action ()] (self)

    # Create a local copy of the user's remote directory, overwriting an
    # eventual existing local tree
    def checkout (self):
        self.update (checkout=True)

    def __get_all_ifolders (self):
        return self.client.service.GetiFolders (0, 0)

    def __add_ifolder (self, ifolder):
        if not os.path.isdir (ifolder.Name):
            self.__debug ('Creating new iFolder \'{0}\' ...'.format (ifolder.Name), False)
            os.mkdir (ifolder.Name)
            self.__debug ('done.')

    # Download the unique file identified by ifolderID and 
    # entryID from the server
    def __fetch (self, iFolderID, entryID, path):
        handle = self.client.service.OpenFileRead (iFolderID, entryID)
        with open (path, 'wb') as f:
            while True:
                b64data = self.client.service.ReadFile \
                    (handle, icm.soapbuflen ())
                # When the remote file pointer reaches the end,
                # ReadFile returns nothing
                if b64data is None:
                    break
                f.write (base64.b64decode (b64data))
            self.client.service.CloseFile (handle)

    # Update the user's local copy of the iFolder tree
    # WARNING: what does it happen whether the user adds/modifies a file
    #          in a shared directory and, in the meanwhile, on the server
    #          side, someone else creates/modifies a file with the same
    #          path/name ?
    #          
    #          1. Execute a default action, like to keep the local version
    #             or to dowload the server one
    #          2. Ask the user what to do
    #
    # TROUBLE: How to determine whether the user has made any kind of local
    #          changes on a file in a shared directory, since the last update ?

    # SOLUTION: While updating, we may store, for each file-entry, also
    #           its hash in the local database. Then, when we run the update,
    #           for each file, we might do something like ...
    #           
    #           if hash (change.Name) != db.get_hash (iFolder.ID, change.ID)
    #           then the file has local changes ...
    #           
    #           if the hashes coincide, then we can do the check on the mtime
    #           and if the mtime of the file on the server, is newer than the
    #           one stored in the local database, we can safely fetch the newer
    #           version.
    #          
    def update (self, checkout=False):
        if checkout:
            self.dbm.create_schema ()
        ifolders = self.__get_all_ifolders ()
        ifolders_count = ifolders.Total
        if ifolders_count > 0:
            for ifolder in ifolders.Items.iFolder:
                self.__add_ifolder (ifolder)
                entries = self.__get_children_by_ifolder (ifolder)
                entries_count = entries.Total
                if entries_count > 0:
                    for entry in entries.Items.iFolderEntry:
                        latest_change = self.__get_latest_change (entry)
                        if latest_change.Total > 0:
                            for change in latest_change.Items.ChangeEntry:
                                self.__apply_change (ifolder, change, checkout)
                                break
                    entries_count = entries_count - 1
                    if entries_count == 0:
                        break
                ifolders_count = ifolders_count - 1
                if ifolders_count == 0:
                    break
    
    def __get_children_by_ifolder (self, ifolder):
        operation = self.client.factory.create ('SearchOperation')
        return self.client.service.GetEntriesByName ( \
            ifolder.ID, ifolder.ID, operation.Contains, '.', 0, 0)

    def __get_latest_change (self, entry):
        return self.client.service.GetChanges (entry.iFolderID, entry.ID, 0, 1)

    # Apply `change' to `ifolder'. If `force' is True, apply
    # the change unconditionally
    def __apply_change (self, ifolder, change, force=False):
        iet = self.client.factory.create ('iFolderEntryType')
        if not force and os.path.exists (change.Name):
            # If the entry already exists in the 
            # local copy, we need to check whether 
            # it has to be updated or not
            if change.Time > self.dbm.mtime (ifolder.ID, change.ID):
                # The server contains a more recent 
                # copy of the entry, let's sync it ...
                if change.Type == iet.File:
                    self.__debug ('Found a more recent version of the file \'{0}\', fetching it ...'.format (change.Name), False)
                    self.__fetch (ifolder.ID, change.ID, change.Name)
                    self.__debug ('done.')
                elif change.Type == iet.Directory:
                    if not os.path.isdir (change.Name):
                        os.makedirs (change.Name)
                # Update the information about the
                # entry's mtime
                self.dbm.update (ifolder.ID, change.ID, change.Time)
        else:
            # The entry does not already exist on the 
            # local copy, so just download it
            if change.Type == iet.File:
                self.__debug ('Found new file \'{0}\', fetching it ...'.format (change.Name), False)
                self.__fetch (ifolder.ID, change.ID, change.Name)
                self.__debug ('done.')
            elif change.Type == iet.Directory:
                if not os.path.isdir (change.Name):
                    self.__debug ('Creating new directory \'{0}\' ...'.format (change.Name), False)
                    os.makedirs (change.Name)
                    self.__debug ('done.')
            self.dbm.update (ifolder.ID, change.ID, change.Time)

    # Print message to the stderr, if the user supplied the verbosity
    # command line switch. If newline is False, don't add the newline
    def __debug (self, message, newline=True):
        if self.icm.verbose ():
            if newline:
                print >> sys.stderr, message
            else:
                print >> sys.stderr, message,

if __name__ == '__main__':
    icm = pyFolderConfigManager ()
    try:    
        ifc = pyFolder (icm)
    except WebFault, wf:
        print wf
