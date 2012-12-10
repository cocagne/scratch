/* Compile with gcc rsa_test.c -lssl -lcrypto */

#include <stdio.h>
#include <openssl/rsa.h>
#include <openssl/evp.h>
#include <openssl/objects.h>
#include <openssl/x509.h>
#include <openssl/err.h>
#include <openssl/pem.h>
#include <openssl/ssl.h>
#include <openssl/bn.h>


EVP_PKEY * load_private_key( const char * fname )
{
   FILE *          fp;
   EVP_PKEY *      pkey;
   
   fp = fopen (fname, "r");
   
   if (fp == NULL)
      return NULL;
   
   pkey = PEM_read_PrivateKey(fp, NULL, NULL, NULL);
   fclose (fp);

   
   if (pkey == NULL)
      ERR_print_errors_fp (stderr);

   return pkey;
}


unsigned char * sign_it( EVP_PKEY * pkey, const EVP_MD * htype, char * data, int data_len, int * sig_len )
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
      
      ERR_print_errors_fp(stderr);
   }
   
   return sig;
}


EVP_PKEY * load_public_key( const char * fname )
{
   FILE *     fp;
   EVP_PKEY * pkey;
   
   fp = fopen (fname, "r");
   
   if (fp == NULL)
      return NULL;
   
   pkey = PEM_read_PUBKEY(fp, NULL, NULL, NULL);
   fclose (fp);
   
   if (pkey == NULL) 
      ERR_print_errors_fp (stderr);

   return pkey;
}


int verify_sig( EVP_PKEY * pkey, const EVP_MD * htype, char * data, int data_len, unsigned char * sig, int sig_len )
{
   EVP_MD_CTX     md_ctx;
   
   EVP_VerifyInit   (&md_ctx, htype);
   EVP_VerifyUpdate (&md_ctx, data, data_len);
   
   if ( EVP_VerifyFinal (&md_ctx, sig, sig_len, pkey) != 1)
   {
      ERR_print_errors_fp (stderr);
      return 0;
   }

   return 1;
}


void gen_keys( const char * priv_file, const char * pub_file )
{
   FILE   * fp;
   RSA    * rsa = RSA_new();
   BIGNUM * e   = BN_new();
   EVP_PKEY * pkey = EVP_PKEY_new();
   
   BN_dec2bn(&e, "65537");
   
   RSA_generate_key_ex(rsa, 512, e, NULL);

   fp = fopen(priv_file, "w");
   PEM_write_RSAPrivateKey(fp, rsa, 0, 0, 0, 0, 0);
   fclose(fp);

   fp = fopen(pub_file, "w");
   EVP_PKEY_assign_RSA(pkey,rsa);
   PEM_write_PUBKEY(fp, pkey);
   fclose(fp);

   BN_free(e);
   EVP_PKEY_free(pkey); // Also deletes rsa
}



int main()
{
   EVP_PKEY      * priv_key   = 0;
   EVP_PKEY      * pub_key    = 0;
   char          * data       = "Hello World";
   int             data_len   = strlen(data);
   unsigned char * sig        = 0;
   int             sig_len    = 0;

   gen_keys( "priv.pem", "pub.pem" );

   priv_key   = load_private_key( "priv.pem" );
   pub_key    = load_public_key2( "pub.pem" );

   if (!priv_key || !pub_key)
   {
      printf("failed to load keys\n");
      return 1;
   }
   
   sig = sign_it( priv_key, EVP_sha1(), data, data_len, &sig_len );

   if (!sig)
   {
      printf("Failed to generate signature\n");
      return 1;
   }

   if ( verify_sig( pub_key, EVP_sha1(), data, data_len, sig, sig_len ) )
      printf("Signature matches!!\n");
   else
      printf("*** SIG FAILED ***\n");

   free(sig);
   EVP_PKEY_free (priv_key);
   EVP_PKEY_free (pub_key);

   return 0;
}


