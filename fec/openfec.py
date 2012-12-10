import os
import os.path
from   ctypes import *

if 'OPENFEC_LIB' in os.environ:
	lib_file = os.environ['OPENFEC_LIB']

elif 'LD_LIBRARY_PATH' in os.environ:
	for p in os.environ['LD_LIBRARY_PATH'].split(':'):
		if os.path.exists( os.path.join(p,'libopenfec.so') ):
			lib_file = os.path.join(p,'libopenfec.so')
else:
	lib_file = 'libopenfec.so'

oflib = cdll.LoadLibrary(lib_file)

OF_CODEC_NIL                        = 0
OF_CODEC_REED_SOLOMON_GF_2_8_STABLE = 1
OF_CODEC_REED_SOLOMON_GF_2_M_STABLE = 2
OF_CODEC_LDPC_STAIRCASE_STABLE      = 3
OF_CODEC_2D_PARITY_MATRIX_STABLE    = 5
OF_CODEC_LDPC_FROM_FILE_ADVANCED    = 6

OF_ENCODER             = 0x1
OF_DECODER             = 0x2
OF_ENCODER_AND_DECODER = OF_ENCODER | OF_DECODER

OF_STATUS_OK          = 0
OF_STATUS_FAILURE     = 1
OF_STATUS_ERROR       = 2
OF_STATUS_FATAL_ERROR = 3


class of_session (Structure):
	_fields_ = [ ("codec_id",   c_int),
	             ("codec_type", c_int) ]
				
session_ptr = POINTER( of_session )


class of_parameters (Structure):
	_fields_ = [("nb_source_symbols",      c_uint),
				("nb_repair_symbols",      c_uint),
				("encoding_symbol_length", c_uint)]

				
of_create_codec_instance = oflib.of_create_codec_instance
of_create_codec_instance.argtypes = [ POINTER( session_ptr ), c_int, c_int, c_uint ]


of_release_codec_instance = oflib.of_release_codec_instance
of_release_codec_instance.argtypes = [ session_ptr, ]


of_set_fec_parameters = oflib.of_set_fec_parameters
of_set_fec_parameters.argtypes = [ session_ptr, POINTER( of_parameters ) ]


DECODE_CALLBACK = PYFUNCTYPE( c_void_p, c_void_p, c_uint, c_uint )

of_set_callback_functions = oflib.of_set_callback_functions
#of_set_callback_functions.argtypes = [ session_ptr, DECODE_CALLBACK, DECODE_CALLBACK, c_void_p ]
of_set_callback_functions.argtypes = [ session_ptr, DECODE_CALLBACK, c_void_p, c_void_p ]


of_build_repair_symbol = oflib.of_build_repair_symbol
of_build_repair_symbol.argtypes = [ session_ptr, c_void_p, c_uint ]


of_decode_with_new_symbol = oflib.of_decode_with_new_symbol
of_decode_with_new_symbol.argtypes = [ session_ptr, c_void_p, c_uint ]


of_set_available_symbols = oflib.of_set_available_symbols
of_set_available_symbols.argtypes = [ session_ptr, c_void_p ]


of_finish_decoding = oflib.of_finish_decoding
of_finish_decoding.argtyps = [ session_ptr, ]


of_is_decoding_complete = oflib.of_is_decoding_complete
of_is_decoding_complete.argtypes = [session_ptr,]


of_get_source_symbols_tab = oflib.of_get_source_symbols_tab
of_get_source_symbols_tab.argtypes = [ session_ptr, c_void_p ]

of_set_control_parameter = oflib.of_set_control_parameter
of_set_control_parameter.argtypes = [ session_ptr, c_uint, c_void_p, c_uint ]


of_get_control_parameter = oflib.of_get_control_parameter
of_get_control_parameter.argtypes = [ session_ptr, c_uint, c_void_p, c_uint ]

OF_CTRL_GET_MAX_K = 1
OF_CTRL_GET_MAX_N = 2


#----------------------------------------------------------------------------------------
# Python encoding / decoding functions
#

def encode(codec, symbol_array, num_repair_symbols):
	num_source_symbols = len(symbol_array)
	total_symbols      = num_source_symbols + num_repair_symbols
	symbol_size        = len(symbol_array[0])
	
	session = session_ptr()
	
	try:
	
		if len(symbol_array) != num_source_symbols:
			raise Exception('Invalid symbols array size. Size must be num_source_symbols in size')
		
		if of_create_codec_instance( byref(session), codec, OF_ENCODER, 1 ) != 0:
			raise Exception('Failed to create codec instance for codec: ' + str(codec))
		
	
		p = of_parameters()
		
		p.nb_source_symbols      = num_source_symbols
		p.nb_repair_symbols      = num_repair_symbols
		p.encoding_symbol_length = symbol_size
		
		of_set_fec_parameters( session, byref(p) )
		
		ARR = c_void_p * total_symbols
		tbl = ARR()

		repair_symbols  = list()
	
		for i in range(0, len(symbol_array)):
			tbl[i] = cast( c_char_p(symbol_array[i]), c_void_p ) 
		
		for i in range(num_source_symbols, total_symbols):
			r      = create_string_buffer( len(symbol_array[0]) )
			tbl[i] = cast( r, c_void_p )
			repair_symbols.append( r )
		
		for i in range(num_source_symbols, total_symbols):
			of_build_repair_symbol( session, tbl, i )
		
		return [ r.raw for r in repair_symbols ]
	
	finally:
		of_release_codec_instance( session )



def decode(codec, num_source_symbols, num_repair_symbols, symbol_array):
	symbol_size   = 0
	total_symbols = num_source_symbols + num_repair_symbols
	
	session = session_ptr()
	
	try:
	
		if len(symbol_array) != total_symbols:
			raise Exception('Invalid symbols array size. Size must be num_source_symbols + num_repair_symbols in size')
		
		if of_create_codec_instance( byref(session), codec, OF_ENCODER, 1 ) != 0:
			raise Exception('Failed to create codec instance for codec: ' + str(codec))
	
		for i in range(0, len(symbol_array)):
			if symbol_array[i] is not None:
				symbol_size = len( symbol_array[i] )
				break
	
		p = of_parameters()
		
		p.nb_source_symbols      = num_source_symbols
		p.nb_repair_symbols      = num_repair_symbols
		p.encoding_symbol_length = symbol_size
		
		of_set_fec_parameters( session, byref(p) )
		
		ARR = c_void_p * total_symbols
		tbl = ARR()
				
		repairs  = list()
	
		for i in range(0, len(symbol_array)):
			if symbol_array[i] is not None:
				tbl[i] = cast( c_char_p(symbol_array[i]), c_void_p )
			else:
				tbl[i] = None
				repairs.append( i )
		
		if of_set_available_symbols( session, tbl ) != 0:
			raise Exception('Failed to set symbols')
	
		if of_finish_decoding( session ) != 0:
			raise Exception('Decoding failed!')
		
		tbl2 = ARR()
		of_get_source_symbols_tab( session, tbl2 )

		rep_buff = create_string_buffer( symbol_size )
	
		for i in repairs:
		
			memmove(rep_buff, tbl2[i], symbol_size)
			symbol_array[ i ] = rep_buff.raw
	finally:
		of_release_codec_instance( session )

		
#-------------------------------------------------------------------------------------------------

test_data = '''\
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

def test_encoding():

	d1 = test_data[:256]
	d2 = test_data[256:512]
	d3 = test_data[512:768]
	d4 = test_data[768:]
	
	num_source_symbols = 4
	num_repair_symbols = 2
	codec              = OF_CODEC_REED_SOLOMON_GF_2_M_STABLE
	symbol_array       = [d1, d2, d3, d4]
	
	print 'Encode1: ', symbol_array[1]
	print 'Encode3: ', symbol_array[3]
	
	repair_symbols = encode(codec, symbol_array, num_repair_symbols)
	
	dec_syms = symbol_array + repair_symbols
	
	dec_syms[1] = None
	dec_syms[3] = None
	
	decode(codec, num_source_symbols, num_repair_symbols, dec_syms)
	
	print 'decode1: ', dec_syms[1]
	print 'decode3: ', dec_syms[3]
