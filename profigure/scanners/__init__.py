
class ScanError (Exception):
    pass


def shell_output( sh_command_line, input=None ):
    import subprocess    
    return subprocess.Popen( sh_command_line, stdout=subprocess.PIPE, shell=True ).communicate(input)[0]



class SimpleScanner(object):
    
        
    def to_dict(self):
        d = dict()
        
        for k,v in self.__dict__.iteritems():
            if isinstance(v, (basestring, int, long, float, bool, list, dict)):
                d[ k ] = v
        return d
            
    
    
    def from_dict(self, d):
        for k,v in d.iteritems():
            setattr(self,k,v)
        
        
        
