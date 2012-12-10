import tempfile
import subprocess
import os
import json


class FormatErr (Exception):
    
    def __init__(self, msg, stack):
        self.msg = msg
        self.stack = stack
        
    def __str__(self):
        l = list()
        l.append( '------------------------------' )
        l.append( self.msg )
        l.append( 'Stack: ' )
        for i in range(0,len(self.stack)):
            l.append('[%d]: \t' % i + str(self.stack[i]))
        return '\n'.join(l)

    

def get_sh_data( script_file, pretty_print = False ):
    rfd, wfd = os.pipe()

    if rfd != 3:
        os.dup2(rfd, 3)
        os.close(rfd)
        rfd = 3
    if wfd != 4:
        os.dup2(wfd, 4)
        os.close(wfd)
        wfd = 4
    
    tfd, tfn = tempfile.mkstemp()

    try:
        os.write(tfd, script)
        os.write(tfd, "\n. %s\n\n" % script_file)
        os.fdatasync(tfd)
        os.close(tfd)

        p = subprocess.Popen(['/bin/bash', tfn], executable='/bin/bash')
        
        os.close(wfd)

        result = rdata( rfd )
        if pretty_print:
            return json.dumps( result , indent = 4)
        else:
            return json.dumps( result )
    finally:
        os.close( rfd )
        os.unlink( tfn )



script = r'''
_pf_cmd()
{
    while (( "$#" )); do
        echo -ne "$1" >&4
        echo -ne "\0" >&4
        shift
    done
}

pf_push_object() { _pf_cmd "A" "${1-**NOTSET**}"; }
pf_pop_object()  { _pf_cmd "B";                   }
pf_push_list()   { _pf_cmd "C" "${1-**NOTSET**}"; }
pf_pop_list()    { _pf_cmd "D";                   }
pf_add_attr()    { _pf_cmd "E" "$1" "$2";         }
pf_add_attrn()   { _pf_cmd "F" "$1" "$2";         }
pf_add_litem()   { _pf_cmd "G" "$1";              }
pf_add_litemn()  { _pf_cmd "H" "$1";              }

'''

        

def rdata( rfd ):
    ldat = list()
    while True:
        d = os.read( rfd, 4096 )
        if d:
            ldat.append( d )
        else:
            break
    buff = ''.join( ldat )
    
    def tgen():
        i = 0
        while i < len(buff):
            s = i
            while i < len(buff) and buff[i] != '\0':
                i += 1
            x = buff[s:i]
            #print '    ', x
            yield x
            i += 1
            
    tgenerator = tgen()
    
    def nextToken():
        try:
            return tgenerator.next()
        except:
            return None

    result = dict()
    ostack = list()
    ostack.append( result )
    
    def throwErr( msg ):
        raise FormatErr( msg, ostack )
    
    def toInt( n ):
        try:
            if n.startswith('0x'):
                return int(n,16)
            elif n.startswith('0'):
                return int(n,8)
            else:
                return int(n)
        except ValueError:
            throwErr( 'Invalid integer: "%s"' % n )
            
    def pf_push( cls ):
        name    = nextToken()
        new_cls = cls()
        if isinstance(ostack[-1], dict):
            if name == '**NOTSET**':
                throwErr( 'Failed to specify name to %s. This is required when an object is on the stack' % ('pf_push_object' if cls is dict else 'pf_push_list') )
            else:
                ostack[-1][ name ] = new_cls
        else:
            ostack[-1].append( new_cls )
        ostack.append( new_cls )
        
    def pf_pop( cls ):
        if len(ostack) == 1:
            kind = 'object' if cls is dict else 'list'
            throwErr( 'Attempted to call pf_pop_%s when stack is empty' % kind )
        if not isinstance(ostack[-1], cls):
            tpl = ('object', 'list') if cls is dict else ('list', 'object')
            throwErr( 'Attempted to call pf_pop_%s when %s is on the stack' % tpl)
        ostack.pop()
        
    def pf_add_attr( as_integer ):
        if not isinstance(ostack[-1], dict):
            throwErr( 'Attempted to call pf_add_attr when list is on the stack. Key = %s' % str(nextToken()) )
        name  = nextToken()
        value = nextToken()
        if as_integer:
            value = toInt( value )
        ostack[-1][ name ] = value
        
    def pf_add_litem( as_integer ):
        if not isinstance(ostack[-1], list):
            throwErr( 'Attempted to call pf_add_litem when object is on the stack' )
        value = nextToken()
        if as_integer:
            value = toInt( value )
        ostack[-1].append( value )
    
        
    pmap = { 'A' : lambda : pf_push(dict),
             'B' : lambda : pf_pop(dict),
             'C' : lambda : pf_push(list),
             'D' : lambda : pf_pop(list),
             'E' : lambda : pf_add_attr(False),
             'F' : lambda : pf_add_attr(True),
             'G' : lambda : pf_add_litem(False),
             'H' : lambda : pf_add_litem(True) }



    cmd = nextToken()
    while cmd:
        #print 'Command: ', cmd
        pmap[ cmd ]()
        cmd = nextToken()

   
    #print 'Result: '
    #import pprint
    #pprint.pprint( result )
    
    return result
