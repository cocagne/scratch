#!/usr/bin/env python

from distutils.core      import setup
from distutils.extension import Extension

py_modules = ['rsa']

ext_modules = [ Extension('_rsa', ['_rsa.c',], libraries = ['ssl',]), ]

setup(name         = 'rsa',
	  version      = '0.1',
	  description  = 'Python Wrapper for OpenSSL RSA Keys',
	  author       = 'Tom Cocagne',
	  author_email = 'tom.cocagne@gmail.com',
	  py_modules   = py_modules,
	  ext_modules  = ext_modules)
