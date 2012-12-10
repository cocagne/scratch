#include <Python.h>

#include <openssl/rsa.h>
#include <openssl/evp.h>
#include <openssl/bn.h>
#include <openssl/rand.h>


static unsigned char * pub_der_encode( RSA *rsa, int *len )
{
   unsigned char *buff, *next;
   *len = i2d_RSAPublicKey(rsa, NULL);
   buff = next = (unsigned char *) malloc(*len);
   i2d_RSAPublicKey(rsa, &next);
   return buff;
}


static unsigned char * pri_der_encode( RSA *rsa, int *len )
{
   unsigned char *buff, *next;
   *len = i2d_RSAPrivateKey(rsa, NULL);
   buff = next = (unsigned char *) malloc(*len);
   i2d_RSAPrivateKey(rsa, &next);
   return buff;
}

static EVP_PKEY * pub_der_decode( const unsigned char * buff, int len )
{
   return d2i_PublicKey(EVP_PKEY_RSA, NULL, &buff, len);
}


static EVP_PKEY * pri_der_decode( const unsigned char * buff, int len )
{
   return d2i_PrivateKey(EVP_PKEY_RSA, NULL, &buff, len);
}


void generate_keypair( int nbits,
                       unsigned char ** priv_der, int * priv_len,
                       unsigned char ** pub_der,  int * pub_len )
{
   RSA      * rsa  = RSA_new();
   BIGNUM   * e    = BN_new();
   
   BN_dec2bn(&e, "65537");

   do
   {
      RSA_generate_key_ex(rsa, nbits, e, NULL);
   }
   while( !RSA_check_key(rsa) );

   *priv_der = pri_der_encode( rsa, priv_len );
   *pub_der  = pub_der_encode( rsa, pub_len  );
   
   BN_free(e);
   RSA_free(rsa);
}



static unsigned char * sign_it( EVP_PKEY * pkey, const EVP_MD * htype, unsigned char * data, int data_len, unsigned int * sig_len )
{
   EVP_MD_CTX     md_ctx;
   unsigned char *sig = malloc( EVP_PKEY_size(pkey) );

   *sig_len = EVP_PKEY_size(pkey);
   
   EVP_SignInit   (&md_ctx, htype);
   EVP_SignUpdate (&md_ctx, data, data_len);
      
   if (EVP_SignFinal (&md_ctx, sig, sig_len, pkey) != 1)
   {
      free(sig);
      sig = 0;
      *sig_len = 0;
   }
   
   return sig;
}


static int verify_sig( EVP_PKEY * pkey, const EVP_MD * htype, unsigned char * data, int data_len, unsigned char * sig, unsigned int sig_len )
{
   EVP_MD_CTX     md_ctx;
   
   EVP_VerifyInit   (&md_ctx, htype);
   EVP_VerifyUpdate (&md_ctx, data, data_len);
   
   if ( EVP_VerifyFinal (&md_ctx, sig, sig_len, pkey) != 1)
      return 0;

   return 1;
}


/******************************************************************************
 * 
 *                         Python Module
 * 
 *****************************************************************************/

typedef enum 
{
    RSA_SHA1,
    RSA_SHA224, 
    RSA_SHA256,
    RSA_SHA384, 
    RSA_SHA512
} RSA_Hash;


typedef struct 
{
   PyObject_HEAD
   EVP_PKEY * pkey;
   int        is_private;
}PyKey;


typedef struct 
{
   PyObject_HEAD
   PyKey      *key;
   EVP_MD_CTX  md_ctx;
}PySigCtx;


typedef struct 
{
   PyObject_HEAD
   EVP_CIPHER_CTX ctx;
   int            is_encrypt;
}PyAES;



/******************************************************************************
 * Private Key
 *****************************************************************************/

static PyObject * key_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
   PyKey *self = (PyKey *) type->tp_alloc(type, 0);
   
   if (!self)
      return NULL;
   
   self->pkey       = NULL;
   self->is_private = 0;
   
   return (PyObject *) self;
}


static void key_dealloc( PyKey * self )
{
   if (self->pkey != NULL )
      EVP_PKEY_free(self->pkey);
        
   self->ob_type->tp_free( (PyObject *) self );
}


static int key_init( PyKey *self, PyObject *args, PyObject *kwds )
{
   const unsigned char * der_key;
   int                   der_len;
   int                   is_private = 0;
        
   if ( self->pkey != NULL )
   {
      PyErr_SetString(PyExc_TypeError, "Type cannot be re-initialized");
      return -1;
   }
    
   if ( ! PyArg_ParseTuple(args, "t#i", &der_key, &der_len, &is_private) )
   {
      return -1;
   }
   self->is_private = is_private;

   if (is_private)
      self->pkey = pri_der_decode( der_key, der_len );
   else
      self->pkey = pub_der_decode( der_key, der_len );

   if ( self->pkey == NULL )
   {
      PyErr_SetString(PyExc_Exception, "Failed to load key");
      return -1;
   }
    
    return 0;
}

static PyObject * key_sign_oneshot( PyKey * self, PyObject * args )
{
   unsigned char * sig;
   unsigned int    sig_len;
   unsigned char * data;
   int             data_len;
   PyObject      * py_sig;
   const EVP_MD  * htype;
   int             hash_type = RSA_SHA1;
    
   if ( self->pkey == NULL ) {
      PyErr_SetString(PyExc_Exception, "Type not initialized");
      return NULL;
   }

   if ( !self->is_private ) {
      PyErr_SetString(PyExc_Exception, "Cannot sign with a public key");
      return NULL;
   }
    
   if ( ! PyArg_ParseTuple(args, "t#|i", &data, &data_len, &hash_type) )
   {
      return NULL;
   }

   switch (hash_type)
   {
    case RSA_SHA1  : htype = EVP_sha1();   break;
    case RSA_SHA224: htype = EVP_sha224(); break;
    case RSA_SHA256: htype = EVP_sha256(); break;
    case RSA_SHA384: htype = EVP_sha384(); break;
    case RSA_SHA512: htype = EVP_sha512(); break;
    default:
       return 0;
   };

   sig = sign_it(self->pkey, htype, data, data_len, &sig_len);

   if (!sig)
   {
      PyErr_SetString(PyExc_Exception, "Failed to load private key");
      return NULL;
   }

   py_sig = PyString_FromStringAndSize((const char *) sig, sig_len);

   free(sig);

   return py_sig;    
}


static PyObject * key_verify_oneshot( PyKey * self, PyObject * args )
{
   unsigned char * sig;
   unsigned int    sig_len;
   unsigned char * data;
   int             data_len;
   const EVP_MD  * htype;
   int             hash_type = RSA_SHA1;
   
    
   if ( self->pkey == NULL ) {
      PyErr_SetString(PyExc_Exception, "Type not initialized");
      return NULL;
   }

   if ( self->is_private ) {
      PyErr_SetString(PyExc_Exception, "Cannot verify with a private key");
      return NULL;
   }
    
   if ( ! PyArg_ParseTuple(args, "t#t#|i", &data, &data_len, &sig, &sig_len, &hash_type) )
   {
      return NULL;
   }

   switch (hash_type)
   {
    case RSA_SHA1  : htype = EVP_sha1();   break;
    case RSA_SHA224: htype = EVP_sha224(); break;
    case RSA_SHA256: htype = EVP_sha256(); break;
    case RSA_SHA384: htype = EVP_sha384(); break;
    case RSA_SHA512: htype = EVP_sha512(); break;
    default:
       return 0;
   };

   if ( verify_sig(self->pkey, htype, data, data_len, sig, sig_len) )
      Py_RETURN_TRUE;
   else
      Py_RETURN_FALSE;
}


static PyObject * key_encrypt( PyKey * self, PyObject * args )
{
   unsigned char * data;
   int             data_len;
   unsigned char * enc_buff;
   int             enc_len;
   PyObject      * py_enc;
   RSA           * rsa;
   
   if ( self->pkey == NULL ) {
      PyErr_SetString(PyExc_Exception, "Type not initialized");
      return NULL;
   }

   if ( ! PyArg_ParseTuple(args, "t#", &data, &data_len) )
   {
      return NULL;
   }

   rsa = EVP_PKEY_get1_RSA( self->pkey );

   enc_buff = malloc( RSA_size(rsa) );

   if ( self->is_private )
      enc_len = RSA_private_encrypt( data_len, data, enc_buff, rsa, RSA_PKCS1_PADDING );
   else
      enc_len = RSA_public_encrypt( data_len, data, enc_buff, rsa, RSA_PKCS1_OAEP_PADDING );

   RSA_free(rsa);

   if ( enc_len != -1 )
      py_enc = PyString_FromStringAndSize((const char *) enc_buff, enc_len);

   free(enc_buff);

   if ( enc_len == -1 )
   {
      PyErr_SetString(PyExc_Exception, "Encryption failed");
      return NULL;
   }

   return py_enc;
}

static PyObject * key_decrypt( PyKey * self, PyObject * args )
{
   unsigned char * data;
   int             data_len;
   unsigned char * enc_buff;
   int             enc_len;
   PyObject      * py_enc;
   RSA           * rsa;
   
   if ( self->pkey == NULL ) {
      PyErr_SetString(PyExc_Exception, "Type not initialized");
      return NULL;
   }

   if ( ! PyArg_ParseTuple(args, "t#", &data, &data_len) )
   {
      return NULL;
   }

   rsa = EVP_PKEY_get1_RSA( self->pkey );

   enc_buff = malloc( RSA_size(rsa) );

   if ( self->is_private )
      enc_len = RSA_private_decrypt( data_len, data, enc_buff, rsa, RSA_PKCS1_OAEP_PADDING );
   else
      enc_len = RSA_public_decrypt( data_len, data, enc_buff, rsa, RSA_PKCS1_PADDING );

   RSA_free(rsa);

   if ( enc_len != -1 )
      py_enc = PyString_FromStringAndSize((const char *) enc_buff, enc_len);

   free(enc_buff);

   if ( enc_len == -1 )
   {
      PyErr_SetString(PyExc_Exception, "Decryption failed");
      return NULL;
   }

   return py_enc;
}



static PyMethodDef PyKey_methods[] = {
    {"sign_oneshot", (PyCFunction) key_sign_oneshot, METH_VARARGS,
     PyDoc_STR("Signs the given data and returns the signature string ")
    },
    {"verify_oneshot", (PyCFunction) key_verify_oneshot, METH_VARARGS,
     PyDoc_STR("Verifies the data and signature string ")
    },
    {"encrypt", (PyCFunction) key_encrypt, METH_VARARGS,
     PyDoc_STR("Encrypts the string")
    },
    {"decrypt", (PyCFunction) key_decrypt, METH_VARARGS,
     PyDoc_STR("Decrypts the string")
    },
    {NULL} /* Sentinel */
};


static PyTypeObject PyKey_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_rsa.Key",            /*tp_name*/
    sizeof(PyKey),         /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    /* methods */
    (destructor)key_dealloc,    /*tp_dealloc*/
    0,                          /*tp_print*/
    0,                          /*tp_getattr*/
    0,                          /*tp_setattr*/
    0,                          /*tp_compare*/
    0,                          /*tp_repr*/
    0,                          /*tp_as_number*/
    0,                          /*tp_as_sequence*/
    0,                          /*tp_as_mapping*/
    0,                          /*tp_hash*/
    0,                          /*tp_call*/
    0,                          /*tp_str*/
    0,                          /*tp_getattro*/
    0,                          /*tp_setattro*/
    0,                          /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,         /*tp_flags*/
    "Key",           /*tp_doc*/
    0,                          /*tp_traverse*/
    0,                          /*tp_clear*/
    0,                          /*tp_richcompare*/
    0,                          /*tp_weaklistoffset*/
    0,                          /*tp_iter*/
    0,                          /*tp_iternext*/
    PyKey_methods,         /*tp_methods*/
    0,                          /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    (initproc)key_init,         /*tp_init*/
    0,                          /*tp_alloc*/
    key_new,                    /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};



/******************************************************************************
 * SigCtx
 *****************************************************************************/

static PyObject * sigctx_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
   PySigCtx *self = (PySigCtx *) type->tp_alloc(type, 0);
   
   if (!self)
      return NULL;
   
   self->key = (PyKey *)Py_None;

   Py_INCREF( (PyObject *) self->key );
   
   return (PyObject *) self;
}


static void sigctx_dealloc( PySigCtx * self )
{
   Py_XDECREF( (PyObject *)self->key );
        
   self->ob_type->tp_free( (PyObject *) self );
}


static int sigctx_init( PySigCtx *self, PyObject *args, PyObject *kwds )
{
   PyKey        * key;
   const EVP_MD * htype;
   int            hash_type = RSA_SHA1;
   
   if ( ! PyArg_ParseTuple(args, "O|i", &key, &hash_type) )
   {
      return -1;
   }

   if ( !PyObject_TypeCheck((PyObject*)key, &PyKey_Type) )
   {
      PyErr_SetString(PyExc_TypeError, "arg #1 must be an instance of _rsa.PrivateKey or _rsa.Key");
      return -1;
   }

   switch (hash_type)
   {
    case RSA_SHA1  : htype = EVP_sha1();   break;
    case RSA_SHA224: htype = EVP_sha224(); break;
    case RSA_SHA256: htype = EVP_sha256(); break;
    case RSA_SHA384: htype = EVP_sha384(); break;
    case RSA_SHA512: htype = EVP_sha512(); break;
    default:
       return 0;
   };

   self->key = key;

   Py_INCREF((PyObject*) self->key);

   if ( self->key->is_private )
      EVP_SignInit(&self->md_ctx, htype);
   else
      EVP_VerifyInit(&self->md_ctx, htype);

   return 0;
}


static PyObject * sigctx_update( PySigCtx * self, PyObject * args )
{
   unsigned char * data;
   int             data_len;
       
   if ( ! PyArg_ParseTuple(args, "t#", &data, &data_len) )
   {
      return NULL;
   }

   if (self->key->is_private)
      EVP_SignUpdate (&self->md_ctx, data, data_len);
   else
      EVP_VerifyUpdate (&self->md_ctx, data, data_len);
   
   Py_RETURN_NONE;
}



static PyObject * sigctx_sign( PySigCtx * self )
{
   PyObject      *py_sig  = 0;
   EVP_PKEY      *pkey    = self->key->pkey;
   unsigned int   sig_len = EVP_PKEY_size( pkey );
   unsigned char *sig     = malloc( sig_len );

   if ( !self->key->is_private )
   {
      PyErr_SetString(PyExc_Exception, "Signature cannot be created with a Public Key");
      return NULL;
   }
      
   if (EVP_SignFinal (&self->md_ctx, sig, &sig_len, pkey) != 1)
   {
      free(sig);
      PyErr_SetString(PyExc_Exception, "Signature creation failed");
      return NULL;
   }
   
   py_sig = PyString_FromStringAndSize((const char *) sig, sig_len);

   free(sig);

   return py_sig;
}


static PyObject * sigctx_verify( PySigCtx * self, PyObject * args )
{
   unsigned char * sig;
   int             sig_len;
   EVP_PKEY      * pkey = self->key->pkey;

   if ( self->key->is_private )
   {
      PyErr_SetString(PyExc_Exception, "Signature cannot be verified with a Private Key");
      return NULL;
   }
   
   if ( ! PyArg_ParseTuple(args, "t#", &sig, &sig_len) )
   {
      return NULL;
   }

   if ( EVP_VerifyFinal (&self->md_ctx, sig, sig_len, pkey) == 1 )
      Py_RETURN_TRUE;
   else
      Py_RETURN_FALSE;
}



static PyMethodDef PySigCtx_methods[] = {
    {"update", (PyCFunction) sigctx_update, METH_VARARGS,
     PyDoc_STR("Updates the signer's context with the given data. Subsequent calls to t"
               "his method are cumulative")
    },
    {"sign", (PyCFunction) sigctx_sign, METH_NOARGS,
     PyDoc_STR("Signs the data passed to update")
    },
    {"verify", (PyCFunction) sigctx_verify, METH_VARARGS,
     PyDoc_STR("Verifies the data passed to update")
    },
    {NULL} /* Sentinel */
};


static PyTypeObject PySigCtx_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_rsa.SigCtx",            /*tp_name*/
    sizeof(PySigCtx),         /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    /* methods */
    (destructor)sigctx_dealloc,    /*tp_dealloc*/
    0,                          /*tp_print*/
    0,                          /*tp_getattr*/
    0,                          /*tp_setattr*/
    0,                          /*tp_compare*/
    0,                          /*tp_repr*/
    0,                          /*tp_as_number*/
    0,                          /*tp_as_sequence*/
    0,                          /*tp_as_mapping*/
    0,                          /*tp_hash*/
    0,                          /*tp_call*/
    0,                          /*tp_str*/
    0,                          /*tp_getattro*/
    0,                          /*tp_setattro*/
    0,                          /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,         /*tp_flags*/
    "SigCtx",           /*tp_doc*/
    0,                          /*tp_traverse*/
    0,                          /*tp_clear*/
    0,                          /*tp_richcompare*/
    0,                          /*tp_weaklistoffset*/
    0,                          /*tp_iter*/
    0,                          /*tp_iternext*/
    PySigCtx_methods,         /*tp_methods*/
    0,                          /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    (initproc)sigctx_init,         /*tp_init*/
    0,                          /*tp_alloc*/
    sigctx_new,                    /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};


/***********************************************************************************/


static PyObject * py_generate_keypair( PyObject * self, PyObject * args )
{
   int             nbits;
   unsigned char * pri_der;
   unsigned char * pub_der;
   int             pri_len;
   int             pub_len;
       
   if ( ! PyArg_ParseTuple(args, "i", &nbits) )
   {
      return NULL;
   }

   Py_BEGIN_ALLOW_THREADS
   
   generate_keypair( nbits, &pri_der, &pri_len, &pub_der, &pub_len );

   Py_END_ALLOW_THREADS

   return Py_BuildValue( "(s#,s#)", pri_der, pri_len, pub_der, pub_len );
}



static PyMethodDef rsa_module_methods[] = {
    {"generate_keypair", (PyCFunction) py_generate_keypair, METH_VARARGS,
            PyDoc_STR("Generates a new keypair")
    },
    {NULL} /* Sentinel */
};


PyMODINIT_FUNC
init_rsa(void)
{
   int       init_ok    = 0;
   PyObject *m          = NULL;
   PyObject *os         = NULL;
   PyObject *py_urandom = NULL;
    
   os = PyImport_ImportModule("os");
    
   if (os == NULL)
      return;
    
   py_urandom = PyObject_GetAttrString(os, "urandom");

   if ( py_urandom && PyCallable_Check(py_urandom) )
   {
      PyObject *args = Py_BuildValue("(i)", 32);
      if ( args )
      {
         PyObject *randstr = PyObject_CallObject(py_urandom, args);
         if ( randstr && PyString_Check(randstr))
         {
            char       *buff = NULL;
            Py_ssize_t  slen = 0;
            if (!PyString_AsStringAndSize(randstr, &buff, &slen))
            {
               RAND_seed( buff, slen );

               init_ok = 1;
            }
         }
         Py_XDECREF(randstr);
      }
      Py_XDECREF(args);
   }
    
   Py_XDECREF(os);
   Py_XDECREF(py_urandom);
    
   if (!init_ok)
   {
      PyErr_SetString(PyExc_ImportError, "Initialization failed");
      return;
   }
    
            
   if ( PyType_Ready(&PyKey_Type)    < 0 ||
        PyType_Ready(&PySigCtx_Type) < 0 )
      return;
        
   m = Py_InitModule3("_rsa", rsa_module_methods,"RSA keys");
        
   if (m == NULL)
      return;
    
   Py_INCREF(&PyKey_Type);
   Py_INCREF(&PySigCtx_Type);
    
   PyModule_AddObject(m, "Key", (PyObject*) &PyKey_Type );
   PyModule_AddObject(m, "SigCtx",     (PyObject*) &PySigCtx_Type );

   PyModule_AddIntConstant(m, "SHA1",   RSA_SHA1);
   PyModule_AddIntConstant(m, "SHA224", RSA_SHA224);
   PyModule_AddIntConstant(m, "SHA256", RSA_SHA256);
   PyModule_AddIntConstant(m, "SHA384", RSA_SHA384);
   PyModule_AddIntConstant(m, "SHA512", RSA_SHA512);
}

#if 0
/******************************************************************************
 * 
 *                         AES Oneshot
 * 
 *****************************************************************************/



unsigned char * aes_oneshot_encrypt( const unsigned char * key, int key_len,
                                     const unsigned char * salt, int salt_len,
                                     const unsigned char * data, int data_len,
                                     int * out_len)
{
   int             nalloc    = 0;
   int             npartial  = 0;
   int             nfinal    = 0;
   unsigned char * encrypted = 0;
   unsigned char   key_buff[SHA256_DIGEST_LENGTH];
   unsigned char   iv_buff[SHA256_DIGEST_LENGTH];

   *out_len = 0;
   
   SHA256( key, key_len, key_buff );
   SHA256( salt, salt_len, iv_buff );

   EVP_CIPHER_CTX ctx;

   EVP_EncryptInit(&ctx, EVP_aes_256_cbc(), key_buff, iv_buff);

   nalloc = data_len + EVP_CIPHER_CTX_block_size(&ctx);

   encrypted = (unsigned char *) malloc( nalloc );

   EVP_EncryptUpdate(&ctx, encrypted, &npartial, data, data_len);

   
   EVP_EncryptFinal_ex(&ctx, encrypted+npartial, &nfinal);

   *out_len = npartial + nfinal;
   
   return encrypted;
}





/******************************************************************************
 * AES
 *****************************************************************************/

static PyObject * pyaes_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
   PyAES *self = (PyAES *) type->tp_alloc(type, 0);
   
   if (!self)
      return NULL;
   
   return (PyObject *) self;
}


static void pyaes_dealloc( PyAES * self )
{        
   self->ob_type->tp_free( (PyObject *) self );
}


static int pyaes_init( PyAES *self, PyObject *args, PyObject *kwds )
{
   int             nbits;
   int             is_encrypt;
   unsigned char * key;
   unsigned char * iv;
   int             key_len;
   int             iv_len;
   EVP_CIPHER    * cipher_type;
   
   if ( ! PyArg_ParseTuple(args, "iit#t#", &nbits, &is_encrypt, &key, &key_len, &iv, &iv_len) )
   {
      return -1;
   }
   
   switch (nbits)
   {
    case RSA_AES128 : cipher_type = EVP_aes_128_cbc(); break;
    case RSA_AES256 : cipher_type = EVP_aes_256_cbc(); break;
    default:
       PyErr_SetString(PyExc_TypeError, "Invalid AES bit size");
       return -1;
   };

   
   if ( key_len != EVP_CIPHER_key_length(cipher_type) )
   {
      PyErr_SetString(PyExc_TypeError, "Invalid AES key size");
      return -1;
   }


   if ( iv_len != EVP_CIPHER_block_size(cipher_type) )
   {
      PyErr_SetString(PyExc_TypeError, "Invalid AES iv size");
      return -1;
   }

   self->is_encrypt = is_encrypt;

   if ( self->is_encrypt )
      EVP_EncryptInit(&self->ctx, cipher_type, key, iv);
   else
      EVP_DecryptInit(&self->ctx, cipher_type, key, iv);

   return 0;
}


static PyObject * pyaes_update( PyAES * self, PyObject * args )
{
   PyObject      * ret;
   unsigned char * data;
   int             data_len;
       
   if ( ! PyArg_ParseTuple(args, "t#", &data, &data_len) )
   {
      return NULL;
   }

   if (self->is_encrypt)
   {
      int enc_len = 0;
      int nalloc  = data_len + EVP_CIPHER_CTX_block_size(&self->ctx);
      
      char * encrypted = (unsigned char *) malloc( nalloc );
      
      EVP_EncryptUpdate(&self->ctx, encrypted, &enc_len, data, data_len);

      ret = PyString_FromStringAndSize((const char *) encrypted, enc_len);

      free( encrypted );
   }
   else
   {
      
   }
   
   Py_INCREF(ret);
   return ret;
}



static PyObject * pyaes_sign( PyAES * self )
{
   PyObject      *py_sig  = 0;
   EVP_PKEY      *pkey    = self->key->pkey;
   unsigned int   sig_len = EVP_PKEY_size( pkey );
   unsigned char *sig     = malloc( sig_len );

   if ( !self->is_encrypt )
   {
      PyErr_SetString(PyExc_Exception, "Signature cannot be created with a Public Key");
      return NULL;
   }
      
   if (EVP_SignFinal (&self->md_ctx, sig, &sig_len, pkey) != 1)
   {
      free(sig);
      PyErr_SetString(PyExc_Exception, "Signature creation failed");
      return NULL;
   }
   
   py_sig = PyString_FromStringAndSize((const char *) sig, sig_len);

   free(sig);

   return py_sig;
}


static PyObject * pyaes_verify( PyAES * self, PyObject * args )
{
   unsigned char * sig;
   int             sig_len;
   EVP_PKEY      * pkey = self->key->pkey;

   if ( self->is_encrypt )
   {
      PyErr_SetString(PyExc_Exception, "Signature cannot be verified with a Private Key");
      return NULL;
   }
   
   if ( ! PyArg_ParseTuple(args, "t#", &sig, &sig_len) )
   {
      return NULL;
   }

   if ( EVP_VerifyFinal (&self->md_ctx, sig, sig_len, pkey) == 1 )
      Py_RETURN_TRUE;
   else
      Py_RETURN_FALSE;
}



static PyMethodDef PyAES_methods[] = {
    {"update", (PyCFunction) pyaes_update, METH_VARARGS,
     PyDoc_STR("Updates the signer's context with the given data. Subsequent calls to t"
               "his method are cumulative")
    },
    {"sign", (PyCFunction) pyaes_sign, METH_NOARGS,
     PyDoc_STR("Signs the data passed to update")
    },
    {"verify", (PyCFunction) pyaes_verify, METH_VARARGS,
     PyDoc_STR("Verifies the data passed to update")
    },
    {NULL} /* Sentinel */
};


static PyTypeObject PyAES_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_rsa.AES",            /*tp_name*/
    sizeof(PyAES),         /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    /* methods */
    (destructor)pyaes_dealloc,    /*tp_dealloc*/
    0,                          /*tp_print*/
    0,                          /*tp_getattr*/
    0,                          /*tp_setattr*/
    0,                          /*tp_compare*/
    0,                          /*tp_repr*/
    0,                          /*tp_as_number*/
    0,                          /*tp_as_sequence*/
    0,                          /*tp_as_mapping*/
    0,                          /*tp_hash*/
    0,                          /*tp_call*/
    0,                          /*tp_str*/
    0,                          /*tp_getattro*/
    0,                          /*tp_setattro*/
    0,                          /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,         /*tp_flags*/
    "AES",           /*tp_doc*/
    0,                          /*tp_traverse*/
    0,                          /*tp_clear*/
    0,                          /*tp_richcompare*/
    0,                          /*tp_weaklistoffset*/
    0,                          /*tp_iter*/
    0,                          /*tp_iternext*/
    PyAES_methods,         /*tp_methods*/
    0,                          /*tp_members*/
    0,                          /*tp_getset*/
    0,                          /*tp_base*/
    0,                          /*tp_dict*/
    0,                          /*tp_descr_get*/
    0,                          /*tp_descr_set*/
    0,                          /*tp_dictoffset*/
    (initproc)pyaes_init,         /*tp_init*/
    0,                          /*tp_alloc*/
    pyaes_new,                    /*tp_new*/
    0,                          /*tp_free*/
    0,                          /*tp_is_gc*/
};

#endif
