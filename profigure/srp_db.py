import os.path
import srp
import re
import sqlite3

comment_re         = re.compile('^\s*#')
whitespace_only_re = re.compile('^\s*$')


class SRPError (Exception):
    pass


class SrpDB (object):
       
    def close(self):
        raise NotImplementedError
    
    def add_user(self, username, password):
        raise NotImplementedError
        
    def remove_user(self, username):
        raise NotImplementedError
    
    def get_sv(self, username):
        raise NotImplementedError

    
    
class SqliteSrpDB (SrpDB):
    
    def __init__(self, filename):
        self.filename = filename
        
        create_db = not os.path.exists( self.filename )
        
        self.conn = sqlite3.connect( self.filename )
        self.c    = self.conn.cursor()
        
        if create_db:
            self.c.execute('create table users (username text UNIQUE PRIMARY KEY, salt text, verifier text)')
            self.c.execute('create index name_index ON users (username)')
            self.conn.commit()
        
        
    def __del__(self):
        if self.conn:
            self.close()
        
            
    def close(self):
        self.conn.commit()
        self.conn.close()
        self.conn = None
        
        
    def add_user(self, username, password):
        s,v = srp.gen_sv( username, password )
        self.add_user_sv_hex( username, hex(s), hex(v) )

        
    def add_user_sv_hex(self, username, s_hex, v_hex):
        try:
            self.c.execute('insert into users values (?,?,?)', (username, s_hex, v_hex) )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise SRPError('User name already exists: %s' % username)
        
        
    def change_password(self, username, password):
        s,v = srp.gen_sv( username, password )
        self.c.execute('update users set salt=?, verifier=? where username=?', (hex(s), hex(v), username) )
        self.conn.commit()
        
        
    def remove_user(self, username):
        self.c.execute('delete from users where username=?', (username,) )
        self.conn.commit()
    
        
    def get_sv(self, username):
        self.c.execute('select salt, verifier from users where username=?', (username,))
        result = self.c.fetchone()
        if result:
            return ( long(result[0],16), long(result[1],16) )
        else:
            return (None, None)

        
    
    

class SimpleSrpDB (SrpDB):
    
    def __init__(self, filename):
        self.filename = filename
        
        self.db        = dict() # maps: username => (salt, verifier)
        self._comments = list()
        
        self.load_db()
    
    def close(self):
        pass
        
    def load_db(self):
        if not os.path.exists( self.filename ):
            return
        
        with open(self.filename,'r') as fobj:
            for line in fobj:
                if comment_re.match(line) or whitespace_only_re.match(line):
                    self._comments.append(line)
                    continue
                tpl = line.split(':')
                if len(tpl) != 3:
                    print 'Corrupt Line in SRP Database:\n     ', line
                    continue
                username, hex_salt, hex_verifier = tpl
                
                self.db[ username ] = (long(hex_salt,16), long(hex_verifier,16))
                
                
    def write_db(self):
        with open(self.filename,'w') as fobj:
            for cmt in self._comments:
                fobj.write(cmt)
            for u,(s,v) in self.db.iteritems():
                fobj.write( '%s:%s:%s\n' % (u, hex(s), hex(v)) )
                
                
    def add_user(self, username, password):
        self.db[ username ] = srp.gen_sv( username, password )
        self.write_db()
        
        
    def remove_user(self, username):
        if username in self.db:
            del self.db[ username ]
            self.write_db()
    
    def get_sv(self, username):
        return self.db.get( username, (None,None) )
        
        
        
if __name__ == '__main__':
    import sys
    
    def usage():
        print 'python srp_db.py [add|remove|change|show] <username> [password]'
    
    db = SqliteSrpDB( 'srp_db.sqlite' )
    
    if len(sys.argv) == 4:
        if sys.argv[1] == 'add':
            db.add_user( sys.argv[2], sys.argv[3] )
        elif sys.argv[1] == 'change':
            db.change_password( sys.argv[2], sys.argv[3] )
        else:
            usage()
    elif len(sys.argv) == 3:
        if sys.argv[1].startswith('del') or sys.argv[1].startswith('rem'):
            db.remove_user( sys.argv[2] )
        elif sys.argv[1] == 'show':
            s,v = db.get_sv( sys.argv[2] )
            if s: s = hex(s)
            if v: v = hex(v)
            print 'User: %s, Salt: %s, Verifier: %s' % (sys.argv[2], s, v)
        else:
            usage()
    else:
        usage()
        
        
        
        
        
        
        
