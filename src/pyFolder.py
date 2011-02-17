#!/usr/bin/python

from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds import WebFault
from optparse import OptionParser

import datetime
import base64
import os
import sqlite3
import sys

DEFAULT_SOAP_BUFLEN = 65536
DEFAULT_CONFIG_FILE = os.path.expanduser (os.path.join ('~', '.ifolderrc'))
DEFAULT_SQLITE_FILE = os.path.expanduser (os.path.join ('~', '.ifolderdb'))

class iFolderConfigManager ():
    class iFolderConfigFile:
        def __init__ (self, ifcm):
            pass

    def __init__ (self):

        # Try to read the configuration file
        iFolderConfigManager.iFolderConfigFile (self)
        
        # If the user provides any command line option, just overwrite the 
        # settings previously read from the configuration file
        self.parser = OptionParser ()

        self.parser.add_option ('--username', '-u', \
                                    action='store', \
                                    type='string', \
                                    dest='username', \
                                    help='The username for your iFolder account')

        self.parser.add_option ('--password', '-p', \
                                    action='store', \
                                    type='string', \
                                    dest='password', \
                                    help='The password for your iFolder account')

        self.parser.add_option ('--ifolderws', \
                                    action='store', \
                                    type='string', \
                                    dest='ifolderws', \
                                    help='The iFolder Web Service URI')

        self.parser.add_option ('--soapbuflen', '-b', \
                                    action='store', \
                                    type='int', \
                                    dest='soapbuflen', \
                                    help='Bufferize up to SOAPBUFLEN bytes before to flush [ default : %default ]', \
                                    default=DEFAULT_SOAP_BUFLEN)

        self.parser.add_option ('--config', '-c', \
                                    action='store', \
                                    type='string', \
                                    dest='configfile', \
                                    help='Read the configuration from CONFIGFILE [ default : %default ]', \
                                    default=DEFAULT_CONFIG_FILE)

        self.parser.add_option ('--pathtodb', '-s', \
                                    action='store', \
                                    type='string', \
                                    dest='pathtodb', \
                                    help='The path to a local sqlite database containing the mapping between '\
                                    'the entry-IDs and their modification times [ default : %default ]', \
                                    default=DEFAULT_SQLITE_FILE)

        self.parser.add_option ('--action', '-a', \
                                    action='store', \
                                    type='choice', \
                                    dest='action', \
                                    help='The action that will be done by iFolderClient [ default: %default ]', \
                                    choices=self.choices (), \
                                    default=self.choices ()[0])

        self.parser.add_option ('--verbose', '-v', \
                                    action='store_true', \
                                    dest='verbose', \
                                    help='Starts iFolderClient in verbose mode, printing debug/error messages ' \
                                    'on the stderr [ default : %default ]', \
                                    default=False)
                                    
        (self.options, self.args) = self.parser.parse_args ()
        if self.options.username is None or self.options.password is None or self.options.ifolderws is None:
            self.parser.print_help ()
            sys.exit ()

    def choices (self):
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

class iFolderDBManager:
    def __init__ (self, pathtodb):
        self.cx = sqlite3.connect (pathtodb)

    def create_schema (self):
        cu = self.cx.cursor ()
        try:
            # If the schema already exists ...
            cu.execute ('CREATE TABLE iFolder (iFolderID TEXT, entryID TEXT, mtime DATETIME, PRIMARY KEY (iFolderID, entryID))')

        except sqlite3.OperationalError, oe:
            
            # ... just remove all the tuples
            cu.execute ('DELETE FROM iFolder')

        finally:
            self.cx.commit ()

    def add (self, iFolderID, entryID, mtime):
        cu = self.cx.cursor ()
        cu.execute ('INSERT INTO iFolder VALUES (?, ?, ?)', (iFolderID, entryID, mtime))
        self.cx.commit ()

    def update (self, iFolderID, entryID, mtime):
        cu = self.cx.cursor ()

        if self.mtime (iFolderID, entryID) > datetime.datetime (datetime.MINYEAR, 1, 1, 0, 0, 0, 0):

            cu.execute ('UPDATE iFolder SET mtime=(?) WHERE iFolderID=(?) AND entryID=(?)', (mtime, iFolderID, entryID))
            self.cx.commit ()

        else:

            self.add (iFolderID, entryID, mtime)
    
    def mtime (self, iFolderID, entryID):
        cu = self.cx.cursor ()
        try:

            cu.execute ('SELECT i.mtime FROM iFolder AS i WHERE i.iFolderID=? AND i.entryID=?', (iFolderID, entryID))
            mtime = cu.fetchone ()

            if mtime is not None:

                # The entry exists in the local copy, so return its mtime
                mtime = datetime.datetime.strptime (mtime[0], '%Y-%m-%d %H:%M:%S.%f')

            else:

                # The db is empty or the entry does not exist yet in the local copy
                mtime = datetime.datetime (datetime.MINYEAR, 1, 1, 0, 0, 0, 0)

        except sqlite3.OperationalError, oe:
            
            # We are probably running the 'update' action without running the 'checkout', so
            # we need to create the schema first
            self.create_schema ()
            mtime = datetime.datetime (datetime.MINYEAR, 1, 1, 0, 0, 0, 0)
            
        return mtime

    def __del__ (self):
        self.cx.close ()

class iFolderClient:

    def __init__ (self, icm):
        transport = HttpAuthenticated (username=icm.username (), password=icm.password ())
        self.icm = icm
        self.client = Client (icm.ifolderws (), transport=transport)
        self.dbm = iFolderDBManager (self.icm.pathtodb ())
        self.action ()
        
    def action (self):
        iFolderClient.__dict__[self.icm.action ()] (self)

    # Creates a local copy of the user's remote directory tree and the database
    # needed to handle the changes
    def checkout (self):

        # Create a new schema or delete the contents of the existing database
        self.dbm.create_schema ()
        
        # Get all the iFolders belonging to the current user
        ifolders = self.client.service.GetiFolders (0, 0)

        ifolders_count = ifolders.Total
        if ifolders_count > 0:
            for ifolder in ifolders.Items.iFolder:
            
                # Add the ifolder to the base tree, if it does not already exist
                if not os.path.isdir (ifolder.Name):
                    os.mkdir (ifolder.Name)

                # Get all the children of the given iFolder
                operation = self.client.factory.create ('SearchOperation')
                entries = self.client.service.GetEntriesByName (ifolder.ID, ifolder.ID, operation.Contains, '.', 0, 0)

                # This check is just to avoid the 'AttributeError' exception raised by suds when we access to the
                # Total attribute, which has no iFolderEntry value
                entries_count = entries.Total
                if entries_count > 0:
                    for entry in entries.Items.iFolderEntry:

                        # Add the entry to the local database. We use GetChanges to get the time of the latest 
                        # modification, because of the GetEntries* WS's, do not provide the microsecond field 
                        # of the timestamp with the LastModified attribute.
                        changes = self.client.service.GetChanges (entry.iFolderID, entry.ID, 0, 1)

                        if changes.Total > 0:
                            for change in changes.Items.ChangeEntry:
                                self.dbm.add (entry.iFolderID, entry.ID, change.Time)
                                # Get just the latest change
                                break

                            # If the entry is a directory and it does not already exist, create it recursively,
                            # making intermediate-levels directories
                            if entry.IsDirectory == True:
                                if not os.path.isdir (entry.Path):
                                    os.makedirs (entry.Path)
                            else:
                                # if it is a file, just fetch it
                                self.fetch (entry.iFolderID, entry.ID, entry.Path)

                        entries_count = entries_count - 1
                        if entries_count == 0:
                            break

                ifolders_count = ifolders_count - 1
                if ifolders_count == 0:
                    break

    # Downloads the unique file identified by ifolderID and entryID from the server
    def fetch (self, iFolderID, entryID, path):
        handle = self.client.service.OpenFileRead (iFolderID, entryID)
        with open (path, 'wb') as f:
            while True:
                b64data = self.client.service.ReadFile (handle, icm.soapbuflen ())
                if b64data is None:
                    break
                f.write (base64.b64decode (b64data))
            self.client.service.CloseFile (handle)

    # Updates the user's local copy
    def update (self):

        ifolders = self.client.service.GetiFolders (0, 0)

        for ifolder in ifolders.Items.iFolder:

            # If any new iFolder is found, create it locally
            if not os.path.isdir (ifolder.Name):
                os.mkdir (ifolder.Name)

            # Get all the children of the current iFolder
            operation = self.client.factory.create ('SearchOperation')
            entries = self.client.service.GetEntriesByName (ifolder.ID, ifolder.ID, operation.Contains, '.', 0, 0)
            
            try:
                for entry in entries.Items.iFolderEntry:
                    changes = self.client.service.GetChanges (entry.iFolderID, entry.ID, 0, 1)

                    for change in changes.Items.ChangeEntry:
                        
                        iet = self.client.factory.create ('iFolderEntryType')

                        if os.path.exists (change.Name):

                            # If the entry already exists on the local copy, we need to check whether it has to be updated or not
                            if change.Time > self.dbm.mtime (ifolder.ID, change.ID):
                                
                                # The server contains a more recent copy of the entry, let's sync it ...
                                if change.Type == iet.File:
                                    
                                    if self.icm.verbose ():
                                        print 'Found a more recent version of the entry \'{0}\', fetching it ...'.format (change.Name)

                                    self.fetch (ifolder.ID, change.ID, change.Name)

                                # elif change.Type == iet.Directory:

                                #     os.makedirs (change.Name)

                                # Update the information about the entry's mtime
                                self.dbm.update (ifolder.ID, change.ID, change.Time)

                        else:
                            
                            # The entry does not already exist on the local copy, so let's just silently download it ...
                            if self.icm.verbose ():
                                print 'Found a new entry, \'{0}\', retrieving it ...'.format (change.Name)
                            
                            if change.Type == iet.File:
                                self.fetch (ifolder.ID, change.ID, change.Name)
                            elif change.Type == iet.Directory:
                                os.makedirs (change.Name)
                            self.dbm.update (ifolder.ID, change.ID, change.Time)

                        # We mind just about the latest change made to the entry
                        break

            except AttributeError, ae:
                print ae
            
if __name__ == '__main__':
    icm = iFolderConfigManager ()

    try:    
        ifc = iFolderClient (icm)
    except WebFault, wf:
        print wf
