#!/usr/bin/python
import os
import os.path

this_dir = os.path.dirname(os.path.abspath(__file__))

env = os.environ
LDP = 'LD_LIBRARY_PATH'

if LDP in env:
    env[ LDP ] += ':' + this_dir
else:
    env[ LDP ] = this_dir

import ctypes

OF_CODEC_REED_SOLOMON_GF_2_8_STABLE = 1
OF_CODEC_REED_SOLOMON_GF_2_M_STABLE = 2
OF_CODEC_LDPC_STAIRCASE_STABLE      = 3
OF_CODEC_2D_PARITY_MATRIX_STABLE    = 5

RS_2 = 1
RS_M = 2
LDPC = 3

dll = ctypes.cdll.LoadLibrary('libtlib.so')

def fec_encode(codec_id, num_repair, symbols):
    num_syms = len(symbols)
    sym_size = len(symbols[0])
    tot_syms = num_syms + num_repair
    all_syms = (ctypes.c_void_p * tot_syms)()
    repairs  = list()
    for i in range(0,num_syms):
        all_syms[i] = ctypes.cast(ctypes.c_char_p(symbols[i]), ctypes.c_void_p)
    for i in range(num_syms, tot_syms):
        r = ctypes.create_string_buffer( sym_size )
        repairs.append(r)
        all_syms[i] = ctypes.cast(r, ctypes.c_void_p)
        
    r = dll.fec_encode( codec_id, num_syms, num_repair, sym_size, all_syms )
    
    print 'Encode returned: ', r
    
    ret = symbols[:]
    for r in repairs:
        ret.append( r.raw )
        
    return ret
    

#int fec_decode( of_codec_id_t codec, int nsource, int nrepair, int sym_size,
#                void *symbols[], void *repaired_buffers[] )
def fec_decode(codec_id, nsource, nrepair, sym_size, all_symbols):
    repairs  = list()
    tot_syms = nsource + nrepair
    all_syms = (ctypes.c_void_p * tot_syms)()
    
    for i in range(0,len(all_symbols)):
        if all_symbols[i] is None and i < nsource:
            r = ctypes.create_string_buffer( sym_size )
            repairs.append( (i,r) )
            all_syms[i] = None
        else:
            all_syms[i] = ctypes.cast(ctypes.c_char_p(all_symbols[i]), ctypes.c_void_p)
            
    repair_buffs = (ctypes.c_void_p * len(repairs))()
    for i in range(0, len(repairs)):
        repair_buffs[i] = ctypes.cast(repairs[i][1], ctypes.c_void_p)
        
    r = dll.fec_decode( codec_id, nsource, nrepair, sym_size, all_syms, repair_buffs )
    print 'Decode returned: ', r
    
    ret = all_symbols[:nsource]
    for i,s in repairs:
        ret[i] = s.raw
        
    return ret
    


def encode_block(codec_id, block_data, nsyms, nrepair):
    npadding = len(block_data) % nsyms
    size     = len(block_data) / nsyms
    last     = 0
    syms     = list()
    for i in range(0, nsyms-1):
        syms.append( block_data[ last : last+size] )
        last = last+size
    syms.append( block_data[last:] + '\0'*npadding )
    
    return npadding, fec_encode(codec_id, nrepair, syms)


def decode_block(codec_id, nrepair, sym_size, npadding, syms):
    nsyms = len(syms) - nrepair
    ds = fec_decode(codec_id, nsyms, nrepair, sym_size, syms)    
    
    if npadding != 0:
        t = ds[:-1]
        t.append( ds[-1][:-npadding] )
    else:
        t = ds
        
    return ''.join(t)
    


#====================================================================

data = '''\
FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E08\
8A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B\
302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9\
A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE6\
49286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8\
FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D\
670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C\
180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718\
3995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D\
04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7D\
B3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D226\
1AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200C\
BBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFC\
E0FD108E4B82D120A92108011A723C12A787E6D788719A10BDBA5B26\
99C327186AF4E23C1A946834B6150BDA2583E9CA2AD44CE8DBBBC2DB\
04DE8EF92E8EFC141FBECAA6287C59474E6BC05D99B2964FA090C3A2\
233BA186515BE7ED1F612970CEE2D7AFB81BDD762170481CD0069127\
D5B05AA993B4EA988D8FDDC186FFB7DC90A6C08F4DF435C934063199\
FFFFFFFFFFFFFFFF'''

def tsmall():
    d1 = data[0:256]
    d2 = data[256:512]
    d3 = data[512:768]
    d4 = data[768:]
    
    syms = [d1, d2, d3, d4]
    
    def p4(s):
        for i in range(0,4):
            print ' ', i, ":", s[i]
            
    print 'Encoding: '
    p4(syms)
    r = fec_encode(OF_CODEC_REED_SOLOMON_GF_2_8_STABLE, 2, syms)
    
    print 'Decoding: '
    r[1] = None
    r = fec_decode(OF_CODEC_REED_SOLOMON_GF_2_8_STABLE, 4, 2, 256, r)
    p4(r)

import hashlib
import os.path
import time
nsym = 180
nrep = 150
code = LDPC
fn = '~/downloads/tortoisehg-1.1.7-hg-1.7.2-x86.msi'
with open(os.path.expanduser(fn), 'r') as f:
    data = f.read()
    
data += '\0' * (len(data) % 1024)

print '--------------------------'
print 'Datalen:  ', len(data)
print 'Datahash: ', hashlib.md5(data).hexdigest()
print '--------------------------'
es = time.time()
npadding, symbols = encode_block(code, data, nsym, nrep)
ee = time.time()

sym_size = len(symbols[0])
print 'Pad: ', npadding, 'syms: ', len(symbols), 'size: ', sym_size
print 'Erasing symbol 1'
symbols[1] = None

ds = time.time()
ndat = decode_block(code, nrep, sym_size, npadding, symbols)
de = time.time()
print '--------- Decoded -----------'
print '--------------------------'
print 'Datalen:  ', len(ndat)
print 'Datahash: ', hashlib.md5(ndat).hexdigest()
print '--------------------------'

etime = ee-es
dtime = de-ds
mb    = len(data)/1024.0/1024.0
print 'Encoding time: ', etime, '(%f Mb/s)' % (mb/etime)
print 'Decoding time: ', dtime, '(%f Mb/s)' % (mb/dtime)
#print ndat
