import os.path
from   profigure.scanners import ScanError, SimpleScanner, shell_output


def cat( filename ):
    with open(filename, 'r') as f:
        return f.read()
    

class Scanner(SimpleScanner):
    
    def __init__(self):
        self.hostname       = None
        self.os_type        = None      # linux, solaris, openbsd, aix...
        self.kernel_release = None      # ex: 2.6.12-r4
        self.kernel_version = None      # ex: VendorCompileString SMP 2002-02-12
        self.distribution   = 'unknown' # redhat, suse, gentoo, ubuntu...
        self.dist_version   = 'unknown' # content of /etc/SuSE-release or equivalent
        self.processor      = None      # i686, i486, etc

        
    def scan(self):
        self.hostname       = cat( '/proc/sys/kernel/hostname' )
        self.kernel_release = cat( '/proc/sys/kernel/osrelease' )
        self.kernel_version = cat( '/proc/sys/kernel/version' )
        self.os_type        = cat( '/proc/sys/kernel/ostype' ).lower()
        self.processor      = shell_output('uname -p')
        
        
        if os.path.exists('/etc/SuSE-release'):
            self.distribution = 'suse'
            import re
            m = re.search('=\s*(\S+)', cat('/etc/SuSE-release'))
            if m:
                self.dist_version = m.group(1)
