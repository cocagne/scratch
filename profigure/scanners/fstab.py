
from   profigure.scanners import ScanError


class Entry (object):
    
    _attrs = ('device', 'mount_point', 'fs_type', 'options', 'freq', 'passno')
    
    def from_line(self, line):
        tpl = line.split()
                
        if len(tpl) < 4 or len(tpl) > 6:
            raise ScanError('Failed to parse FSTAB entry: ' + line)
       
        self.device      = tpl[0]
        self.mount_point = tpl[1]
        self.fs_type     = tpl[2]
        self.options     = tpl[3]
        self.freq        = tpl[4] if len(tpl) > 3 else '0'
        self.passno      = tpl[5] if len(tpl) > 4 else '0'
    
        
    def from_dict(self, d):
        for a in self._attrs:
            setattr(self, a, d[a])
        
            
    def to_dict(self):
        d = dict()
        for a in self._attrs:
            d[a] = getattr(self,a)
        return d
        
        

class Scanner(object):
    
    def __init__(self):
        self.entries = dict() # maps mount point & device-name/uuid/label to Entry
        self.order   = list() # List of mount points in the order they occur

        
    def to_dict(self):
        el = list()
        for e in self.entries.itervalues():
            el.append( e.to_dict() )
        return { 'entries' : el, 'order' : self.order }
    
    
    def from_dict(self, d):
        
        for ed in d['entries']:
            e = Entry()
            e.from_dict( ed )
            self.entries[ e.mount_point ] = e
            self.entries[ e.device_name ] = e
            
        self.order = d['order']
        
        
    def iter_mounts(self):
        for m in self.order:
            yield self.entries[ m ]
        
            
    def scan(self):
        with open('/etc/fstab', 'r') as fobj:
            for line in fobj:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                e = Entry()
                e.from_line( line )
                
                self.order.append( e.mount_point )
                self.entries[ e.mount_point ] = e
                self.entries[ e.device_name ] = e
        
        
