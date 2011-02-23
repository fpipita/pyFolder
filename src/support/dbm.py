from datetime import *
import sqlite3
import os

class DBM:
    Q_CREATE_TABLE_ENTRIES = \
        """
        CREATE TABLE entry (
           ifolder        TEXT REFERENCES ifolder (id),
           id             TEXT,
           mtime          timestamp,
           digest         TEXT,
           parent         TEXT,
           path           TEXT,
           PRIMARY KEY (ifolder, id)
        )
        """

    Q_CREATE_TABLE_IFOLDERS = \
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
        INSERT INTO entry VALUES (?, ?, ?, ?, ?, ?)
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

    def __init__ (self, pathtodb, pyFolder):
        self.pathtodb = pathtodb
        self.pyFolder = pyFolder
        self.__connect ()

    def __create_tables (self):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_CREATE_TABLE_IFOLDERS)
        cu.execute (DBM.Q_CREATE_TABLE_ENTRIES)        

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

    def add_ifolder (self, ifolder_id, mtime, name, entry_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_ADD_IFOLDER, (ifolder_id, mtime, name, entry_id))
        self.pyFolder.debug ('DBM.add_ifolder : ' \
                                 'In table `ifolder\' : added new tuple ' \
                                 '(id={0}, mtime={1}, name={2}, ' \
                                 'entry_id={3})'.format \
                                 (ifolder_id, mtime, name, entry_id))
        self.cx.commit ()

    def delete_ifolder (self, ifolder_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_DELETE_IFOLDER, (ifolder_id,))
        self.pyFolder.debug ('DBM.delete_ifolder : ' \
                                 'In table `ifolder\' : removed tuple ' \
                                 'with id={0}'.format \
                                 (ifolder_id))
        self.cx.commit ()

    def get_ifolders (self):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_IFOLDERS)
        return cu.fetchall ()

    def get_ifolder (self, ifolder_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_IFOLDER, (ifolder_id,))
        return cu.fetchone ()

    def update_mtime_by_ifolder (self, ifolder_id, mtime):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_UPDATE_MTIME_BY_IFOLDER, (mtime, ifolder_id))
        self.pyFolder.debug ('DBM.update_mtime_by_ifolder : ' \
                                 'In table `ifolder\' : updated tuple ' \
                                 'whose `id\' field is `{0}\' with ' \
                                 'new mtime value `{1}\''.format (ifolder_id, mtime))
        self.cx.commit ()

    def add_entry (self, ifolder_id, entry_id, mtime, digest, parent_id, path):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_ADD_ENTRY, \
                        (ifolder_id, entry_id, mtime, digest, parent_id, path))
        self.pyFolder.debug ('DBM.add_entry : ' \
                                 'In table `entry\' : added new tuple ' \
                                 '(ifolder={0}, id={1}, mtime={2}, ' \
                                 'digest={3}, parent={4}, path={5})'.format \
                                 (ifolder_id, entry_id, mtime, digest, \
                                      parent_id, path))
        self.cx.commit ()

    def delete_entry (self, ifolder_id, entry_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_DELETE_ENTRY, (ifolder_id, entry_id))
        self.pyFolder.debug ('DBM.delete_entry : ' \
                                 'In table `entry\' : removed tuple ' \
                                 'with ifolder={0} and id={1}'.format \
                                 (ifolder_id, entry_id))
        self.cx.commit ()

    def delete_entries_by_ifolder (self, ifolder_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_DELETE_ENTRIES_BY_IFOLDER, (ifolder_id,))
        self.cx.commit ()

    def delete_entries_by_parent (self, parent_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_DELETE_ENTRIES_BY_PARENT, (parent_id,))
        self.cx.commit ()

    def update_mtime_and_digest_by_entry (self, ifolder_id, entry_id, mtime, digest):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_UPDATE_MTIME_AND_DIGEST_BY_ENTRY, \
                        (mtime, digest, ifolder_id, entry_id))
        self.cx.commit ()
    
    def get_mtime_by_entry (self, ifolder_id, entry_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_MTIME_BY_ENTRY, (ifolder_id, entry_id))
        return cu.fetchone ()

    def get_digest_by_entry (self, ifolder_id, entry_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_DIGEST_BY_ENTRY, (ifolder_id, entry_id))
        return cu.fetchone ()

    def get_entry (self, ifolder_id, entry_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_ENTRY, (ifolder_id, entry_id))
        return cu.fetchone ()

    def get_entries_by_ifolder (self, ifolder_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_ENTRIES_BY_IFOLDER, (ifolder_id,))
        return cu.fetchall ()
    
    def get_entries_by_parent (self, parent_id):
        cu = self.cx.cursor ()
        cu.execute (DBM.Q_GET_ENTRIES_BY_PARENT, (parent_id,))
        return cu.fetchall ()

    def __del__ (self):
        self.cx.commit ()
        self.cx.close ()
