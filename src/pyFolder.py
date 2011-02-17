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
        self.action ()
    
    # Execute the chosen action
    def action (self):
        pyFolder.__dict__[self.icm.action ()] (self)

    # Create a local copy of the user's remote directory, overwriting an
    # eventual existing local tree
    def checkout (self):
        # Create a new schema or delete the contents of the existing database
        self.dbm.create_schema ()
        # Get all the iFolders belonging to the current user
        ifolders = self.client.service.GetiFolders (0, 0)
        ifolders_count = ifolders.Total
        if ifolders_count > 0:
            for ifolder in ifolders.Items.iFolder:
                # Add the ifolder to the base tree, if it does not already 
                # exist
                if not os.path.isdir (ifolder.Name):
                    self.debug ('Creating new iFolder \'{0}\' ...'.format (ifolder.Name), False)
                    os.mkdir (ifolder.Name)
                    self.debug ('done.')
                self.debug ('Getting all the children for iFolder \'{0}\' ...'.format (ifolder.Name), False)
                # Get all the children of the given iFolder
                operation = self.client.factory.create ('SearchOperation')
                entries = self.client.service.GetEntriesByName \
                    (ifolder.ID, ifolder.ID, operation.Contains, '.', 0, 0)
                self.debug ('done.')
                # This check is just to avoid the 'AttributeError' exception
                # raised by suds when we access to the Total attribute, which
                # has not the iFolderEntry value
                entries_count = entries.Total
                if entries_count > 0:
                    for entry in entries.Items.iFolderEntry:
                        # Add the entry to the local database. We use
                        # GetChanges to get the time of the latest
                        # modification, because of the GetEntries* 
                        # WS's, do not provide the microsecond field
                        # of the timestamp with the LastModified attribute
                        changes = self.client.service.GetChanges \
                            (entry.iFolderID, entry.ID, 0, 1)
                        if changes.Total > 0:
                            for change in changes.Items.ChangeEntry:
                                self.dbm.add \
                                    (entry.iFolderID, entry.ID, change.Time)
                                # Get just the latest change
                                break
                            # If the entry is a directory and it does
                            # not already exist, create it recursively,
                            # making intermediate-levels directories
                            if entry.IsDirectory == True:
                                if not os.path.isdir (entry.Path):
                                    self.debug ('Adding directory \'{0}\' ...'.format (entry.Path), False)
                                    os.makedirs (entry.Path)
                                    self.debug ('done.')
                            else:
                                # if it is a file, just fetch it
                                self.debug ('Fetching file \'{0}\' ...'.format (entry.Path), False)
                                self.fetch \
                                    (entry.iFolderID, entry.ID, entry.Path)
                                self.debug ('done.')
                        entries_count = entries_count - 1
                        if entries_count == 0:
                            break
                ifolders_count = ifolders_count - 1
                if ifolders_count == 0:
                    break

    # Download the unique file identified by ifolderID and 
    # entryID from the server
    def fetch (self, iFolderID, entryID, path):
        handle = self.client.service.OpenFileRead (iFolderID, entryID)
        with open (path, 'wb') as f:
            while True:
                b64data = self.client.service.ReadFile \
                    (handle, icm.soapbuflen ())
                if b64data is None:
                    break
                f.write (base64.b64decode (b64data))
            self.client.service.CloseFile (handle)

    # Update the user's local copy of the iFolder tree
    def update (self):
        ifolders = self.client.service.GetiFolders (0, 0)
        ifolders_count = ifolders.Total
        if ifolders_count > 0:
            for ifolder in ifolders.Items.iFolder:
                # If any new iFolder is found, create it locally
                if not os.path.isdir (ifolder.Name):
                    self.debug ('Found new iFolder \'{0}\' adding it to the local copy ...'.format (ifolder.Name), False)
                    os.mkdir (ifolder.Name)
                    self.debug ('done.')
                # Get all the children of the current iFolder
                operation = self.client.factory.create ('SearchOperation')
                entries = self.client.service.GetEntriesByName \
                    (ifolder.ID, ifolder.ID, operation.Contains, '.', 0, 0)
                entries_count = entries.Total
                if entries_count > 0:
                    for entry in entries.Items.iFolderEntry:
                        # Get the latest change for the current entry
                        changes = self.client.service.GetChanges \
                            (entry.iFolderID, entry.ID, 0, 1)
                        changes_count = changes.Total
                        if changes_count > 0:
                            for change in changes.Items.ChangeEntry:
                                iet = self.client.factory.create \
                                    ('iFolderEntryType')
                                if os.path.exists (change.Name):
                                    # If the entry already exists on the 
                                    # local copy, we need to check whether 
                                    # it has to be updated or not
                                    if change.Time > self.dbm.mtime \
                                            (ifolder.ID, change.ID):
                                        # The server contains a more recent 
                                        # copy of the entry, let's sync it ...
                                        if change.Type == iet.File:
                                            self.debug ('Found a more recent version of the file \'{0}\', fetching it ...'.format (change.Name), False)
                                            self.fetch \
                                                (ifolder.ID, change.ID, \
                                                     change.Name)
                                            self.debug ('done.')
                                        elif change.Type == iet.Directory:
                                            if not os.path.isdir (change.Name):
                                                os.makedirs (change.Name)
                                        # Update the information about the
                                        # entry's mtime
                                        self.dbm.update \
                                            (ifolder.ID, change.ID, \
                                                 change.Time)
                                else:
                                    # The entry does not already exist on the 
                                    # local copy, so just download it
                                    if change.Type == iet.File:
                                        self.debug ('Found new file \'{0}\', fetching it ...'.format (change.Name), False)
                                        self.fetch (ifolder.ID, change.ID, change.Name)
                                        self.debug ('done.')
                                    elif change.Type == iet.Directory:
                                        if not os.path.isdir (change.Name):
                                            self.debug ('Creating new directory \'{0}\' ...'.format (change.Name), False)
                                            os.makedirs (change.Name)
                                            self.debug ('done.')
                                    self.dbm.add \
                                        (ifolder.ID, change.ID, change.Time)
                                # We mind just about the latest change made 
                                # to the entry
                                break
                    entries_count = entries_count - 1
                    if entries_count == 0:
                        break
                ifolders_count = ifolders_count - 1
                if ifolders_count == 0:
                    break
    
    # Print message to the stderr, if the user supplied the verbosity
    # command line switch. If newline is False, don't add the newline
    def debug (self, message, newline=True):
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
