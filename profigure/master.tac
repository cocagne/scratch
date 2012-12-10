import sys
import os.path

this_file    = os.path.abspath( __file__ )
this_dir     = os.path.dirname( this_file )

sys.path.append( os.path.dirname( this_dir ) )

from twisted.python import log
from profigure      import master

config_dir = '/etc/profigure' if not os.path.exists('profigure.conf') else '.'

log.startLogging( sys.stdout )

application = master.get_application( config_dir )
