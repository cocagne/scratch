import os
import os.path
import ctypes


this_dir = os.path.abspath(os.path.dirname(__file__))
cimplso = os.path.join(this_dir, 'libcimpl.so.1.0')

def build_cimpl():
    os.system('cd %s; gcc -shared -Wl,-soname,libcimpl.so.1 -o libcimpl.so.1.0 -fPIC cimpl.c' % this_dir)

if not os.path.exists(cimplso):
    build_cimpl()

if os.stat(os.path.join(this_dir, 'cimpl.c')).st_mtime > os.stat(cimplso).st_mtime:
    build_cimpl()
    
if not os.path.exists(cimplso):
    print 'Compile cimpl library with:'
    print '  gcc -shared -Wl,-soname,libcimpl.so.1 -o libcimpl.so.1.0 -fPIC cimpl.c'
    raise Exception('Wrapper library not built.')


libc = ctypes.CDLL("libc.so.6")
libcimpl = ctypes.CDLL(cimplso)


S_IFMT     = 0170000   #bit mask for the file type bit fields
S_IFSOCK   = 0140000   #socket
S_IFLNK    = 0120000   #symbolic link
S_IFREG    = 0100000   #regular file
S_IFBLK    = 0060000   #block device
S_IFDIR    = 0040000   #directory
S_IFCHR    = 0020000   #character device
S_IFIFO    = 0010000   #FIFO
S_ISUID    = 0004000   #set UID bit
S_ISGID    = 0002000   #set-group-ID bit (see below)
S_ISVTX    = 0001000   #sticky bit (see below)
S_IRWXU    = 00700     #mask for file owner permissions
S_IRUSR    = 00400     #owner has read permission
S_IWUSR    = 00200     #owner has write permission
S_IXUSR    = 00100     #owner has execute permission
S_IRWXG    = 00070     #mask for group permissions
S_IRGRP    = 00040     #group has read permission
S_IWGRP    = 00020     #group has write permission
S_IXGRP    = 00010     #group has execute permission
S_IRWXO    = 00007     #mask for permissions for others (not in group)
S_IROTH    = 00004     #others have read permission
S_IWOTH    = 00002     #others have write permission
S_IXOTH    = 00001     #others have execute permission



class timespec (ctypes.Structure):
    _fields_ = [ ("tv_sec", ctypes.c_long),   # Seconds
                 ("tv_nsec", ctypes.c_long) ] # Nanoseconds

class dev_t (ctypes.Structure):
    _fields_ = [ ("major", ctypes.c_long),  
                 ("minor", ctypes.c_long) ] 

class sstat (ctypes.Structure):
    _fields_ = [ ("st_dev", ctypes.c_ulonglong),
                 ("st_ino", ctypes.c_ulonglong),
                 ("st_mode", ctypes.c_uint),
                 ("st_nlink", ctypes.c_ulonglong),
                 ("st_uid", ctypes.c_ulong),
                 ("st_gid", ctypes.c_ulong),
                 ("st_rdev", dev_t),
                 ("st_size", ctypes.c_ulonglong),
                 ("st_blksize", ctypes.c_ulonglong),
                 ("st_blocks", ctypes.c_ulonglong),
                 ("st_atime", timespec),
                 ("st_mtime", timespec),
                 ("st_ctime", timespec)
                 ] 


    
TimespecArray = timespec * 2

libc.futimens.argtypes               = [ctypes.c_int, TimespecArray]
libcimpl.statwrap.argtypes           = [ctypes.c_char_p, ctypes.POINTER(sstat)]
libcimpl.set_mtime_ns.argtypes       = [ctypes.c_char_p, ctypes.c_long, ctypes.c_long]

def old_set_nsec_mtime( filename, mtime_in_nsec ):
    sec  = mtime_in_nsec / 1000000000
    nsec = mtime_in_nsec % 1000000000
    
    tvs = TimespecArray()
    tvs[0].tv_sec  = sec
    tvs[0].tv_nsec = nsec
    tvs[1].tv_sec  = sec
    tvs[1].tv_nsec = nsec
    
    if not os.path.exists( filename ):
        raise OSError("Unknown file or directory: %s" % filename)

    fd = os.open(filename, os.O_WRONLY)
    try:
        if libc.futimens( fd, tvs ) != 0:
            raise OSError("Unknown error encountered while attempting to set modification time for: %s" % filename)
    finally:
        os.close(fd)



def set_nsec_mtime( filename, mtime_in_nsec ):
    sec  = mtime_in_nsec / 1000000000
    nsec = mtime_in_nsec % 1000000000

    assert filename[0] == '/'
    
    libcimpl.set_mtime_ns( filename, sec, nsec )
    

    
def lstat( fn ):
    s = sstat()

    ret = libcimpl.statwrap( fn, s )

    return s if ret == 0 else None



def print_stat( s ):
    print 'dev', s.st_dev
    print 'ino', s.st_ino
    print 'mode', s.st_mode
    print 'nlink', s.st_nlink
    print 'uid', s.st_uid
    print 'gid', s.st_gid
    print 'rdev.major', s.st_rdev.major
    print 'rdev.minor', s.st_rdev.minor
    print 'size', s.st_size
    print 'blksize', s.st_blksize
    print 'blocks', s.st_blocks
    print 'atime.sec', s.st_atime.tv_sec
    print 'atime.nsec', s.st_atime.tv_nsec
    print 'mtime.sec', s.st_mtime.tv_sec
    print 'mtime.nsec', s.st_mtime.tv_nsec
    print 'ctime.sec', s.st_ctime.tv_sec
    print 'ctime.nsec', s.st_ctime.tv_nsec
    
