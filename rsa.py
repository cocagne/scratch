#!/usr/bin/python

import sys
sys.path.append( 'build/lib.linux-i686-2.6/' )
sys.path.append( 'build/lib.linux-x86_64-2.6/' )

import os
import os.path
import tempfile
import _rsa

generate_keypair = _rsa.generate_keypair
            
class PrivateKey (object):

    def __init__(self, priv_key_str):
        self._key = _rsa.Key( priv_key_str, 1 )
        self.encrypt = self._key.encrypt
        self.decrypt = self._key.decrypt

    def sign_oneshot(self, data):
        return self._key.sign_oneshot( data )
    
        
class PublicKey (object):

    def __init__(self, pub_key_str):
        self._key = _rsa.Key( pub_key_str, 0 )
        self.encrypt = self._key.encrypt
        self.decrypt = self._key.decrypt

    def verify_oneshot(self, data, sig):
        return self._key.verify_oneshot( data, sig )

    
        

    
class Signer (object):

    def __init__(self, pri_key):
        if not isinstance(pri_key, PrivateKey):
            raise TypeError('arg #1 must be a PrivateKey instance')
        self._signer = _rsa.SigCtx( pri_key._key, _rsa.SHA256 )

    def update(self, data):
        self._signer.update( data )

    def sign(self):
        return self._signer.sign()


class Verifier (object):

    def __init__(self, pub_key):
        if not isinstance(pub_key, PublicKey):
            raise TypeError('arg #1 must be a PublicKey instance')
        self._verifier = _rsa.SigCtx( pub_key._key, _rsa.SHA256 )

    def update(self, data):
        self._verifier.update( data )

    def verify(self, sig):
        return self._verifier.verify(sig)


def phex(s):
    return ''.join( ['%x' % ord(c) for c in s] )
    

import time
start = time.time()
pri_str, pub_str = generate_keypair( 512 )

print "Gen duration: ", time.time() - start

print '-'*80
print 'Len prikey: ', len(pri_str)
print '-'*80
print 'Len pubkey: ', len(pub_str)

pri = PrivateKey( pri_str )
pub = PublicKey( pub_str )

data = "Hello World"

#sig = pri.sign_oneshot( data )
s = Signer( pri )

s.update( "Hello " )
s.update( "World"  )
 
sig = s.sign()

print 'Sig len: ', len(sig)

#print 'Verified: ', pub.verify_oneshot( data, sig )
v = Verifier( pub )
v.update(data)
print 'Verified: ', v.verify(sig)

enc = pri.encrypt( data )
print 'Encrypted: ', phex(enc)
print 'Decrypted: ', pub.decrypt( enc )
