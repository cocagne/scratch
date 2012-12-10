from ZODB import FileStorage, DB

import os.path

from kamino.body.db import types
from kamino.body.db import file_store


class BodyDB( object ):

    def __init__(self, db_dir):
        self.zodb_file     = os.path.join(db_dir, 'kamino.zodb')
        self.file_store_fn = os.path.join(db_dir, 'file_store')
        
        self.zodb_storage  = FileStorage.FileStorage( self.zodb_file )
        self.zodb_db       = DB(self.zodb_storage)
        self.zodb_con      = self.zodb_db.open()
    
        self.db_root  = self.zodb_con.root()
    
        if not self.db_root.has_key('/'):
            self.db_root['/']        = types.Directory( '', None, 0, 0, 0755, 0 )
            self.db_root['fs_db']    = types.FileSystems()
            self.db_root['file_db']  = types.FileDatabase()
            self.db_root['patch_db'] = types.PatchDatabase()

        self.fs_db    = self.db_root['fs_db']
        self.file_db  = self.db_root['file_db']
        self.patch_db = self.db_root['patch_db']
        
        # Ensure that all mounted local filesystems have an ID
        self.fs_db.check_filesystems()

        self.file_store = file_store.FileStore( self.file_store_fn, self )
        
