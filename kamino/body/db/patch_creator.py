
import transaction

from   kamino.body               import fs
from   kamino.body.db            import types



_db_constructor = { fs.REGULAR   : types.File,
                    fs.SYMLINK   : types.Symlink,
                    fs.SOCKET    : types.Socket,
                    fs.FIFO      : types.Fifo,
                    fs.BLOCKDEV  : types.BlockDev,
                    fs.CHARDEV   : types.CharDev }


class PatchCreator (object):

    
    def __init__(self, body_db, db_updater):
        self.body_db    = body_db
        self.db_updater   = db_updater
        self.db_dir       = None
        self.indent       = ''
        self.proot        = body_db.patch_db.create_patch( body_db )
        self._tdir        = None
        self.have_content = False
        self.dstack       = list()


    def _get_t(self):
        self.have_content = True
        
        if self._tdir:
            return self._tdir
        
        p = self.proot.root
        for db_dir in self.dstack[1:]:
            if not db_dir.name in p.subdirs:
                p.subdirs[ db_dir.name ] = types.PatchedDirectory( db_dir.name, p,
                                                                   db_dir.uid, db_dir.gid,
                                                                   db_dir.mode, db_dir.mtime_ns)
            p = p.subdirs[ db_dir.name ]
            
        self._tdir = p

        return self._tdir

    this_dir = property(_get_t)

    
    def push_dir(self, dir_name):
        self.db_updater.push_dir( dir_name )
        
        self.indent += '   '
        
        if self.db_dir is None:
            self.db_dir = self.body_db.db_root['/']
        else:
            self.db_dir = self.db_dir.content[ dir_name ]

        self.dstack.append( self.db_dir )
        self._tdir = None

            
    def pop_dir(self):
        self.db_updater.pop_dir()
        
        self.indent = self.indent[:-3]
        self.db_dir = self.db_dir.parent
        self.dstack.pop()
        self._tdir = None

        if len(self.dstack) == 0:
            if self.have_content:
                self.proot.set_complete( self.body_db )
                transaction.commit()
                print 'PATCH Completed: ', self.proot.id_number
            else:
                print 'PATCH: No changes detected'

        
    def copy_db_file(self, db_file):
        p_file = _db_constructor[ db_file.ftype ]( db_file.name, self.this_dir, db_file.uid, db_file.gid, db_file.mode, db_file.mtime_ns )
        
        if db_file.ftype == fs.REGULAR:
            p_file.file_id  = db_file.file_id
            p_file.size     = db_file.size
            p_file.mtime_ns = db_file.mtime_ns

        elif db_file.ftype == fs.SYMLINK:
            p_file.target = db_file.target

        elif db_file.ftype in (fs.BLOCKDEV, fs.CHARDEV):
            p_file.dev_major = db_file.dev_major
            p_file.dev_minor = db_file.dev_minor

        return p_file
    

    def content_added(self, fs_file, force_zero_length = False):
        self.db_updater.content_added( fs_file, force_zero_length )

        db_file = self.db_dir.content[ fs_file.name ]
        
        p_file = self.copy_db_file( db_file )

        #print self.indent, 'Patch Add: ',  fs.tmap[ db_file.ftype ].ljust(12), db_file.get_fq_name()
        
        self.this_dir.adds[ p_file.name ] = p_file

        transaction.commit()


    
    def content_removed(self, db_file):

        p_file = self.copy_db_file( db_file )
        self.this_dir.removes[ p_file.name ] = p_file
        
        #print self.indent, 'Patch Remove: ', fs.tmap[ db_file.ftype ].ljust(12), db_file.get_fq_name()

        self.db_updater.content_removed( db_file )

        

    def metadata_changed(self, db_file, fs_file):

        self.this_dir.meta_changes[ db_file.name ] = ((fs_file.uid, fs_file.gid, fs_file.mode), (db_file.uid, db_file.gid, db_file.mode))

        #print self.indent, 'Patch Meta: ', fs_file.name, (fs_file.uid, fs_file.gid, fs_file.mode), ' ==> ', (db_file.uid, db_file.gid, db_file.mode)
        
        self.db_updater.metadata_changed( db_file, fs_file )
        
        
        
    # Called in a bottom-up manner
    def directory_removed(self, db_dir):

        sd = None
        if not db_dir.name in self.this_dir.subdirs:
            self.this_dir.subdirs[ db_dir.name ] = types.PatchedDirectory( db_dir.name, self.this_dir,
                                                                           db_dir.uid, db_dir.gid,
                                                                           db_dir.mode, db_dir.mtime_ns)

        self.this_dir.subdirs[ db_dir.name ].state = types.PatchedDirectory.REMOVED

        #print self.indent, 'Patch Removing Dir: ', db_dir.name
        
        self.db_updater.directory_removed( db_dir )

        
    # Called in a top-down manner
    def directory_added(self, fs_dir):

        pd = types.PatchedDirectory( fs_dir.name, self.this_dir, fs_dir.uid, fs_dir.gid, fs_dir.mode, fs_dir.mtime_ns )

        pd.state = types.PatchedDirectory.ADDED

        self.this_dir.subdirs[ fs_dir.name ] = pd

        #print self.indent, 'Patch Adding Dir: ', fs_dir.name
        
        self.db_updater.directory_added( fs_dir )

