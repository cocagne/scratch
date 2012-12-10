import os.path
import re

from profigure import ProfigureException


class RosterErr (ProfigureException):
    pass


role_re = re.compile('([a-zA-Z_][\w]+)')

class Roster (object):
    
    def __init__(self, roster_ini_file):
        self.ini_file = roster_ini_file

        self.master_hostname  = None
        self.master_port      = None
        self.all_hosts        = list()
        self.all_roles        = list()
        self.role_members     = dict() # maps role-name to membership list
        self.host_role        = dict() # maps host-name to role
        self.role_deps        = dict() # maps role-name to list of role dependencies

        
    def get_modified_hosts(self, other_roster, modified_hosts_set = set(), modified_roles_set = set()):
        hcur = set( self.all_hosts ) 
        hold = set( other_roster.all_hosts )
        rcur = set( self.all_roles ) 
        rold = set( other_roster.all_roles )
        
        modified_hosts_set.update( hcur - hold ) # all added hosts
        # We can ignore *removed* hosts since, by definition, we don't do anything with them anymore...
                    
        for host in hcur & hold:
            hrc = set( self.get_all_host_roles(host) )
            hro = set( other_roster.get_all_host_roles(host) )
            if hrc != hro or hrc & modified_roles_set:
                modified_hosts_set.add( host )

        return modified_hosts_set
    
    
                
        
    def get_all_host_roles( self, hostname ):
        rs = set()
        rl = list()
        
        rs.add('default')
        
        def grole( role_name ):
            if not role_name in rs:
                rl.append( role_name )
                for rd in self.role_deps[ role_name ]:
                    grole( rd )
        
        grole( self.host_role[hostname] )
        
        rl.append('default')
        return rl
    
    
    
    def get_role_deps( self, base_role ):
        rs = set()
        rl = list()
        
        rs.add('default')
        
        def grole( role_name ):
            if not role_name in rs:
                rl.append( role_name )
                for rd in self.role_deps[ role_name ]:
                    grole( rd )
        
        grole( base_role )
        
        rl.append('default')
        return rl

    
    def get_all_hosts_depending_on_role(self, role_name):
        
        dependent_roles = [ r for r in self.all_roles if role_name in self.get_role_deps( r ) ]
        dependent_roles.append( role_name )
        
        host_set  = set()
        
        for r in dependent_roles:
            for h in self.role_members[ r ]:
                host_set.add(h)
                
        return list(host_set)
    
    
    def get_hosts_depending_on_roles(self, role_list):
        rs = set()
        hs = set()
        
        for r in role_list:
            for rd in ( x for x in self.all_roles if not x in rs and r in self.get_role_deps( x ) ):
                rs.add( rd )
                for h in self.get_all_hosts_depending_on_role( rd ):
                    hs.add( h )
                    
        return list( hs )
    
        
    def read(self):
        hs = set()
        rs = set()
        line_no = 1
        current_role = 'default'
        self.role_members[ current_role ] = list()
        
        if not os.path.isfile( self.ini_file ):
            raise RosterErr('Missing roster file: %s' % self.ini_file)
        
        with open(self.ini_file, 'r') as fobj:
            for line in fobj:
                l = line.strip()
                
                if l and not l.startswith('#'):
                    
                    l = l.strip()
                    
                    if l.lower().startswith('master'):
                        if self.master_hostname:
                            raise RosterErr('Only one master may be defined')
                        
                        tpl = l.split()[1:]
                        
                        if tpl[0] == '=':
                            tpl.pop(0)
                        
                        try:
                            self.master_hostname, self.master_port = tpl[0].split(':')
                            self.master_port = int(self.master_port)
                        except Exception:
                            raise RosterErr('Invalid master definition. Format is "MASTER = hostname:port"')
                        
                        
                    elif l.startswith('['):
                        tpl = role_re.findall(l)
                        if not tpl:
                            raise RosterErr('Invalid role definition "%s" on line %d' % (l,line_no))
                        current_role = tpl[0]
                        if current_role in rs:
                            raise RosterErr('Duplicate definition of role "%s" on line %d' % (current_role, line_no))
                        rs.add(current_role)
                        self.all_roles.append(current_role)
                        self.role_members[ current_role ] = list()
                        self.role_deps[ current_role ] = list()
                        if len(tpl) > 1:
                            for i in range(1,len(tpl)):
                                dep = tpl[i]
                                if not dep in rs:
                                    raise RosterErr('Invalid role "%s" requested on line %d' % (dep, line_no))
                                self.role_deps[ current_role ].append( dep )
                        
                    else:
                        if l in hs:
                            raise RosterErr('Duplicate definition of membership for host "%s" on line %d' % (l,line_no))
                        hs.add(l)
                        self.all_hosts.append(l)
                        self.role_members[ current_role ].append(l)
                        self.host_role[ l ] = current_role
                        
                line_no += 1
                
        for rd in self.role_deps.itervalues():
            rd.append('default')
        self.all_roles.append('default')
