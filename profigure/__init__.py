
# It is expected that user-defined Doctrine generators will 'import *' this module. Place all common
# utilities here, or in a submodule that this file in turn does an 'import *' for

class ProfigureException (Exception):
    pass

DEBUGGING = False

def shell_output( sh_command_line, input=None ):
    import subprocess    
    return subprocess.Popen( sh_command_line, stdout=subprocess.PIPE, shell=True ).communicate(input)[0]

    
def shell_test( sh_command_line ):
    import subprocess
    return subprocess.Popen( sh_command_line, shell=True ).wait()


def shell_silent( sh_command_line ):
    shell_test( sh_command_line )

    
from profigure.doctrine import Doctrine
