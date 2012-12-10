from twisted.spread   import pb
from twisted.internet import reactor, ssl, base, address
from twisted.python   import failure

from OpenSSL        import SSL
from zope.interface import implements

import traceback

import srp

    
#------------------------------------------------------------------------------
# Client
#
def client_login( host, port, username, password, use_ssl=False ):
    f = pb.PBClientFactory()
    f.noisy = False # suppress logging message for every start/stop & connection
    
    if use_ssl:
        reactor.connectSSL(host, port, f, ssl.ClientContextFactory())
    else:
        reactor.connectTCP(host, port, f)
        
    d = f.getRootObject()
    d.addCallback(_pb_srp_connected, username, password, f.disconnect)
    return d
    
    
def _pb_srp_connected(login_mgr, username,  password, disconnect_func):
    #print 'PB SRP Login as:', username
    
    c = srp.Client( username, password )
    I,A = c.step1()
    
    d = login_mgr.callRemote('login', I, srp.long_to_bytes(A))
    
    def step2( ((s,B), validator) ):
        
        if s is None or B is None or validator is None:
            raise Exception('User Authentication Failed')
        
        s = srp.bytes_to_long(s)
        B = srp.bytes_to_long(B)
        
        M = c.step2( (s,B) )
        
        return validator.callRemote('validate_user', M)
    
    def step3( (HAMK, pb_if) ):
        c.validate_server( HAMK )
        return pb_if
    
    def result( arg ):
        if isinstance( arg, failure.Failure ):
            print 'PB SRP Login FAILURE as "%s":' % username, arg.getErrorMessage()
            return arg
        else:
            print 'PB SRP Login success as "%s".' % username
            return (arg, srp.long_to_bytes(c.K), disconnect_func)
    
    d.addCallback( step2 )
    d.addCallback( step3 )
    d.addBoth( result )
    
    return d
    

#------------------------------------------------------------------------------
# Server
#
class SRPLoginManager (pb.Root):
    def __init__(self, avatar_factory, get_user_sv = None):
        self.get_user_sv    = get_user_sv
        self.avatar_factory = avatar_factory
        
    def lookup_user_sv(self, username):
        if self.get_user_sv:
            return self.get_user_sv( username )
        else:
            raise NotImplementedError
        
    def remote_login(self, username, A):
        try:
            A = srp.bytes_to_long(A)
            v = SRPValidator( self.avatar_factory, SimpleSRP(username, *self.lookup_user_sv(username)), username, A)
            return v.challenge, v
        except Exception, e:
            traceback.print_exc()
            return 'Authentication Failed: ' + str(e), None
            


class SimpleSRP (srp.Server):
    def __init__(self, username, s, v):
        self.username = username
        self.s        = s
        self.v        = v
        
    def get_user_sv(self, username):
        assert self.username == username
        return self.s,self.v

    
        
class SRPValidator (pb.Referenceable):
    
    def __init__(self, avatar_factory, srp_server, username, A):
        self.username       = username
        self.srp_server     = srp_server
        self.avatar_factory = avatar_factory
        
        s,B = srp_server.step1( (username, A) )
        
        self.challenge  = (srp.long_to_bytes(s), srp.long_to_bytes(B))
        

    def remote_validate_user(self, user_M):
        try:
            HAMK = self.srp_server.validate_user( user_M )
            print 'PB SRP Login succeeded for:', self.username
            pb_obj = self.avatar_factory( self.username, srp.long_to_bytes(self.srp_server.K) )
            return HAMK, pb_obj
        except Exception,e:
            traceback.print_exc()
            print 'PB SRP Login failed for "%s":' % self.username, str(e)
            return (None,None)
    
#--------------------------------------------------------------------------------------------------
# Connection Helpers
#
class SRPAddrBroker (object):

    implements(pb.IPBRoot)
    
    def __init__(self, avatar_factory):
        self.avatar_factory = avatar_factory
    
    def rootObject(self, broker):
        # Save in local variable
        current_addr    = broker.factory.current_addr
        
        def disconnect_func():
            broker.transport.loseConnection()
        
        def addr_wrap( username, session_key ):
            return self.avatar_factory(current_addr, username, session_key, disconnect_func)
        
        return SRPLoginManager( addr_wrap, broker.factory.lookup_user_sv )

    
    
class SRPFactoryProxy (pb.PBServerFactory):
    
    def __init__( self, srp_database, avatar_factory = None):
        pb.PBServerFactory.__init__(self, SRPAddrBroker( avatar_factory ))
        import srp
        import srp_db
        
        self.db = srp_database
        self.noisy = False # suppress logging message for every start/stop & connection
    
    def lookup_user_sv(self, username):
        return self.db.get_sv( username )
    
    def buildProtocol(self, addr):
        self.current_addr = addr
        broker = pb.PBServerFactory.buildProtocol(self, addr)
        self.current_addr = None
        return broker
#-------------------------------------------------------------

    
# Required avatar_factory signature: ( peer_address, username, session_key )
#
def accept_connections( base_port, avatar_factory, srp_database, ssl_dir ):
    import ssl_certs
    dcerts = ssl_certs.gen_ssl_certs( ssl_dir )
    
    def done( (ssl_key, ssl_cert) ):        
        cf   = ssl.DefaultOpenSSLContextFactory(ssl_key, ssl_cert, sslmethod=SSL.TLSv1_METHOD)
        p    = reactor.listenSSL( base_port, SRPFactoryProxy( srp_database, avatar_factory ), cf )
        addr = p.getHost()
        print 'Master server running on port %d with certs: ' % addr.port, ssl_key, ssl_cert
        
        
    dcerts.addCallback( done )
    

    
# ConnectionInstanceFactory signature: ( peer_address, username, session_key, disconnect_func, root_obj )
#
def srp_connect( host, port, username, password, ConnectionInstanceFactory ):
    resolver = base.ThreadedResolver( reactor )
    dres     = resolver.getHostByName( host )
    
    def resolved( ip_addr ):
        
        d = client_login( host, port, username, password, use_ssl=True )

        def gotRoot( (root, session_key, disconnect_func) ):
            addr = address.IPv4Address('TCP', ip_addr, port)
            return ConnectionInstanceFactory( addr, username, session_key, disconnect_func, root )
            
        def failed( msg ):
            if not 'Connection refused' in msg.getErrorMessage():
                print 'Failed to login: ', msg.getErrorMessage()
            return msg
            
        d.addCallbacks( gotRoot, failed )
        
        return d
        
    dres.addCallback( resolved )
    
    return dres



#--------------------------------------------------------------------------------------------------
# test_code
#            
def test_server():
    class AuthConn(pb.Referenceable):
        def __init__(self, username):
            self.username = username
        
        def remote_woo(self, arg):
            print 'Woo!  ', arg

    udict = srp.get_test_dict()
    
    def get_user_sv( username ):
        return udict[ username ]
            
    slm = SRPLoginManager( AuthConn, get_user_sv )
    
    reactor.listenTCP(2222, pb.PBServerFactory(slm))
    reactor.run()

    
def test_client():
    
    d = client_login( '127.0.0.1', 2222, 'testuser', 'testpassword' )
    
    def done( (pb_if, session_key) ):
        print 'Login succeeded'
        pb_if.callRemote('woo', 'hoooo!')
        
    d.addCallback( done )
    reactor.run()
