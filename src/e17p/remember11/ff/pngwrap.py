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

import struct

from ...base.file_data import DataRefFile


class R11ImagePNG(DataRefFile):
   """R11 wrapped PNG file."""
   HEADER_LEN = 0x7c
   def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      if (self.size < self.HEADER_LEN):
         raise ValueError('Need at least 0x7c bytes of data.')
      self.f.seek(self.off)
      hdr = self.f.read(self.HEADER_LEN)
      if (hdr[:7] != b'PNGFILE'):
         raise ValueError('Invalid header start data.')
      self._img_fn = hdr[28:28+64].rstrip(b'\x00')
      (chunk_len,) = struct.unpack(b'<L', hdr[24:28])
      if (chunk_len > self.size):
         raise ValueError('Invalid PNGFILE inline length field; read {} expecting {}.'.format(chunk_len, self.size))
      self.size = chunk_len
   
   def get_pygame_image(self):
      from pygame.image import load
      self.f.seek(self.off + self.HEADER_LEN)
      # pygame.image.load() insists on closing the file we pass it when it's done, so give it a dupe instead of the primary
      # reference.
      return load(open(self.f.fileno(), 'rb', closefd=False))
   
   def write_png(self, out):
      out(self.get_data_image())
   
   def write_bmp(self, out):
      raise ValueError('PNG -> BMP conversion is currently unimplemented.')
   
   def get_data_image(self):
      self.f.seek(self.off + self.HEADER_LEN)
      return self.f.read(self.size - self.HEADER_LEN)
   
   def get_fn(self):
      return self._img_fn
