import os
import os.path
import json

import re



def load( fn ):
    with open(fn, 'r') as f:
        j = json.load(f)

    return j#cvt_to_str( j )



def cvt_to_str( j ):
    if isinstance(j, dict):
        d = dict()
        for k, v in j.iteritems():
            d[ str(k) ] = cvt_to_str(v)
        return d
    
    elif isinstance(j, list):
        return [ cvt_to_str(x) for x in j ]
    
    elif isinstance(j, unicode):
        return str(j)
    
    else:
        return j



    
