#!/usr/bin/env python3
#Copyright 2010 Sebastian Hagen, Svein Ove Aas <svein.ove@aas.no>
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

# CPS image file format support.

import struct

from . import data_handler_reg
from ...base.file_data import DataRefFile
from ...base.ff.bmp import BMPImage, IMConvert, rgb_get_lengths

from ...base.aif import AIFuncs
_aifs = AIFuncs()

class CPSImageE17:
   def __init__(self, width, height, color_depth, line_length, opp, base_l_off, image_data, alpha_data, palette_data):
      self.width = width
      self.height = height
      self.color_depth = color_depth
      self.line_length = line_length
      self.image_data = image_data
      self.alpha_data = alpha_data
      self.palette_data = palette_data
      self.opp = opp
      self._base_l_off = base_l_off
   
   def get_coords_opengl(self, pos_data):
      """Return (left, right) offsets in opengl coordinates for specified position data."""
      if (pos_data is None):
         # Background mode.
         return (-1,1)
      
      (off, width) = self._base_l_off
      base_off = (off/(width/2) - 1)
      
      scene_off = (pos_data-320)/320
      left = base_off + scene_off
      return (left, left + self.width/400)
   
   @classmethod
   def build_from_data(cls, data):
      m = memoryview(data)
      
      if (m[:4] != b'PRT\x00'):
         raise ValueError('Unexpected preamble {!r}.'.format(data[:4]))
      
      (tv,) = struct.unpack(b'<H', m[4:6])
      
      if (tv == 0x66):
         (color_depth,off_palette,off_data,width,height,alpha,base_l_off,u2,width2,height2) = struct.unpack(b'<HHHHHLLLLL', m[6:36])
      elif (tv == 0x65):
         (color_depth,off_palette,off_data,width,height,alpha) = struct.unpack(b'<HHHHHL', m[6:20])
         height2 = width2 = base_l_off = u2 = 0
      else:
         raise ValueError('Unexpected type val {:x}.'.format(tv))
      
      if (off_data > off_palette):
         m_palette = m[off_palette:off_data]
         if (len(m_palette) != (1 << color_depth)*4):
            raise ValueError('Invalid pallette size {} for color depth {}.'.format(len(m_palette), color_depth))
      else:
         m_palette = None
      
      m_body = m[off_data:]
      # Update on seperately stored actual image dimensions
      base_width = width
      base_height = height
      if (width2 != 0):
         width = width2
      
      if (height2 != 0):
         height = height2
      
      pixel_count = width*height
      (opp, cd_mod) = divmod(color_depth, 8)
      
      if (cd_mod != 0):
         raise ValueError('Unsupported color depth {!d}.'.format(cd_mod))
      
      # Input lines are padded to 32bit boundaries; calculate full length here.
      (ill, rgbd_len) = rgb_get_lengths(opp, width, height)
      if (alpha):
         m_alpha = m_body[rgbd_len:]
      else:
         m_alpha = None
      m_body = m_body[:rgbd_len]
      
      return cls(width, height, color_depth, ill, opp, (base_l_off, base_width), m_body, m_alpha, m_palette)
   
   @staticmethod
   @_aifs.add
   def cps_mix_alpha(m_body, m_alpha, width, height, ill):
      pixel_count = width*height
      if (len(m_alpha) < pixel_count):
         raise ValueError('Insufficient alpha data: Got {}/{} bytes.'.format(len(m_alpha), pixel_count))
         
      rgba_data = bytearray(pixel_count*4)
      line_off = 0
      o_i = 0
      for y in range(height):
         i_i = line_off
         for x in range(width):
            rgba_data[o_i:o_i+3] = m_body[i_i:i_i+3]
            rgba_data[o_i+3:o_i+4] = m_alpha[-y*width - width + x]
            i_i += 3
            o_i += 4
         line_off += ill

      image_data = memoryview(rgba_data)
      return image_data
   
   @staticmethod
   @_aifs.add
   def cps_map_palette(m_body, m_palette, width, height):
      ill = ((width+3)//4)*4
      ill_data = width
      oll = ((width*3+3)//4)*4
      
      rv = bytearray(oll*height)
      o = 0
      i = 0
      for _ in range(height):
         rv[o:o+3*width] = b''.join((bytes(m_palette[4*ord(b):4*ord(b)+3])) for b in m_body[i:i+width])
         i += ill
         o += oll
      return rv
   
   def get_rgba(self):
      color_depth = self.color_depth
      
      if not (self.palette_data is None):
         if (self.color_depth != 8):
            raise ValueError('Paletted {} bit images are currently unsupported.'.format(self.color_depth))
         image_data = self.cps_map_palette(self.image_data, self.palette_data, self.width, self.height)
         color_depth = 24
      
      elif not (self.alpha_data is None):
         m_alpha = self.alpha_data
         if (self.color_depth != 24):
            raise ValueError('Unsupported color depth {} with alpha data.'.format(color_depth))
         image_data = self.cps_mix_alpha(self.image_data, self.alpha_data, self.width, self.height, self.line_length)
         color_depth += 8
         
      else:
         image_data = self.image_data
      
      return (self.width, self.height, color_depth, image_data)

   def get_bmp(self):
      params = self.get_rgba()
      return BMPImage(*params, do_sanity_checks=True)


class DataRefCPSE17(DataRefFile):
   CPS_CLS = CPSImageE17
   HDR_LEN = 20
   
   def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.f.seek(self.off)
      hdr_data = self.f.read(20)
      
      if (self.get_size() < 20):
         raise ValueError('Insufficient data {:d} bytes for format with header size {:d}.'.format(self.get_size(), 20))
      
      if (hdr_data[:4] != b'CPS\x00'):
         raise ValueError('Unexpected preamble {!r}.'.format(hdr_data[:4]))
     
      (sz_comp,) = struct.unpack(b'<L', hdr_data[4:8])
      if (sz_comp != self.size):
         raise ValueError('Size mismatch: Outer {} != inline {}.'.format(self.size, sz_comp))
      
      if (hdr_data[8:10] != b'\x66\x00'):
         raise ValueError('Unexpected type id bytes: {!r}'.format(hdr_data[8:10]))
      
      (self.size_plain,) = struct.unpack(b'<L', hdr_data[12:16])
      
      cmp_type_raw = ord(hdr_data[10:11])
      if (cmp_type_raw & 0x01):
         cmp_type = 1
      elif (cmp_type_raw == 0x00):
         cmp_type = 0
         if (sz_comp < self.size_plain + 20):
            raise ValueError('Size mismatch for compression type 0: {}/{}'.format(sz_comp, self.size_plain))
      else:
         raise ValueError('Unknown cmp_type {}.'.format(cmp_type_raw))
      self.cmp_type = cmp_type
   
   def __str__(self):
      return '< {} image type {} length {}({}) @ {}({}:{}):>'.format(type(self).__name__, self.cmp_type, self.size_plain,
         self.size, self.f, self.off, self.off+self.size)
   
   def get_content_raw(self):
      self.f.seek(self.off+self.HDR_LEN)
      rv = self.f.read(self.size - self.HDR_LEN)
      return rv
   
   
   def get_content_unobfuscated(self):
      data = bytearray(self.get_data())
      self.cps_unobfuscate(data)
      return data

   @staticmethod
   @_aifs.add
   def cps_unobfuscate(data):
      v_off = struct.unpack(b'<L', data[-4:])[0] - 0x7534682
      if (v_off == 0):
         return data
      
      val_obf = struct.unpack(b'<L', data[v_off:v_off+4])[0] + v_off + 0x3786425
      data_len = len(data)
      if (data_len < 20):
         return data
      
      i_i = 0x10
      off_lim = len(data)-4
      vlim = 1 << 32
      
      while (i_i < off_lim):
         if (i_i != v_off):
            # Skip obfuscation information
            (v,) = struct.unpack('<L', data[i_i:i_i+4])
            v -= val_obf + data_len
            v %= vlim
            data[i_i:i_i+4] = struct.pack('<L', v)
         
         val_obf *= 0x41c64e6d
         val_obf %= vlim
         val_obf += 0x9b06 
         val_obf %= vlim
         
         i_i += 4
      del(data[-4:])
      return data
   
   def get_content_decompressed(self):
      if (self.cmp_type == 1):
         return self._get_content_decompressed_1()
      if (self.cmp_type == 0):
         m = memoryview(self.get_content_unobfuscated())
         return m[20:self.size_plain+20]
      raise ValueError('Unknown cmp_type {!r}.'.format(self.cmp_type))
   
   def _get_content_decompressed_1(self):
      from .rle import e17_rle_unpack
      
      din = memoryview(self.get_content_unobfuscated())
      out_sz = self.size_plain
      rv = e17_rle_unpack(din[20:], out_sz)
      return rv
   
   def get_bmp(self):
      return self.get_img().get_bmp()
   
   def get_img(self):
      d = self.get_content_decompressed()
      return self.CPS_CLS.build_from_data(d)

   @classmethod
   def _main(cls):
      import optparse
      import os
      import sys
      op = optparse.OptionParser()
      op.add_option('-d', '--decompress', default=False, dest='decompress', action='store_true', help='Attempt to decompress files.')
      op.add_option('-q', '--deobfuscate', default=False, dest='deobfuscate', action='store_true', help='Dump deobfuscated file data.')
      op.add_option('-o', '--outdir', default=None, dest='outdir', metavar='PATH', help='Directory to write output files to.')
      #op.add_option('-i', '--sanity-check-override', default=False, action='store_true', dest='insanity', help="Don't skip undecodable files.")
      op.add_option('-b', '--bmp', default=False, dest='bmp_out', action='store_true', help='Write image data to BMP files.')
      op.add_option('-p', '--png', default=False, dest='png_out', action='store_true', help='Write image data to PNG files.')
      op.add_option('--lnk', default=False, dest='lnk', action='store_true', help='Parse input from LNK archive instead of presplitted scr files.')
      (opts, args) = op.parse_args()
      
      outdir = opts.outdir
      if not (outdir is None):
         outdir = outdir.encode()
      
      def get_of(fn_orig, ext):
         if (outdir is None):
            fn = fn_orig + ext
         else:
            fn = os.path.join(outdir, os.path.basename(fn_orig)) + ext
         f = open(fn, 'wb')
         print('--> {}'.format(f.name))
         return f
      
      need_img = opts.bmp_out or opts.png_out
      
      if (opts.png_out):
         (env_ok,exc) = IMConvert.test_environment()
         if not (env_ok):
            print("ERROR: You requested PNG output, and I'm unable to find a working convert(1) binary. Test call failed with: {!r}.".format(exc))
            sys.exit(255)
      
      if (opts.lnk):
         from .lnk import LNKParser
         def get_drefs():
            for fn in args:
               print('------------------------ Processing LNK archive {!r}'.format(fn))
               lnkp = LNKParser.build_from_file(open(fn, 'rb'))
               for chunk in list(lnkp):
                  fn_sub = chunk.name
                  if not (fn_sub.lower().endswith(b'.cps')):
                     print('Skipping non-CPS file {!r}.'.format(fn_sub))
                     continue
                  
                  cps = cls.build_from_similar(chunk)
                  yield (fn_sub, cps)

      else:
         def get_drefs():
            for fn in args:
               fn = fn.encode()
               f = open(fn, 'rb')
               size = f.seek(0,2)
               cps = cls(f, 0, size)
               yield(fn, cps)


      for (fn,cps) in get_drefs():
         print('-------- Processing {}: {}.'.format(fn, cps))
         if (opts.deobfuscate):
            data_out = cps.get_content_unobfuscated()
            f2 = get_of(fn, b'.u')
            f2.write(data_out)
         
         if (opts.decompress):
            data_out = cps.get_content_decompressed()
            f2 = get_of(fn, b'.d')
            f2.write(data_out)
         
         if (need_img):
            img = cps.get_bmp()
         
         if (opts.bmp_out):
            f2 = get_of(fn, b'.bmp')
            img.write_bmp(f2.write)
         
         if (opts.png_out):
            f2 = get_of(fn, b'.png')
            img.write_png(f2.write)

data_handler_reg(b'cps')(DataRefCPSE17.build_from_similar)
_main = DataRefCPSE17._main
if (__name__ == '__main__'):
   _main()
