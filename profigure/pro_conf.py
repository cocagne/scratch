# Parser for profigure.conf

import os.path

class ConfigError (Exception):
    pass


def parse_line( l ):
    l = l.lower()
    
    tpl = [ x for x in l.split() if x and not x == '=' ]
    
    one = tpl[0] if len(tpl) > 0 else None
    two = tpl[1] if len(tpl) > 1 else None
    
    return one, two
    

class ProfigureConf (object):
    
    def __init__(self, filename, require_host_info = False):
        self.filename = filename

        self.hostname        = None
        self.host_port       = None
        self.master_hostname = None
        self.master_port     = None
        self.database_dir    = None
        self.log_dir         = None
        self.have_master     = None # just used for error checking
        self.require_host    = require_host_info
        
        if os.path.exists( filename ):
            self._read()
            
            
    def _read(self):
        
        with open(self.filename, 'r') as fobj:
            for l in fobj:
                
                l = l.strip()
                    
                if l and not l.startswith('#'):
                    
                    key, val = parse_line( l )
                    
                    if key == 'master':
                        if self.master_hostname:
                            raise ConfigError('Only one master may be defined')
                                                
                        try:
                            self.master_hostname, self.master_port = val.split(':')
                            self.master_port = int(self.master_port)
                            self.have_master = True
                        except Exception:
                            raise ConfigError('Invalid master definition. Format is "MASTER = hostname:port"')
                        
                    elif key == 'database_dir':
                        if self.database_dir:
                            raise ConfigError('Only one database directory is permitted')
                        
                        self.database_dir = val
                        
                    elif key == 'hostname':
                        if self.hostname:
                            raise ConfigError('Only one name for the host is permitted')
                        
                        self.hostname = val
                        
                    elif key == 'host_port':
                        try:
                            self.host_port = int(val)
                        except ValueError:
                            raise ConfigError('Invalid port number "%s"' % val )
                                                
                    elif key == 'log_dir':
                        self.log_dir = val
                        
        
        def check_attr( attr ):
            v = getattr(self, attr)
            if v is None:
                raise ConfigError('Missing required attribute "%s"' % attr)
            
        check_attr('have_master')
        
        if self.require_host:
            check_attr('hostname')
            check_attr('host_port')
        
