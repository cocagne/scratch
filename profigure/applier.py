import os
import os.path
import sys
import tempfile
import tarfile
import zipfile
import hashlib
import traceback
import shutil

from Cheetah import NameMapper

import profigure
from   profigure import *
from   profigure import localhost, roster, doctrine


class Tee (object):
    
    def __init__( self, out_file ):
        self.f = open(out_file, 'w')
        self.stdout = sys.stdout
        sys.stdout = self
        
    def write(self, msg):
        self.f.write( msg )
        self.stdout.write( msg )
        
    def close(self):
        self.f.flush()
        self.f.close()
        sys.stdout = self.stdout
        
        
    def fileno(self):
        return self.stdout.fileno()


    
class Undo (object):
    
    def __init__(self):
        fd, tpath = tempfile.mkstemp()
        os.close(fd)
        
        self.tarball_name = tpath
        self.tarball      = tarfile.open( tpath, 'w' )
        self.metas        = list() # (filename, orig_st)
        self.new_files    = list() # list of paths
        self.new_dirs     = list() # list of new dirs
        
    def __del__(self):
        self.cleanup()
            
    def cleanup(self):
        if self.tarball:
            self.tarball.close()
            os.unlink( self.tarball_name )
            self.tarball = None
        
    def log_meta(self, path):
        if os.path.exists(path):
            self.metas.append( (path, os.lstat(path) ) )
            
    def backup(self, path):
        if os.path.exists( path ):
            self.tarball.add( path )
        else:
            self.new_files.append( path )
            
    def log_new_dir(self, path):
        self.new_dirs.append( path )
            
    def undo(self):
        self.new_files.sort()
        
        for p in self.new_files:
            if os.path.exists(p):
                os.unlink(p)
        
        self.new_dirs.sort()
        self.new_dirs.reverse()
        for d in self.new_dirs:
            if os.path.isdir(d):
                shutil.rmtree(d)
                
        self.tarball.close()
        self.tarball = None
        
        try:
            tb = tarfile.open( self.tarball_name, 'r:' )
            tb.extractall( path = '/' ) # all members are added via fully qualified path
            tb.close()
        except tarfile.ReadError, e:
            print '***** DOH *******', str(e)
            pass
        
        os.unlink( self.tarball_name )
                
        for path, s in self.metas:
            if os.path.exists( path ):
                c = os.lstat(path)
                if (c.st_mode & 0777) != (s.st_mode & 0777):
                    os.chmod( path, s.st_mode & 0777 )
                nuid = -1 if s.st_uid == c.st_uid else s.st_uid
                ngid = -1 if s.st_gid == c.st_gid else s.st_gid
                if nuid != -1 or ngid != -1:
                    os.chown( path, nuid, ngid )


class Applier (object):
    
    def __init__(self, hostname, root_dir):
        
        self.hostname  = hostname
        self.localhost = localhost.LocalHost( hostname )
        
        self.localhost.scan_system()
        
        root_dir = os.path.expanduser( os.path.expandvars(root_dir) )
        
        self.root        = root_dir 
        self.output_root = None     # All output will be relative to this directory
        self.dist_pkg    = None     # zip file containing all config data
        self.roster      = None
        self.roles       = None     # list of all roles for this host
        self.temp_dir    = None
        self.doc         = doctrine.Doctrine()
        self.modules     = dict()   # maps hostname => hostname module (if any) and rolename => role module
        
        self.skip_identical = True

        self.is_test     = True
        self.meta_log    = None
        self.undo        = None
        
        self.updates     = list()
        
        # collects errors as they occur. Output will be sent to the log file
        #
        self.tracebacks    = list()  # list( (short_descrip, traceback) )
        self.template_errs = list()  # list( (short_descrip, traceback or None) )
        

        
        
    def delete_tempdir(self):
        if self.temp_dir:
            shell_silent('rm -rf %s' % self.temp_dir)
            self.temp_dir = None
        
            
    def test(self, dist_package, output_tarfile, skip_identical = False):
        
        self.skip_identical = skip_identical
        
        if not os.path.exists( os.path.dirname(output_tarfile) ):
            os.makedirs( os.path.dirname(output_tarfile) )
        
        self.temp_dir = tempfile.mkdtemp()
        print 'Created temp dir: ', self.temp_dir
            
        try:
            self.output_root = os.path.join( self.temp_dir, 'output' )
            self.dist_pkg    = dist_package

            self.is_test             = True  # For this file
            profigure.DEBUGGING      = True  # For role/host.py files
            self.localhost.DEBUGGING = True  # For Cheetah templates
            
            src_dir = os.path.join( self.temp_dir, 'source' )
            
            os.mkdir( self.output_root )
            os.mkdir( src_dir          )

            tee = Tee( os.path.join(self.output_root, 'STDOUT') )
            
            self._run_package( dist_package, src_dir )
            
            print ''
            print '****** Test Summary ******'
            print ''
            if self.updates:
                for l in self.updates:
                    print l
            else:
                print 'No changes made'

            tee.close()
            
            if self.meta_log:
                self.meta_log.close()
                
            self.gen_error_log( os.path.join(self.output_root,'ERROR_LOG') )

            t = tarfile.open( output_tarfile, 'w:gz' )
            
            for fn in os.listdir( self.output_root ):
                t.add( os.path.join(self.output_root, fn), fn )
                
            t.close()            
        finally:
            self.delete_tempdir()
    

            
    def apply_config(self, dist_package, err_log_file ):
        
        self.temp_dir = tempfile.mkdtemp()
        self.undo     = Undo()
        
        self.skip_identical = False
        
        try:
            self.dist_pkg = dist_package

            self.is_test             = False # For this file
            profigure.DEBUGGING      = False # For role/host.py files
            self.localhost.DEBUGGING = False # For Cheetah templates
            
            self.output_root = self.root

            updated_list = self._run_package( dist_package, self.temp_dir )
                        
            if self.tracebacks or self.template_errs:
                self.undo.undo()
                self.gen_error_log( err_log_file )
            else:
                for cfg in updated_list:
                    cfg.run_updated_callback()
                
        finally:
            self.undo.cleanup()
            self.undo = None
            self.delete_tempdir()
        
    
            
    def gen_error_log(self, log_file):
        if self.tracebacks or self.template_errs:
            with open( log_file, 'w' ) as f:
                if self.template_errs:
                    f.write('******************* Template Errors *******************\n\n')
                    for desc, tb in self.template_errs:
                        f.write( '-'*50 + '\n' )
                        f.write( '- ' + desc + '\n-\n' )
                        if tb:
                            f.write( tb + '\n\n' )

                if self.tracebacks:
                    f.write('*******************   Tracebacks    *******************\n\n')
                    for desc, tb in self.tracebacks:
                        f.write( '-'*50 + '\n' )
                        f.write( '- ' + desc + '\n-\n' )
                        f.write( tb + '\n\n' )
            

    def log_meta(self, path, mode, uid, gid):
        if not self.meta_log:
            self.meta_log = open( os.path.join(self.output_root,'META_LOG'), 'w' )
            
        m = 'mode = n/a'
        u = 'uid = n/a  '
        g = 'gid = n/a  '
        if mode:      m = 'mode = %3o' % mode
        if uid != -1: u = 'uid = %5d' % uid
        if gid != -1: g = 'gid = %5d' % gid
            
        self.meta_log.write( '%s %s %s %s\n' % (m, u, g, path) )
                        
            
    def _run_package(self, dist_package, src_dir):
        
        os.chdir( src_dir )
            
        z = zipfile.ZipFile( dist_package )
        z.extractall()
            
        def touch( fn ):
            if not os.path.exists( fn ):
                with open(fn,'w') as f:
                    pass

        for d in ('roles', 'hosts'):
            x = os.path.join(src_dir, d)
            if not os.path.exists(x):
                os.makedirs(x)
                
        touch( os.path.join( src_dir, 'roles', '__init__.py' ) )
        touch( os.path.join( src_dir, 'hosts', '__init__.py' ) )
        
        sys.path.append( src_dir )
                    
        self.roster = roster.Roster('roster')
        self.roster.read()
            
        self.roles = self.roster.get_all_host_roles( self.hostname )
            
        self.load_modules()
        
        self.run_preconfigure_hooks()
            
        updated_list = self.configure()
        
        self.run_postconfigure_hooks()
        
        return updated_list

    
    
    def log_err(self, desc):
        self.tracebacks.append( (desc, traceback.format_exc()) )
    
        
            
    def load_modules(self):
        
        def log_import_error( mname ):
            self.log_err( 'Failed to import module: ' + mname )
                    
        try:
            mname = 'hosts.%s' % self.hostname
            __import__( mname )
            self.merge_doctrine( mname )
            self.modules[ self.hostname ] = sys.modules[ mname ]
        except ImportError, e:
            if not str(e) == 'No module named %s' % self.hostname:
                log_import_error( mname )
        except Exception:
            log_import_error( mname )
            
        
        for r in self.roles:
            mname = 'roles.%s' % r
            if not mname in sys.modules:
                try:
                    __import__( mname )
                    self.merge_doctrine( mname )
                    self.modules[ r ] = sys.modules[ mname ]
                except ImportError, e:
                    if not str(e) == 'No module named %s' % mname:
                        log_import_error( mname )
                except Exception, e:
                    log_import_error( mname )
                    
            
            
            
            
    def merge_doctrine(self, mod_name):
        
        module = sys.modules[ mod_name ]
        d      = getattr( module, 'doctrine', None )
        
        assert isinstance(d, doctrine.Doctrine)
        
        d.base_dir    = os.path.dirname( os.path.abspath( module.__file__ ) )
        d.module      = module
        d.module_name = mod_name
        
        self.doc.merge_with( d )
            

        
    def _hooker(self, hook_name, *args):
        def run_hook( mod ):
            if mod in self.modules:
                hook = getattr(self.modules[ mod ], hook_name, None)
                if hook:
                    try:
                        hook(*args)
                    except Exception:
                        self.log_err( 'Error in %s.%s' % (mod, hook_name) )
        run_hook( self.hostname )
        for r in self.roles:
            run_hook(r)
            

            
    def run_preconfigure_hooks(self):
        self._hooker( 'preconfigure_hook', self.localhost )
        
        
        
    def run_postconfigure_hooks(self):
        self._hooker( 'postconfigure_hook' )


    
    def assert_dir_exists(self, sys_file, out_file ):
        if not os.path.isdir( os.path.dirname(sys_file) ):
            raise Exception('Parent directory does not exist')
        
        if self.is_test:
            if not os.path.isdir( os.path.dirname(out_file) ):
                os.makedirs( os.path.dirname(out_file) )
        
        
    def create_directory( sys_dir_name, out_dir_name, mode ):
        try:
            self.assert_dir_exists( sys_dir_name, out_dir_name )
            
            if os.path.exists( out_dir_name ) and not os.path.isdir( out_dir_name ):
                if self.undo:
                    self.undo.backup( out_dir_name )
                os.unlink( out_dir_name )

            if not os.path.isdir( out_dir_name ):
                os.mkdir( out_dir_name, mode )
                self.updates.append( 'Created directory: ' + sys_dir_name )
        except Exception, e:
            self.log_err('Failed to create directory %s: %s' % (out_dir_name, str(e)))
        
                
        
        
    # returns: True for file updated, False if content is identical and file was not written
    def write_config(self, sys_file, out_file, mode, content ):
        
        try:
            should_write = True
            
            if self.skip_identical and os.path.exists( sys_file ):
                with open(sys_file,'r') as fobj:
                    if hashlib.sha1( fobj.read() ).digest() == hashlib.sha1( content ).digest():
                        should_write = False
                
            if not should_write:
                print 'SKIPPING IDENTICAL CONFIG: ', sys_file
                return False
            
            self.assert_dir_exists( sys_file, out_file )
            
            # Backup file in case we encounter errors later and need to restore it
            if self.undo:
                self.undo.backup( out_file )
                        
            if os.path.exists( out_file ) and os.path.isdir( out_file ):
                # Overwriting a directory with a file. Blow away the directory. 
                shutil.rmtree( out_file )
                                            
            prev = os.umask(0077)
            with open(out_file, 'w') as fobj:
                fobj.write( content )
            os.umask( prev )
            
            os.chmod(out_file, mode)
        
            self.updates.append( 'Wrote file: ' + sys_file )
            return True
        except Exception:
            self.log_err('Failed to write file: %s' % out_file)
            return False

        
        
    def make_symlink(self, sys_from_path, out_from_path, to_path):
        try:
            if self.skip_identical and os.path.islink( sys_from_path ) and os.readlink( sys_from_path ) == to_path:
                return False
            
            self.assert_dir_exists( sys_from_path, out_from_path )
            
            if self.undo:
                self.undo.backup( out_from_path )
            
            if os.path.exists( out_from_path ):
                os.unlink( out_from_path )
                    
            self.updates.append( 'Created symlink: ' + sys_from_path )
            os.symlink(to_path, out_from_path)
        except Exception:
            self.log_err('Failed to create symlink: %s' % out_from_path)
        
            
    def change_meta(self, sys_path, out_path, mode, uid, gid):
        def do_change( mode, uid, gid ):
            if self.is_test:
                self.log_meta( sys_path, mode, uid, gid )
                
            if os.path.exists( out_path ):
                if self.undo:
                    self.undo.log_meta( out_path )
                if mode:
                    os.chmod(out_path, mode)
                    self.updates.append( 'Changed mode on:       ' + sys_path )
                if uid != -1 or ngid != -1:
                    os.chown(out_path, uid, gid)
                    self.updates.append( 'Changed ownership of : ' + sys_path )
                    
        try:
            if not os.path.exists( sys_path ):
                raise Exception('Path does not exist')
                
            s = os.lstat( sys_path )

            nmode = None
            if mode and not mode == (s.st_mode & 0777):
                nmode = mode
                
            nuid = -1 if uid is None or s.st_uid == uid else uid
            ngid = -1 if gid is None or s.st_gid == gid else gid
            
            if nmode or nuid != -1 or ngid != -1:
                do_change( nmode, nuid, ngid )
                
        except Exception, e:
            self.log_err('Metatdata change on %s failed: %s' % (out_path, str(e)))


    
    def get_sys_out(self, file_name):
        if file_name[0] == '/':
            file_name = file_name[1:]
        sys_file     = os.path.join(self.root,        file_name)
        out_file     = os.path.join(self.output_root, file_name)
        return sys_file, out_file
            
            
    # Returns a list of updated doctrine.ConfigFile instances so their 'run_updated_callback'
    # methods can be invoked at the proper time
    def configure(self):

        updated_list = list() # list of doctrine.ConfigFiles that were updated
        named_roles  = dict()
        search_list  = [ named_roles, self.localhost ]
                
        hmod = sys.modules.get( 'hosts.%s' % self.hostname, None )
        
        if hmod:
            named_roles[ self.hostname ] = hmod
            search_list.append( hmod )
                        
        for rn in self.roster.get_all_host_roles( self.hostname ):
            try:
                rmod = sys.modules[ 'roles.%s' % rn ]
                named_roles[ rn ] = rmod
                search_list.append( rmod )
            except KeyError:
                pass
            
        #
        # Directories
        #
        dmap     = {}
        dlist    = list()
        for path, mode in self.doc.iter_directories():
            dmap[ path ] = mode
            dlist.append( path )
        dlist.sort() # ensure we create top-level directories before attempting to create subdirectories
        
        for path in dlist:
            sys_dir, out_dir = self.get_sys_out( path )
            self.create_directory( sys_dir, out_dir, dmap[path] )
            
        
        #
        # Config files
        #
        for cfg in self.doc.iter_config_files():
            
            fq_tmpl_file = cfg.get_template_file()
            
            sys_file, out_file = self.get_sys_out( cfg.file_name )
                        
            content      = None
            if not fq_tmpl_file.endswith('.tmpl'):
                #
                # Static File
                #
                content = ''
                with open( fq_tmpl_file, 'r' ) as fobj:
                    content = fobj.read()
            else:
                #
                # Cheetah Template
                #
                class_name = cfg.template_name[:-5]
                tmpl_mod   = '%s.%s' % (cfg.doctrine.module_name, class_name)
                
                try:
                    __import__( tmpl_mod )
                    
                    tmpl_class = getattr(sys.modules[ tmpl_mod ], class_name)
                    tmpl       = tmpl_class( searchList = search_list )
                    content    = str(tmpl)
                except NameMapper.NotFound, e:
                    self.template_errs.append( ('Template Symbol Error in %s.tmpl: %s' % (tmpl_mod.replace('.','/'), str(e)), None)  )
                    print str(e)
                except Exception, e:
                    self.template_errs.append( ('Error in template %s.tmpl: %s' % (tmpl_mod.replace('.','/'), str(e)), traceback.format_exc())  )
                    print str(e)
                    

            if content:
                if self.write_config( sys_file, out_file, cfg.mode, content ):
                    updated_list.append( cfg )
        #
        # Symlinks
        #
        for from_path, to_path in self.doc.iter_symlinks():
            
            sys_from_path, out_from_path = self.get_sys_out( from_path )
                
            self.make_symlink( sys_from_path, out_from_path, to_path )
            
            
        #
        # Metas
        #
        for path, (mode, uid, gid) in self.doc.iter_metas():
            sys_path, out_path = self.get_sys_out( path )
            self.change_meta( sys_path, out_path, mode, uid, gid )
                
        return updated_list
                
        
        
