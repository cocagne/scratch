  # N    A large safe prime (N = 2q+1, where q is prime)
  #      All arithmetic is done modulo N.
  # g    A generator modulo N
  # k    Multiplier parameter (k = H(N, g) in SRP-6a, k = 3 for legacy SRP-6)
  # s    User's salt
  # I    Username
  # p    Cleartext Password
  # H()  One-way hash function
  # ^    (Modular) Exponentiation
  # u    Random scrambling parameter
  # a,b  Secret ephemeral values
  # A,B  Public ephemeral values
  # x    Private key (derived from p and s)
  # v    Password verifier

import os
import hashlib
import binascii



#N = 0xec98646f269480bae07c983e1c5938dd6a645275370cd31bd9dad0b0a4265137815c8e38b38cae8bbf68381e77e88d21ecb22d7c3300d065467c9211e9251027ae50de0a677c5914361e14c7cf6aeafb0bebf6eb3474dddafbb38f916a30098bf6c57e9772738f177f1b732080179a6cdc9b0ad88c1a48ca58c22aec92d1a953L;
N = 0xAC6BDB41324A9A9BF166DE5E1389582FAF72B6651987EE07FC3192943DB56050A37329CBB4A099ED8193E0757767A13DD52312AB4B03310DCD7F48A9DA04FD50E8083969EDB767B0CF6095179A163AB3661A05FBD5FAAAE82918A9962F0B93B855F97993EC975EEAA80D740ADBF4FF747359D041D5C33EA71D281E446B14773BCA97B43A23FB801676BD207A436C6481F1D2B9078717461A5B9D32E688F87748544523B524B0D57D5EA77A2775D2ECFA032CFBDBF52FB3786160279004E57AE6AF874E7303CE53299CCC041C7BC308D82A5698F3A8D0C38271AE35F8E9DBFBB694B5C803D89F7AE435DE236D525F54759B65E372FCD68EF20FA7111F9E4AFF73;
g = 2;


def get_random_long( nbits ):
    return bytes_to_long( os.urandom( nbits/8) )


def bytes_to_long(s):
    return long(binascii.hexlify(s), 16)

def long_to_bytes(n):
    if isinstance(n, basestring):
        return n
    s = "%x" % n
    if len(s) % 2 == 1:
        s = '0' + s
    return binascii.unhexlify(s)



def H( s1, s2 = ''):
    if isinstance(s1, (long, int)):
        s1 = long_to_bytes(s1)
    if s2 and isinstance(s2, (long, int)):
        s2 = long_to_bytes(s2)
    s = s1 + s2
    return long(hashlib.sha1(s).hexdigest(), 16)


HNxorHg = hashlib.sha1( long_to_bytes(H(N) ^ H(g)) ).digest()


def gen_x( salt, username, password ):
    return H( salt, H( username + ':' + password ) )
    
    
class Safeguard (Exception):
    pass

class AuthFailed (Exception):
    pass
  
class Server (object):
    
    def get_user_sv(self, username):
        raise NotImplementedError
    
    def step1(self, (I,A) ):
        # SRP-6a safety check
        if (A % N) == 0:
            raise Safeguard()
            
        self.I = I
        self.A = A
        s,v    = self.get_user_sv( I )
        self.s = s
        self.v = v
        self.b = get_random_long(256)
        self.k = H(N, g)
        self.B = (self.k*self.v + pow(g, self.b, N)) % N
        self.u = H(self.A, self.B)

        return (self.s, self.B)
        
    def step2(self):
        self.S = pow(self.A*pow(self.v, self.u, N ), self.b, N)
        self.K = H(self.S) 
        
        h = hashlib.sha1()
        h.update( HNxorHg )
        h.update( hashlib.sha1( self.I ).digest() )
        for n in (self.s, self.A, self.B, self.K):
            h.update( long_to_bytes(n) )
    
        self.M = h.digest()
        
    def validate_user(self, user_M):
        self.step2()
        
        if self.M == user_M:
            h = hashlib.sha1()
            for n in (self.A, self.M, self.K):
                h.update( long_to_bytes(n) )
            return h.digest()
        else:
            raise AuthFailed()
        #print 'Server K: ' + hex(self.K)
        
        
        
class Client (object):
    def __init__(self, username, password):
        self.I = username
        self.p = password
        
    def step1(self):
        self.a = get_random_long(256)
        self.A = pow(g, self.a, N)
        return (self.I, self.A)
        
    def step2(self, (s,B)):
    
        # SRP-6a safety check
        if (B % N) == 0:
            raise Safeguard()
            
        self.s = s
        self.B = B
        
        self.k = H( N, g )
        self.u = H( self.A, self.B )
        
        # SRP-6a safety check
        if self.u == 0:
            raise Safeguard()
        
        self.x = gen_x( self.s, self.I, self.p )
        
        v = pow(g, self.x, N)
        
        self.S = pow((self.B - self.k*v), (self.a + self.u*self.x), N)
        self.K = H(self.S)

        h = hashlib.sha1()
        h.update( HNxorHg )
        h.update( hashlib.sha1( self.I ).digest() )
        for n in (self.s, self.A, self.B, self.K):
            h.update( long_to_bytes(n) )
    
        self.M = h.digest()

        return self.M
    
    def validate_server(self, server_HAMK):
        h = hashlib.sha1()
        for n in (self.A, self.M, self.K):
            h.update( long_to_bytes(n) )
        HAMK = h.digest()
        
        if HAMK != server_HAMK:
            raise AuthFailed( 'Server Validation Failed' )
        
        #print 'Client K: ' + hex(self.K)
        
        

def gen_sv( username, password ):
    s = get_random_long(32)
    x = gen_x( s, username, password )
    v = pow(g, x, N)

    return (s,v)

        
        
        
def get_test_dict():
    users = { 'testuser' : "testpassword" }
    
    udict = {}
    for username, clearpass in users.iteritems():
        s = get_random_long(32)
        x = gen_x( s, username, clearpass )
        v = pow(g, x, N)
        udict[ username ] = (s,v)
        
    return udict
        
        
if __name__ == '__main__':
    users = { 'testuser' : "testpassword" }
    
    udict = {}
#    for username, clearpass in users.iteritems():
#        s = get_random_long(32)
#        x = gen_x( s, username, clearpass )
#        v = pow(g, x, N)
#        udict[ username ] = (s,v)

    udict = get_test_dict()

    class TestServer(Server):
        def get_user_sv(self, username):
            return udict[ username ]
        
    NITER = 5
    import time
    start = time.time()
    for i in range(0,NITER):
        c = Client( 'testuser', 'testpassword' )
        s = TestServer()
        
        c1 = c.step1()
        s1 = s.step1( c1 )
        M = c.step2( s1 )
        HAMK = s.validate_user( M )
        c.validate_server( HAMK )
    duration = time.time() - start
    print 'Time per call: ', duration/NITER
