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

# Parser for R11 T2P / TIM2 bitmap image files.

import struct

from ...base.file_data import DataRefFile
from ...base.ff.bmp import BMPImage, IMConvert, rgb_get_lengths
from .pngwrap import R11ImagePNG

class DataRefT2P(DataRefFile):
   """R11 T2P/TIM2 bitmap image."""
   def get_img(self):
      body_preamble = self.get_data(7, self.hdr_len)
      if (body_preamble == b'PNGFILE'):
         # Wrapped PNG image
         return R11ImagePNG(self.f, self.off+self.hdr_len, self.get_size()-self.hdr_len)
      
      return self._rgba2bmp()
   
   hdr_fmt = '<4sHH8sL5sHxLHHHH24s'
   hdr_len = struct.calcsize(hdr_fmt)
   @classmethod
   def build_from_similar(cls, dref, *args, unpack=True, **kwargs):
      if (unpack):
         dref = dref.get_data_unpacked()
      
      return super().build_from_similar(dref, *args, **kwargs)
   
   def _rgba2bmp(self):
      size = self.get_size()
      if (size < self.hdr_len):
         raise ValueError('Insufficient file size {} for T2P format (hdr len is {}).'.format(size, self.hdr_len))
      
      self.f.seek(self.off)
      (preamble, opp, uk0, uk1, ilsz, uk2, uk3, uk5, uk6, uk7, width, height, uk10) = \
         struct.unpack(self.hdr_fmt, self.f.read(self.hdr_len))
      
      if (preamble != b'TIM2'):
         raise ValueError('Unexpected preamble {!a}.'.format(preamble))
      
      if (opp != 4):
         # Check whether this really holds, and if not what the interpretations of other opps are.
         raise ValueError('Unexpected octet/pixel value {:d}.'.format(opp))
      
      if (ilsz != size - 16):
         raise ValueError('Got inline size {} while expecting {}.'.format(ilsz, size - 16))
      
      blen = size - self.hdr_len
      ill = ((width*opp + 3)//4)*4
      
      if (ill*height != blen):
         raise ValueError('Unexpected body size {} for (w {} h {} b {}); expected {}.'.format(blen, width, height, opp, ill*height))
      
      data_out = bytearray(blen)
      m_out = memoryview(data_out)
      for off in range(blen-ill, -ill, -ill):
         self.f.readinto(m_out[off:off+ill])
      
      for i in range(0,blen,4):
         data_out[i+3] = min(data_out[i+3] << 1,255)
         (data_out[i], data_out[i+2]) = (data_out[i+2], data_out[i])
      
      return BMPImage(width, height, opp*8, data_out)


def _main():
   import optparse
   import os.path
   
   from .afs import AFSParser, R11PackedDataRefFile
   
   op = optparse.OptionParser()
   op.add_option('-a', '--afs', dest='afs_in', default=False, action='store_true', help='Extract image data from AFS files instead of pre-splitted T2P ones.')
   op.add_option('-b', '--bmp', dest='bmp_out', default=False, action='store_true', help='Write image data to BMP files.')
   op.add_option('-p', '--png', dest='png_out', default=False, action='store_true', help='Write image data to PNG files.')
   op.add_option('-o', '--outdir', dest='outdir', default=None, help='Directory to write output files to.')
   op.add_option('-u', '--unpack', dest='unpack', default=False, action='store_true', help='Unpack pre-split T2P files before attempting to parse them.')
   
   (opts, args) = op.parse_args()
   
   if (opts.afs_in):
      unpack = True
      def get_dlist(f):
         p = AFSParser.build_from_file(f)
         for (cfn, dref, _) in p:
            if cfn.endswith(b'.T2P'):
               yield (cfn, dref)
      
   else:
      unpack = opts.unpack
      def get_dlist(f):
         return ((f.name, R11PackedDataRefFile(f, 0, f.seek(0,2))),)
   
   outdir = opts.outdir
   if not (outdir is None):
      outdir = outdir.encode()
   
   def get_of(fn, ext):
      if (outdir):
         bfn = os.path.basename(fn)
         fn = os.path.join(outdir, bfn)
      
      rv = open(fn + ext, 'wb')
      print('--> {}'.format(rv.name))
      return rv
   
   fns = args
   
   for base_fn_str in fns:
      base_fn = base_fn_str.encode()
      f = open(base_fn, 'rb')
      print('---------------- Opening {!r}.'.format(base_fn))
      for (fn, dref) in get_dlist(f):
         print('-------- Processing data for {!r}.'.format(fn))
         drt2p = DataRefT2P.build_from_similar(dref, unpack=unpack)
         img = drt2p.get_img()
         print('--- Image: {}'.format(img))
         if (opts.bmp_out):
            f2 = get_of(fn, b'.bmp')
            img.write_bmp(f2.write)
         
         if (opts.png_out):
            f2 = get_of(fn, b'.png')
            img.write_png(f2.write)
         


if (__name__ == '__main__'):
   _main()
