import sys
import os
import os.path
import tempfile
import tarfile
import traceback
import shutil
import atexit
import time

from   twisted.spread            import pb
from   twisted.internet          import reactor, protocol, defer, utils, error

from   twisted.application       import service
from   twisted.python            import log
from   twisted.python.log        import ILogObserver, FileLogObserver
from   twisted.python.logfile    import LogFile

this_file    = os.path.abspath( __file__ )
this_dir     = os.path.dirname( this_file )

sys.path.append( this_dir )

# Only dependencies are srp.py & pb_srp.py
import pb_srp



class ConfigError (Exception):
    pass



def get_application ():
    
    config_dir = '/etc/profigure' if not os.path.exists('profigure.conf') else '.'
        
    app = service.Application('Profigure Host')
        
    app.client_conf = ClientConfig( config_dir )
    
    log_dir = app.client_conf.log_dir
    
    if not log_dir:
        log_dir = '/tmp'
    
    lf = LogFile( 'profigure_host_%s.log' % app.client_conf.hostname, log_dir, defaultMode=0640 )
        
    app.setComponent(ILogObserver, FileLogObserver(lf).emit )
    
    return app



def parse_line( l ):
    l = l.lower()
    
    tpl = [ x for x in l.split() if x and not x == '=' ]
    
    one = tpl[0] if len(tpl) > 0 else None
    two = tpl[1] if len(tpl) > 1 else None
    
    return one, two


        
class ClientConfig (object):
    
    def __init__(self, config_dir):
        
        self.config_dir      = config_dir
        self.hostname        = None
        self.password        = None
        self.master_hostname = None
        self.master_port     = None
        self.log_dir         = None
        
        pwd_file = os.path.join(config_dir, 'passwd')
        cfg_file = os.path.join(config_dir, 'profigure.conf')
        
        if not os.path.exists( pwd_file ):
            raise ConfigError('Host not initialized. Missing required file: %s' % pwd_file)
        
        if not os.path.exists( cfg_file ):
            raise ConfigError('Host not initialized. Missing required file: %s' % cfg_file)

        try:
            with open(pwd_file, 'r') as f:
                self.password = f.read()
        except Exception, e:
            raise ConfigError('Failed to read password file %s: %s' % (pwd_file, str(e)))
        
        if not self.password:
            raise ConfigError('Password file is empty')
        
        # Read connection & logging values from the config file.
        with open(cfg_file, 'r') as f:
            for l in f:
                l = l.strip()
                    
                if l and not l.startswith('#'):
                    
                    key, val = parse_line( l )
                    
                    if key == 'master':
                        if self.master_hostname:
                            raise ConfigError('Only one master may be defined')
                        try:
                            self.master_hostname, self.master_port = val.split(':')
                            self.master_port = int(self.master_port)
                        except Exception:
                            raise ConfigError('Invalid master definition. Format is "MASTER = hostname:port"')
                        
                    elif key == 'hostname':
                        if self.hostname:
                            raise ConfigError('Only one name for the host is permitted')
                        self.hostname = val
                        
                    elif key == 'log_dir':
                        self.log_dir = val
                                                
        if not self.master_hostname: raise ConfigError('Missing required entry: "MASTER = hostname:port"')
        if not self.master_port:     raise ConfigError('Missing required entry: "MASTER = hostname:port"')
        if not self.hostname:        raise ConfigError('Missing required entry: "HOSTNAME = hostname"')
        
        self.connect()
        
        
        
    def connect(self, attempt=1):
        def makeConn( peer_addr, username, session_key, disconnect_func, peer_pb_if ):
            return ClientConnection( self, peer_addr, username, session_key, disconnect_func, peer_pb_if )
        
        d = pb_srp.srp_connect( self.master_hostname, self.master_port, self.hostname, self.password, makeConn )
        
        def retry( _ ):
            reactor.callLater( min(15.0, 3 * attempt), self.connect, attempt + 1 )
            
            
        d.addErrback( retry )
        #d.addErrback( lambda _: reactor.callLater(3.0, self.connect) )

        
        
        
class ClientConnection(pb.Referenceable):
    
    def __init__(self, client_conf, peer_addr, username, session_key, disconnect_func, peer_pb_if):
        
        self.client_conf     = client_conf
        self.peer_addr       = peer_addr
        self.username        = username
        self.session_key     = session_key
        self.disconnect_func = disconnect_func
        self.peer            = peer_pb_if
        
        self.temp_tar        = tempfile.TemporaryFile()
        self.temp_dir        = tempfile.mkdtemp()
        
        atexit.register( self.cleanup )
        
        self.peer.notifyOnDisconnect( self.on_disconnect )
        
        self.peer.callRemote( "get_client_code", self )
        
        print 'Connection Established'
        

    def cleanup(self):
        if os.path.exists( self.temp_dir ):
            shutil.rmtree(self.temp_dir)
        
            
    
        
            
    def on_disconnect(self, *args):
        self.cleanup()
        # TODO: Restart the daemon process. May just be able to exec() the new process and
        #       thereby retain the current PID. Just be sure all open handles are closed.
        if reactor.running:
            reactor.stop()
        
        

    def remote_append_code(self, data, done):
        self.temp_tar.write( data )
        
        if done:
            self.temp_tar.seek(0)
            tf = tarfile.open( fileobj=self.temp_tar, mode='r:gz' )
            
            tf.extractall( path = self.temp_dir )
            
            self.temp_tar = None # delete temp file
            tf            = None
        
            sys.path.append( self.temp_dir )
            
            # Import host & create connection object.
            try:
                from profigure import host
                host.start_host( self.client_conf.config_dir, 
                                 self.peer_addr, 
                                 self.username, 
                                 self.session_key, 
                                 self.disconnect_func, 
                                 self.peer )
            except Exception, e:
                traceback.print_exc()
                print 'FAILED TO INITALIZE HOST'
                print 'Delaying 10 seconds then restarting'
                reactor.callLater(10.0, reactor.stop)










# ---- Setup for twistd ----

class RestartService (service.Service):
    is_restarting = False
    
    def stopService(self):
        if self.is_restarting:
            print '********** SKIPPING REDUNDANT CALL **********'
            return
        self.is_restarting = True
        
        print '************* RESTARTING *****************'
        ppid = os.getpid()
        
        if os.fork() == 0:
        
            try:
                while True:
                    os.kill(ppid, 0)
                    time.sleep(0.03)
            except:
                # parent process is dead
                
                # Close all open file descriptors above 0,1,2. 
                # twisted may create a few behind-the-scenes so use 30 as a guess at
                # the upper limit
                os.closerange(3,30)
                
                cmd  = '/etc/init.d/profigure-client'
                args = [cmd, 'restart']
                
                for a in sys.argv:
                    if 'noy' in a: # testing in foreground
                        cmd  = sys.argv[0]
                        args = sys.argv
                    
                os.execv(sys.argv[0], sys.argv)

log.startLogging( sys.stdout )
application = get_application()
sc          = service.IServiceCollection(application)

restarter = RestartService()
restarter.setName('Auto-Restart')
restarter.setServiceParent(sc)