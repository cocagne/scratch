#!/bin/sh

/usr/bin/gcc  -fPIC   -shared -Wl,-soname,libtlib.so -o libtlib.so tlib.c -L. -lopenfec