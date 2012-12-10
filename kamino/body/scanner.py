import os
import os.path
import subprocess

from kamino.body import fs
from kamino.body import db



class Delta (object):

    def push_dir(self, dir_name):
        pass

    def pop_dir(self):
        pass

    def content_added(self, fs_file, force_zero_length=False):
        pass

    def content_removed(self, db_file):
        pass

    def metadata_changed(self, db_file, fs_file):
        pass

    # Called in a bottom-up manner
    def directory_removed(self, db_dir):
        pass
    
    # Called in a top-down manner
    def directory_added(self, fs_dir):
        pass


class Filter (object):

    def __init__(self):
        self.touch_new_only = False
        self.track_files    = True

        self.ignore_dirs = set()

        self.filters = dict()
        self.dstack  = list()
        self.fstack  = list()

        
    def add_ignore(self, path):
        self.ignore_dirs.add( path )

    def add_touch_new_files(self, path):
        self.filters[ path ] = (True, True)

    def add_track_dirs_only(self, path):
        self.filters[ path ] = (False, False)

    def push_dir(self, dir_name):
        self.dstack.append( dir_name )

        p = os.path.join(*self.dstack)
        
        t = (self.touch_new_only, self.track_files)
        self.fstack.append( t )
        
        self.touch_new_only, self.track_files = self.filters.get( p, t )
        
        print 'FILT ', dir_name, self.touch_new_only, self.track_files

    def pop_dir(self):
        self.touch_new_only, self.track_files = self.fstack.pop()
        self.dstack.pop()
        

    
class Scanner (object):

    def __init__(self, root_fs_dir, body_db, delta, filter_obj):

        self.fs_id_map  = dict()
        self.filter     = filter_obj
        self.fs_root    = root_fs_dir
        self.body_db    = body_db
        self.delta      = delta

        
        
    def scan(self, ignore_mounts=True):

        # Ensure our mount points and skip dirs are up to date
        
        for mount_point, fs_id in self.body_db.fs_db.mounts.iteritems():
            self.fs_id_map[ mount_point ] = fs_id

        if ignore_mounts:
            for mount, is_local in fs.get_mount_table().iteritems():
                if not is_local:
                    self.filter.add_ignore( mount )
                    
        self.recursive_scan( self.fs_root, self.body_db.db_root['/'] )

        
    def _push_dir(self, dir_name):
        self.filter.push_dir( dir_name )
        self.delta.push_dir( dir_name )

    def _pop_dir(self):
        self.filter.pop_dir()
        self.delta.pop_dir()



    def recursive_scan(self, fs_dir_path, db_dir, fs_id=None ):

        if fs_dir_path in self.filter.ignore_dirs:
            return

        self._push_dir( db_dir.name )
        
        if fs_id is None:
            mounts = self.fs_id_map.keys()
            mounts.sort()
            mounts.reverse()
            for mp in mounts:
                if fs_dir_path.startswith( mp ):
                    fs_id = self.fs_id_map[ mp ]
                    break

        if fs_dir_path in self.fs_id_map:
            fs_id = self.fs_id_map[ fs_dir_path ]

        assert fs_id is not None

        fs_content = fs.read_dir( fs_dir_path )

        fs_set = set( (f.name, f.ftype) for f in fs_content.itervalues() )
        db_set = db_dir.get_content_set()

        removed = [ db_dir.content[ t[0] ] for t in db_set.difference( fs_set ) ]
        added   = [ fs_content[ t[0] ]     for t in fs_set.difference( db_set ) ]
        same    = [ (fs_content[t[0]], db_dir.content[t[0]]) for t in db_set.intersection( fs_set ) ]

        # Remove modified files & symlinks from 'same'
        if self.filter.track_files and not self.filter.touch_new_only:
            for tpl in same:
                fs_f, db_f = tpl
                if (fs_f.ftype == fs.SYMLINK and fs_f.target   != db_f.target  ) or (
                    fs_f.ftype == fs.REGULAR and fs_f.mtime_ns != db_f.mtime_ns):
                    same.remove( tpl )
                    removed.append( db_f )
                    added.append( fs_f )
        

        meta_modified = list()
        for tpl in same:
            fs_f, db_f = tpl
            if (fs_f.uid, fs_f.gid, fs_f.mode) != (
                db_f.uid, db_f.gid, db_f.mode):
                if self.filter.track_files or fs_f.ftype == fs.DIRECTORY:
                    meta_modified.append( tpl )

        # process order:
        #   1. Non-directory Removals
        #   2. Non-directory Additions
        #   3. Meta Modifications
        #   4. Recursive directory removals
        #   5. Recursive directory additions
        #   6. Recursive scan pre-existing directories


        if self.filter.track_files:
            for db_f in (x for x in removed if not x.ftype == fs.DIRECTORY):
                self.delta.content_removed( db_f )
            

            for fs_f in (x for x in added if not x.ftype == fs.DIRECTORY):
                if fs_f.ftype == fs.REGULAR:
                    fs_f.fs_id = fs_id
                self.delta.content_added( fs_f, self.filter.touch_new_only )
            
            
        for tpl in meta_modified:
            fs_file, db_file = tpl
            self.delta.metadata_changed(db_file, fs_file)
    

        for db_f in (x for x in removed if x.ftype == fs.DIRECTORY):
            self.recursive_remove( db_f )

            
        for fs_f in (x for x in added if x.ftype == fs.DIRECTORY):
            self.recursive_add( fs_dir_path, fs_f, fs_id )

            
        for tpl in same:
            if tpl[0].ftype == fs.DIRECTORY:
                self.recursive_scan( os.path.join(fs_dir_path, tpl[0].name), tpl[1], fs_id )

        self._pop_dir()




    def recursive_remove(self, db_dir):
        # Bottom up, recurse to lower directories first
        self._push_dir( db_dir.name )
        
        for subdir in [x for x in db_dir.content.itervalues() if x.ftype == fs.DIRECTORY]:
            self.recursive_remove( subdir )

        for f in [x for x in db_dir.content.itervalues() if not x.ftype == fs.DIRECTORY]:
            self.delta.content_removed( f )

        self._pop_dir()
        self.delta.directory_removed( db_dir )

        


    
    def recursive_add(self, fs_dir_path, fs_f, fs_id):
        # Top down, recurse to lower directories last
    
        if fs_dir_path in self.filter.ignore_dirs:
            return

        self.delta.directory_added( fs_f )

        self._push_dir( fs_f.name )
        
        if fs_dir_path in self.fs_id_map:
            fs_id = self.fs_id_map[ fs_dir_path ]
    
        path = os.path.join( fs_dir_path, fs_f.name )
    
        content = fs.read_dir( path )

        if self.filter.track_files:
            for f in ( x for x in content.itervalues() if not x.ftype == fs.DIRECTORY ):
                if f.ftype == fs.REGULAR:
                    f.fs_id = fs_id
                self.delta.content_added( f, self.filter.touch_new_only )
            
        for f in ( x for x in content.itervalues() if x.ftype == fs.DIRECTORY ):
            self.recursive_add( path, f, fs_id )

        self._pop_dir()


    
    
    

            
