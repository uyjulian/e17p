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

# MSADPCM support.

from ..file_data import DataRefFile

# Straightforward MSADPCM decoder implementation based on <http://wiki.multimedia.cx/index.php?title=Microsoft_ADPCM>.
_dt_adapt = (230, 230, 230, 230, 307, 409, 512, 614, 768, 614, 512, 409, 307, 230, 230, 230)
_dt_coeff1 = (256, 512, 0, 192, 240, 460, 392)
_dt_coeff2 = (0, -256, 0, 64, 0, -208, -232)

def _nibble_u2s(n):
   if (n & 8):
      return -8 + (n & 7)
   
   return n

def _adpcmdec(pred, delta, s1, s2):
   yield s2
   c1 = _dt_coeff1[pred]
   c2 = _dt_coeff2[pred]
   nibble = 0
   while (True):
      nibble = (yield s1)
      
      pred = (s1*c1 + s2*c2)
      (pred2, pred_mod) = divmod(pred, 256)
      pred = pred2 + ((pred2 < 0) and bool(pred_mod))     # manually round towards zero
      
      pred += _nibble_u2s(nibble)*delta
      
      (delta2, delta_mod) = divmod(_dt_adapt[nibble]*delta, 256)
      delta = delta2 + ((delta2 < 0) and bool(delta_mod)) # manually round towards zero
      delta = max(delta,16)
      delta %= 2**31
      
      s2 = s1
      s1 = max(min(pred, 32767), -32768)      


class DataRefADPCM(DataRefFile):
   def __init__(self, f, off, size, stereo, blocksize):
      super().__init__(f, off, size)
      self.stereo = stereo
      self.blocksize = blocksize
   
   def get_pcm(self):
      from struct import pack,unpack
      data = memoryview(self.get_data())
      out = []
      bhdr_sz = 7*(self.stereo + 1)
      
      while (data):
         if (self.stereo):
            (pred0, pred1, delta0, delta1, s10, s11, s20, s21) = unpack('<BBhhhhhh', data[:bhdr_sz])
            d0 = _adpcmdec(pred0, delta0, s10, s20).send
            d1 = _adpcmdec(pred1, delta1, s11, s21).send
            out.extend((d0(None),d1(None),d0(None),d1(None)))
         
         else:
            (pred, delta, s1, s2) = unpack('<Bhhh', data[:bhdr_sz])
            d0 = d1 = _adpcmdec(pred, delta, s1, s2).send
            out.extend((d0(None),d0(None)))
         
         for b in data[bhdr_sz:self.blocksize]:
            v = ord(b)
            out.append(d0(v >> 4))
            out.append(d1(v & 0xf))
         
         data = data[self.blocksize:]
         
      rv = b''.join(pack('<h',v) for v in out)
      return rv
   
   def get_pcm_dref(self):
      from io import BytesIO
      d = self.get_pcm()
      bio = BytesIO(d)
      
      return DataRefFile(bio, 0, len(d))
