#!/usr/bin/env python3
#Copyright 2010 Sebastian Hagen
# This file is part of e17p.

# E17p is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 
# as published by the Free Software Foundation
#
# E17p is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import distutils.util
import platform
import sys
from distutils.core import setup, Extension

if (sys.version_info[0] <= 2):
   raise Exception('E17p needs a python >= 3.0') 

if (platform.system() == 'Windows'):
   socket_libs = ['Ws2_32']
   ogl_libs = ['opengl32']
else:
   socket_libs = []
   ogl_libs = ['GL']

ext_modules = [
   Extension('e17p.ever17.ff._rle', sources=['src/e17p/ever17/ff/_rlemodule.c']),
   Extension('e17p.ever17.ff._cps', sources=['src/e17p/ever17/ff/_cpsmodule.c'], libraries=socket_libs),
   Extension('e17p.ui._effects',
             sources = ['src/e17p/ui/_effects.c'],
             libraries=ogl_libs + ['m'],
             extra_compile_args=['-O3','-ffast-math'])
]

setup(name='e17p',
   version='0.1',
   description='E17p',
   url='http://git.memespace.net/git/e17p.git',
   ext_modules=ext_modules,
   packages=(
      'e17p',
      'e17p.base', 'e17p.base.ff', 'e17p.base.codec',
      'e17p.ui', 'e17p.ui.data',
      'e17p.fantranslation',
      'e17p.never7', 'e17p.never7.ff',
      'e17p.ever17', 'e17p.ever17.ff',
      'e17p.remember11', 'e17p.remember11.ff',
   ),
   package_data={
      'e17p.ui': ['data/fonts/*'],
   },
   package_dir={'':'src'}
)

