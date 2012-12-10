import sys
import os
import os.path

from   twisted.spread            import pb
from   twisted.internet          import reactor, protocol, defer, utils, error

from   twisted.application       import service
from   twisted.python.log        import ILogObserver, FileLogObserver
from   twisted.python.logfile    import LogFile

from   profigure            import connection, file_transfer, pro_conf
from   profigure.connection import PError



this_file    = os.path.abspath( __file__ )
this_dir     = os.path.dirname( this_file )
applier_cmd  = os.path.join( this_dir, 'applier' )

            

def start_host(config_dir, peer_addr, username, session_key, disconnect_func, peer_pb_if):
    
    dft = file_transfer.start_main_server()
        
    def start(_):
        return MasterConnection( config_dir, peer_addr, username, session_key, disconnect_func, peer_pb_if )
    
    dft.addCallback( start )
        
    return dft

    
        
class MasterConnection(connection.Connection):
    
    def __init__(self, config_dir, peer_addr, username, session_key, disconnect_func, peer_pb_if):
        
        connection.Connection.__init__( self, peer_addr, username, session_key, disconnect_func, peer_pb_if )

        print '**** Connected to Master ****'
        
        cfg_file = os.path.join(config_dir, 'profigure.conf')

        try:
            self.config = pro_conf.ProfigureConf(cfg_file, True)
        except pro_conf.ConfigError, e:
            raise pro_conf.ConfigError('Error in %s: %s' % (cfg_file, str(e)))
        
        abs_cfg_file = os.path.abspath(cfg_file)
        
        if abs_cfg_file == '/etc/profigure/profigure.conf':
            self.root_dir = '/'
        else:
            self.root_dir = os.path.dirname( abs_cfg_file )
        
        self.conf_dir  = os.path.join(self.root_dir, 'etc/profigure')
        self.rev_file  = os.path.join(self.conf_dir, 'rev_number')
        
        if '~' in self.root_dir:
            self.root_dir = os.path.expanduser(self.root_dir)
        
        os.umask(0022)
        
        if not os.path.exists( self.conf_dir ):
            os.makedirs( self.conf_dir )
        
        
        
    def get_version(self):
        if os.path.exists( self.rev_file ):
            with open(self.rev_file, 'r') as f:
                return f.read().strip()
        else:
            return ''
        
        
        
    def set_version(self, rev_number):
        with open(self.rev_file, 'w') as f:
            f.write(rev_number)
        
            
        
    def on_disconnect(self):
        print 'Disconnected from Master'

        
    #----------------------------------------------------------------
    #                 Remote Interface
    #----------------------------------------------------------------

    
    def remote_ping(self):
        print '*** PING ***'

        
    def remote_restart_client_daemon(self):
        
        # Sometimes duplicate restart requests will arrive. Ignore
        # subsequent ones 
        if hasattr(self, 'restarting'):
            return
        else:
            self.restarting = True
            
        print '*** Restart Requested ***'
        
        reactor.stop()
                    
        
        
    def remote_get_version(self):
        return self.get_version()
        
    
        
    def remote_test(self):
        dist_zip    = os.path.join(self.temp_dir, '%s.zip'         % self.config.hostname)
        results_tar = os.path.join(self.temp_dir, '%s_results.tgz' % self.config.hostname)
        
        if not os.path.exists( dist_zip ):
            raise PError('Missing distribution zip file!')
        
        args = [applier_cmd, self.config.hostname, dist_zip, results_tar, self.root_dir, 'test']
        
        pp = SimpleProto('applier')
    
        reactor.spawnProcess(pp, applier_cmd, args=args, env=None, path=self.temp_dir)
        
        d = pp.d
        
        def done( out ):
            print 'Config Application test complete'
            if out:
                print out
            
        d.addCallback( done )
        d.addCallback( lambda _: self.send_file( results_tar ) )
        
        return d
    
    
    def remote_apply_config(self, rev_number):
        dist_zip     = os.path.join(self.temp_dir, '%s.zip'         % self.config.hostname)
        results_tar  = os.path.join(self.temp_dir, '%s_results.tgz' % self.config.hostname)
        err_log_file = os.path.join(self.temp_dir, '%s.log'         % self.config.hostname)
        
        print 'Config Application started for revision: ', rev_number
        
        if not os.path.exists( dist_zip ):
            raise PError('Missing distribution zip file!')
        
        args = [applier_cmd, self.config.hostname, dist_zip, results_tar, self.root_dir, err_log_file]
        
        pp = SimpleProto('applier')
    
        reactor.spawnProcess(pp, applier_cmd, args=args, env=None, path=self.temp_dir)
        
        d = pp.d
        
        def done( out ):
            
            self.set_version( rev_number )
            
            if os.path.exists( err_log_file ):
                print 'Config application failed! See error log for details.'
                derr = self.send_file( err_log_file )
                
                def cleanup(_):
                    os.unlink( err_log_file )
                    return os.path.basename(err_log_file)
                
                derr.addCallback( cleanup )
                
                return derr
            else:
                print 'Configuration applied'
                return None
            
        d.addCallback( done )
        
        return d

    
    
#--------------------------------------------------------------------------------------------------
# Helper Classes & Functions
#--------------------------------------------------------------------------------------------------

class SimpleProto (protocol.ProcessProtocol):
    
    def __init__(self, cmd_name):
        self.cmd_name = cmd_name
        self.d = defer.Deferred()
        
        
    def connectionMade(self):
        pass
        
    def outReceived(self, data):
        pre = '%s Out: ' % self.cmd_name
        jstr = '\n%s' % pre
        
        print pre + jstr.join(data.split('\n'))
        pass
        
    def errReceived(self, data):
        pre = '%s Err: ' % self.cmd_name
        jstr = '\n%s' % pre
        print pre + jstr.join(data.split('\n'))
        
    def processExited(self, status):
        #print 'Key Exited with status: ', status.value
        if isinstance(status.value, error.ProcessDone):
            self.d.callback( None )
        else:
            self.d.errback( Exception('Process exited with failure code: ' + str(status.value)) )







