import re
import os
import os.path
import tempfile

from   profigure import roster

from   twisted.internet import reactor, protocol, utils, defer, error


stat_re = re.compile('^. (roles|hosts|roster)/?([^./]+)?')


def path_find( cmd_name ):
    for p in os.environ['PATH'].split(':'):
        fp = os.path.join( os.path.expanduser(os.path.expandvars(p)), cmd_name )
        if os.path.exists( fp ):
            return fp

        
HG_PATH = path_find( 'hg' )


if not HG_PATH:
    raise ImportError('Unable to find Mercurial command "hg"')

        

class SimpleProto (protocol.ProcessProtocol):
    
    def __init__(self):
        self.d = defer.Deferred()
        
        
    def connectionMade(self):
        pass
        
    def outReceived(self, data):
        #print 'PROTO OUT: ', data
        pass
        
    def errReceived(self, data):
        #print 'PRTO ERR: ', data
        pass
        
    def processExited(self, status):
        #print 'Key Exited with status: ', status.value
        if isinstance(status.value, error.ProcessDone):
            self.d.callback( None )
        else:
            self.d.errback( Exception('Process exited with failure code: ' + str(status.value)) )



class HgStatusProto (SimpleProto):
    
    def __init__(self):
        SimpleProto.__init__(self)
        self.roles  = set()
        self.hosts  = set()
        self.roster = False
        self.err_msg = ''
        
    def outReceived(self, data):
        for l in data.split('\n'):
            l = l.rstrip()
            if not l:
                continue
            m = stat_re.match(l)
            if m:
                kind, name = m.groups()
                if kind == 'roles' and name:
                    self.roles.add( name )
                elif kind == 'hosts' and name:
                    self.hosts.add( name )
                elif kind == 'roster':
                    self.roster = True

        #print '-----------------------------------------'
        #print data
        #print '-----------------------------------------'
        #print 'Roles:  ', self.roles
        #print 'Hosts:  ', self.hosts
        #print 'Roster: ', self.roster
        
    def errReceived(self,data):
        self.err_msg = data
        
    def processExited(self, status):
        if isinstance(status.value, error.ProcessDone):
            self.d.callback( (self.roster, self.roles, self.hosts) )
        else:
            self.d.errback( Exception('hg status failed: ' + self.err_msg) )

            
class HgSummaryProto (SimpleProto):
    
    def __init__(self):
        SimpleProto.__init__(self)
        self.rev_number = None
        self.is_clean   = None
        
    def outReceived(self, data):
        for l in data.split('\n'):
            l = l.rstrip()
            
            if l.startswith('parent:') and self.rev_number is None:
                self.rev_number = l.split()[1].split(':')[1]
                
            elif l.startswith('commit:') and self.is_clean is None:
                self.is_clean = l.split()[1] == '(clean)'
        
    def errReceived(self,data):
        self.err_msg = data
        
    def processExited(self, status):
        if isinstance(status.value, error.ProcessDone):
            self.d.callback( (self.rev_number, self.is_clean) )
        else:
            self.d.errback( Exception('hg summary failed: ' + self.err_msg) )

            
            
class HgCatProto (SimpleProto):
            
    def outReceived(self, data):
        print '---------- OUT RECEIVED... Ohs Noes! -----------'
        print data
        
    def errReceived(self,data):
        self.err_msg = data
        
        
        

class HgSimpleProto (SimpleProto):
    err_msg  = ''
    cmd_name = 'UNKNOWN'
    
    def errReceived(self,data):
        self.err_msg = data
        
    def processExited(self, status):
        if isinstance(status.value, error.ProcessDone):
            self.d.callback( None )
        else:
            self.d.errback( Exception('hg command %s failed: %s' % (self.cmd_name, self.err_msg)) )
    
        
        
def cat_file( hg_repo_dir, file_to_cat, dest_file, revision = '-1' ):
    fobj = None

    hg_repo_dir = os.path.expanduser( os.path.expandvars(hg_repo_dir) )
    
    if not os.path.isdir( os.path.join(hg_repo_dir, '.hg') ):
        return defer.fail( Exception('Invalid HG Repository: %s' % hg_repo_dir) )
    
    try:
         fobj = open( dest_file, 'w' )
    except IOError, e:
        return defer.fail( e )
    
    args = [HG_PATH, 'cat', '--rev', revision, file_to_cat]
    
    childFDs = { 0:'w', 1:fobj.fileno(), 2:'r' }
    
    pp = HgCatProto()
    
    reactor.spawnProcess(pp, HG_PATH, args=args, env=None, path=hg_repo_dir, childFDs=childFDs)
    
    def close_file( _ ):
        fobj.close()
        return _
 
    pp.d.addBoth( close_file )
    
    return pp.d
    
    
    

        

# Returns deferred to (rev_number, is_clean)
#
def get_summary( hg_repo_dir ):
    
    hg_repo_dir = os.path.expanduser( os.path.expandvars(hg_repo_dir) )
    
    if not os.path.isdir( os.path.join(hg_repo_dir, '.hg') ):
        return defer.fail( Exception('Invalid HG Repository: %s' % hg_repo_dir) )
    
    sp = HgSummaryProto()
    
    args = [HG_PATH, 'summary']
    
    reactor.spawnProcess(sp, HG_PATH, args=args, env=None, path=hg_repo_dir)
 
    return sp.d



# Runs 'hg push' from the repository directory
#
def do_push( hg_repo_dir ):
    
    hg_repo_dir = os.path.expanduser( os.path.expandvars(hg_repo_dir) )
    
    if not os.path.isdir( os.path.join(hg_repo_dir, '.hg') ):
        return defer.fail( Exception('Invalid HG Repository: %s' % hg_repo_dir) )
    
    sp = HgSimpleProto()
    sp.cmd_name = 'push'
    
    args = [HG_PATH, 'push']
    
    reactor.spawnProcess(sp, HG_PATH, args=args, env=None, path=hg_repo_dir)
 
    return sp.d



# Runs 'hg update -r <revision_number>' in the repository directory
#
def do_update( hg_repo_dir, rev_number ):
    
    hg_repo_dir = os.path.expanduser( os.path.expandvars(hg_repo_dir) )
    
    if not os.path.isdir( os.path.join(hg_repo_dir, '.hg') ):
        return defer.fail( Exception('Invalid HG Repository: %s' % hg_repo_dir) )
    
    sp = HgSimpleProto()
    sp.cmd_name = 'update'
    
    args = [HG_PATH, 'update', '-r', rev_number]
    
    reactor.spawnProcess(sp, HG_PATH, args=args, env=None, path=hg_repo_dir)
 
    return sp.d




# Returns deferred to (roster_modified_bool, modified_roles_set, modified_hosts_set)
#
def get_status( hg_repo_dir, from_revision = None, to_revision = None ):
    
    hg_repo_dir = os.path.expanduser( os.path.expandvars(hg_repo_dir) )
    
    if not os.path.isdir( os.path.join(hg_repo_dir, '.hg') ):
        return defer.fail( Exception('Invalid HG Repository: %s' % hg_repo_dir) )
    
    
    rev_str = ''
    
    if from_revision:
        rev_str = '%s' % from_revision
        
    if to_revision:
        rev_str = rev_str + ':%s' % to_revision
    
    sp = HgStatusProto()
    
    args = [HG_PATH, 'status']
    
    if rev_str:
        args.append( '--rev' )
        args.append( rev_str )

    reactor.spawnProcess(sp, HG_PATH, args=args, env=None, path=hg_repo_dir)
 
    return sp.d



# returns a set of hostnames
def get_modified_hosts( doctrine_dir, from_revision = None, to_revision = None ):

    doctrine_dir = os.path.expanduser( os.path.expandvars(doctrine_dir) )
    
    rcur = roster.Roster( os.path.join(doctrine_dir, 'roster') )
    rcur.read()
        
    d = get_status( doctrine_dir, from_revision, to_revision )
        
    def got_stat( (roster_modified, role_set, host_set) ):
            
        host_set.update( rcur.get_hosts_depending_on_roles(role_set) )
            
        if roster_modified:
            fhandle, troster = tempfile.mkstemp()
            os.close(fhandle)
            dcat = cat_file( doctrine_dir, 'roster', troster, revision = '-1' )
            
            def got_old(_):
                rold = roster.Roster( troster )
                try:
                    rold.read()
                    return rcur.get_modified_hosts( rold, host_set, role_set )
                except Exception, e:
                    print 'Failed to load previous versions roster. Assuming all hosts have been modified...'
                    return rcur.all_hosts
                
                    
            def cleanup(_):
                os.unlink( troster )
                return _
                
            dcat.addCallback( got_old )
            dcat.addErrback( cleanup )
                
            return dcat
        else:
            return defer.succeed( host_set )

    d.addCallback( got_stat )
    return d



def test():
    
    #d = get_status( '~/test/merc/trepo1', '0' )
    #d = get_status( '~/clonearmy', '0' )
    
    #d = cat_file( '~/test/merc/trepo1', 'roster', '/tmp/troster', '-1')
    
    #d = get_modified_hosts('~/test/merc/trepo1')
    d = get_modified_hosts( '~/clonearmy' )

    def done( arg ):
        print 'Done!!!: ', arg
        reactor.stop()

    d.addBoth(done)
    reactor.run()
    
if __name__ == '__main__':
    test()
