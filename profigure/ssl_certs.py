import os
import os.path
from   twisted.internet import reactor, protocol, utils, defer, error

def path_find( cmd_name ):
    for p in os.environ['PATH'].split(':'):
        fp = os.path.join( os.path.expanduser(os.path.expandvars(p)), cmd_name )
        if os.path.exists( fp ):
            return fp


OPENSSL_PATH = path_find('openssl')


_cert_request_txt = '''ME
The Shire
Bag End
Hobbits
Baggins
Frodo
frodo@baggins.me
Gollum
Fellowship of the Ring
'''.split()

class SimpleProto (protocol.ProcessProtocol):
    
    def __init__(self):
        self.d = defer.Deferred()
        
        
    def connectionMade(self):
        pass
        
    def outReceived(self, data):
        #print 'Key Out: ', data
        pass
        
    def errReceived(self, data):
        #print 'Key Err: ', data
        pass
        
    def processExited(self, status):
        #print 'Key Exited with status: ', status.value
        if isinstance(status.value, error.ProcessDone):
            self.d.callback( None )
        else:
            self.d.errback( Exception('OpenSSL certificate generation failed') )



class CtxProto (SimpleProto):
    
    def __init__(self):
        SimpleProto.__init__(self)
        self.idx   = 0
        
        
    def outReceived(self, data):
        #print 'Out: ', data
        if data.endswith(']:'):
            #print 'Sending: ', self.lines[self.idx]
            self.transport.write( _cert_request_txt[self.idx] + '\n' )
            self.idx += 1
    
        

# Will ensure that ssl_key.pem and ssl_cert.pem exist
def gen_ssl_certs( output_dir ):
    
    key = os.path.join( output_dir, 'ssl_key.pem'  )
    csr = os.path.join( output_dir, 'ssl_csr.pem'  )
    crt = os.path.join( output_dir, 'ssl_cert.pem' )
    
    if os.path.exists( crt ):
        return defer.succeed( (key, crt) )
    
    orig_umask = os.umask(0077)
    
    pk = SimpleProto()

    reactor.spawnProcess(pk, OPENSSL_PATH, ('genrsa -out %s 1024' % key).split())
 
    drsa = pk.d

    def rsa_done(_):
        args = ('req -new -key %s -out %s' % (key,csr)).split()
        
        pp = CtxProto()
        
        reactor.spawnProcess(pp, OPENSSL_PATH, args, usePTY=True)
    
        return pp.d

    def req_done( status ):
        ps = SimpleProto()
        args = ('x509 -req -days 1095 -in %s -signkey %s -out %s' %(csr,key,crt)).split()
        reactor.spawnProcess(ps, OPENSSL_PATH, args)
        return ps.d

    drsa.addCallback( rsa_done )
    drsa.addCallback( req_done )
    drsa.addCallback( lambda _: (key,crt) )
    
    def reset_umask( _ ):
        os.umask( orig_umask )
        return _
    
    drsa.addBoth( reset_umask )
        
    return drsa


def test():
    d = gen_ssl_certs( '.' )

    def done( (key,crt) ):
        print 'Key: ', key
        print 'Crt: ', crt
        reactor.stop()

    d.addCallback(done)
    reactor.run()
