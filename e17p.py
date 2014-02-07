#!/usr/bin/env python3
#Copyright 2010 Sebastian Hagen
# This file is part of E17p.
#
# E17p is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# E17p is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Relative imports in python mix extremely badly with running sub-modules as main programs ... so we don't do that. Use this
# wrapper script to run such modules instead.

import sys

def get_distutils_libdir():
   from distutils.command.build import get_platform
   return 'lib.{}-{}'.format(get_platform(), sys.version[0:3])

def main(build):
   import os
   import os.path
   import sys
   
   sname = sys.argv[0]
   sfname = os.path.basename(sname)
   basedir = os.path.dirname(__file__)
   if (basedir == ''):
      basedir = '.'
   
   if (build):
      # Run setup.py, and then get stuff from build/.
      from subprocess import Popen, PIPE
      # Note that setup.py doesn't appreciate being run from outside its own dir.
      p = Popen([sys.executable, './setup.py', 'build'], stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=basedir)
      (stdout, stderr) = p.communicate()
      rc = p.wait()
      if (rc):
         # Stdout in python is a text stream by default ... that's no good for us, so make a binary one from it.
         stdout_bin = sys.stdout.buffer
         
         print('./setup.py build execution failed. RC: {!r}'.format(rc))
         print('-------- STDOUT:')
         stdout_bin.write(stdout)
         print('-------- STDERR:')
         stdout_bin.write(stderr)
         sys.exit(1)
      
      spath = os.path.join(basedir, 'build', get_distutils_libdir())
   else:
      # Default behaviour: Load modules from src/
      spath = os.path.join(basedir, 'src')
   
   sys.path.insert(0, spath)
   mname = sys.argv[1]
   del(sys.argv[1])
   pname = ' '.join((sys.argv[0],mname))
   sys.argv[0] = pname
   
   if not (mname.startswith('e17p.')):
      mname = 'e17p.' + mname
   
   __import__(mname)
   m = sys.modules[mname]
   
   return m._main()

if (__name__ == '__main__'):
   main(build=False)

