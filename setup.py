#!/usr/bin/env python
from setuptools import setup, find_packages
import sys

import versioneer

long_description = ''

if 'upload' in sys.argv:
    with open('README.rst') as f:
        long_description = f.read()


setup(
    name='codetransformer',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='Python code object transformers',
    author='Joe Jevnik and Scott Sanderson',
    author_email='joejev@gmail.com',
    packages=find_packages(),
    long_description=long_description,
    license='GPL-2',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Pre-processors',
    ],
    url='https://github.com/llllllllll/codetransformer',
    install_requires=['toolz'],
    extras_require={
        'dev': [
            'flake8==2.4.0',
            'pytest==2.8.4',
        ],
    },
)
