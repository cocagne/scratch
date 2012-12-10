# Intent: Protocol for securely transferring files between systems.
#
# Assumptions:
#    This approach relies upon both ends sharing an AES password and upon
#    an external, secure mechanism for transfering generated file ids and
#    AES initialization vectors. In the Profigure code, this is done via a 
#    Perspective Broker connection running on top of SSL.
#
# Approach:
#    1. Files are made available via FileTransferServerFactory.serve_file()
#    2. The resulting file_id, sha1_digest, & aes_IV are sent to the destination machine
#    3. The destination machine connects to the file server and sends it the file_id it's interested in
#    4. The server then sends the client the AES-encrypted content of the file
#    5. On complete reception, the client checks the decrypted files' SHA digest against what the
#       server said it should be. If they match, file successfully transferred. Otherwise, it's a failure
#
# Security Concerns:
#
#    This approach does not guard against Man-in-the-Middle attacks. However, at best, an
#    attacker could gain the AES-encrypted file content but would lack the AES password
#    and CBC initialization vector.
#
#    The server will give the AES-encrypted file to the first connection requesting it.
#    As this is a random 8-byte string coming from os.urandom() it should be impossible to
#    "guess" remotely but a MiM attack could steal it and turn around to request the file
#    from the server. Packet sniffers would be useless for this protocol as the file ids are
#    discarded immediately on first use.
#
#    At best, the MiM could cause a Denial of Service by causing the 'one-chance' file transfer
#    to fail each time for the recipient.
#
#
import os
import hashlib
import tempfile

from   Crypto.Cipher import AES

from   twisted.internet          import reactor, protocol, defer, ssl
from   twisted.protocols         import basic
from   twisted.internet.protocol import ClientFactory

from profigure import ssl_certs

# Set to main file server instance
main_server = None

def start_main_server():
    global main_server
        
    main_server = FileTransferServerFactory()

    p = reactor.listenTCP( 0, main_server )
        
    addr = p.getHost()
        
    main_server.port = addr.port
        
    print 'Running File Transfer server on port %d' % main_server.port
        
    return defer.succeed(None)


def get_file(host, port, file_id, sha1_digest, aes_passwd, aes_IV, file_size, dest_file):
    # TODO: Switch to tempfile.mkstemp
    
    afd  = AESFileDecrypter(dest_file, aes_passwd, aes_IV, file_size)
    d    = defer.Deferred()
    
    class Fact(ClientFactory):
        def buildProtocol(self, addr):
            return FileTransferClientProtocol(file_id, afd, d)
        def clientConnectionFailed(self, connector, reason):
            d.errback(reason)

    def done(_):
        if afd.sha_digest != sha1_digest:
            raise Exception('SHA Digest mismatch')
        return _
            
    def closeit( _ ):
        afd.close()
        return _
    
    d.addCallback( done )
    d.addBoth( closeit )
            
    reactor.connectTCP( host, port, Fact() )

    return d



def get_file_hash(file_name):

    sha = hashlib.sha1()
        
    with open(file_name, 'r') as fobj:
        while True:
            data = fobj.read( 16 * 1024 )
            if not data:
                break
            sha.update(data)

                
    return sha.digest()



class AESFile(object):
    
    def __init__(self, filename, aes_passwd, aes_IV, mode, file_size):
        assert len(aes_IV) == AES.block_size
        self.crypt     = AES.new(aes_passwd, AES.MODE_CBC, aes_IV)
        self.fobj      = open(filename, mode)
        self.file_size = file_size
        self.npad      = AES.block_size - (self.file_size % AES.block_size)
        if self.npad == 16:
            self.npad = 0
            
    def close(self):
        self.fobj.close()
        

        
class AESFileEncrypter(AESFile):
    
    def __init__(self, filename, aes_passwd, aes_IV):
        AESFile.__init__(self, filename, aes_passwd, aes_IV, 'r', os.lstat(filename).st_size)
        self.nread = 0

            
    def read(self, chunk_size):
        assert chunk_size % AES.block_size == 0
        d = self.fobj.read( chunk_size )
        
        if not d:
            return d
                
        self.nread += len(d)
        
        if len(d) < chunk_size:
            assert self.nread == self.file_size

            d = d + '\0'*self.npad
            
        return self.crypt.encrypt( d )
        
    
        
    
class AESFileDecrypter(AESFile):
    
    WSIZE = 16 * 1024
    
    def __init__(self, filename, aes_passwd, aes_IV, file_size):
        AESFile.__init__(self, filename, aes_passwd, aes_IV, 'w', file_size)
        self.nrecv      = 0
        self.buff       = ''
        self.done       = False
        self.sha_digest = None
        self.sha        = hashlib.sha1()
        
        
    def _write(self, data):
        self.sha.update(data)
        self.fobj.write( data )
        
        
    def write(self, data):
        assert not self.done

        self.nrecv += len(data)
        
        self.buff = self.buff + data

        while len(self.buff) >= self.WSIZE:
            self._write( self.crypt.decrypt( self.buff[:self.WSIZE] ) )
            self.buff = self.buff[self.WSIZE:]
            
        if self.nrecv == self.file_size + self.npad:
            if self.npad:
                self._write( self.crypt.decrypt( self.buff )[:-self.npad] )
            else:
                self._write( self.crypt.decrypt( self.buff ) )
                        
            self.done       = True
            self.sha_digest = self.sha.digest()
    
    

class FileTransferServerFactory ( protocol.Factory ):
    
    def __init__(self):
        
        self.pending  = dict() # maps 8-byte file_id => (file_name, deferred, [timeout | None])
        self.id_len   = 8
        self.port     = None   # set after creation

    
    # Returns: (file_id, sha1_digest, aes_IV, d)
    #
    def serveFile(self, aes_passwd, file_name, connect_timeout = None):
        d           = defer.Deferred()
        aes_IV      = os.urandom( AES.block_size )
        file_id     = os.urandom( self.id_len )
        sha1_digest = get_file_hash( file_name )
        afe         = AESFileEncrypter( file_name, aes_passwd, aes_IV )
        
        def cleanup(_):
            afe.close()
            return _
                
        d.addBoth( cleanup )
            
        def time_out():
            if file_id in self.pending:
                del self.pending[ file_id ]
                d.errback(Exception('Time Out'))
                
        dcall = None if connect_timeout is None else reactor.callLater(connect_timeout, time_out)
        
        self.pending[ file_id ] = (afe, d, dcall)
        
        return (file_id, sha1_digest, aes_IV, d)
        
        
        
    # Raises KeyError if the aes_passwd is invalid
    def connectedFor(self, file_id):
        afe, d, dcall = self.pending[ file_id ]
        del self.pending[ file_id ]
        dcall.cancel()
        return afe, d
        
        
    def buildProtocol( self, addr ):
        p = FileTransferServerProtocol()
        p.factory = self
        return p

    
    
class FileTransferServerProtocol ( protocol.Protocol ):
    
    id_buff    = ''
    
#    def connectionMade(self):
#        print 'FT Server Connect!'
                
    def dataReceived(self, data):

        self.id_buff = self.id_buff + data
        
        if len(self.id_buff) < self.factory.id_len:
            return
        
        try:
            
            self.send_file( *self.factory.connectedFor( self.id_buff ) )
            
        except KeyError:
            # Authorization failed
            self.transport.loseConnection()
            return
        
        
    def send_file(self, afe, deferred):

        def cleanup(_):
            self.transport.loseConnection()
            return _
        
        d = basic.FileSender().beginFileTransfer( afe, self.transport )
        
        d.addBoth( cleanup )
        
        d.chainDeferred( deferred )
        
    
        
class FileTransferClientProtocol (protocol.Protocol):
    
    def __init__(self, file_id, afd, deferred):
        self.file_id       = file_id
        self.afd           = afd
        self.deferred      = deferred
        
    def connectionMade(self):
        self.transport.write( self.file_id )
        
    def connectionLost(self, reason):
        if self.afd.done:
            self.deferred.callback(None)
        else:
            self.deferred.errback(reason)
            
    def dataReceived(self, data):
        self.afd.write(data)
        
        
        

        
        
        
        
    
