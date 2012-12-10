import os
import os.path

from kamino import KaminoException

from kamino.mind import definition


class RoleDefinitionError (KaminoException):
    def __init__(self, role_name, msg):
        self.role_name = role_name
        self.err       = str(msg)
    def __str__(self):
        return 'Error in role definition {0}.json: {1}'.format(self.role_name, self.err)

class MROError (RoleDefinitionError):
    pass

class MissingDefinition (RoleDefinitionError):
    pass

    

# Argument must be a dictionary containing "role_name" -> [parent_rolename1, parent_rolename2...]
# Roles with no parents should point to an empty list
def get_roles_mro( d ):
    c = dict()
    def mc( name ):
        if not name in c:
            try:
                c[ str(name) ] = type(str(name), tuple([ mc(x) for x in d[name] ] if d[name] else [object]), {})
            except TypeError, e:
                s = str(e)
                bases = [ x.strip() for x in s[s.index('bases')+len('bases')+1:].split(',') ]
                raise MROError(name, 'Unable to resolve inclusion order of parent roles: ' + ', '.join(bases))
                
        return c[ name ]
    for name in d.iterkeys():
        mc(name)

    mro = dict()
    for role_name, cls in c.iteritems():
        mro[ role_name ] = [ q.__name__ for q in cls.mro() ][1:-1]
        
    return mro



def load_roles( roles_dir ):
    
    roles = dict()
    
    for role_name in os.listdir( roles_dir ):
        rd = os.path.join( roles_dir, role_name )
        if os.path.isdir( rd ):
            d = os.path.join( rd, role_name + '.json' )
            if os.path.exists( d ):
                try:
                    roles[ role_name ] = definition.load( d )
                except Exception, e:
                    raise RoleDefinitionError(role_name, e)
            else:
                raise MissingDefinition(role_name, 'File does not exist')
            
    for_mro = dict()
    for role_name, r in roles.iteritems():
        parents = list()
        for_mro[ role_name ] = parents
        if 'parent_roles' in r:
            if not isinstance(r['parent_roles'], list):
                raise RoleDefinitionError(role_name, '"parent_roles" must be a list')
            for v in r['parent_roles']:
                if not isinstance(v, basestring) or not v in roles:
                    raise RoleDefinitionError(role_name, 'Invalid parent role name "{0!s}"'.format(v))
                parents.append( v )

        if 'globals' in r:
            if not isinstance(r['globals'], dict):
                raise RoleDefinitionError(role_name, '"globals" must be JSON object definition')

        if 'locals' in r:
            if not isinstance(r['locals'], dict):
                raise RoleDefinitionError(role_name, '"locals" must be JSON object definition')

        if 'config_files' in r:
            if not isinstance(r['config_files'], dict):
                raise RoleDefinitionError(role_name, '"config_files" must be JSON object definition')
            cf = r['config_files']
            for k,v in cf.iteritems():
                if not isinstance(k, basestring):
                    raise RoleDefinitionError(role_name, '"config_files" keys must be strings. {0!s} is invalid'.format(v))
                if not isinstance(v, dict):
                    raise RoleDefinitionError(role_name, '"config_files" values must be JSON objects. {0!s} is invalid'.format(v))                
                cf[ k.strip() ] = v
                if not k.startswith('/'):
                    raise RoleDefinitionError(role_name, '"config_files" keys must contain absolute path names. {0!s} is invalid'.format(k))

    mro = get_roles_mro( for_mro )

    return roles, mro




class RoleManager (object):
    def __init__(self, mind_dir):
        self.mind_dir  = mind_dir
        self.roles_dir = os.path.join( mind_dir, 'roles' )

        self.raw_roles, self.mros = load_roles( self.roles_dir )

        self._roles = dict()

        for k in self.raw_roles.iterkeys():
            self.getRole(k)
            

    def getRole(self, role_name):
        if role_name in self._roles:
            return self._roles[ role_name ]

        parents = [ self.getRole(p) for p in self.mros[ role_name ] ]

        self._roles[ role_name ] = Role( role_name,
                                         self.raw_roles[role_name],
                                         os.path.join(self.roles_dir, role_name),
                                         parents )

        return self._roles[ role_name ]


    
class ConfigFile (object):
    def __init__(self, role_name, role_dir, abs_path, cfg):
        self.role_name   = role_name
        self.name        = abs_path

        if 'template' in cfg and 'static_file' in cfg:
            raise RoleDefinitionError(role_name, 'Invalid config_files entry {0}. "template" and "static_file" are mutually exclusive'.format(self.name))

        if not 'template' in cfg and not 'static_file' in cfg:
            raise RoleDefinitionError(role_name, 'Missing "template" or "static_file" definition in config_files entry {0}'.format(self.name))

        
        self.is_template = 'template' in cfg
        self.fn          = cfg['template'] if self.is_template else cfg['static_file']
        self.abs_fn      = os.path.join(role_dir, self.fn)

        try:
            self.mode        = int(cfg['mode'],8) if 'mode' in cfg else 0644
        except ValueError:
            raise RoleDefinitionError(role_name, 'Invalid octal "mode" definition in config_files entry {0}'.format(self.name))

        if not os.path.exists( self.abs_fn ):
            raise RoleDefinitionError(role_name, 'Missing file for config_files entry {0}'.format(self.name))
        

        

class Role (object):

    def __init__(self, role_name, role_data, role_dir, parents):
        self.role_name     = role_name
        self.parents       = parents
        self.raw_data      = role_data
        self.role_dir      = role_dir
        self.config_files  = dict()
        self.globals       = dict()
        self.globals_ident = dict() # used to identify which role defines the associated global variable

        rparents = parents[:]
        rparents.reverse()

        for rp in rparents:
            for k,v in rp.globals.iteritems():
                if rp.globals_ident[k] == rp.role_name:
                    self.globals[k]       = v
                    self.globals_ident[k] = rp.role_name
                
            for k,v in rp.config_files.iteritems():
                if v.role_name == rp.role_name:
                    self.config_files[k] = v

        if 'globals' in self.raw_data:
            for k,v in self.raw_data['globals'].iteritems():
                self.globals[k]       = v
                self.globals_ident[k] = role_name

        if 'config_files' in self.raw_data:
            for k,v in self.raw_data['config_files'].iteritems():
                self.config_files[ k ] = ConfigFile(self.role_name, self.role_dir, k, v)

        self.locals = self.raw_data['locals'] if 'locals' in self.raw_data else dict()

        

