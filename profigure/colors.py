import os
import sys

# This module provides basic support for outputting colored text on color-capable terminals
# (i.e. Linux/Cygwin consoles)


USE_COLOR = False

if os.environ.has_key('TERM'):
    if os.environ['TERM'] in ('xterm', 'Eterm', 'aterm', 'rxvt', 'screen', 'vt100'):
        USE_COLOR = True


colors             = dict()
colors['none'     ]=''
colors['reset'    ]='\x1b[0m'
colors['bold'     ]='\x1b[01m'        
colors['teal'     ]='\x1b[36;06m'
colors['turquoise']='\x1b[36;01m'        
colors['fuscia'   ]='\x1b[35;01m'
colors['purple'   ]='\x1b[35;06m'        
colors['blue'     ]='\x1b[34;01m'
colors['darkblue' ]='\x1b[34;06m'        
colors['green'    ]='\x1b[32;01m'
colors['darkgreen']='\x1b[32;06m'        
colors['yellow'   ]='\x1b[33;01m'
colors['brown'    ]='\x1b[33;06m'        
colors['red'      ]='\x1b[31;01m'
colors['darkred'  ]='\x1b[31;06m'

        
SUCCESS = 'green'
FAILURE = 'red'
WARNING = 'yellow'
NORMAL  = 'reset'


def wrap( msg, color ):
    if USE_COLOR:
        return colors[color] + msg + colors[NORMAL]
    else:
        return msg


def color_print(color, text, append_newline=1, use_err_stream=None):
    stream = use_err_stream and sys.stderr or sys.stdout
    
    if append_newline:
        text = text + '\n'
        
    if USE_COLOR:
        stream.write(colors[color] + text + colors[NORMAL])
    else:
        stream.write(text)

        
def color_err_print(color, text, append_newline=1):
    color_print(color, text, append_newline, 1)
    

    
def set_color(color, err_stream=None):
    if USE_COLOR:
        if err_stream:
            sys.stderr.write(colors[color])
        else:
            sys.stdout.write(colors[color])
    
            
def set_err_color(color):
    set_color(color, 1)
        
    
    
def print_failure( text ):
    color_err_print(FAILURE, text)
    
def print_warning( text ):
    color_print(WARNING, text)

def print_success( text ):
    color_print(SUCCESS, text)
