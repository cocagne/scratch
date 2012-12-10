
import zlib

CHUNK_SIZE = 1024 * 1024

class FileStore (object):

    def __init__(self, file_store_fn, body_db):
        
        self.file_store = open( file_store_fn, 'ab+' )
        self.file_db    = body_db.file_db


    def import_data(self, file_obj, nbytes):
        nwritten = 0
        
        self.file_store.seek( self.file_db.get_last_offset() )
        
        while nwritten != nbytes:
            chunk = file_obj.read( min(CHUNK_SIZE, nbytes-nwritten) )
            self.file_store.write( chunk )
            nwritten += len(chunk)


    def export_data(self, file_obj, offset, nbytes):
        nwritten = 0
        
        self.file_store.seek( offset )
        
        while nwritten != nbytes:
            chunk = self.file_store.read( min(CHUNK_SIZE, nbytes-nwritten) )
            file_obj.write( chunk )
            nwritten += len(chunk)

            
        
    def add_file(self, fs_f, force_zero_length = False):
        
        if force_zero_length:
            return self.file_db.add_file( 0, 0 )
        
        self.file_store.seek( self.file_db.get_last_offset() )

        c = zlib.compressobj()
        
        with open( fs_f.fq_name, 'r' ) as f:
            nwritten = 0
            zwritten = 0
            
            while nwritten < fs_f.size:
                chunk  = f.read( CHUNK_SIZE )
                zchunk = c.compress( chunk )
                if len(chunk) < CHUNK_SIZE:
                    zchunk += c.flush()
                self.file_store.write( zchunk )
                nwritten += len(chunk)
                zwritten += len(zchunk)

        return self.file_db.add_file( fs_f.size, zwritten )

    
    def extract_file(self, to_filename, offset, num_zbytes):
        with open( to_filename, 'w' ) as f:
            self.file_store.seek( offset )

            nread = 0
            d     = zlib.decompressobj()
            
            while nread != num_zbytes:
                chunk = self.file_store.read( min(CHUNK_SIZE, num_zbytes-nread) )
                nread += len(chunk)

                f.write( d.decompress(chunk) )

            f.write( d.flush() )
            
                
