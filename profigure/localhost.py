import os.path


class Partition (object):
    
    def __init__(self, uuid, dev_name, fs_type):
        self.uuid        = uuid
        self.dev_name    = dev_name
        self.fs_type     = fs_type
        self.mount_point = None
        



class LocalHost (object):
    
    def __init__(self, hostname):
        self.hostname   = hostname
        self.dns_domain = ''
        self.ip_address = ''
        self.DEBUGGING  = False
        self.partitions = dict() # maps device_name, uuid, and mount point to Partition object
        
        
        
    def scan_system(self):
        self._get_partitions()
        self._read_fstab()
        
        
    def iter_partitions(self):
        seen = set()
        for p in self.partitions.itervalues():
            if p in seen:
                continue
            seen.add(p)
            yield p
        
            
    def _get_partitions(self):
        for uuid in os.listdir('/dev/disk/by-uuid'):
            link = os.path.join('/dev/disk/by-uuid',uuid)
            dev  = os.path.normpath( os.path.join('/dev/disk/by-uuid',os.readlink(link)) )
            
            # TODO: use blkid to obtain the filesystem type
            
            p = Partition( uuid, dev, 'unknown_fs' )
            
            self.partitions[ uuid ] = p
            self.partitions[ dev  ] = p
            
            
    def _read_fstab(self):
        with open('/etc/fstab','r') as fobj:
            for line in fobj:
                line = line.strip()
                if line.startswith('#'):
                    continue
                
                tpl = line.split()
                
                if len(tpl) < 5:
                    continue
                
                dev = tpl[0]
                if dev.startswith('UUID='):
                    dev = dev[5:]
                if dev in self.partitions:
                    p = self.partitions[ dev ]
                    
                    p.mount_point = tpl[1]
                    
                    if not p.fs_type:
                        p.fs_type = tpl[2]
                        
                    self.partitions[ p.mount_point ] = p
                        
                    if p.mount_point == 'swap':
                        self.swap_partition = p
                        
                    elif p.mount_point == '/':
                        self.root_partition = p
        
        
