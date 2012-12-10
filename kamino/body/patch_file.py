# Patch file format:
#
# 1 Header:
#     16-byte Patch UUID
#     16-byte Previous Patch UUID
#     8-byte length of the file-store data
#     8-byte length of the file-store description pickle
#
# 2 File-Store Index Pickle (List of StoredFile instances)
#
# 3 File-Store Data (series of compressed files)
#
# 4 Series of DirDescrip pickles
#     4-byte pickle length
#     pickle data
#
import os
import os.path
import struct
import cPickle as pickle

import transaction

from   kamino.body    import fs
from   kamino.body.db import types

_db_constructor = { fs.REGULAR   : types.File,
                    fs.SYMLINK   : types.Symlink,
                    fs.SOCKET    : types.Socket,
                    fs.FIFO      : types.Fifo,
                    fs.BLOCKDEV  : types.BlockDev,
                    fs.CHARDEV   : types.CharDev }


class StoredFile (object):
    def __init__(self, file_id, offset, length, zlength):
        self.file_id = file_id
        self.offset  = offset
        self.length  = length
        self.zlength = zlength # compressed length


class FileDescrip (object):
    def __init__(self, db_f):
        self.ftype    = db_f.ftype
        self.name     = db_f.name
        self.uid      = db_f.uid
        self.gid      = db_f.gid
        self.mode     = db_f.mode   
        self.mtime_ns = db_f.mtime_ns

        if db_f.ftype == fs.REGULAR:            
            self.size     = db_f.size
            self.file_id  = db_f.file_id

        elif db_f.ftype == fs.SYMLINK:
            self.target = db_f.target

        elif db_f.ftype in (fs.BLOCKDEV, fs.CHARDEV):
            self.major = db_f.major
            self.minor = db_f.minor

            
class DirDescrip (FileDescrip):
    def __init__(self, db_dir):
        FileDescrip.__init__(self, db_dir)
        
        self.fq_name = db_dir.get_fq_name()
        self.state   = db_dir.state

        if db_dir.adds:
            self.adds = [ FileDescrip(db_f) for db_f in db_dir.adds.itervalues() ]

        if db_dir.removes:
            self.removes = [ FileDescrip(db_f) for db_f in db_dir.removes.itervalues() ]

        if db_dir.meta_changes:
            self.meta = dict()
            for k,v in db_dir.meta_changes.iteritems():
                self.meta[k] = v
            
        

def export_patch( filename, patch_num, body_db ):
    p      = body_db.patch_db.patches[ patch_num ]

    if not p.is_complete:
        raise Exception('Patch incomplete. Cannot export')
    
    store_offset = 0
    store_len    = 0
    
    store_description = list()

    if p.ending_file_id >= p.starting_file_id:
    
        start = body_db.file_db.files[ p.starting_file_id  ]
        end   = body_db.file_db.files[ p.ending_file_id    ]
        
        store_offset = start.offset
        store_len    = (end.offset - start.offset) + end.zlength
        
        i = p.starting_file_id 
        
        while i <= p.ending_file_id:
            dbf = body_db.file_db.files[ i ]
            store_description.append( StoredFile(dbf.file_id, dbf.offset, dbf.length, dbf.zlength) )
            i += 1

    sd_pickle = pickle.dumps( store_description )
    
    with open( filename, 'w' ) as f:
        # Header
        f.write( p.uuid )
        f.write( p.previous_uuid )
        f.write( struct.pack('>Q', store_len) )    
        f.write( struct.pack('>Q', len(sd_pickle)) )

        # Store Description Pickle
        f.write( sd_pickle )

        print 'Store offset,len: ', store_offset, store_len
        body_db.file_store.export_data( f, store_offset, store_len )

        def export_dirs( db_dir ):
            dd_pickle = pickle.dumps( DirDescrip( db_dir ) )
            f.write( struct.pack('>I', len(dd_pickle)) )
            f.write( dd_pickle )
            dd_pickle = None # don't hold in memory as we recurse

            for subdir in db_dir.subdirs.itervalues():
                export_dirs( subdir )
        
        export_dirs( p.root )


def import_patch( filename, body_db ):

    with open(filename, 'r') as f:
        uuid          = f.read(16)
        previous_uuid = f.read(16)

        lid = body_db.patch_db.last_patch_id

        if lid is None and previous_uuid != '\0'*16:
            raise Exception('Patch database is empty. Must import a root patch first')
        
        if lid is not None and previous_uuid != body_db.patch_db.patches[ lid ].uuid:
            raise Exception('Requested patch prerequesite does not match the top of the current patch stack')
                
        store_len     = struct.unpack('>Q', f.read(struct.calcsize('>Q')))[0]
        sd_pickle_len = struct.unpack('>Q', f.read(struct.calcsize('>Q')))[0]
        
        store_pickle  = f.read( sd_pickle_len )
        store_description = pickle.loads( store_pickle )

        sd = None
        
        for sd in store_description:
            body_db.file_db.files[ sd.file_id ] = types.DBFile( sd.file_id, sd.offset, sd.length, sd.zlength )

        if sd:
            body_db.file_db.next_file_id = sd.file_id + 1

        transaction.commit()

        store_description = None # no need to keep in memory

        body_db.file_store.import_data( f, store_len )

        p = body_db.patch_db.create_patch( body_db )

        p.uuid = uuid
        p.previous_uuid = previous_uuid

        fsize = os.stat( filename ).st_size
            

        int_size = struct.calcsize('>I')
        while f.tell() != fsize:
            pkl_len = struct.unpack('>I', f.read(int_size))[0]
            dd = pickle.loads( f.read( pkl_len ) )

            if dd.fq_name == '':
                _populate( dd, p.root )
                transaction.commit()
            else:
                comps = dd.fq_name.split('/')
                pd    = p.root
                for c in comps[1:-1]:
                    pd = pd.subdirs[ c ]

                dir_name = comps[-1]

                new_pd = types.PatchedDirectory( dd.name, pd, dd.uid, dd.gid, dd.mode, dd.mtime_ns )
                
                _populate( dd, new_pd )

                pd.subdirs[ dir_name ] = new_pd
                
                transaction.commit()

        p.set_complete(body_db)
        transaction.commit()
                

def _populate( dd, db_dir ):
    db_dir.state = dd.state
    
    if hasattr(dd, 'adds'):
        for f in dd.adds:
            db_dir.adds[ f.name ] = _create_patch_file( f, db_dir )
    if hasattr(dd, 'removes'):
        for f in dd.removes:
            db_dir.removes[ f.name ] = _create_patch_file( f, db_dir )
    if hasattr(dd, 'meta'):
        for k,v in dd.meta.iteritems():
            db_dir.meta_changes[k] = v

                    
def _create_patch_file( f, parent ):
    pf = _db_constructor[ f.ftype ]( f.name, parent, f.uid, f.gid, f.mode, f.mtime_ns )

    if pf.ftype == fs.REGULAR:
        pf.size     = f.size
        pf.file_id  = f.file_id
        
    elif pf.ftype == fs.SYMLINK:
        pf.target = f.target
            
    elif pf.ftype in (fs.BLOCKDEV, fs.CHARDEV):
        pf.dev_major = f.dev_major
        pf.dev_minor = f.dev_minor

    return pf
    
