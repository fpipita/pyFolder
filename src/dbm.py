from datetime import *
import sqlite3
import os

class DBM:
    Q_CREATE_TABLE_ENTRIES = \
        """
        CREATE TABLE entry (
           ifolder        TEXT REFERENCES ifolder (ifolder_id),
           entry_id       TEXT,
           mtime          DATETIME,
           digest         TEXT,
           PRIMARY KEY (ifolder, entry_id)
        )
        """

    Q_CREATE_TABLE_IFOLDERS = \
        """
        CREATE TABLE ifolder (
           ifolder_id     TEXT PRIMARY KEY,
           mtime          DATETIME
        )
        """

    Q_ENTRY_ADD = \
        """
        INSERT INTO entry VALUES (?, ?, ?, ?)
        """
    
    Q_ENTRY_UPDATE = \
        """
        UPDATE entry SET mtime=(?), digest=(?)
        WHERE ifolder=(?) AND entry_id=(?)
        """

    Q_ENTRY_MTIME = \
        """
        SELECT e.mtime FROM entry AS e
        WHERE i.ifolder=? AND i.entryID=?
        """

    Q_ENTRY_DIGEST = \
        """
        SELECT e.digest FROM entry AS e
        WHERE e.ifolder=? AND e.entry_id=?
        """

    Q_IFOLDER_ADD = \
        """
        INSERT INTO ifolder VALUES (?, ?)
        """

    Q_IFOLDER_MTIME = \
        """
        SELECT i.mtime FROM ifolder AS i
        WHERE i.ifolder_id=?
        """

    def __init__ (self, pathtodb):
        self.pathtodb = pathtodb
        self.cx = sqlite3.connect (pathtodb)

    def __create_tables (self):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_CREATE_TABLE_IFOLDERS)
        cu.execute (DBM.Q_CREATE_TABLE_ENTRIES)        

    def create_schema (self):
        try:
            self.__create_tables ()
        except sqlite3.OperationalError, oe:
            self.cx.close ()
            if os.path.isfile (self.pathtodb):
                os.remove (self.pathtodb)
            self.cx = sqlite3.connect (self.pathtodb)
            self.__create_tables ()
        finally:
            self.cx.commit ()

    def ifolder_add (self, ifolder):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_IFOLDER_ADD, (ifolder.ID, ifolder.LastModified))
        self.cx.commit ()

    def entry_add (self, ifolder, change, digest):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_ENTRY_ADD, (ifolder.ID, change.ID, change.Time, digest))
        self.cx.commit ()

    def entry_update (self, ifolder, change, digest):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_ENTRY_UPDATE, \
                        (change.Time, digest, ifolder.ID, change.ID))
        self.cx.commit ()
    
    def get_entry_mtime (self, ifolder, change):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_ENTRY_MTIME, (ifolder.ID, change.ID))
        row = cu.fetchone ()
        mtime = datetime.strptime (row[0], '%Y-%m-%d %H:%M:%S.%f')
        return mtime

    def get_entry_digest (self, ifolder, change):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_ENTRY_DIGEST, (ifolder.ID, change.ID))
        row = cu.fetchone ()
        digest = row[0]
        return digest

    def __del__ (self):
        self.cx.commit ()
        self.cx.close ()
