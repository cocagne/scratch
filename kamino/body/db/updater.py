import os
import os.path

import transaction

from   kamino.body               import fs
from   kamino.body.db            import types
from   kamino.body.db.file_store import FileStore


_db_constructor = { fs.REGULAR   : types.File,
                    fs.SYMLINK   : types.Symlink,
                    fs.SOCKET    : types.Socket,
                    fs.FIFO      : types.Fifo,
                    fs.BLOCKDEV  : types.BlockDev,
                    fs.CHARDEV   : types.CharDev }


class DBUpdater (object):

    
    def __init__(self, body_db):
        self.body_db    = body_db
        self.db_dir     = None
        self.fs_db      = body_db.fs_db
        self.file_store = body_db.file_store
        self.indent     = ''

        
    def push_dir(self, dir_name):
        self.indent += '   '
        
        if self.db_dir is None:
            self.db_dir = self.body_db.db_root['/']
        else:
            self.db_dir = self.db_dir.content[ dir_name ] 

            
    def pop_dir(self):
        self.indent = self.indent[:-3]
        self.db_dir = self.db_dir.parent


    def content_added(self, fs_file, force_zero_length = False):
        db_file = _db_constructor[ fs_file.ftype ]( fs_file.name, self.db_dir, fs_file.uid, fs_file.gid, fs_file.mode, fs_file.mtime_ns )

        
        print self.indent, 'Adding: ', 'ZERO' if force_zero_length else 'NRML',  fs.tmap[ db_file.ftype ].ljust(12), db_file.get_fq_name()

        if db_file.ftype == fs.REGULAR:
            db_file.inode    = fs_file.inode
            db_file.size     = fs_file.size
            db_file.fs_id    = fs_file.fs_id

            file_id = None
            
            if fs_file.nlink > 1:
                file_id = self.fs_db.get_inode_file_id( fs_file.fs_id, fs_file.inode )
                
            if file_id is None:
                file_id = self.file_store.add_file( fs_file, force_zero_length )
            else:
                print self.indent, '   HARDLINK to existing file: ', self.fs_db.get_inode_paths( fs_file.fs_id, fs_file.inode )

            db_file.file_id  = file_id
        
            self.fs_db.link_inode( db_file.fs_id, fs_file.inode, db_file.file_id, db_file.get_fq_name() )
                
        
        elif db_file.ftype == fs.SYMLINK:
            db_file.target = fs_file.target

        elif db_file.ftype in (fs.BLOCKDEV, fs.CHARDEV):
            db_file.dev_major = fs_file.dev_major
            db_file.dev_minor = fs_file.dev_minor

        self.db_dir.content[ db_file.name ] = db_file

        transaction.commit()

        return db_file

    
    def content_removed(self, db_file):
        print self.indent, 'Removing: ', fs.tmap[ db_file.ftype ].ljust(12), db_file.get_fq_name()

        if db_file.ftype == fs.REGULAR:
            l = self.fs_db.get_inode_paths( db_file.fs_id, db_file.inode )

            if len(l) > 1:
                print self.indent, '   Removing HARDLINK to existing file: ', [ f for f in l ]
    
            self.fs_db.unlink_inode( db_file.fs_id, db_file.inode, db_file.get_fq_name() )
        
        del self.db_dir.content[ db_file.name ]

        transaction.commit()
        

    def metadata_changed(self, db_file, fs_file):
        print self.indent, 'MetaChange: ', fs_file.name, (db_file.uid, db_file.gid, db_file.mode), ' ==> ', (fs_file.uid, fs_file.gid, fs_file.mode)
        db_file.uid, db_file.gid, db_file.mode = fs_file.uid, fs_file.gid, fs_file.mode
        transaction.commit()

        
    # Called in a bottom-up manner
    def directory_removed(self, db_dir):
        print self.indent, 'Removing Dir: ', db_dir.name
        
        del self.db_dir.content[ db_dir.name ]
            
        transaction.commit()

        
    # Called in a top-down manner
    def directory_added(self, fs_dir):
        print self.indent, 'Adding Dir: ', fs_dir.name
        
        db_dir = types.Directory( fs_dir.name, self.db_dir, fs_dir.uid, fs_dir.gid, fs_dir.mode, fs_dir.mtime_ns )
        self.db_dir.content[ db_dir.name ] = db_dir

        transaction.commit()
