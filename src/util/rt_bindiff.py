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

# Generic RE helper: Binary diffs.

import operator
from e17p.base.text_fmt import *
from e17p.base.text_markup_ansi import *

def _bwop(d1, d2, op):
   return bytes([op(b1, b2) for (b1,b2) in zip(d1,d2)])

class BD:
   def __init__(self, f1, f2):
      self.f1 = f1
      self.f2 = f2
      l1 = self.f1.seek(0,2)
      l2 = self.f2.seek(0,2)
      if (l1 != l2):
         raise ValueError('Length mismatch: {} != {}.'.format(f1, f2))
   
   def seek(self, off, whence=0):
      return (self.f1.seek(off, whence), self.f2.seek(off, whence))
   
   def read(self, *args, **kwargs):
      return (self.f1.read(*args, **kwargs), self.f2.read(*args, **kwargs))
   
   def get_limits(self):
      i = -1
      self.seek(0)
      f1 = self.f1
      f2 = self.f2
      ds = None
      de = None
      while (True):
         i += 1
         (c1,c2) = self.read(1)
         if ((c1 == b'') or (c2 == b'')):
            if (c1 != c2):
               raise ValueError('Length mismatch.')
            break
         if (c1 == c2):
            continue
         de = i
         if (ds is None):
            ds = i
      
      if not (de is None):
         de += 1
      
      return (ds,de)

   def get_diff(self):
      (ds, de) = self.get_limits()
      if (ds is None is de):
         return None
      self.seek(ds)
      (d1, d2) = self.read(de-ds)
      return (ds,de,d1,d2)

   def print_xdiff(self, fmt_func, out=print, color=False):
      (ds,de,d1,d2) = self.get_diff()
      xdiff = _bwop(d1,d2, lambda x,y: ((x-y) % 256))
      out('--- Offsets: {:#x} {:#x}'.format(ds,de))
      d1_out = fmt_func(d1)
      d2_out = fmt_func(d2)
      dx_out = fmt_func(xdiff)
      if (color):
         d1_out = AFCC_BLUE.apply(d1_out)
         d2_out = AFCC_CYAN.apply(d2_out)
         dx_out = AFCC_YELLOW.apply(dx_out)
      
      out('D1: {}'.format(d1_out))
      out('D2: {}'.format(d2_out))
      out('DX: {}'.format(dx_out))


def _diff_files(fn1, fn2, color, *args, **kwargs):
   hdr = '-------------------------------- Diffing files: {!r} {!r}'.format(fn1, fn2)
   if (color):
      hdr = AFCC_YELLOW_D.apply(hdr)
   print(hdr)
   f1 = open(fn1, 'rb')
   f2 = open(fn2, 'rb')
   bd = BD(f1, f2)
   bd.print_xdiff(*args, color=color, **kwargs)


class _CIBytes(bytes):
   def __eq__(self, other):
      return (self.lower() == other.lower())
   def __ne__(self, other):
      return (self.lower() != other.lower())
   def __hash__(self):
      return hash(self.lower())

def main():
   import os
   import optparse
   op = optparse.OptionParser()
   op.add_option('-d', '--directories', default=False, action='store_true', dest='dirmode', help='Operate on directories.')
   op.add_option('-b', '--binary', default=False, action='store_true', dest='format_bin', help='Dump bits in base 2.')
   op.add_option('-u', '--color', default=False, action='store_true', dest='color', help='Colorize output.')
   op.add_option('-i', '--case-insensitive', default=False, action='store_true', dest='ci', help='Ignore case for filename match purposes in -d mode.')
   (opts, args) = op.parse_args()
   (fn1, fn2) = args[:2]
   
   if (opts.format_bin):
      fmt_func = bins
   else:
      fmt_func = hexs
   
   if (opts.dirmode):
      # No use trying to futz wround with encoded filenames here, let's use a sane interface instead.
      dn1 = fn1.encode()
      dn2 = fn2.encode()
      fns1 = sorted(os.listdir(dn1))
      fns2 = os.listdir(dn2)
      if (opts.ci):
         fns1 = [_CIBytes(fn) for fn in fns1]
         fns2 = [_CIBytes(fn) for fn in fns2]
      fns2 = dict((k,k) for k in fns2)
      
      for fn in fns1:
         if not (fn in fns2):
            continue
         
         p1 = os.path.join(dn1, fn)
         p2 = os.path.join(dn2, fns2[fn])
         _diff_files(p1, p2, color=opts.color, fmt_func=fmt_func)
   
   else:
      _diff_files(fn1, fn2, color=opts.color, fmt_func=fmt_func)



if (__name__ == '__main__'):
   main()
