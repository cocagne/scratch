import os.path


class ConfigFile (object):
    
    def __init__(self, doctrine, config_file_name, template_name, mode, pre_config_func, post_config_func, updated_function):
        self.doctrine      = doctrine
        self.file_name     = config_file_name
        self.template_name = template_name
        self.mode          = mode
        self.pre_config    = pre_config_func
        self.post_config   = post_config_func
        self.on_update     = updated_function
        self.was_updated   = False
        
        
    def get_template_file(self):
        return os.path.join( self.doctrine.base_dir, self.template_name )
    
    
    def run_updated_callback(self):
        if self.on_update:
            self.on_update()
        

        
class Doctrine (object):
    
    def __init__(self):
        
        self._config_files = dict()
        self._symlinks     = dict() # from => to
        self._metas        = dict() # path => (mode, uid, gid)  Use 'None' for 'no change'
        self._directories  = dict()
        
        # Set by brainwasher to reference the module & directory that creates the
        # Doctrine instance (needed to locate the template files)
        self.base_dir      = None 
        self.module        = None 
        self.module_name   = None 

        
        
    def add_config_file(self, config_file_name, template, mode=0644, pre_configure_function = None, post_configure_function = None, updated_function = None):
        self._config_files[ config_file_name ] = ConfigFile( self, config_file_name, template, mode, pre_configure_function, post_configure_function, updated_function )
        
        
    def add_directory(self, dir_name, mode=0755):
        self._directories[ dir_name ] = mode
                    
        
    def add_symlink(self, from_path, to_path):
        self._symlinks[ from_path ] = to_path
        
        
    def add_meta(self, path, mode=None, uid=None, gid=None):
        assert mode is not None or uid is not None or gid is not None
        # TODO: Lookup numeric uid/gid for symbolic names
        self._metas[ path ] = (mode, uid, gid)
        
            
    def iter_config_files(self):
        return self._config_files.itervalues()
    
    def iter_symlinks(self):
        return self._symlinks.iteritems()
    
    def iter_metas(self):
        return self._metas.iteritems()
    
    def iter_directories(self):
        return self._directories.iteritems()
        
    
    def merge_with( self, other ):
        
        for k,v in other._config_files.iteritems():
            if not k in self._config_files:
                self._config_files[ k ] = v
                
        for k,v in other._symlinks.iteritems():
            if not k in self._symlinks:
                self._symlinks[ k ] = v
                
        for k,v in other._metas.iteritems():
            if not k in self._metas:
                self._metas[ k ] = v
                
        for k,v in other._directories.iteritems():
            if not k in self._directories:
                self._directories[ k ] = v
                
        
        
        
