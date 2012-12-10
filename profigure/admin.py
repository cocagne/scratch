import os
import os.path
import tarfile
import shutil
import tempfile


from   twisted.spread            import pb
from   twisted.internet          import reactor, defer

import profigure
from   profigure              import ProfigureException
from   profigure              import connection, file_transfer, hg_interface, pb_srp
from   profigure.dist_builder import Builder


class TestFailed (ProfigureException):
    def __init__(self, hostname, reason):
        ProfigureException.__init__(self, reason)
        self.hostname = hostname

        
class UserError (ProfigureException):
    pass
        
        
class Admin (object):

    def __init__(self, master_hostname, master_port, username, password, conf_dir = '~/.profigure'):
        
        self.username        = username
        self.password        = password
        self.conn            = None
        self.dconn           = None
        
        self.master_hostname = master_hostname
        self.master_port     = master_port
        
        # TODO: Enhance security here. Check for directory ownership & permissions. Essentially, the same stuff SSH does.
        conf_dir = os.path.expanduser(conf_dir)
        ssl_dir  = os.path.join(conf_dir, 'ssl')
        
        if not os.path.exists( conf_dir ):
            umsk = os.umask( 0077 )
            os.makedirs(conf_dir)
            os.makedirs(ssl_dir)
            os.umask( umsk )
            
        self.conf_dir = conf_dir
        
        dft = file_transfer.start_main_server()
        
        
        
    def getConnection(self):
        if self.conn:
            return defer.succeed( self.conn )
        
        if self.dconn:
            return self.dconn
        
        def makeConn( peer_addr, username, session_key, disconnect_func, peer_pb_if ):
            return AdminConnection( self, peer_addr, username, session_key, disconnect_func, peer_pb_if)#, temp_dir = '/tmp/profigure/admin/%s' % self.username )

        dconn = pb_srp.srp_connect( self.master_hostname, self.master_port, self.username, self.password, makeConn )
        
        self.dconn = dconn
        
        def clear(_):
            self.dconn = None
            return _
        
        dconn.addBoth(clear)
        
        return dconn
        
    
        
    def on_connect(self, ac):
        self.conn = ac
    
        
            
    def on_disconnect(self):
        self.conn = None
        
        

        
class AdminConnection(connection.Connection):
    
    def __init__(self, admin_obj, peer_addr, username, session_key, disconnect_func, peer_pb_if = None, temp_dir = None):
        connection.Connection.__init__( self, peer_addr, username, session_key, disconnect_func, peer_pb_if, temp_dir )
        
        self.admin = admin_obj
        
        self.admin.on_connect( self )
        
        self.doctrine_dir = None
        

        
    def on_disconnect(self):
        self.admin.on_disconnect()

        
        
    def ping(self, host_list):
        dh = self.peer.callRemote('get_host_list')
                
        def pingit( hostname ):
            d = self.peer.callRemote('ping', hostname)
            d.addCallbacks( lambda _: (hostname, None), lambda err: (hostname, err.getErrorMessage()) )
            return d
        
        def pingem( host_list ):
            if host_list:
                cs = set( host_list )
                hs = set( host_list )
                if not cs.issuperset( hs ):
                    raise ProfigureException('Unknown hosts: ' + ', '.join( hs.difference(cs) ))
                host_list = host_list
            return defer.DeferredList( [ pingit(hostname) for hostname in host_list ] )
        
        dh.addCallback( pingem )
        
        return dh
    
    
    
    def add_admin(self, admin_name, admin_password, permission_set = []):
        import srp
        s,v = srp.gen_sv( admin_name, admin_password )
        return self.peer.callRemote('add_admin', admin_name, hex(s), hex(v), permission_set)
    
    
    
    def remove_admin(self, admin_name):
        return self.peer.callRemote('remove_admin', admin_name)
    
    
    
    def add_host(self, hostname, host_password):
        import srp
        s,v = srp.gen_sv( hostname, host_password )
        return self.peer.callRemote('add_host', hostname, hex(s), hex(v))
    
    
    
    def remove_host(self, hostname):
        return self.peer.callRemote('remove_host', hostname)
    
    
    
    def _test_one(self, hostname):        
        zip_file = os.path.join(self.temp_dir, '%s.zip'         % hostname)
        results  = os.path.join(self.temp_dir, '%s_results.tgz' % hostname )
        
        dsend = self.send_file( zip_file )
        
        dsend.addCallback(  lambda _:  self.peer.callRemote('test_host', hostname) )
        
        def done( _ ):
            if not os.path.exists( results ):
                raise KError('Failed to obtain test results')
            print 'Test complete: ', hostname, 'SUCCESS'
            
            test_root = os.path.join( self.doctrine_dir, 'results' )
            test_dir  = os.path.join( test_root, hostname )
            
            if not os.path.isdir( test_root ):
                os.mkdir( test_root, 0700 )
                
            if os.path.exists( test_dir ):
                try:
                    shutil.rmtree( test_dir )
                except Exception, e:
                    print 'Error deleting directory test_results/%s prior to reporting new results. Stale data may persist.' % hostname
                
            try:
                os.mkdir( test_dir, 0700 )
            except Exception:
                pass
            
            tf = tarfile.open( results )
            
            # TODO: Security issue. Replace extractall with something that validates extraction path
            tf.extractall( test_dir )
            
            return (hostname, 'ok')
            
        def fail( err ):
            print 'Test complete: ', hostname, 'FAILURE: ', err.getErrorMessage()
            return (hostname, 'failed: ' + err.getErrorMessage())
            
        dsend.addCallback( done )
        dsend.addErrback( fail )
        
        return dsend
    
        
    def test_config(self, doctrine_dir):
        
        self.doctrine_dir = doctrine_dir
        tdir              = self.temp_dir
        d                 = hg_interface.get_modified_hosts( self.doctrine_dir )
        
        
        def got_hosts( modified_hosts ):
            try:
                b = Builder( self.doctrine_dir, tdir, os.path.join(tdir, 'test_build_temp') )

                b.build_dist( modified_hosts )
                
                b.cleanup()
                
            except ProfigureException, e:
                print 'Error in doctrine: ' + str(e)
                print 'Test aborted.'
                return
            
            except:
                import traceback
                traceback.print_exc()
                raise
            
            return defer.DeferredList( [self._test_one(n) for n in modified_hosts], consumeErrors=True )
            
        def all_done( results ):
            print 'All tests completed!: '
            for ok, (cname, msg) in results:
                print cname, msg 
        
            

            
        d.addCallback( got_hosts )
        
        return d
    
    
    # returns deferred to list of hosts that encountered errors when attempting to update
    def apply_config(self, doctrine_dir):
        
        self.doctrine_dir = doctrine_dir
        tdir              = self.temp_dir
        d                 = hg_interface.get_summary( self.doctrine_dir )
        
        def got_summary( (rev_number, is_clean) ):
            
            if not is_clean:
                raise UserError('Uncommitted changes are present in the repository. Commit them prior to running the brainwash command')
            
            dpush = hg_interface.do_push( self.doctrine_dir )
            
            dpush.addCallback( lambda _: rev_number )
            
            return dpush
        
        def push_done( rev_number ):
            return self.peer.callRemote('apply_config', rev_number)
            
        def apply_done( results ):
            if results is None:
                results = list()
            return results
                        
        d.addCallback( got_summary )
        d.addCallback( push_done   )
        d.addCallback( apply_done  )
        
        return d
                
    
