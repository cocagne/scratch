#!/usr/bin/python 

import os
import os.path

os.environ['OPENFEC_LIB'] = './libopenfec.so'

from openfec import *


def encode_file(filename, output_dir, codec, num_parts, num_required):
	
	if not os.path.isfile( filename ):
		raise Exception('Invalid file: ' + filename)

	base_name     = os.path.basename(filename)
	total_symbols = num_parts
	num_symbols   = num_required
	num_repair    = total_symbols - num_required
	file_size     = os.stat(filename).st_size
		
	
	source = open( filename, 'rb' )
	
	if not os.path.isdir( output_dir ):
		os.makedirs( output_dir )
		
	parts = list()
	
	for i in range(0, num_parts):
		parts.append( open( os.path.join(output_dir, base_name + '_%03d' % i), 'wb' ) )
		
	block_sizes = [65536, 32768, 16384, 8192, 4096, 1024, 512, 256, 128, 64, 32, 16, 0]
	
	nleft = file_size
		
	while nleft:
		
		for symbol_size in block_sizes:
			if nleft >= symbol_size * num_symbols:
				break
		
		if symbol_size == 0:
			# copy final bytes directly. Too small for erasure encoding
			trailing_bytes = source.read( nleft )
			for p in parts:
				p.write( trailing_bytes )
			nleft = 0
		else:
			chunk_size  = symbol_size * num_symbols
			chunk       = source.read( chunk_size )
			
			assert len(chunk) == chunk_size
			
			symbols_array = list()
			
			last = 0
			next = 0
			for i in range(0,num_symbols):
				last = next
				next += symbol_size
				symbols_array.append( chunk[last:next] )
			
			repairs = encode(codec, symbols_array, num_repair)
	
			symbols_array.extend( repairs )
		
			for i in range(0, len(symbols_array)):
				parts[i].write( symbols_array[i] )
				
			nleft -= chunk_size
			
	print 'file size  = ', file_size

	for p in parts:
		p.flush()
		p.close()
		
		
		
		
def decode_file(dest_file, base_filename, file_size, parts_dir, codec, num_parts, num_required):
	if not os.path.isdir( parts_dir ):
		raise Exception('Invalid file: ' + filename)

	total_symbols = num_parts
	num_symbols   = num_required
	num_repair    = total_symbols - num_required
	
	parts  = list()
	nparts = 0
	
	for i in range(0, num_parts):
		part_fn = os.path.join(parts_dir, base_filename + '_%03d' % i)
		if os.path.exists( part_fn ):
			parts.append( open( part_fn, 'rb' ) )
			nparts += 1
		else:
			parts.append( None )
			
	if nparts < num_required:
		raise Exception('Insufficient parts for file decoding')
	
	dest = open( dest_file, 'wb' )
	
	try:
		block_sizes = [65536, 32768, 16384, 8192, 4096, 1024, 512, 256, 128, 64, 32, 16, 0]
		
		nleft = file_size
			
		while nleft:
			
			for symbol_size in block_sizes:
				if nleft >= symbol_size * num_symbols:
					break
		
			if symbol_size == 0:
				for p in parts:
					if p is not None:
						dest.write( p.read(nleft) )
						nleft = 0
						break
			else:
			
				symbols_array = list()
			
				for p in parts:
					if p is None:
						symbols_array.append( None )
					else:
						symbols_array.append( p.read(symbol_size) )
				
				decode(codec, num_symbols, num_repair, symbols_array)
		
				for i in range(0, num_symbols):
					dest.write( symbols_array[i] )
					nleft -= symbol_size
					
		dest.flush()
		dest.close()
	except Exception:
		os.unlink( dest_file )
		raise
				
	
		
		
def test():
	import time
	#src_file    = '/home/rakis/Downloads/openfec-1.2.1.tgz'
	#src_file    = '/home/rakis/devel/temp/Python-2.7.tar.bz2'
	#src_file    = '/etc/passwd'
	#src_file    = '/etc/timezone'
	src_file    = '/tmp/dsl.iso'
	parts_dir   = '/tmp/tdir'
	tgt_file    = '/tmp/tdecode'
	
	num_parts    = 50
	num_required = 43
	codec        = OF_CODEC_REED_SOLOMON_GF_2_8_STABLE
	
	if os.path.exists( parts_dir ):
		os.system('rm -r %s' % parts_dir)
	if os.path.exists( tgt_file ):
		os.system('rm -f %s' % tgt_file)
	
	senc = time.time()
	encode_file(src_file, parts_dir, codec, num_parts, num_required)
	eenc = time.time()
	
	base_filename = os.path.basename(src_file)
	file_size     = os.stat(src_file).st_size
	
	os.unlink( '%s/%s_003' % (parts_dir, base_filename) )
	
	sdec = time.time()
	decode_file(tgt_file, base_filename, file_size, parts_dir, codec, num_parts, num_required)
	edec = time.time()
	
	fmb = (file_size / 1024.0) / 1024.0
	etime = eenc - senc
	dtime = edec - sdec
	print 'Size in Mb: ', fmb, fmb/etime
	print 'Encoding time: %f sec, %f Mb/sec' % ( etime, fmb/etime )
	print 'Decoding time: %f sec, %f Mb/sec' % ( dtime, fmb/dtime )
	
test()
	