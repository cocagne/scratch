import os
import os.path
import subprocess

DIRECTORY = 1
REGULAR   = 2
SYMLINK   = 3
SOCKET    = 4
FIFO      = 5
BLOCKDEV  = 6
CHARDEV   = 7

tmap = { DIRECTORY : 'Directory',
         REGULAR   : 'File',
         SYMLINK   : 'Symlink',
         SOCKET    : 'Socket',
         FIFO      : 'Fifo',
         BLOCKDEV  : 'BlockDev',
         CHARDEV   : 'CharDev' }

from kamino.body.fs import cwrap

ftype_map = { cwrap.S_IFDIR  : DIRECTORY,
              cwrap.S_IFREG  : REGULAR,
              cwrap.S_IFLNK  : SYMLINK,
              cwrap.S_IFSOCK : SOCKET,
              cwrap.S_IFIFO  : FIFO,
              cwrap.S_IFBLK  : BLOCKDEV,
              cwrap.S_IFCHR  : CHARDEV }


local_filesystems = set( ['ext2', 'ext3', 'ext4', 'btrfs'] )


def get_mount_table():
    mtbl = dict()
    
    # Ignore all non-local file systems
    mounts = subprocess.Popen(['mount',], stdout=subprocess.PIPE).communicate()[0]
        
    for line in mounts.split('\n'):
        p = line.split()
        if p:
            mtbl[ p[2] ] = p[4] in local_filesystems

    return mtbl



class File (object):

    def __init__(self, name, fq_name, s):
        self.ftype    = ftype_map[ s.st_mode & cwrap.S_IFMT ]
        self.name     = name
        self.fq_name  = fq_name
        self.uid      = int(s.st_uid)
        self.gid      = int(s.st_gid)
        self.mode     = int(s.st_mode & ~cwrap.S_IFMT)
        self.mtime_ns = long(s.st_mtime.tv_sec * 1000000000 + s.st_mtime.tv_nsec)
        
        if self.ftype == REGULAR:
            self.inode    = int(s.st_ino)
            self.nlink    = int(s.st_nlink)
            self.size     = long(s.st_size)
            self.fs_id    = None # Optional value that may be added by Scanner module

        elif self.ftype == SYMLINK:
            self.target = os.readlink( self.fq_name )

        elif self.ftype in (BLOCKDEV, CHARDEV):
            self.dev_major = int(s.st_rdev.major)
            self.dev_minor = int(s.st_rdev.minor)
        


def read_dir( path ):

    if not os.path.isdir(path):
        print '#### BAD PATH: ', path
    assert os.path.isdir(path)

    content = dict()
    
    for fn in os.listdir( path ):

        fqfn = os.path.join(path, fn)
        
        s = cwrap.lstat( fqfn )

        if s is None:
            raise Exception("Failed to lstat " + fqfn)

        content[ fn ] = File( fn, fqfn, s )

    return content

        




