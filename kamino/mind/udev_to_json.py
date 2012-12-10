#!/usr/bin/env python

from pyudev import Context

class TopDev (object):
    def __init__(self, d):
        self.d = d
        self.sub = list()

def getem( subsys ):
    c = Context()

    tops = dict()

    for d in c.list_devices(subsystem=subsys):
        if d.parent and d.parent.subsystem == subsys:
            if not d.parent.device_path in tops:
                tops[ d.parent.device_path ] = TopDev( d.parent )
            tops[ d.parent.device_path ].sub.append( d )
        else:
            if not d.device_path in tops:
                tops[ d.device_path ] = TopDev( d )

    return tops.values()


def get_driver( d ):
    if d.driver:
        return d.driver
    p = d.parent
    if p is None:
        return None
    return get_driver(p)


def printem( subsys ):
    dlist = getem(subsys)

    ignores = set('DEVPATH DEVNAME SUBSYSTEM UDEV_LOG DEVLINKS'.split())
    
    def pdev( d, indent='' ):
        print indent, '-'* (80-len(indent))
        print indent, 'kernel:   ', d.device_path
        print indent, 'sysfs:    ', d.sys_path
        print indent, 'sys_name: ', d.sys_name
        print indent, 'driver:   ', get_driver(d)
        print indent, 'dtype:    ', d.device_type
        print indent, '/dev:     ', d.device_node
        for k,v in d.iteritems():
            if not k in ignores and not (k == 'TAGS' and v == ':udev-acl:'):
                print indent, '{0} = {1}'.format(k,v)

    dlist.sort( key=lambda td: td.d.device_path )
    
    for td in dlist:
        pdev( td.d )
        for s in td.sub:
            pdev( s, '    ' )



    
            

def get_jdisks():
    tblocks = getem('block')

    jdisks = list()

    mounts = dict()
    with open('/proc/self/mountinfo') as f:
        for l in f:
            comps = l.split()
            if len(comps) > 5:
                mounts[ comps[2] ] = (comps[4], comps[-1])

    def get_mount( part_dev ):
        return mounts.get( "{0}:{1}".format( part_dev['MAJOR'], part_dev['MINOR'] ), ('','') )

    for b in tblocks:
        d = b.d

        if d.sys_name.startswith('loop'):
            continue

        def gbool( attr ):
            try:
                return attr in d and int(d[attr]) == 1
            except:
                return False
        
        jd = dict()

        jdisks.append( jd )

        jd['sys_name'    ] = d.sys_name
        jd['sysfs'       ] = d.sys_path
        jd['driver'      ] = get_driver(d)
        jd['dev_path'    ] = d.device_node
        jd['major'       ] = d['MAJOR']
        jd['minor'       ] = d['MINOR']
        jd['symlinks'    ] = ' '.join( list(d.device_links) )
        jd['is_cdrom'    ] = gbool('ID_CDROM')
        jd['serial'      ] = d.get('ID_SERIAL',None)
        jd['rotation_rpm'] = d.get('ID_ATA_ROTATION_RATE_RPM', None)
        jd['model'       ] = d.get('ID_MODEL',None)
        jd['bus'         ] = d.get('ID_BUS',None)

        if gbool('ID_CDROM'):
            jd['cd_r'         ] = gbool('ID_CDROM_CD_R')
            jd['cd_rw'        ] = gbool('ID_CDROM_CD_RW')
            jd['dvd_r'        ] = gbool('ID_CDROM_DVD_R')
            jd['dvd_rw'       ] = gbool('ID_CDROM_DVD_RW')
            jd['dvd_ram'      ] = gbool('ID_CDROM_DVD_RAM')
            jd['dvd_plus_r'   ] = gbool('ID_CDROM_DVD_PLUS_R')
            jd['dvd_plus_rw'  ] = gbool('ID_CDROM_DVD_PLUS_RW')
            jd['dvd_plus_r_dl'] = gbool('ID_CDROM_DVD_PLUS_R_DL')

        if len(b.sub):
            jd['partitions'] = list()

            for dp in b.sub:
                jp = dict()
                jd['partitions'].append( jp )

                mount_point, mount_ops = get_mount(dp)
                ata_id  = None
                scsi_id = None
                wwn_id  = None

                part_no = dp.sys_name[3:]
                
                if gbool('ID_ATA'):
                    ata_id = 'ata={0}-part{1}'.format( dp['ID_SERIAL'], part_no )

                if 'ID_SCSI_COMPAT' in dp:
                    scsi_id = 'scsi-{0}-part{1}'.format( dp['ID_SCSI_COMPAT'], part_no )

                if 'ID_WNN' in d:
                    wnn_id = 'wnn-{0}-part{1}'.format( d['ID_WNN'], part_no )
                
                jp['name'        ] = dp.sys_name
                jp['dev_path'    ] = dp.device_node
                jp['major'       ] = dp['MAJOR']
                jp['minor'       ] = dp['MINOR']
                jp['id_serial'   ] = dp.get('ID_SERIAL', None)
                jp['ata_id'      ] = ata_id
                jp['scsi_id'     ] = scsi_id
                jp['wwn_id'      ] = wwn_id
                jp['mount_point' ] = mount_point
                jp['mount_ops'   ] = mount_ops
                jp['uuid'        ] = dp.get('ID_FS_UUID', None)
                jp['fs_type'     ] = dp.get('ID_FS_TYPE', None)
                jp['fstab_name'  ] = dp.get('FSTAB_NAME', None)
                jp['fstab_mount' ] = dp.get('FSTAB_DIR', None)
                jp['fstab_opts'  ] = dp.get('FSTAB_OPTS', None)
                
    return jdisks

        


class D (object):
        
    def __init__(self, d):
        self.d        = d
        self.parent   = None
        self.children = list()

def get_devs(): 

    dmap = dict()
    
    c = Context()

    for d in c.list_devices():
        dmap[ d.device_path ] = D(d)

    for d in list(dmap.itervalues()):
        p = d.d.parent
        if p:
            if p.device_path in dmap:
                pd = dmap[ p.device_path ]
                
            else:
                #print '*** Missing parent: ({0}: {1} => {2})'.format(d.d.sys_name, d.d.device_path, p.device_path)
                pd = D( p )
                dmap[ p.device_path ] = pd
                if p.parent:
                    if p.parent.device_path in dmap:
                        pd.parent = dmap[ p.parent.device_path ]
                        pd.parent.children.append( pd )
                    #else:
                    #    print '     *** Missing parent is missing parent! ', p.parent.device_path
                
            d.parent = pd
            pd.children.append( d )
    return dmap


def get_subsys( kind ):
    dmap = get_devs()

    results = list()
    rset    = set()

    def rfind( d ):
        try:
            if d.d.subsystem == kind and not d.d.device_path in rset:
                results.append(d)
                rset.add( d.d.device_path )
                return
        except:
            pass
        for sub in d.children:
            rfind( sub )

    for x in dmap.itervalues():
        rfind(x)

    return results


def print_devs( dlist = None ):

    def pd( d, indent = '' ):
        try:
            ss = d.d.subsystem
        except:
            ss = 'INVALID'
            
        print indent, '{0:15}  {1:30}  {2!s}'.format(ss, d.d.device_path or 'None', d.d.device_node or 'None')
        indent += '   '
        for c in d.children:
            pd( c , indent )

    if dlist is None:
        dlist = (d for d in get_devs().itervalues() if d.parent is None)
        
    for t in dlist:
        pd( t )
    
    
