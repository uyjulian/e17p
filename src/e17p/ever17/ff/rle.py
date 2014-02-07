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

# E17 RLE decompression algorithm. This compression scheme is used for CPS/PRT images, as well as WAF files in voice.dat.

import struct

from ...base.file_data import DataRefFile
from ...base.aif import AIFuncs
_aifs = AIFuncs()

@_aifs.add
def e17_rle_unpack(din, out_sz):
   dout = bytearray(out_sz)
      
   def read_data(num=1):
      nonlocal i_i
      rv = din[i_i:i_i+num]
      i_i += 1
      return rv
      
   def read_u8():
      return ord(read_data()[0])
      
   def copy_bytes(n):
      nonlocal i_i, i_o
      dout[i_o:i_o+n] = din[i_i:i_i+n]
      i_i += n
      i_o += n
      
   i_i = 0
   i_o = 0
   while (i_o < out_sz):
      rt = read_u8()
      #print(rt, len(din)-i_i, out_sz-i_o)
      if (rt & 0x80):
         if (rt & 0x40):
            # RLE encoded byte sequence
            run_length = (rt & 0x1F) + 2
            if (rt & 0x20):
               run_length += read_u8() << 5
            run_length = max(run_length,1)   
            data_byte = read_data()
               
            output_left = out_sz - i_o + 1
            if (output_left < run_length):
               run_length = output_left
               
            dout[i_o:i_o+run_length] = bytes(data_byte) * run_length
            i_o += run_length
            
         else:
            # Reference to an earlier version of the same byte sequence
            rl_raw = (rt >> 2) & 0xF
               
            run_length = max(rl_raw + 2,1)
            out_off = ((rt & 3) << 8) + read_u8() + 1
            i_oi = i_o - out_off
            for i in range(run_length):
               dout[i_o+i] = dout[i_oi+i]
            i_o += run_length
      else:
         if (rt & 0x40):
            # Repeated byte sequence
            iter_count = read_u8()+1
            run_length = (rt & 0x3F) + 2
            run_length = max(run_length,1)
               
            if (iter_count):
               for _ in range(iter_count):
                  output_left = out_sz - i_o + 1
                  if (output_left < run_length):
                     run_length = output_left
                     
                  dout[i_o:i_o+run_length] = din[i_i:i_i+run_length]
                  i_o += run_length
            else:
               raise
            i_i += run_length
               
         else:
            # Literal multi-byte sequence
            run_length = (rt & 0x1F) + 1
            if (rt & 0x20):
               run_length += read_u8() << 5
            run_length = max(run_length,1)

            output_left = out_sz - i_o + 1
            if (output_left < run_length):
               run_length = output_left
            copy_bytes(run_length)
   return dout

if (__name__ == '__main__'):
   _main()
