import os
import os.path
import shutil
import tempfile
import tarfile

from   twisted.internet          import reactor, defer, inotify
from   twisted.application       import service
from   twisted.python            import filepath
from   twisted.python.log        import ILogObserver, FileLogObserver
from   twisted.python.logfile    import LogFile

from   profigure               import connection, file_transfer, ssl_certs, srp_db, acct_db, hg_interface, pro_conf, pb_srp

from   profigure.connection    import PError

from   profigure.dist_builder  import Builder


this_file    = os.path.abspath( __file__ )
this_dir     = os.path.dirname( this_file )

client_files = '''
applier
applier.py
connection.py
doctrine.py
file_transfer.py
hg_interface.py
host.py
__init__.py
localhost.py
pro_conf.py
roster.py
ssl_certs.py
'''


def get_application (config_dir):
    app = service.Application('Profigure Master')
    
    app.master = Master( config_dir )
    
    log_dir = app.master.config.log_dir
    
    if not log_dir:
        log_dir = '/tmp'
        
    if not os.path.exists( log_dir ):
        u = os.umask(0007)
        os.makedirs( log_dir )
        os.umask(u)
        
    lf = LogFile( 'profigure_master.log', log_dir, defaultMode=0640 )
    
    app.setComponent(ILogObserver, FileLogObserver(lf).emit )
    
    return app
        


class Master (object):
    
    def __init__(self, config_dir):
        
        cfg_file = os.path.join(config_dir, 'profigure.conf')
        
        if not os.path.exists( cfg_file ):
            raise pro_conf.ConfigError('Missing configuation file: %s' % cfg_file)
        
        self.config = pro_conf.ProfigureConf(cfg_file)
        
        if self.config.database_dir is None:
            raise pro_conf.ConfigError('Missing required attribute "database_dir" from configuration file: ' + cfg_file)
        
        database_dir = self.config.database_dir
        
        self.dist_dir         = os.path.join(database_dir, 'distribution')
        self.err_dir          = os.path.join(database_dir, 'err_logs')
        self.ssl_dir          = os.path.join(database_dir, 'ssl_certs')
        self.repository       = os.path.join(database_dir, 'repository')
        self.rev_file         = os.path.join(database_dir, 'rev_number')
        
        def chkdir( d ):
            if not os.path.exists( d ):
                u = os.umask(0007)
                os.makedirs( d )
                os.umask(u)
            
        chkdir( self.dist_dir )
        chkdir( self.err_dir  )
        chkdir( self.ssl_dir  )
        
        self.current_rev      = None
        
        with open( self.rev_file, 'r' ) as f:
            self.current_rev = f.read().strip()
        
        self.connected_hosts  = dict()
        self.connected_admins = dict()
        
        self.client_code      = None # Binary data of gzipped tarfile containing client Python code
        
        self.load_client_code()
        
        print 'Connecting to SRP Database'
        self.srp_db          = srp_db.SqliteSrpDB( os.path.join(database_dir, 'srp_db.sqlite') )
        
        print 'Connecting to Account Database'
        self.acct_db         = acct_db.AcctDB( os.path.join(database_dir, 'acct_db.sqlite') )

        print 'Starting file transfer protocol'
        file_transfer.start_main_server()
        
        print 'Starting connection handler'
        pb_srp.accept_connections( self.config.master_port, self.avatar_factory, self.srp_db, self.ssl_dir )
        
        print 'WATCHING PATH'
        self.inotifier = inotify.INotify()
        self.inotifier.startReading()
        for d in (this_dir, os.path.join(this_dir, 'scanners')):
            self.inotifier.watch( filepath.FilePath(d), mask=inotify.IN_MODIFY, callbacks=[self.code_updated,])
        
        
    def code_updated(self, watch_obj, fpath_obj, mask):
        if fpath_obj.path.endswith('.py'):
            print 'CODE UPDATED: ', fpath_obj.path
            print 'Rebuilding client code tarfile & instructing all hosts to restart'
            self.load_client_code()
            
            for h in self.connected_hosts.values():
                h.restart_client_daemon()
        
        
        
    def load_client_code(self):
        tmp = tempfile.TemporaryFile()
        tf  = tarfile.open( fileobj=tmp, mode='w:gz' )

        tf.add( this_dir, 'profigure', False )
        
        for fn in client_files.split():
            if fn:
                tf.add( os.path.join(this_dir, fn), 'profigure/' + fn, False )
                
        tf.add( os.path.join(this_dir, 'scanners'), 'profigure/scanners', True )
            
        tf.close()
        tmp.seek(0)
        self.client_code = tmp.read()

                
        
    def avatar_factory(self, peer_addr, username, session_key, disconnect_func):
        if self.acct_db.have_host( username ):
            return HostConnection( self, peer_addr, username, session_key, disconnect_func, None)#, temp_dir = '/tmp/profigure/master/%s' % username )
        elif self.acct_db.have_admin( username ):
            return AdminConnection( self, peer_addr, username, session_key, disconnect_func, None)#, temp_dir = '/tmp/profigure/master/%s' % username )
        else:
            print '******** ERROR! Unknown AUTHENTICATED user "%s" Eeeep!!!!!' % username
            print 'ALL ADMINS:'
            print self.acct_db.list_admins()


            
    def set_revision(self, rev_number):
        d = hg_interface.do_update( self.repository, rev_number )
        
        def update_done(_):
            with open(self.rev_file, 'w') as f:
                f.write( rev_number )
            self.current_rev = rev_number
            
        d.addCallback( update_done )
        
        return d

    def get_host_version(self, hostname):
        return self.acct_db.get_host_version( hostname )
    
    def host_connected(self, host):
        self.connected_hosts[ host.name ] = host

        
    def host_disconnected(self, host):
        del self.connected_hosts[ host.name ]
        
        
    def admin_connected(self, admin):
        self.connected_admins[ admin.name ] = admin

        
    def admin_disconnected(self, admin):
        del self.connected_admins[ admin.name ]
        
        
        

    #-------------------------------------------------------
    # Admin methods
    #
    def add_host(self, hostname, s_hex, v_hex):
        try:
            self.srp_db.add_user_sv_hex( hostname, s_hex, v_hex )
            self.acct_db.add_host( hostname, set(['default']), self.current_rev )
        except srp_db.SRPError, e:
            raise PError(str(e))
        
        
    def add_admin(self, admin_name, s_hex, v_hex, permission_set):
        try:
            self.srp_db.add_user_sv_hex( admin_name, s_hex, v_hex )
            self.acct_db.add_admin( admin_name, permission_set )
        except srp_db.SRPError, e:
            raise PError(str(e))
        
        
    def remove_host(self, hostname):
        if not self.acct_db.have_host( hostname ):
            raise PError('Unknown host: %s' % hostname)
        
        self.srp_db.remove_user( hostname )
        self.acct_db.remove_host( hostname )
        
        
    def remove_admin(self, admin_name):
        if not self.acct_db.have_host( admin_name ):
            raise PError('Unknown admin: %s' % admin_name)
        self.srp_db.remove_user( admin_name )
        self.acct_db.remove_admin( admin_name )

    
    
    def apply_config(self, rev_number, force_update_all = False):

        orig_rev = self.current_rev
        
        d = self.set_revision( rev_number )
        
        def rev_set(_):
            return hg_interface.get_modified_hosts( self.repository, orig_rev, rev_number )
        
        
        def got_hosts( modified_hosts ):
            print 'apply_config: modified hosts = ', modified_hosts
            
            try:
                b = Builder( self.repository, self.dist_dir )

                b.build_dist( modified_hosts )
                
                b.cleanup()
                
            except Exception, e:
                import traceback
                traceback.print_exc()
                #return
                def try_rebuild(_):
                    try:
                        b = Builder( self.repository, self.dist_dir )
                        b.build_dist( modified_hosts )
                    except:
                        pass
                    raise Exception('Failed to build distribution files: ' + str(e))
                dreset = self.set_revision( orig_rev )
                dreset.addCallback( try_rebuild )
                return dreset
                
                
            for hn in modified_hosts:
                self.acct_db.update_host_version( hn, rev_number )

            l = list()
            for hn in modified_hosts:
                if hn in self.connected_hosts:
                    l.append( self.connected_hosts[hn].apply_config(rev_number) )
                    
            if l:
                return defer.DeferredList(l, consumeErrors=True)
            else:
                return defer.succeed(None)
            
        def results( arg ):
            if arg is None:
                return None
            else:
                l = list()
                for ok, val in arg:
                    if not ok:
                        l.append( val.getErrorMessage() )
                return l if l else None
            
        d.addCallback( rev_set )
        d.addCallback( got_hosts )
        d.addCallback( results )

        
        return d


        
        

class HostConnection(connection.Connection):
    
    def __init__(self, master_obj, peer_addr, name, session_key, disconnect_func, peer_pb_if, temp_dir = None):
        print 'Host connected: ', name
        connection.Connection.__init__( self, peer_addr, name, session_key, disconnect_func, peer_pb_if, temp_dir )
        self.master = master_obj

    
    def restart_client_daemon(self):
        self.peer.callRemote('restart_client_daemon')
        
        
    def remote_get_client_code(self, pb_obj):
        size = 5 * 1024
        
        cc = self.master.client_code
        
        def send_some( offset ):
            if offset + size >= len(cc):
                pb_obj.callRemote('append_code', cc[ offset: ], True )
            else:
                d = pb_obj.callRemote('append_code', cc[ offset : offset + size ], False )
                d.addCallback( lambda _: send_some( offset + size ) )
                
        send_some(0)
                
        
        
    def on_connect(self):
        self.master.host_connected( self )
        db_version = self.master.get_host_version( self.name )
        d = self.peer.callRemote('get_version')
        
        def got_v( cversion ):
            
            print ' VERSIONS: Host "%s"  master "%s"' % (cversion, db_version)
            
            if db_version != cversion:
                print 'Connected host %s is out of date! DB version = %s, Host version = %s' % (self.name, db_version, cversion)
                print '   Updating it...'
                dwash = self.apply_config( db_version )
                
                def ok(_):
                    print 'apply_config complete for host %s' % self.name
                    
                def bad(err):
                    print 'apply_config failed for host %s: %s' % (self.name, err.getErrorMessage())
                
                dwash.addCallbacks( ok, bad )
                
        d.addCallback( got_v )
                
        
        #self.send_file('/usr/local/home/cocagnetd/temp/Twisted-10.0.0.tar.bz2')
        #self.send_file('/tmp/tfile2')
        
        
    def on_disconnect(self):
        self.master.host_disconnected( self )
        

        
    def apply_config(self, rev_number):
        dist_zip       = os.path.join( self.master.dist_dir, '%s.zip' % self.name )
        master_err_log = os.path.join(self.master.err_dir, '%s.log' % self.name)
        
        if not os.path.exists(dist_zip):
            return defer.succeed(None)
        
        if os.path.exists( master_err_log ):
            os.unlink( master_err_log )
        
        dsend = self.send_file( dist_zip )
        
        def sent(_):
            return self.peer.callRemote('apply_config', rev_number)
        
        def result( err_log_file ):
            if err_log_file:
                shutil.move( os.path.join(self.temp_dir, err_log_file), master_err_log )
                raise Exception(self.name)
        
        dsend.addCallback(sent)
        dsend.addCallback(result)
        
        return dsend

        
        
        
        
class AdminConnection(connection.Connection):
    
    def __init__(self, master_obj, peer_addr, name, session_key, disconnect_func, peer_pb_if, temp_dir = None):
        print 'Admin connected: ', name
        connection.Connection.__init__( self, peer_addr, name, session_key, disconnect_func, peer_pb_if, temp_dir )
        self.master = master_obj
        
        

        
    def on_connect(self):
        self.master.admin_connected( self )
        #self.send_file('/usr/local/home/cocagnetd/temp/Twisted-10.0.0.tar.bz2')
        
        
    def on_disconnect(self):
        self.master.admin_disconnected( self )

        
    def remote_add_host(self, hostname, s_hex, v_hex):
        try:
            print 'Adding host ', hostname
            self.master.add_host( hostname, s_hex, v_hex )
        except Exception, e:
            raise PError( str(e) )
        
        
    def remote_add_admin(self, admin_name, s_hex, v_hex, permission_set):
        try:
            self.master.add_admin( admin_name, s_hex, v_hex, permission_set )
        except Exception, e:
            raise PError( str(e) )
        
                
    def remote_remove_host(self, hostname):
        try:
            self.master.remove_host( hostname )
        except Exception, e:
            raise PError( str(e) )
        
        
    def remote_remove_admin(self, admin_name):
        try:
            self.master.remove_admin( admin_name )
        except Exception, e:
            raise PError( str(e) )

        
    def remote_get_host_list(self):
        return self.master.acct_db.list_hosts()
        

    def remote_ping(self, hostname):
        if hostname in self.master.connected_hosts:
            print 'Pinging host...'
            return self.master.connected_hosts[ hostname ].peer.callRemote('ping')
        else:
            print 'Ping failed for %s. Host is off-line' % hostname
            raise PError( 'Ping failed for %s. Host is off-line' % hostname )
        
        
    def remote_test_host(self, hostname):
        
        dtest = defer.Deferred()
        
        c = self.master.connected_hosts.get( hostname, None )
        
        if not c:
            raise PError('offline')
        else:
            d = c.send_file( os.path.join(self.temp_dir, '%s.zip' % hostname) )
        
            def sent(_):
                return c.peer.callRemote('test')
            
            def test_done(_):
                results = os.path.join(c.temp_dir, '%s_results.tgz' % hostname)
                if os.path.exists( results ):
                    return self.send_file( results )
                else:
                    raise PError('Master failed to obtain results')
        
            def ok(_):
                return None
            
            def bad( err ):
                raise PError( err.getErrorMessage() )
        
            d.addCallback( sent      )
            d.addCallback( test_done )
            d.addCallbacks( ok, bad )
        
            return d
        
        
    def remote_apply_config(self, rev_number, force_update_all = False):
        
        return self.master.apply_config( rev_number, force_update_all )
        
    
        

            
        
        
