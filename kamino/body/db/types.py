import uuid

from persistent         import Persistent
from persistent.mapping import PersistentMapping
from persistent.list    import PersistentList
from BTrees.IOBTree     import IOBTree


from kamino.body import fs



class FileMeta (Persistent):
    def __init__(self, name, parent, uid, gid, mode, mtime_ns):
        self.name     = name
        self.parent   = parent
        self.uid      = uid
        self.gid      = gid
        self.mode     = mode   # Must have file type bits masked off
        self.mtime_ns = mtime_ns

    def get_fq_name(self):
        l = [self.name,]
        p = self.parent
        while p:
            l.append( p.name )
            p = p.parent
        l.reverse()
        return '/'.join(l)

    def dbg_meta(self):
        return '%d %d %s %s' % (self.uid, self.gid, oct(self.mode), self.name)
        

        
        
class Directory (FileMeta):

    ftype = fs.DIRECTORY
    
    def __init__(self, name, parent, uid, gid, mode, mtime_ns):
        FileMeta.__init__(self, name, parent, uid, gid, mode, mtime_ns)
        
        self.content = PersistentMapping()


    def get_content_set(self):
        return set( (v.name, v.ftype) for v in self.content.itervalues() )

    def get_meta_set(self, filenames):
        s = set()
        for fn in filenames:
            v = self.content[ fn ]
            s.add( (v.name, v.uid, v.gid, v.mode) )
        return s


    

class File (FileMeta):

    ftype = fs.REGULAR
    
    def __init__(self, name, parent, uid, gid, mode, mtime_ns):
        FileMeta.__init__(self, name, parent, uid, gid, mode, mtime_ns)

        self.inode    = None # Inode on the filesystem
        self.size     = None
        
        self.fs_id    = None # Internal fileystem ID
        self.file_id  = None # Internal file id

    def pdbg(self, indent):
        print indent, 'File %5d %5s %s' % (self.file_id, self.size, self.dbg_meta())



class Symlink (FileMeta):

    ftype = fs.SYMLINK
    
    def __init__(self, name, parent, uid, gid, mode, mtime_ns):
        FileMeta.__init__(self, name, parent, uid, gid, mode, mtime_ns)
        
        self.target = None

    def pdbg(self, indent):
        print indent, 'Link %s => %s' % (self.dbg_meta(), self.target)

        
class Socket (FileMeta):

    ftype = fs.SOCKET
    
    def __init__(self, name, parent, uid, gid, mode, mtime_ns):
        FileMeta.__init__(self, name, parent, uid, gid, mode, mtime_ns)

    def pdbg(self, indent):
        print indent, 'Socket %s' % self.dbg_meta()

        

class Fifo (FileMeta):

    ftype = fs.FIFO
    
    def __init__(self, name, parent, uid, gid, mode, mtime_ns):
        FileMeta.__init__(self, name, parent, uid, gid, mode, mtime_ns)

    def pdbg(self, indent):
        print indent, 'Socket %s' % self.dbg_meta()


        
class BlockDev (FileMeta):

    ftype = fs.BLOCKDEV
    
    def __init__(self, name, parent, uid, gid, mode, mtime_ns):
        FileMeta.__init__(self, name, parent, uid, gid, mode, mtime_ns)

        self.major = None
        self.minor = None

    def pdbg(self, indent):
        print indent, 'BlockDev %d:%d %s' % (self.major, self.minor, self.dbg_meta())

        

class CharDev (FileMeta):

    ftype = fs.CHARDEV
    
    def __init__(self, name, parent, uid, gid, mode, mtime_ns):
        FileMeta.__init__(self, name, parent, uid, gid, mode, mtime_ns)

        self.major = None
        self.minor = None

    def pdbg(self, indent):
        print indent, 'CharDev %d:%d %s' % (self.major, self.minor, self.dbg_meta())
    
#----------------------------------------------------------------------------------
# File System Database
#----------------------------------------------------------------------------------

class FileSystems (Persistent):
    def __init__(self):
        self.next_fs_id   = 1
        self.mounts       = PersistentMapping()
        self.inode_map    = PersistentMapping()

        
    def add_mount(self, mount_point):
        i = self.next_fs_id
        self.next_fs_id += 1

        self.mounts[ mount_point ] = i
        self.inode_map[ i ] = IOBTree() # maps Inode Number to list of paths

        import transaction
        transaction.commit()

        
    def link_inode(self, fs_id, inode, file_id, path):
        t = self.inode_map[ fs_id ]
        if not inode in t:
            t[ inode ] = PersistentList()
            t[ inode ].append( file_id )
        t[ inode ].append( path )


    def unlink_inode(self, fs_id, inode, path):
        l = self.inode_map[ fs_id ][ inode ]
        l.remove( path )

        # If only the file_id is left, remove it completely. The
        # inode may be recycled by the file system
        if len(l) == 1:
            del self.inode_map[ fs_id ][ inode ]
        


    def get_inode_file_id(self, fs_id, inode):
        try:
            return self.inode_map[ fs_id ][ inode ][0]
        except KeyError:
            return None


    def get_inode_paths(self, fs_id, inode):
        try:
            return self.inode_map[ fs_id ][ inode ][1:]
        except KeyError:
            return []
        
    
    def check_filesystems(self):
        mtbl = fs.get_mount_table()

        for mount, is_local in mtbl.iteritems():
            if is_local and not mount in self.mounts:
                self.add_mount( mount )
                
#----------------------------------------------------------------------------------
# File Store Database
#----------------------------------------------------------------------------------

class DBFile (Persistent):
    def __init__(self, file_id, offset, length, zlength):
        self.file_id = file_id
        self.offset  = offset
        self.length  = length
        self.zlength = zlength # compressed length


        
class FileDatabase (Persistent):
    def __init__(self):
        self.next_file_id       = 1
        self.files              = IOBTree()
        
    def get_last_offset(self):
        if self.next_file_id == 1:
            return 0
        else:
            lf = self.files[ self.next_file_id - 1 ]
            return lf.offset + lf.zlength
    
    def add_file(self, file_length, file_zlength):
        i = self.next_file_id
        
        self.files[i] = DBFile( i, self.get_last_offset(), file_length, file_zlength )

        self.next_file_id += 1
        
        return i

    

                
#----------------------------------------------------------------------------------
# Patch Database
#----------------------------------------------------------------------------------


class PatchedDirectory (FileMeta):

    ftype = fs.DIRECTORY

    EXISTING = 0
    ADDED    = 1
    REMOVED  = 2
    
    def __init__(self, name, parent, uid, gid, mode, mtime_ns):
        FileMeta.__init__(self, name, parent, uid, gid, mode, mtime_ns)
        
        self.adds         = PersistentMapping()
        self.removes      = PersistentMapping()
        self.meta_changes = PersistentMapping() # name => ((to_uid, to_gid, to_mode), (from_uid, from_gid, from_mode))

        self.subdirs      = PersistentMapping()

        self.state        = PatchedDirectory.EXISTING

    def pdbg(self, indent = ''):
        s = { 0 : 'EXISTING', 1 : 'ADDED', 2 : 'REMOVED' }
        
        print indent, 'Dir %s %s' % (s[self.state], self.dbg_meta())
        
        if self.adds:
            print indent, ' ** Adds **'
            for v in self.adds.itervalues():
                v.pdbg( indent + '   ' )
        if self.removes:
            print indent, ' ** Removes **'
            for v in self.removes.itervalues():
                v.pdbg( indent + '   ' )

        if self.meta_changes:
            print indent, ' ** Meta Mods **'
            for k, v in self.removes.iteritems():
                print indent + '   ', k, v

        for s in self.subdirs.itervalues():
            s.pdbg( indent + '   ' )
                


    

class Patch (Persistent):
    def __init__(self, id_number, previous_uuid, starting_file_id):
        self.id_number        = id_number
        self.is_complete      = False
        self.starting_file_id = starting_file_id
        self.ending_file_id   = None
        self.uuid             = uuid.uuid4().bytes
        self.previous_uuid    = previous_uuid
        self.root             = PatchedDirectory('', None, 0, 0, 755, 0)

    def set_complete(self, body_db):
        self.ending_file_id = body_db.file_db.next_file_id - 1
        self.is_complete    = True



        
class PatchDatabase (Persistent):
    
    def __init__(self):
        self.last_patch_id      = None
        self.last_patch_file_id = None
        self.patches            = IOBTree()
        
    # Continues the previous patch if it didn't finish or allocates a new one
    def create_patch(self, body_db):
        if self.last_patch_id is not None:
            p = self.patches[ self.last_patch_id ]
            if not p.is_complete:
                return p

        if self.last_patch_id is None:
            self.last_patch_id = 0
            previous_uuid = '\0'*16
        else:
            previous_uuid = self.patches[ self.last_patch_id ].uuid

        self.last_patch_id += 1

        p = Patch( self.last_patch_id, previous_uuid, body_db.file_db.next_file_id )
        
        self.patches[ self.last_patch_id ] = p
        
        return p



    
    
        
