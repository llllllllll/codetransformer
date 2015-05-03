#!/usr/bin/env python
from distutils.core import setup
import sys

long_description = ''

if 'upload' in sys.argv:
    with open('README.rst') as f:
        long_description = f.read()

setup(
    name='codetransformer',
    version='0.4.0',
    description='Python code object transformers',
    author='Joe Jevnik',
    author_email='joejev@gmail.com',
    packages=[
        'codetransformer',
    ],
    long_description=long_description,
    license='GPL-2',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Pre-processors',
    ],
    url='https://github.com/llllllllll/codetransformer',
)
