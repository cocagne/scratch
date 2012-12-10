import sys
import os
import os.path
import zipfile
import traceback
import tempfile
import shutil

from profigure.roster import Roster
from profigure import *


class ProfigureSyntaxError (ProfigureException):
    pass


class Builder (object):
    
    def __init__(self, source_dir, dist_dir, temp_dir=None):
               
        self.need_cleanup = False
        self.temp_dir     = temp_dir
        self.source_dir   = source_dir
        
        if self.temp_dir is None:
            self.need_cleanup = True
            self.temp_dir     = tempfile.mkdtemp()

        self.roster = Roster( '%s/roster' % source_dir )
        self.roster.read()
        
        # TODO: Load modules and ensure all files doctrine files exist
        #for role_name in self.roster.all_roles:
        #    if not os.path.exists( os.path.join(self.source_dir, 'roles', role_name + '.py') ):
        #        raise ProfigureException('Missing file "roles/%s.py" for role %s' % (role_name, role_name))
        
        self.dist_dir  = dist_dir
        self.build_dir = '%s/build'       % self.temp_dir
        self.hosts_dir = '%s/build/hosts' % self.temp_dir
        self.roles_dir = '%s/build/roles' % self.temp_dir
        
        shell_silent('rm -rf  %s' % self.temp_dir)
        
        for d in (self.dist_dir, self.build_dir):
            shell_silent('mkdir -p  %s' % d)
            
        self._copy_and_compile()
        
        sys.path.append( self.build_dir )

        self.load_modules()
        
        
        
    def __del__(self):
        self.cleanup()
        
        
        
    def cleanup(self):
        if self.need_cleanup:
            self.need_cleanup = False
            shutil.rmtree( self.temp_dir )
            self.temp_dir = None
        

        
            
    def _copy_and_compile(self):
        # Copy content to temporary directory & cheetah compile templates
        shell_silent('cp -r %s/* %s' % (self.source_dir, self.build_dir))
        
        # Rename all host/role.py files to corresponding '__init__.py'
        def rename_file( parent_dir, module_name ):
            mdir   = os.path.join(parent_dir, module_name)
            pyfile = os.path.join(parent_dir, module_name + '.py')
            init   = os.path.join(mdir, '__init__.py')
            
            if not os.path.exists(parent_dir):
                os.mkdir( parent_dir )
                
            if not os.path.exists( mdir ):
                os.mkdir( mdir )

            if os.path.exists( pyfile ):
                os.rename( pyfile, init )
            else:
                with open( init, 'w' ) as f:
                    f.write('from profigure import *\ndoctrine = Doctrine()\n')
                
                
        for r in self.roster.all_roles:
            rename_file( os.path.join(self.build_dir, 'roles'), r )
            
        for h in self.roster.all_hosts:
            rename_file( os.path.join(self.build_dir, 'hosts'), h )
        
        for rh in ('hosts', 'roles'):
            d = os.path.join(self.build_dir,rh)
            if not os.path.exists(d):
                os.mkdir(d)
            with open( os.path.join(d,'__init__.py'), 'w' ) as fobj:
                pass
        
            
        print shell_output( 'cd %s; cheetah compile -R' % self.build_dir )
        
        # TODO: Ensure all templates compiled successfully


                
                
                
    #---------------------------------------------------------------------------
    # Module load & doctrine verification
    #
    def check_doctrine(self, module_name, dirpath):
        module   = sys.modules[ module_name ]
        have_dir = os.path.exists( dirpath )
        
        kind      = 'hosts' if module_name.startswith('hosts') else 'roles'
        base_name = module_name[ module_name.rfind('.')+1: ]
        src_file  = os.path.join(self.source_dir, kind, base_name) + '.py'
        mod_dir   = os.path.join(self.build_dir, kind, base_name)
        
        doc = getattr( module, 'doctrine', None )
        
        
        if not isinstance(doc, Doctrine):
            raise ProfigureException('Error: %s "define_doctrine()" function did not return a Doctrine object!' % src_file)
        
        
        for cfg in doc.iter_config_files():
            
            if not cfg.file_name.startswith('/') or cfg.file_name.endswith(' '):
                raise ProfigureException('Invalid configuration file path "%s". All paths must be absolute and contain no leading or trailing spaces.' % cfg.file_name)
            
            if cfg.template_name.endswith('.tmpl'):
                
                mod      = '%s.%s' % (module_name, cfg.template_name[:-5])
                fn       = os.path.join(mod_dir, cfg.template_name[:-5] + '.py')
                err_file = mod.replace('.','/') + '.tmpl'
                
                if not os.path.exists(fn):
                    raise ProfigureException('Missing Cheetah compiled .py file for template: %s' % err_file)

                try:
                    __import__( mod )
                except ImportError, e:
                    raise ProfigureException('Python module import failed in %s: %s' % (err_file, str(e)))
            else:
                fn = os.path.join(mod_dir, cfg.template_name)
                if not os.path.exists( fn ):
                    k = 'host' if kind == 'hosts' else 'role'
                    raise ProfigureException('Missing static file "%s" for %s "%s"' % (cfg.template_name, k, module_name[ module_name.find('.')+1: ]))
        
        
    def load_modules(self):
        for r in self.roster.all_roles:
            mname = 'roles.%s' % r
            if not mname in sys.modules:
                try:
                    __import__( mname )
                except Exception:
                    bt = traceback.format_exc()
                    mfile = os.path.join(self.source_dir, 'roles', r + '.py')
                    bfile = os.path.join(self.build_dir, 'roles', r, '__init__.py')
                    raise ProfigureSyntaxError( bt.replace( bfile, mfile ) )
            self.check_doctrine( mname, os.path.join(self.build_dir, 'roles', r) )
                
        for h in self.roster.all_hosts:
            mname = 'hosts.%s' % h
            if os.path.exists( os.path.join(self.build_dir, 'hosts', h,  '__init__.py' ) ):
                try:
                    __import__( mname )
                except Exception:
                    bt = traceback.format_exc()
                    mfile = os.path.join(self.source_dir, 'hosts', h + '.py')
                    bfile = os.path.join(self.build_dir, 'hosts', h, '__init__.py')
                    raise ProfigureSyntaxError( bt.replace( bfile, mfile ) )
                self.check_doctrine( mname, os.path.join(self.build_dir, 'hosts', h) )
                
                
    #---------------------------------------------------------------------------
    # Zip-file distribution building
    #
    def _add_prefix(self, z, prefix, sub_name ):
        rfn  = os.path.join(self.build_dir, prefix, sub_name + '.py')
        rdir = os.path.join(self.build_dir, prefix, sub_name )
            
        if os.path.exists( rdir ):
            for dp, dns, fns in os.walk( rdir ):
                for fn in fns:
                    if fn.endswith('.pyc'):
                        continue
                    fqfn    = os.path.join(dp, fn)
                    arcname = fqfn[ len(self.build_dir) + 1: ]
                    z.write( fqfn, arcname )
    
    def _add_role(self, z, role_name ):
        self._add_prefix( z, 'roles', role_name )
        
    def _add_host(self, z, hostname ):
        self._add_prefix( z, 'hosts', hostname )

    
    # Returns list of all hosts for which packages were built
    def build_dist(self, host_list = None, role_list = None):
        if host_list is None and role_list is None:
            host_list = self.roster.all_hosts
            
        if host_list is None:
            host_list = list()
            
        if role_list:
            hs = set( host_list )
            for h in self.roster.get_hosts_depending_on_roles(role_list):
                if not h in hs:
                    hs.add( h )
                    host_list.append( h )
            
            
        for hostname in host_list:
            z = zipfile.ZipFile( os.path.join(self.dist_dir, '%s.zip' % hostname), 'w' )
            
            z.write( os.path.join(self.build_dir, 'roster'), 'roster' )
            
            self._add_host( z, hostname )
            for role_name in self.roster.get_all_host_roles( hostname ):
                self._add_role( z, role_name )
                
            z.close()
            
        return host_list
