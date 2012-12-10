
#include <stdio.h>

typedef enum { A, B } tenum;

int main()
{
    printf("size = %d\n", sizeof(tenum));
    return 0;
}