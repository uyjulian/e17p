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

# R11 compression format support.

import struct

from ...base.file_data import DataRefFile

class R11UnpackError(ValueError):
   pass

class R11PackedDataRefFile(DataRefFile):
   def unpack(self):
      data = self.get_data()
      len_p = len(data)
      # straightforward adaption of decompressbip.c
      (len_u,) = struct.unpack(b'<L', data[:4]) # dubious.
      rv = bytearray(len_u+18)
      off_i = 4
      off_o = 0
      mask = 0
      while (off_i < len_p):
         mask >>= 1
         mask %= 0x100000000
         if (mask < 0x100):
            mask = data[off_i] | 0x8000
            off_i += 1
         if (mask & 1):
            #print(len_u,off_o)
            #print(off_o,len(rv),len_u, off_i,len(data))
            if (off_o >= len_u):
               raise R11UnpackError('R11 decompression output overrun at {}/{}.'.format(off_i, off_o))
            rv[off_o+18] = data[off_i]
            off_o += 1
            off_i += 1
            continue
         roff = ((data[off_i+1] & 0xf0) << 4) + data[off_i] + 18
         rlen = (data[off_i+1] & 0xf) + 3
         m = (off_o & ~0xfff)|(roff&0xfff)
         if (m >= off_o):
            m -= 0x1000
         if (m < -18):
            raise R11UnpackError('R11 decompression failure: Unknown mtype {} at {}/{} (len {})'.format(m, off_i, off_o, rlen))
         if ((off_o + rlen) > len_u):
            raise R11UnpackError('R11 decompression output overrun at {}/{} (m {} len {})'.format(off_i, off_o, m, rlen))
         if ((m + rlen) > len_u):
            raise R11UnpackError('R11 decompression input overrun at {}/{} (m {} len {})'.format(off_i, off_o, m, rlen))
         off_i += 2
         if (abs(off_o-m) >= rlen):
            rv[off_o+18:off_o+rlen+18] = rv[m+18:m+rlen+18]
         else:
            # Progressive memcpy. Doing it byte-for-byte in Py is kinda slow, so only do this if necessary.
            for i in range(rlen):
               rv[off_o+18+i] = rv[m+18+i]
         #print(off_o,rlen, off_o-m, rlen)
         off_o += rlen
      
      if (off_o != len_u):
         raise R11UnpackError('BIP decompression output underrun: Extracted {}/{} bytes.'.format(off_o, len_u))
      return memoryview(rv)[18:]

   @staticmethod
   def pack_nullcompression(data_in):
      # Straight adaption from compressbip.c.
      len_i = len(data_in)
      len_o = (len_i*9+7)//8 + 4
      
      data_out = bytearray(len_o)
      data_out[:4] = struct.pack('<L', len_i)
      o = 4
      i = 0
      while(i < len_i):
         data_out[o] = 0xff
         data_out[o+1:o+9] = data_in[i:i+8]
         i += 8
         o += 9
      
      if (len(data_out) != len_o):
         raise ValueError('Compression failed: Wrote {}/{} outbytes.'.format(len(data_out), len_o))
      
      return data_out   

   def repack_nullcompression(self):
      return self.pack_nullcompression(self.unpack())

   def get_data_unpacked(self):
      from io import BytesIO
      d = self.unpack()
      bio = BytesIO(d)
      return DataRefFile(bio, 0, len(d))

def _main():
   import optparse
   op = optparse.OptionParser()
   (opts, args) = op.parse_args()
   
   fns = args
   for fn in fns:
      print('---------------- Reading file {!r}.'.format(fn))
      f = open(fn, 'rb')
      dref = R11PackedDataRefFile(f,0,f.seek(0,2))
      fn_out = fn + '.d'
      data = dref.get_data_unpacked().get_data()
      
      print('--> {!r}: ({}) bytes.'.format(fn_out, len(data)))
      f_out = open(fn_out, 'wb')
      f_out.write(data)


if (__name__ == '__main__'):
   _main()
