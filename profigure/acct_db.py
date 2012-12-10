import os.path
import sqlite3



class AcctDB (object):
    
    def __init__(self, filename):
        self.filename = filename
        
        create_db = not os.path.exists( self.filename )
        
        self.conn = sqlite3.connect( self.filename )
        self.c    = self.conn.cursor()
        
        self._admins = set()
        self._hosts = set()
        
        if create_db:
            self.c.execute('create table admins (admin_name text UNIQUE PRIMARY KEY, permissions text)')
            self.c.execute('create table hosts (host_name text UNIQUE PRIMARY KEY, permissions text, version text)')
            
            self.c.execute('create index admin_name_index ON admins (admin_name)')
            self.c.execute('create index host_name_index ON hosts (host_name)')
            self.conn.commit()
            
        # populate cache    
        self.c.execute('select admin_name from admins')
        for a in self.c:
            self._admins.add( str(a[0]) )
            
        self.c.execute('select host_name from hosts')
        for a in self.c:
            self._hosts.add( str(a[0]) )
            
            
        
        
    def __del__(self):
        if self.conn:
            self.close()
        
            
    def close(self):
        self.conn.commit()
        self.conn.close()
        self.conn = None
     
        
    #---------------------------------------------------------------------------------------
    # Utility
    #
    def have_admin(self, admin_name):
        return admin_name in self._admins
    
    def have_host(self, host_name):
        return host_name in self._hosts

    #---------------------------------------------------------------------------------------
    # Admins
    #
    def add_admin(self, admin_name, permission_set):
        p = ','.join( permission_set )
        self.c.execute('insert into admins values (?,?)', (admin_name, p))
        self._admins.add( admin_name )
        self.conn.commit()
        
    def change_admin_permissions(self, admin_name, permission_set):
        p = ','.join( permission_set )
        self.c.execute('update admins set permissions=? where admin_name=?', (p, admin_name) )
        self.conn.commit()
        
    def remove_admin(self, admin_name):
        self.c.execute('delete from admins where admin_name=?', (admin_name,) )
        self._admins.remove( admin_name )
        self.conn.commit()
    
    def get_admin(self, admin_name):
        self.c.execute('select permissions from admins where admin_name=?', (admin_name,))
        result = self.c.fetchone()
        if result:
            return result[0]
        else:
            return None
        
    def list_admins(self):
        return list( self._admins )
    
    #---------------------------------------------------------------------------------------
    # hosts
    #
    def add_host(self, host_name, permission_set, version):
        p = ','.join( permission_set )
        self.c.execute('insert into hosts values (?,?,?)', (host_name, p, version))
        self._hosts.add( host_name )
        self.conn.commit()
        
    def change_host_permissions(self, host_name, permission_set):
        p = ','.join( permission_set )
        self.c.execute('update hosts set permissions=? where host_name=?', (p, host_name) )
        self.conn.commit()
        
    def remove_host(self, host_name):
        self.c.execute('delete from hosts where host_name=?', (host_name,) )
        self._hosts.remove( host_name )
        self.conn.commit()
    
    def get_host(self, host_name):
        self.c.execute('select permissions from hosts where host_name=?', (host_name,))
        result = self.c.fetchone()
        if result:
            return result[0]
        else:
            return None
        
    def list_hosts(self):
        return list( self._hosts )
    
    
    def update_host_version(self, host_name, version):
        self.c.execute('update hosts set version=? where host_name=?', (version, host_name) )
        self.conn.commit()

    def get_host_version(self, host_name):
        self.c.execute('select version from hosts where host_name=?', (host_name,))
        result = self.c.fetchone()
        if result:
            return result[0]
        else:
            return None
