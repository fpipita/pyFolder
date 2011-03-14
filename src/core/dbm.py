# -*- coding: utf-8 -*-

from datetime import *
import logging
import os
import sqlite3

class DBM:
    Q_CREATE_TABLE_ENTRY = \
        """
        CREATE TABLE entry (
           ifolder        TEXT REFERENCES ifolder (id),
           id             TEXT,
           mtime          timestamp,
           digest         TEXT,
           parent         TEXT,
           path           TEXT,
           localpath      TEXT,
           PRIMARY KEY    (ifolder, id)
        )
        """

    Q_CREATE_TABLE_IFOLDER = \
        """
        CREATE TABLE ifolder (
           id             TEXT PRIMARY KEY,
           mtime          timestamp,
           name           TEXT,
           entry_id       TEXT
        )
        """

    Q_ADD_ENTRY = \
        """
        INSERT INTO entry VALUES (?, ?, ?, ?, ?, ?, ?)
        """

    Q_DELETE_ENTRY = \
        """
        DELETE FROM entry WHERE ifolder=? AND id=?
        """

    Q_DELETE_ENTRIES_BY_IFOLDER = \
        """
        DELETE FROM entry WHERE ifolder=?
        """

    Q_DELETE_ENTRIES_BY_PARENT = \
        """
        DELETE FROM entry WHERE parent=?
        """

    Q_UPDATE_MTIME_AND_DIGEST_BY_ENTRY = \
        """
        UPDATE entry SET mtime=?, digest=?
        WHERE ifolder=? AND id=?
        """
    
    Q_GET_ENTRY = \
        """
        SELECT * FROM entry AS e 
        WHERE e.ifolder=? AND e.id=?
        """

    Q_GET_ENTRIES_BY_PARENT = \
        """
        SELECT * FROM entry AS e WHERE e.parent=?
        """

    Q_GET_ENTRY_BY_IFOLDER_AND_PATH = \
        """
        SELECT * FROM entry AS e
        WHERE e.ifolder=? AND e.path=?
        """

    Q_GET_ENTRY_BY_IFOLDER_AND_LOCALPATH = \
        """
        SELECT * FROM entry AS e
        WHERE e.ifolder=? AND e.localpath=?
        """

    Q_GET_MTIME_BY_ENTRY = \
        """
        SELECT e.mtime FROM entry AS e
        WHERE i.ifolder=? AND i.id=?
        """

    Q_GET_DIGEST_BY_ENTRY = \
        """
        SELECT e.digest FROM entry AS e
        WHERE e.ifolder=? AND e.id=?
        """

    Q_GET_ENTRIES_BY_IFOLDER = \
        """
        SELECT * FROM entry AS e WHERE e.ifolder=?
        """

    Q_ADD_IFOLDER = \
        """
        INSERT INTO ifolder VALUES (?, ?, ?, ?)
        """

    Q_DELETE_IFOLDER = \
        """
        DELETE FROM ifolder WHERE id=?
        """

    Q_UPDATE_MTIME_BY_IFOLDER = \
        """
        UPDATE ifolder SET mtime=?
        WHERE id=?
        """

    Q_GET_MTIME_BY_IFOLDER = \
        """
        SELECT i.mtime FROM ifolder AS i
        WHERE i.id=?
        """
    Q_GET_IFOLDERS = \
        """
        SELECT * FROM ifolder AS i
        """

    Q_GET_IFOLDER = \
        """
        SELECT * from ifolder AS i where i.id=?
        """

    def __init__ (self, pathtodb):
        self.logger = logging.getLogger ('pyFolder.DBM')
        self.pathtodb = pathtodb
        self.__connect ()

    def __create_tables (self):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_CREATE_TABLE_IFOLDER)
        self.logger.debug ('Created table `ifolder\'')
        cu.execute (DBM.Q_CREATE_TABLE_ENTRY)
        self.logger.debug ('Created table `entry\'')

    def __connect (self):
        self.cx = sqlite3.connect (self.pathtodb, detect_types=\
                                       sqlite3.PARSE_DECLTYPES| \
                                       sqlite3.PARSE_COLNAMES)
        self.cx.row_factory = sqlite3.Row        

    def create_schema (self):
        try:
            self.__create_tables ()
        except sqlite3.OperationalError, oe:
            self.cx.close ()
            if os.path.isfile (self.pathtodb):
                os.remove (self.pathtodb)
            self.__connect ()
            self.__create_tables ()
        finally:
            self.cx.commit ()

    def add_ifolder (self, iFolderID, mtime, Name, EntryID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_ADD_IFOLDER, (iFolderID, mtime, Name, EntryID))
        self.logger.info ('Added iFolder `{0}\', ID={1}'.format \
                               (Name, iFolderID))
        self.cx.commit ()

    def delete_ifolder (self, iFolderID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_DELETE_IFOLDER, (iFolderID,))
        self.logger.info ('Deleted iFolder with ID={0}'.format (iFolderID))
        self.cx.commit ()

    def get_ifolders (self):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_IFOLDERS)
        return cu.fetchall ()

    def get_ifolder (self, iFolderID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_IFOLDER, (iFolderID,))
        return cu.fetchone ()

    def update_mtime_by_ifolder (self, iFolderID, mtime):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_UPDATE_MTIME_BY_IFOLDER, (mtime, iFolderID))
        self.logger.info ('Updated iFolder with ID={0}'.format (iFolderID))
        self.logger.debug ('new_mtime={0}'.format (mtime))
        self.cx.commit ()

    def add_entry (self, iFolderID, EntryID, mtime, \
                       Digest, ParentID, Path, LocalPath):
        cu = self.cx.cursor ()

        cu.execute (\
            DBM.Q_ADD_ENTRY, (\
                iFolderID, \
                    EntryID, \
                    mtime, \
                    Digest, \
                    ParentID, \
                    Path, \
                    LocalPath))

        self.logger.info ('Added entry `{0}\''.format (Path.encode ('utf-8')))
        self.cx.commit ()

    def delete_entry (self, iFolderID, EntryID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_DELETE_ENTRY, (iFolderID, EntryID))
        self.logger.info ('Deleted entry with ID={0}'.format (EntryID))
        self.cx.commit ()

    def delete_entries_by_ifolder (self, iFolderID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_DELETE_ENTRIES_BY_IFOLDER, (iFolderID,))
        self.cx.commit ()

    def delete_entries_by_parent (self, ParentID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_DELETE_ENTRIES_BY_PARENT, (ParentID,))
        self.cx.commit ()

    def update_mtime_and_digest_by_entry (self, iFolderID, EntryID, \
                                              mtime, Digest):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_UPDATE_MTIME_AND_DIGEST_BY_ENTRY, \
                        (mtime, Digest, iFolderID, EntryID))
        self.logger.info ('Updated Entry with ID={0}'.format (EntryID))
        self.cx.commit ()
    
    def get_mtime_by_entry (self, iFolderID, EntryID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_MTIME_BY_ENTRY, (iFolderID, EntryID))
        return cu.fetchone ()

    def get_digest_by_entry (self, iFolderID, EntryID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_DIGEST_BY_ENTRY, (iFolderID, EntryID))
        return cu.fetchone ()

    def get_entry (self, iFolderID, EntryID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_ENTRY, (iFolderID, EntryID))
        return cu.fetchone ()

    def get_entries_by_ifolder (self, iFolderID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_ENTRIES_BY_IFOLDER, (iFolderID,))
        return cu.fetchall ()
    
    def get_entries_by_parent (self, ParentID):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_ENTRIES_BY_PARENT, (ParentID,))
        return cu.fetchall ()

    def get_entry_by_ifolder_and_path (self, iFolderID, Path):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_ENTRY_BY_IFOLDER_AND_PATH, (iFolderID, Path))
        return cu.fetchone ()

    def get_entry_by_ifolder_and_localpath (self, iFolderID, LocalPath):
        cu = self.cx.cursor ()

        cu.execute (\
            DBM.Q_GET_ENTRY_BY_IFOLDER_AND_LOCALPATH, (\
                iFolderID, \
                    LocalPath))

        return cu.fetchone ()

    def __del__ (self):
        self.cx.commit ()
        self.cx.close ()
