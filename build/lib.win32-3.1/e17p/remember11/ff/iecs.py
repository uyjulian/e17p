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

# Parser for R11 AFS files.
import struct
from ...base.file_data import *
from ...base.text_fmt import *


# -------------------------------------------------------------------------------- parser DS
class IECSChunk:
   CT_MAP = {}
   
   def __init__(self, ctype, dref):
      self.type = ctype
      self.data = dref

   @classmethod
   def build(cls, ctype, *args, **kwargs):
      try:
         scls = cls.CT_MAP[ctype]
      except KeyError:
         scls = cls
      return scls(ctype, *args, **kwargs)

   @classmethod
   def _reg_subcls(cls, subcls):
      cls.CT_MAP[subcls.TYPE] = subcls
      return subcls

   def __format__(self, s):
      return 'IECSChunk({0}, {1:12})'.format(self.type, self.data.get_size())
   
   def dump_data(self, out=print):
      out(self.data.get_data())

_reg_iecs_type = IECSChunk._reg_subcls

@_reg_iecs_type
class IECSChunkSetb(IECSChunk):
   TYPE = FourCC(b'Setb')
   def dump_data(self, out=print):
      il = 25
      cl = 50
      d = self.data.get_data()
      out(hexs(d[:il]))
      d = d[il:]
      
      for i in range(0,len(d)+cl,cl):
         out(hexs(d[i:i+cl]))


class IECSParser:
   def __init__(self, chunks):
      self._chunks = chunks
   
   def dump_td(self):
      d = self._td.get_data()
      for i in range(0,len(d),16):
         print(hexs(d[i:i+16]))
   
   def __iter__(self):
      for chunk in self._chunks:
         yield(chunk)
   
   @classmethod
   def build_from_file(cls, f):
      # IECS files are a sequence of chunks. Chunks start with a double FourCC id, followed by a u32 LE specifying the chunk
      # length.
      ilen = f.seek(0,2)
      f.seek(0)
      off = 0
      chunks = []
      while (True):
         chdr = f.read(12)
         if (chdr == b''):
            break
         (pp, ctype, clen) = struct.unpack(b'<LLL', chdr)
         if (pp != 1396917577):
            raise ValueError('Unknown chunk level-0 type {!a}.'.format(ctype))
         
         if (off + clen > ilen):
            raise ValueError('Chunk overflow.')
         
         ctype = FourCC(ctype)
         
         f.seek(off+clen)
         chunks.append(IECSChunk.build(ctype,DataRefFile(f, off+12, clen-12)))
         off += clen
      
      return cls(chunks)
   
   def dump_chunks(self, out=print):
      for chunk in self._chunks:
         out(repr(format(chunk)))


def _main():
   import os
   import sys
   import optparse
   op = optparse.OptionParser()
   op.add_option('-c', '--dump-chunks', dest='dump_chunk_contents', default=False, action='store_true', help='Print chunk data')
   (opts, args) = op.parse_args()
   
   for fn in args:
      print('-------- Parsing {0!a} --------'.format(fn))
      f = open(fn, 'rb')
      lp = IECSParser.build_from_file(f)
      
      lp.dump_chunks()
      #open('t1.o','w+b').write(lp._td.get_data())
      if (opts.dump_chunk_contents):
         for c in lp._chunks:
            c.dump_data()


if (__name__ == '__main__'):
   _main()
