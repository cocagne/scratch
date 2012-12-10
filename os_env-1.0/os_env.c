#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>

#include "config.h"

int main( int argc, char * argv[] )
{
   int i = 0;
   
   char ** v = malloc( sizeof(char*) * (argc + 2) );
   
   for( ; i < argc; i++ )
      v[i+1] = argv[i];
   
   v[0] = "python";
   v[1] = OS_ENV_PY;
   v[argc+1] = NULL;
   
   execv("/usr/bin/python", v);
   
   return 1;
}

