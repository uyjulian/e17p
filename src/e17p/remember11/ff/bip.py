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

# Parser for R11 BIP files
# BIP files are a simple container format, not unlike the top-level structures of E17 script files.

import struct
from ...base.file_data import *
from ...base.text_fmt import *
from .pngwrap import R11ImagePNG

# -------------------------------------------------------------------------------- R11 data chunk parser DS
class R11DataChunk(DataRefFile):
   CST_MAP = {}
   CST_DEFAULT = []
   PREFIX_LEN = 4
   
   @classmethod
   def build_from_file(cls, f, off, size):
      if (size < cls.PREFIX_LEN):
         return cls.CST_DEFAULT[-1](f, off, size)
         
      f.seek(off)
      prefix = f.read(cls.PREFIX_LEN)
      try:
         cls = cls.CST_MAP[prefix]
      except KeyError:
         for dcls in cls.CST_DEFAULT:
            try:
               rv = dcls(f, off, size)
            except ValueError as exc:
               exc2 = exc
               continue
            return rv
         raise exc
      else:
         return cls(f, off, size)
         
   
   @classmethod
   def _reg_subcls_default(cls, subcls):
      cls.CST_DEFAULT.append(subcls)
      return subcls
   
   @classmethod
   def _reg_subcls(cls, subcls):
      cls.CST_MAP[subcls.prefix] = subcls
      return subcls

   def format_hr(self):
      return str(self.get_data())

   def dump_to_files(self, fn_prefix):
      f = open(fn_prefix + b'.bin', 'wb')
      f.write(self.get_data())
      return [(f.name, f.tell())]

_reg_r11_dct = R11DataChunk._reg_subcls
_reg_r11_dctd = R11DataChunk._reg_subcls_default

@_reg_r11_dctd
class R11ImageHeaderDatachunk(R11DataChunk):
   HDR_FMT = b'<LLHH'
   HDR_LEN = struct.calcsize(HDR_FMT)
   E_FMT = b'<6sBB8HL'
   E_LEN = struct.calcsize(E_FMT)
   def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      body_size = self.size - self.HDR_LEN
      if (body_size < 0):
         raise ValueError('Insufficient data; expected >= {!r} bytes, got {!r}.'.format(self.HDR_LEN, self.size))
      (ec, uk0, width, height) = struct.unpack(self.HDR_FMT, self.get_data(self.HDR_LEN))
      
      if (ec*self.E_LEN != body_size):
         raise ValueError('Unexpected body size: Got {!r}, expected {!r}.'.format(body_size, ec*self.E_LEN))
      if (uk0 != 0):
         raise ValueError('Unexpected second value {!r} != 0.'.format(uk0))
      
      self.width = width
      self.height = height
      self.chunk_count = ec
   
   def get_chunks(self):
      self.f.seek(self.off + self.HDR_LEN)
      rv = []
      for _ in range(self.chunk_count):
         data = self.f.read(self.E_LEN)
         (prefix, uk0, uk1, off_x, off_y, tile_width, tile_height, iw_scale, ih_scale, iw_phy, ih_phy, off_data) = \
            struct.unpack(self.E_FMT, data)
         
         if (prefix != b'\x07\x00\x00\x00\x00\x00'):
            raise ValueError('Unexpected prefix in {!r}'.format(data))
         
         if ((iw_scale != self.width) or (ih_scale != self.height)):
            raise ValueError('Got scaled dimensions {}x{} expecting {}x{}.'.format(
               img_width, img_height, self.width, self.height))
         
         tile = R11Tile(iw_phy, ih_phy, off_x, off_y, tile_width, tile_height, uk0, uk1)
         tile._off_data = off_data
         rv.append(tile)
      return rv
   
   def format_hr(self):
      chunks = self.get_chunks()      
      return '< {} width: {} height: {} chunks: {} {} >'.format(
         type(self).__name__, self.width, self.height, len(chunks), '\n   '.join(format(c) for c in chunks))

@_reg_r11_dctd
class R11UnknownDataChunk(R11DataChunk):
   pass

@_reg_r11_dct
class R11EMUARC(R11DataChunk):
   prefix = b'EMUA' # Not sure if this is really unique ...
   def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      if (self.get_size() < 8):
         raise ValueError('Size of {} invalid for EMUARC__ chunk; expected at least 8 bytes.'.format(self.get_size()))
      self.f.seek(self.off)
      hdr = self.f.read(8)
      if (hdr != b'EMUARC__'):
         raise ValueError('Invalid EMUARC__ header {!a}.'.format(hdr))
      self.off_body = self.off + 8
      self.size_body = self.size - 8
   
   def format_hr(self):
      return repr(self)
   
   def get_data_body(self):
      self.f.seek(self.off_body)
      return self.f.read(self.size_body)
   
   def get_images(self):
      off = self.off_body
      off_lim = off + self.size_body
      rv = []
      while (off < off_lim):
         img = R11ImagePNG(self.f, off, off_lim-off)
         off += img.size
         rv.append(img)
      return rv
   
   def dump_to_files(self, fn_prefix):
      rv = []
      for (i,img) in enumerate(self.get_images()):
         fn = b''.join((fn_prefix, b'.', '{:02d}'.format(i).encode(), b'.png'))
         f = open(fn, 'wb')
         img.write_png(f.write)
         rv.append((f.name,f.tell()))
      
      return rv


# -------------------------------------------------------------------------------- BIP parser DS
class BIPFile:
   def __init__(self, chunks):
      self._chunks = chunks
   
   def dump_chunks_hr(self, out=print):
      for c in self._chunks:
         out('  ', c.format_hr())
   
   def dump_chunk_files(self, basepath, out=print):
      from os.path import relpath
      
      if (isinstance(basepath,bytes)):
         basepath = basepath.decode('ascii')
      
      for (c,i) in zip(self._chunks,range(len(self._chunks))):
         fd = c.dump_to_files('{}.{}'.format(basepath,i).encode('ascii').lstrip(b'./'))
         for (fn,size) in fd:
            rp = relpath(fn)
            out('  ---- Dumping ({:12} bytes): {!a}.'.format(size, rp))
   
   @classmethod
   def build_from_file(cls, f, *, bip_off_shift, off_lim=None):
      # Read chunk count.
      cc_raw = f.read(4)
      (cc,) = struct.unpack(b'<L', cc_raw)
      chunk_offs = [struct.unpack(b'<L', f.read(4))[0] for _ in range(cc)]
      off_data = f.tell()
      
      # The actual data start appears to be aligned on a 16byte boundary?
      off_m = off_data % 16
      if (off_m):
         off_data += 16 - off_m
      
      if (off_lim is None):
         off_lim = f.seek(0,2)
      
      f.seek(off_data)
      # Convert chunk off values read into absolute file offsets.
      # For some BIP files (like etc::OPTION.BIP) this adjustment is necessary, and for others (like ev::EV_CO01A.BIP) it isn't
      # ... the following check is an ugly hack, but we don't have a better way right now.
      # ... and in BGM37.BIP they're shifted by << 2 instead? ...
      if (chunk_offs and (chunk_offs[0] == 0)):
         #if (chunk_offs[-1] == off_lim):
            #bip_off_shift = 0
         
         chunk_offs = [(off << bip_off_shift) + off_data for off in chunk_offs]
      
      chunk_offs.append(off_lim)
      chunk_data = [None]*cc
      for i in range(cc):
         coff = chunk_offs[i]
         clen = chunk_offs[i+1]-coff
         if (clen < 0):
            raise ValueError('Invalid chunk offs {}; not monotonically increasing.'.format(chunk_offs))
         chunk_data[i] = (f, coff, clen)
      
      return cls.build_from_chunkdata(chunk_data)
   
   @classmethod
   def build_from_chunkdata(cls, chunk_data):
      return cls(tuple(R11DataChunk.build_from_file(*args) for args in chunk_data))

class R11Tile:
   img = None
   def __init__(self, iw_phy, ih_phy, off_x, off_y, width, height, uk0, uk1):
      self.iw_phy = iw_phy
      self.ih_phy = ih_phy
      self.off_x = off_x
      self.off_y = off_y
      self.width = width
      self.height = height
      self.uk0 = uk0
      self.uk1 = uk1
   
   def __repr__(self):
      return '<{} dim: {}x{} (in {}x{}) at ({:4},{:4}) (with uk {!r:2}, {!r:2}): {}>'.format(
         type(self).__name__, 
         self.width, self.height,
         self.iw_phy, self.ih_phy,
         self.off_x, self.off_y,
         self.uk0, self.uk1,
         self.img
      )
   
   def _set_image(self, f, off, sz):
      self.img = R11ImagePNG(f, off + self._off_data, sz - self._off_data)
      del(self._off_data)
   
   def get_imgdata_rgba(self):
      from pygame.image import tostring
      return tostring(self.img.get_pygame_image(), 'RGBA')

class CompositeImage:
   def __init__(self, width, height):
      self.width = width
      self.height = height
      self.opp = 4
      self.data = bytearray(width*height*self.opp)
   
   def __repr__(self):
      return '<{} ({}x{}x{}) @ {} >'.format(type(self).__name__, self.width, self.height, self.opp*8, id(self))
   
   def write_tile(self, tile):
      if ((tile.iw_phy != self.width) or (tile.ih_phy != self.height)):
         raise ValueError("Can't apply tile {} to {}: Dimension mismatch.".format(tile, self))
      
      # Not really rgba data, because the input PNG files are colorwarped. Dumping it into a BMP file with default settings
      # works, though.
      tile_data = tile.get_imgdata_rgba()
      
      off_delta = self.width*self.opp
      off = tile.off_x*self.opp + tile.off_y*off_delta
      off_tile = 0
      ll = tile.width*self.opp
      if (ll*tile.height != len(tile_data)):
         raise ValueError('Tile data length mismatch; expected {}*{}*{} == {} != {}.'.format(
            tile.width, tile.height, self.opp, ll*tile.height, len(tile_data)))
      
      for _ in range(tile.height):
         self.data[off:off+ll] = tile_data[off_tile:off_tile+ll]
         off += off_delta
         off_tile += ll
   
   def get_bmp(self):
      from ...base.ff.bmp import BMPImage
      img = BMPImage(self.width, self.height, self.opp*8, self.data)
      return img

class BIPFile_Img(BIPFile):
   def __init__(self, img_data, uk0, uk1):
      self.img_data = img_data
      self.uk0 = uk0
      self.uk1 = uk1
   
   def dump_chunks_hr(self, out=print):
      for (i, (w, h, tiles)) in enumerate(self.img_data):
         out('---- sequence: {} ({}x{})'.format(i, w, h))
         for tile in tiles:
            out('  ', tile)
   
   def dump_chunk_files(self, basepath, out=print):
      if not (self.img_data):
         return
      
      tile0 = self.img_data[0][2][0]
      
      ci = CompositeImage(tile0.iw_phy, tile0.ih_phy)
      for (i,(_,_,tiles)) in enumerate(self.img_data):
         for tile in tiles:
            ci.write_tile(tile)
         
         outpath = '{}.{:d}.png'.format(basepath, i)
         out('--->>> {!r}.'.format(outpath))
         f_out = open(outpath, 'wb')
         bmp = ci.get_bmp().write_png(f_out.write)
         f_out.close()
   
   @classmethod
   def build_from_chunkdata(cls, dref_arg_list):
      i = iter(dref_arg_list)
      md = []
      while (True):
         args = i.__next__()
         try:
            dc = R11ImageHeaderDatachunk(*args)
         except ValueError:
            break
         md.append((dc.width, dc.height, dc.get_chunks()))
      
      size = None
      data_uk0 = []
      while (size != 0):
         (f,off,size) = i.__next__()
         data_uk0.append(R11UnknownDataChunk(f, off, size))
      
      emuarc = R11EMUARC(*i.__next__())
      for (_,_,mdc) in md:
         for mdsc in mdc:
            mdsc._set_image(emuarc.f, emuarc.off_body, emuarc.size_body)
      
      data_uk1 = tuple(R11UnknownDataChunk(*args) for args in i)
      return cls(md, data_uk0, data_uk1)

def _main():
   import os
   import sys
   import optparse
   from os.path import basename
   
   op = optparse.OptionParser()
   op.add_option('-o', '--output-dir', dest='odir', default=None, action='store', metavar='DIRECTORY', help='Directory to dump chunks to.')
   op.add_option('-c', '--chunk-details', dest='chunk_details', default=False, action='store_true', help='Print HR information about parsed chunks.')
   op.add_option('-s', '--bitshift', default=4, action='store', metavar='COUNT', help='Bitshift to use for BIP offset parsing.')
   op.add_option('--img', dest='img', default=False, action='store_true', help='Use image-data-only BIP parser.')
   (opts, args) = op.parse_args()
   
   if (opts.img):
      bcls = BIPFile_Img
   else:
      bcls = BIPFile
   
   for fn in args:
      print('-------- Parsing {0!a}.'.format(fn))
      f = open(fn, 'rb')
      p = bcls.build_from_file(f, bip_off_shift=opts.bitshift)
      if (opts.chunk_details):
         p.dump_chunks_hr()

      if (opts.odir):
         p.dump_chunk_files(opts.odir + basename(fn))

if (__name__ == '__main__'):
   _main()
