#include <stdio.h>
#include "../../src/lib_common/of_openfec_api.h"

/* symbols is array of valid pointers to buffers of sym_size. repair buffers will
 * be filled in */
int fec_encode( of_codec_id_t codec, int nsource, int nrepair, int sym_size,
                void *symbols[] )
{
    int              i      = 0;
    const char      *step   = "enc init";
    of_session_t    *ses    = 0;
    of_parameters_t  params = {nsource, nrepair, sym_size};
    
    if( of_create_codec_instance(&ses, codec, OF_ENCODER, 0) != OF_STATUS_OK )
        goto err_exit;
    
    step = "set params";
    if( of_set_fec_parameters(ses, &params) != OF_STATUS_OK )
        goto err_exit;

    step = "build repair";
    for (i=0; i < nrepair; i++)
    {
        if( of_build_repair_symbol(ses, symbols, nsource + i) != OF_STATUS_OK )
            goto err_exit;
    }
    
    step = "release";
    if( of_release_codec_instance(ses) != OF_STATUS_OK )
        goto err_exit;
    
    return 0;
    
    err_exit:
    fprintf(stderr, "%s failed\n", step);
    if (ses)
        of_release_codec_instance(ses);
    return -1;
}


typedef struct {
    int nrepaired;
    void ** buffers;
} DecodeContext;


void * decode_callback( void * vctx, UINT32 size, UINT32 esi )
{
    fprintf(stderr, "CB: Repairing %d\n", esi);
    DecodeContext * ctx = (DecodeContext *)vctx;
    return ctx->buffers[ ctx->nrepaired++ ];
}


int fec_decode( of_codec_id_t codec, int nsource, int nrepair, int sym_size,
                void *symbols[], void *repaired_buffers[] )
{
    const char      *step    = "dec init";
    of_session_t    *ses     = 0;
    of_parameters_t  params  = {nsource, nrepair, sym_size};
    DecodeContext    dec_ctx = {0, repaired_buffers};
    
    
    if( of_create_codec_instance(&ses, codec, OF_DECODER, 0) != OF_STATUS_OK )
        goto err_exit;
    
    step = "set params";
    if( of_set_fec_parameters(ses, &params) != OF_STATUS_OK )
        goto err_exit;

    step = "set callbacks";
    if( of_set_callback_functions(ses, 
                                  &decode_callback, 
                                  0,
                                  &dec_ctx) != OF_STATUS_OK )
        goto err_exit;

    step = "set symbols";
    if( of_set_available_symbols(ses, symbols) != OF_STATUS_OK )
        goto err_exit;
    
    step = "finalize";
    if( of_finish_decoding(ses) != OF_STATUS_OK )
        goto err_exit;

    step = "release";
    if( of_release_codec_instance(ses) != OF_STATUS_OK )
        goto err_exit;
    
    return 0;
    
    err_exit:
    fprintf(stderr, "%s failed\n", step);
    if (ses)
        of_release_codec_instance(ses);
    return -1;
}
