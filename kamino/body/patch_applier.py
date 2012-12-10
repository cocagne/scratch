import os
import os.path
import stat
import socket

from kamino.body    import fs
from kamino.body.fs import cwrap

#
#
# TODO: Add error checking / recovery for target being in inconsistent state
#
#   * Hardlink support
#      -- Prior to extracting file, check to see if it exists in the file system. Hardlink if so.
#
#

class Patcher (object):

    
    def __init__(self, patch_num, body_db):
        self.body_db = body_db
        self.patch   = body_db.patch_db.patches[ patch_num ]


    def reverse_apply(self, root_fs_dir):
        self.apply( root_fs_dir, False )
        
        
    def apply(self, root_fs_dir, forward = True):
        if not os.path.exists( root_fs_dir ):
            os.makedirs( root_fs_dir )
        self.recurse( root_fs_dir, self.patch.root, forward )


    
    def recurse(self, fs_dir, patch_dir, forward):
        
        file_adds    = patch_dir.adds    if forward else patch_dir.removes
        file_removes = patch_dir.removes if forward else patch_dir.adds

        add_type     = patch_dir.ADDED   if forward else patch_dir.REMOVED
        remove_type  = patch_dir.REMOVED if forward else patch_dir.ADDED
        
        dir_adds     = [ pd for pd in patch_dir.subdirs.itervalues() if pd.state == add_type    ]
        dir_removes  = [ pd for pd in patch_dir.subdirs.itervalues() if pd.state == remove_type ]

        meta_mods    = dict()
        
        idx = 0 if forward else 1
        for k, v in patch_dir.meta_changes.iteritems():
            meta_mods[k] = v[idx]
            
        # Order:
        #   1. File Removes
        #   2. Recursive Directory Removes
        #   3. File Additions
        #   4. Recursive Directory Additions
        #   5. Metadata changes
        
        for f in file_removes.itervalues():
            os.unlink( os.path.join(fs_dir, f.name) )

        for subd in dir_removes:
            fsd = os.path.join(fs_dir, subd.name)
            self.recurse( fsd, subd, forward )
            os.rmdir( fsd )

        for f in file_adds.itervalues():
            self.add_file(fs_dir, f)
            
        for subd in dir_adds:
            fsd = os.path.join(fs_dir, subd.name)
            os.mkdir(fsd, 0700)
            self.recurse( fsd, subd, forward )
            self.set_meta(fsd, subd.uid, subd.gid, subd.mode)
            cwrap.set_nsec_mtime( fsd, subd.mtime_ns )

        for k, v in meta_mods.iteritems():
            uid, gid, mode = v
            self.set_meta(os.path.join(fs_dir, k), uid, gid, mode)
        

    def set_meta(self, fn, uid, gid, mode):
        try:
            os.lchown( fn, f.uid, f.gid )
        except:
            pass

        if not os.path.islink(fn):
            os.chmod( fn, mode )

            
    def add_file(self, fs_dir, f):
        fn = os.path.join(fs_dir, f.name)

        if f.ftype == fs.REGULAR:
            dbf = self.body_db.file_db.files[ f.file_id ]
            self.body_db.file_store.extract_file( fn, dbf.offset, dbf.zlength )
            
        elif f.ftype == fs.SYMLINK:
            os.symlink(f.target, fn)

        elif f.ftype == fs.SOCKET:
            s = socket.socket( socket.AF_UNIX )
            s.bind(fn)
            s.close()

        elif f.ftype == fs.FIFO:
            os.mkfifo(fn, f.mode)

        else:
           mode = f.mode | stat.S_IFBLK if f.ftype == fs.BLOCKDEV else stat.S_IFCHR
           device = os.makedev( f.major, f.minor )
           os.mknod( fn, mode, device )

        try:
            os.lchown( fn, f.uid, f.gid )
        except:
            pass
        
        if not f.ftype == fs.SYMLINK:
            os.chmod( fn, f.mode )
            
        cwrap.set_nsec_mtime( fn, f.mtime_ns )
