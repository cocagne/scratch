

import sys            
import os
import os.path
import shutil
import tempfile

from   OpenSSL import SSL

from   zope.interface import implements

from   twisted.spread            import pb
from   twisted.internet          import reactor, protocol, defer, address, base, ssl
from   twisted.internet.protocol import Factory

dp = os.path.dirname

sys.path.append( dp(dp(dp(os.path.abspath(__file__)))) )

from profigure import file_transfer, ssl_certs


class PError (pb.Error):
    pass


# Per-connection instance. Each connection is assigned a private temp directory that
# will be deleted when the connection closes.
class Connection (pb.Referenceable):
    
    def __init__(self, peer_addr, name, session_key, disconnect_func, peer_pb_if = None, temp_dir = None):

        self.session_key = session_key

        if temp_dir is None:
            self.temp_dir = tempfile.mkdtemp()
            self.del_temp = True
        else:
            self.temp_dir = temp_dir
            self.del_temp = False
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)
        
        self.peer_addr     = peer_addr
        self.peer          = None
        self.name          = name
        self.disconnect    = disconnect_func
        
        if peer_pb_if:
            self.remote_register_peer_interface( peer_pb_if )
        
        if self.peer:
            self.peer.callRemote('register_peer_interface', self)
        
        
    def __fini__(self):
        self._rm_tempdir()
        
        
    def _rm_tempdir(self):
        if self.del_temp and self.temp_dir:
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
            
            
    def _run_disconnect_callbacks(self, _):
        self.on_disconnect()
        self._rm_tempdir()
        
            
    def on_disconnect(self):
        print 'Disconnected!'
        
        
    def on_connect(self):
        pass
    
        
    def remote_register_peer_interface(self, pb_peer):
        self.peer = pb_peer
        
        self.peer.notifyOnDisconnect( self._run_disconnect_callbacks )
        
        self.on_connect()
            
        
    def send_file(self, filename):
        
        base_name   = os.path.basename(filename)
        file_size   = os.stat( filename ).st_size
        aes_passwd  = self.session_key[:16]
        
        file_id, sha1_digest, aes_IV, d = file_transfer.main_server.serveFile( aes_passwd, filename, 10 )
        
        print 'Sending: ', base_name, file_size
        dsend =  self.peer.callRemote('get_file', file_transfer.main_server.port, base_name, file_id, file_size, sha1_digest, aes_IV)
        
        def cvt( arg ):
            if arg:
                print '***********************************'
                raise Exception( arg )
        
        dsend.addCallback( cvt )
        
        return dsend

    
    # returns None on success, Error message on failure
    def remote_get_file(self, port, file_name, file_id, file_size, sha1_digest, aes_IV):
        print 'Retreiving file: ', file_name
        
        d = file_transfer.get_file( self.peer_addr.host, 
                                    port,
                                    file_id,
                                    sha1_digest,
                                    self.session_key[:16],
                                    aes_IV,
                                    file_size,
                                    os.path.join( self.temp_dir, file_name ) )
                                        
        d.addErrback( lambda err: err.getErrorMessage() )

        return d
    


        
#------------------------------------------------------------------------------        
# No Authentication
#
class AddrBroker (object):

    implements(pb.IPBRoot)
    
    def rootObject(self, broker):
        return Connection(broker.factory.current_addr, 'UNKNOWN')

    
class PBSFProxy (pb.PBServerFactory):
    
    def buildProtocol(self, addr):
        self.current_addr = addr
        broker = pb.PBServerFactory.buildProtocol(self, addr)
        self.current_addr = None
        return broker

    


