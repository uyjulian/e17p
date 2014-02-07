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

# Waveform audio file format support.

import struct

from ..file_data import *

# ---------------------------------------------------------------- Wave classes
# RIFF/Wave implementation based on "Multimedia Programming Interface and Data Specifications 1.0", 
# <http://www.kk.iij4u.or.jp/~kondo/wave/mpidata.txt>.
# Also, WAVEFORMATEX structure as documented on
# <http://msdn.microsoft.com/en-us/library/ff538799%28VS.85%29.aspx>.
def registry_setup_default(cls):
   cls.build = cls.CT_MAP.build_builder(cls)
   return cls

class RegistryDict(dict):
   def __init__(self, key_attrname=None, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self._key_attrname = key_attrname
   
   def attr_reg(self, e):
      self[getattr(e, self._key_attrname)] = e.build_this
      return e
   
   def explicit_reg(self, key):
      def rv(e):
         self[ket] = e
         return e
      return rv
   
   def build_builder(self, default):
      def build(key, *args, **kwargs):
         try:
            builder = self[key]
         except KeyError as exc:
            if (default is None):
               raise exc
            # Having different arg sets is slightly inelegant, but in practice this is typically the only type that needs
            # to be given the key explicitly.
            return default(key, *args, **kwargs)
         return builder(*args, **kwargs)
      return build

class _RIFFDataSize(int):
   def write_padding(self, out):
      if (self % 2):
         return out(b'\x00')
      return 0

class RIFFChunkBase:
   def get_chunk_header(self, data_size):
      return (struct.pack('>L', self.cid) + struct.pack('<L', data_size))

@registry_setup_default
class RIFFChunk(RIFFChunkBase):
   CT_MAP = RegistryDict('cid')
   def __init__(self, cid, dref):
      self.cid = cid
      self.dref = dref
   
   def get_data_size(self):
      return _RIFFDataSize(self.dref.get_size())
   
   def write_to_file(self, out):
      ds = self.get_data_size()
      rv = out(self.get_chunk_header(ds))
      rv += out(self.dref.get_data())
      rv += ds.write_padding(out)
      return rv
   
   def __repr__(self):
      return '{}({}, {})'.format(type(self).__name__, self.cid, self.dref)

_reg_rc_type = RIFFChunk.CT_MAP.attr_reg

class RIFFChunk_Listlike(RIFFChunkBase):
   def __init__(self, form_type, contents):
      self.form_type = form_type
      self.contents = contents
   
   @classmethod
   def build_this(cls, dref):
      return cls(FourCC(dref.get_data(4)), RIFFChunkList.build_from_file(dref.f, dref.off+4, dref.off + dref.size))
   
   def get_data_size(self):
      return _RIFFDataSize(self.contents.get_data_size() + 4)
   
   def write_to_file(self, out):
      ds = self.get_data_size()
      rv = out(self.get_chunk_header(ds))
      rv += out(self.form_type.get_bytes())
      rv += self.contents.write_to_file(out)
      rv += ds.write_padding(out)
      return rv
   
   def __repr__(self):
      return '{}({}, {})'.format(type(self).__name__, self.form_type, self.contents)

@_reg_rc_type
class RIFFChunk_RIFF(RIFFChunk_Listlike):
   cid = FourCC(b'RIFF')

@_reg_rc_type
class RIFFChunk_List(RIFFChunk_Listlike):
   cid = FourCC(b'LIST')

@_reg_rc_type
class RIFFChunk_Wave_fmt(RIFFChunkBase):
   cid = FourCC(b'fmt ')
   FMT_MS_PCM = 0x1
   FMT_MS_ADPCM = 0x2
   
   def __init__(self, fmt, channels, sfreq, abyterate, blockalign, bits_per_sample, fsd):
      self.fmt = fmt
      self.channels = channels
      self.sfreq = sfreq
      self.abyterate = abyterate
      self.blockalign = blockalign
      self.bits_per_sample = bits_per_sample
      self.fsd = fsd
   
   def __repr__(self):
      return '{}{}'.format(type(self).__name__, (self.fmt, self.channels, self.sfreq, self.abyterate, self.blockalign,
         self.bits_per_sample))
      
   hdr_fmt = '<HHLLH'
   hdr_size = struct.calcsize(hdr_fmt)
   shdr_PCM_fmt = '<H'
   shdr_PCM_size = struct.calcsize(shdr_PCM_fmt)
   @classmethod
   def build_this(cls, dref):
      (fmt, channels, sfreq, abyterate, blockalign) = struct.unpack(cls.hdr_fmt, dref.get_data(cls.hdr_size))
      if (fmt == cls.FMT_MS_PCM):
         (bits_per_sample,) = struct.unpack(cls.shdr_PCM_fmt, dref.get_data(off=cls.hdr_size))
         fsd = b''
      elif (fmt == cls.FMT_MS_ADPCM):
         (bits_per_sample,) = struct.unpack(cls.shdr_PCM_fmt, dref.get_data(2,off=cls.hdr_size))
         fsd = dref.get_data(30, off=cls.hdr_size+2)
      else:
         raise ValueError('Unknown Wave fmt {:d}.'.format(fmt))
      
      return cls(fmt, channels, sfreq, abyterate, blockalign, bits_per_sample, fsd=b'')
   
   def get_data_size(self):
      rv = self.hdr_size
      if (self.fmt in (self.FMT_MS_PCM, self.FMT_MS_ADPCM)):
         # MS_PCM
         rv += self.shdr_PCM_size
      else:
         raise ValueError('Unknown Wave fmt {:d}.'.format(self.fmt))
      rv += len(self.fsd)
      return _RIFFDataSize(rv)
   
   def write_to_file(self, out):
      hdr = struct.pack(self.hdr_fmt, self.fmt, self.channels, self.sfreq, self.abyterate, self.blockalign)
      
      if (self.fmt in (self.FMT_MS_PCM, self.FMT_MS_ADPCM)):
         # MS_PCM
         hdr2 = struct.pack(self.shdr_PCM_fmt, self.bits_per_sample)
      else:
         raise ValueError('Unknown Wave fmt {:d}.'.format(self.fmt))
      
      ds = self.get_data_size()
      rv = out(self.get_chunk_header(ds))
      rv += out(hdr)
      rv += out(hdr2)
      rv += out(self.fsd)
      rv += ds.write_padding(out)
      
      return rv


class RIFFChunkList(list):
   @classmethod
   def build_from_file(cls, f, off=None, off_lim=None):
      rv = cls()
      if (off is None):
         off = f.tell()
      if (off_lim is None):
         off_lim = f.seek(0,2)
         f.seek(off)
      
      while (off < off_lim):
         f.seek(off)
         (cid,) = struct.unpack('>L', f.read(4))
         (csize,) = struct.unpack('<L', f.read(4))
         dref = DataRefFile(f, off+8, csize)
         rv.append(RIFFChunk.build(FourCC(cid), dref))
         off += 8 + csize
         if (csize % 2):
            off += 1
      
      if (off != off_lim):
         raise ValueError('Attempted to read {:d} bytes beyond domain wall.'.format(off-off_lim))
      return rv

   riff_chunk_header_size = 8
   def get_data_size(self):
      return _RIFFDataSize(sum((e.get_data_size() for e in self)) + len(self)*self.riff_chunk_header_size)
   
   def write_to_file(self, out):
      rv = 0
      for e in self:
         rv += e.write_to_file(out)
      return rv

class RIFFFile(RIFFChunkList):
   @classmethod
   def build_wav(cls, dref, *args, **kwargs):
      fmt = RIFFChunk_Wave_fmt(*args, **kwargs)
      data = RIFFChunk(FourCC(b'data'), dref)
      
      rv = cls()
      rv.append(RIFFChunk_RIFF(FourCC(b'WAVE'), RIFFChunkList([fmt, data])))
      return rv

def _main():
   import optparse
   op = optparse.OptionParser()
   op.add_option('-m', '--remux', default=False, action='store_true', help='Attempt to remux files.')
   (opts, args) = op.parse_args()
   
   for fn in args:
      fn = fn.encode()
      f = open(fn, 'rb')
      rifff = RIFFFile.build_from_file(f)
      print(rifff)
      if (opts.remux):
         f2 = open(fn + b'.e17p.tmp', 'wb')
         rifff.write_to_file(f2.write)

if (__name__ == '__main__'):
   _main()
