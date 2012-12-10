import os
import os.path
import sys
import ctypes
import json

import re


def err_exit( msg ):
    print >> sys.stderr, msg
    sys.exit(1)


def usage():
    err_exit('Usage: os_env <environment_name[:profile_name]> [command [args...]]')
    
    
if not os.geteuid() == 0:
    err_exit('This script requires root privileges and is designed to be invoked via a set-uid-root wrapper program.')


if len(sys.argv) < 2:
    usage()

env_root = None
env_cfg  = None
cmd_name = None
cmd_args = None
profile  = 'default'
env_name = None

def_path = []

if os.path.exists('/etc/os_env.path'):
    try:
        with open('/etc/os_env.path') as f:
            def_path = [ p.strip() for p in f.read().split(':') ]
    except:
        print >> sys.stderr, 'Failed to parse /etc/os_env.path'

# --- Process command-line arguments ---

env_name = sys.argv[1]


if ':' in env_name:
    try:
        env_name, profile = env_name.split(':')
    except:
        err_exit('Invalid environment name')
        

if len(sys.argv) > 2:
    cmd_name = sys.argv[2]
    cmd_args = sys.argv[3:]
else:
    cmd_name = '/bin/bash'
    cmd_args = ['--login',]

cmd_args.insert(0, cmd_name)
    
# --- Find the configuration file ---
    
tcfg = os.path.join(env_name, 'os_env.conf')

if os.path.exists( tcfg ):
    env_cfg = tcfg

if env_cfg is None and 'OS_ENV_PATH' in os.environ:
    for d in os.environ['OS_ENV_PATH'].split(':'):
        if d:
            tcfg = os.path.join( d, env_name, 'os_env.conf' )
            if os.path.exists( tcfg ):
                env_cfg = tcfg
                break

if env_cfg is None:
    for d in def_path:
        tcfg = os.path.join( d, env_name, 'os_env.conf' )
        if os.path.exists( tcfg ):
            env_cfg = tcfg
            break

if env_cfg is None:
    err_exit('Unable to find "%s/os_env.conf"' % env_name)

env_cfg  = os.path.abspath( env_cfg )
env_root = os.path.dirname( env_cfg )

# -- Load configuration --

cfg_str    = None
cfg        = None
mount_list = list()
env_list   = list()

def check_profile_types( p, profile_name ):
    if not isinstance(profile_name, basestring):
        err_exit('All profile names must be strings. %s is invalid' % str(profile_name))

    if not isinstance(p, dict):
        err_exit('All profile values must be JSON objects. Profile "%s" is invalid' % profile_name)
        
    i = p.get('inherit', None)
    m = p.get('mounts', None)
    e = p.get('environment', None)
    
    if i:
        if not isinstance(i, basestring) or not i in cfg:
            err_exit('%s.inherit must be a single string containing the name of another profile' % profile_name)
    if m:
        if not isinstance(m, list):
            err_exit('%s.mounts is not defined as a list of strings' % profile_name)

    if e:
        if not isinstance(e, list):
            err_exit('%s.environment is not defined as a list' % profile_name)
        for x in e:
            if not isinstance(x, list) or len(x) != 2 or not isinstance(x[0], basestring) or not isinstance(x[1], basestring):
                err_exit('Invalid entry in %s.environment. All entries must be 2-element lists of strings' % profile_name)


def get_lists( p ):
    if 'inherit' in p:
        get_lists( cfg[p['inherit']] )
    if 'mounts' in p:
        mount_list.extend( p['mounts'] )
    if 'environment' in p:
        env_list.extend( p['environment'] )


try:
    with open(env_cfg, 'r') as f:
        cfg_str = f.read()
except:
    err_exit('Failed to read configuration file: %s' % env_cfg)

try:
    cfg = json.loads(cfg_str)
except ValueError, e:
    err_exit('Failed to parse configuration file "%s" as valid JSON data: %s' % (env_cfg, str(e)))

if not isinstance(cfg, dict):
    err_exit('The configuration file must contain a single JSON object that encloses each profile definition')

for profile_name, profile_obj in cfg.iteritems():
    check_profile_types( profile_obj, profile_name )
    
if not profile in cfg:
    err_exit('Profile "%s" not found in the configuration file: %s' % (profile, env_cfg))

get_lists( cfg[profile] )

# -- Mount Points --

if not mount_list:
    err_exit('No mount point overrides are defined in profile "%s". Aborting.' % profile)

mounts = list()

for s in mount_list:
    if ' ' in s:
        tpl = s.split()
        if len(tpl) != 2:
            err_exit('Invalid mount entry "%s"' % s)
        src, tgt = tpl
    else:
        src = s
        tgt = s
        
    src = str(src.strip()) # strip and convert to string
    tgt = str(tgt.strip()) # json returns unicode
    
    if tgt[0] != '/':
        tgt = '/' + tgt

    mounts.append( (src,tgt) )

# -- Environment Manipulation --

if '/' in env_name:
    env_name = os.path.basename(env_name)
    
os.environ['OS_ENV'        ] = env_name
os.environ['OS_ENV_PROFILE'] = profile
os.environ['OS_ENV_ROOT'   ] = env_root
    
def env_sub( m ):
    v = m.group(0)
    v = v[2:] if v.startswith('${') else v[1:]
    if v in os.environ:
        return os.environ[v]
    else:
        return ''

for x in env_list:
    n = str(x[0])
    v = re.sub('\$([a-zA-Z0-9_{]+)', env_sub, str(x[1]))
    os.environ[ n ] = v
    
#
#-------------------------------------------------------------------------------
#

libc = ctypes.CDLL("libc.so.6")

libc.unshare.argtypes = [ctypes.c_int]
libc.mount.argtypes   = [ctypes.c_char_p, # source
                         ctypes.c_char_p, # target
                         ctypes.c_char_p, # filesystem_type
                         ctypes.c_ulong,  # mount_flags
                         ctypes.c_void_p] # data


CLONE_NEWNS = 0x20000  # from linux/sched.h
MS_BIND     = 4096     # from linux/fs.h


if libc.unshare( CLONE_NEWNS ) < 0:
    err_exit("Failed to unshare file system")


for tpl in mounts:
    src = os.path.join(env_root, tpl[0])
    tgt = tpl[1]
    if libc.mount( src, tgt, "none", MS_BIND, 0 ) < 0:
        err_exit("Failed to overmount %s with %s" % (tgt, src))

# *** Drop privileges ***
#
# All processes in Linux have 3 user id values: real-uid, effective-uid, and the
# saved-set-uid. The effective-uid is used by the kernel for all permission checks
# the real-uid and saved-set-uid values are used by various system calls that
# manipulate the value of the effective-uid.
#
# Normal, non-root processes have all three values set to the user's id.
#  
# When a set-uid program owned by root is executed by a normal user, the 3 uid
# values are set tothe following values:
#    real-uid:      normal-user-id
#    effective-uid: 0
#    saved-set-uid: 0
#
# When called by a process with effective-uid equal to 0 (full root privileges)
# the setuid() call will set all three uid values to the specified uid. This is
# the preferred method for "dropping privileges" on Unix systems. As this script
# is invoked via a setuid wrapper program, we can return to the privileges of the
# user invoking this script by simply calling setuid() with the value of this
# process' real-uid.
#
os.setuid( os.getuid() )
        
#os.execvp("bash", ['bash', '--login'])
#os.execvp("python", ['python',])
#os.execvp(cmd_name, cmd_args)
try:
    os.execvpe(cmd_name, cmd_args, os.environ)
except OSError, e:
    if e.errno == 2:
        print 'Command not found'
    else:
        print 'Error: ', str(e)
