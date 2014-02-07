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

# MS BMP image output support

import struct

class SubprocessError(Exception):
   pass

def rgb_get_lengths(opp, width, height):
   """Calculate padded BMP line and file length from octets/pixel value, width and height. """
   ill = ((width * opp + 3) // 4) * 4
   rgbd_len = ill*height
   return (ill, rgbd_len)

class IMConvert:
   def __init__(self, args):
      # Note that the subprocess interface in CPython 3.1 is rather stupid, and insists on getting a sequence of strings for a
      # call spec. 3.2 is more sane and also accepts sequences of bytes, but we don't want to rely on that here.
      for arg in args:
         if not (isinstance(arg, str)):
            raise ValueError('Invalid arg spec {!r}.'.format(args))
      
      self.args = ['convert'] + args
   
   def run(self, data):
      from subprocess import Popen, PIPE
      p = Popen(self.args, stdout=PIPE, stderr=PIPE, stdin=PIPE)
      (stdout, stderr) = p.communicate(data)
      if (p.wait() != 0):
         raise SubprocessError('"convert" execution {} failed(rc {:d}): {} {}'.format(self.args, p.returncode, stderr, stdout), p.returncode,
            stderr, stdout)
      
      return (stdout, stderr)
   
   @classmethod
   def test_environment(cls):
      """Test whether we have a working convert binary."""
      try:
         self = cls(['--version'])
         self.run(None)
      except (OSError, SubprocessError) as exc:
         return (False,exc)
      return (True,None)


class BMPImage:
   def __init__(self, width, height, color_depth, data, do_sanity_checks=True):
      self.width = width
      self.height = height
      self.data = data
      self.color_depth = color_depth
      if (do_sanity_checks):
         (_, ple) = rgb_get_lengths((color_depth+7)//8, width, height)
         
         if (ple != len(data)):
            raise ValueError('Payload length mismatch: Expected {}*{}*{} == {}, got {}.'.format(width, height, color_depth//8,
               ple, len(data)))
   
   def _get_body_size(self):
      return len(self.data)

   #subhdr_fmt = b'<LLLHHLLllll'
   BMP_CMP_TYPE_RGB = 0
   BMP_CMP_TYPE_BITFIELD = 3
   subhdr_fmt = b'<LLLHHLLllll'  # BITMAPINFOHEADER
   subhdr2_fmt = b'<LLLLL8xL8xL8xL8x4x' # extra BITMAPV4HEADER fields
   subhdr_sz = struct.calcsize(subhdr_fmt)
   subhdr2_sz = subhdr_sz + struct.calcsize(subhdr2_fmt)
   def _get_subhdr(self):
      explicit_bitfields = (self.color_depth > 24)
      if (explicit_bitfields):
         # Imagemagick is a big baby about this, not accepting alpha channels in BMP files using the 'RGB' compression type,
         # so we need to blow this up to a BITMAPV4HEADER, and specify the bitfield for each channel explicitly to work around
         # their bugs.
         cmp_type = self.BMP_CMP_TYPE_BITFIELD
         subhdr_sz = self.subhdr2_sz
      else:
         # Make BITMAPINFOHEADER.
         cmp_type = self.BMP_CMP_TYPE_RGB
         subhdr_sz = self.subhdr_sz
      
      rv = struct.pack(self.subhdr_fmt, subhdr_sz, self.width, self.height, 1, self.color_depth, cmp_type,
         self._get_body_size(),0,0,0,0)
      
      if (explicit_bitfields):
         rv += struct.pack(self.subhdr2_fmt,
            0x00ff0000, # red mask
            0x0000ff00, # green mask
            0x000000ff, # blue mask
            0xff000000, # alpha mask
            1,1,1,1
         )
      return rv
   
   mhdr_fmt = b'<2sL4xL'
   mhdr_sz = struct.calcsize(mhdr_fmt)
   def write_bmp(self, out):
      subhdr = self._get_subhdr()
      hlen = self.mhdr_sz + len(subhdr)
      flen = hlen + self._get_body_size()
      mhdr = struct.pack(self.mhdr_fmt, b'BM', flen, hlen)
      out(mhdr)
      out(subhdr)
      out(self.data)
   
   def write_png(self, out):
      from io import BytesIO
      bmp_buf = BytesIO()
      self.write_bmp(bmp_buf.write)
      ic = IMConvert(['bmp:-', 'png:-'])
      (png_data,stderr) = ic.run(bmp_buf.getvalue())
      out(png_data)