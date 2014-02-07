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

# Parser for Ever17 files, based on reverse-engineering of dat top-level format .

import struct
from ...base.file_data import *
from .rle import e17_rle_unpack

# -------------------------------------------------------------------------------- parser DS
class LNKChunk(DataRefFile):
   def __init__(self, f, off, size, name, is_compressed):
      if (len(name) > 24):
         raise ValueError('Invalid name {!r}; expected at most 24 bytes.'.format(name))
      
      super().__init__(f, off, size)
      self.name = name
      self.is_compressed = is_compressed
   
   
   lnd_hdr_fmt = '<4sHHLL'
   lnd_hdr_sz = struct.calcsize(lnd_hdr_fmt)
   def _decompress_lnd_chunk(self):
      from io import BytesIO
      
      self.f.seek(self.off)
      data = bytearray(self.size)
      self.f.readinto(data)
      mdata = memoryview(data)
      (preamble, uk1, uk2, size_plain, uk3) = struct.unpack(self.lnd_hdr_fmt, mdata[:self.lnd_hdr_sz])
      if (preamble != b'lnd\x00'):
         raise ValueError('Unexpected lnd preamble {!r}.'.format(preamble))
      
      bd_plain = e17_rle_unpack(mdata[self.lnd_hdr_sz:], size_plain)
      bd_f = BytesIO(bd_plain)
      return DataRefFile(bd_f, 0, len(bd_plain))
   
   def get_dref_plain(self):
      if (self.is_compressed):
         return self._decompress_lnd_chunk()
      return self
   
   def get_data_plain(self):
      return self.get_dref_plain().get_data()
   
   def __repr__(self):
      return '{}{}'.format(type(self).__name__, (self.f, self.off, self.size, self.name, self.is_compressed))
      

class LNKParser:
   def __init__(self, chunks):
      self._chunks = chunks
   
   def __iter__(self):
      for c in self._chunks:
         yield(c)
   
   @classmethod
   def build_from_file(cls, f):
      # LNK files start with a static 4 byte preamble, followed by a 4 LE uint specifying the number of contained chunks,
      # followed by 8 bytes of unknown (and possibly always zero) data.
      preamble = f.read(4)
      if (preamble != b'LNK\x00'):
         raise ValueError('Unexpected preamble {0!r}.'.format(preamble))
      fc_data = f.read(4)
      (fc,) = struct.unpack(b'<L', fc_data)
      data_uk1 = f.read(8)
      
      chunks = []
      
      # Chunk data offsets are relative to the beginning of the data section of this file, which starts right after the
      # chunk metadata table.
      data_base_off = 16 + fc*32
      tlen = 0
      
      # Chunk metadata entries look like the following:
      # - chunk data offset (32bit LE uint)
      # - chunk length (32bit LE uint, exactly twice as big as the actual chunk length)
      # - chunk name (24 bytes; NUL-padded)
      cc = 0
      for i in range(fc):
         clen_data = f.read(8)
         (coff, clen_raw) = struct.unpack(b'<LL', clen_data)
         name = f.read(24).rstrip(b'\x00')
         
         (clen, clen_m) = divmod(clen_raw, 2)
         
         coff += data_base_off
         chunk = LNKChunk(f, coff, clen, name, bool(clen_m))
         chunks.append(chunk)
         
         tlen += clen
      
      f.seek(0,2)
      if (tlen + data_base_off != f.tell()):
         raise ValueError('Parser failure: Content length {0!r} does not match file length {1!r}.'.format(tlen + data_base_off, f.tell()))
      
      return cls(chunks)
   
   def write(self, f_out):
      from struct import pack
      f_out.write(b'LNK\x00')
      f_out.write(pack('<Lxxxxxxxx', len(self._chunks)))
      
      off = 0
      for chunk in self._chunks:
         cs = chunk.get_size()
         f_out.write(struct.pack('<LL24s', off, 2*cs + chunk.is_compressed, chunk.name))
         off += cs
      
      for chunk in self._chunks:
         f_out.write(chunk.get_data())
      

def _main():
   import optparse
   import os
   import os.path
   import sys
   
   op = optparse.OptionParser()
   op.add_option('-x', '--extract', action='store_true', default=False, help='Dump raw files from LNK archive.')
   op.add_option('-n', '--no-decompress', dest='decompress', action='store_false', default=True, help='Do not files from LNK arhive on extraction.')
   op.add_option('-o', '--outdir', action='store', help='Directory to write output to.')
   
   (opts,args) = op.parse_args()
   
   outdir = opts.outdir
   if not (outdir is None):
      outdir = outdir.encode()
   
   for fn in args:
      f = open(fn, 'rb')
      lp = LNKParser.build_from_file(f)
      for chunk in lp:
         sfn = chunk.name
         print('-------- {0!r}: size: {1} compression: {2}'.format(sfn, chunk.get_size(), int(chunk.is_compressed)))
         if (opts.extract):               
            ofn = os.path.basename(sfn)
            if not (outdir is None):
               ofn = os.path.join(outdir, ofn)
            if (opts.decompress):
               data = chunk.get_data_plain()
            else:
               data = chunk.get_data()
            
            print('--->>> {!r} ({} bytes)'.format(ofn, len(data)))
            of = open(ofn, 'wb')
            of.write(data)
            of.close()

if (__name__ == '__main__'):
   _main()
