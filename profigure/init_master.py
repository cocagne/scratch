import os
import os.path

import srp_db
import acct_db

def init( admin_name, admin_password, master_dir ):
    
    if not os.path.exists( master_dir ):
        os.makedirs( master_dir )
        
    s = srp_db.SqliteSrpDB( os.path.join(master_dir, 'srp_db.sqlite') )
    s.add_user( admin_name, admin_password )
    s.close()
    
    a = acct_db.AcctDB( os.path.join(master_dir, 'acct_db.sqlite') )
    a.add_admin( admin_name, set(['master',]) )
    a.close()
    
    
    
confirm_set = ('', 'Y','y','yes','ok','youbetcha','justdoitalready')
    
def cmd_line_init( master_dir ):
    import getpass
    admin_name     = getpass.getuser()
    adname         = admin_name
    admin_password = ''
    done           = False
    
    while not done:
        adname = raw_input('Enter primary administrator username [%s]: ' % adname)
        adname = adname.strip()
        
        if not adname:
            adname = admin_name
        
        p1         = getpass.getpass('Enter password: ')
        p2         = getpass.getpass('Confirm password: ')
        
        if p1 != p2:
            print 'Mismatched passwords.'
            continue
        
        c = raw_input('Initialize Profigure with administrator "%s" [Y/n]: ' % adname)
        
        if c in confirm_set:
            admin_name = adname
            admin_password = p1
            done = True
            
    init( admin_name, admin_password, master_dir )
            
    
if __name__ == '__main__':
    import sys
    if not len(sys.argv) == 2:
        print 'Usage: %s <master_config_directory>'
        
    #try:
    if not os.path.exists( sys.argv[1] ):
        if not raw_input('Directory %s does not exist. Create it? [Y/n]: ' % sys.argv[1]) in confirm_set:
            print 'Initialization canceled'
            sys.exit(1)
        
    cmd_line_init( sys.argv[1] )
        
    #except
        
