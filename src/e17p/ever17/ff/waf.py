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

# WAF audio file format support.

import struct

from ...base.file_data import DataRefFile
from . import data_handler_reg

# ---------------------------------------------------------------- WAF format support
class _WAFData:
   hdr_fmt = '<4sHHLLH34sL'
   waf_hdr_sz = struct.calcsize(hdr_fmt)
   def __init__(self, dref):
      from ...base.codec.msadpcm import DataRefADPCM
      
      dref.f.seek(dref.off)
      hdr_data = dref.f.read(self.waf_hdr_sz)
      (preamble,uk1,channels,sfreq,ass,blockalign,fsd,dlen) = struct.unpack(self.hdr_fmt, hdr_data)
      if (preamble != b'WAF\x00'):
         raise ValueError('Unexpected preamble {}.'.format(preamble))
      
      body_dref = DataRefADPCM(dref.f, dref.off+self.waf_hdr_sz, dlen, channels>1, blockalign)
      (bits_per_sample,) = struct.unpack('<H', fsd[:2])
      
      self.body_dref = body_dref
      self.channels = channels
      self.sfreq = sfreq
      self.ass = ass
      self.blockalign = blockalign
      self.fsd = fsd
      self.bits_per_sample = bits_per_sample
      self.uk1 = uk1

class WAFDataSegment:
   def __init__(self, dref):
      self.d = dref
   
   def get_pygame_sound(self):
      from io import BytesIO
      from pygame.mixer import Sound
      b = BytesIO()
      wav = self.get_wav()
      wav.write_to_file(b.write)
      b.seek(0)
      
      return Sound(b)
   
   def get_data(self):
      return self.d.get_dref_plain()
   
   def get_waf_data(self):
      return _WAFData(self.d.get_dref_plain())
      
   def get_wav(self):
      from ...base.ff.wav import RIFFFile, RIFFChunk_Wave_fmt
      wd = self.get_waf_data()
      
      return RIFFFile.build_wav(wd.body_dref, fmt=RIFFChunk_Wave_fmt.FMT_MS_ADPCM, channels=wd.channels, sfreq=wd.sfreq,
         blockalign=wd.blockalign, abyterate=wd.ass, bits_per_sample=wd.bits_per_sample, fsd=wd.fsd)
      
   def get_wav_pcm(self):
      from ...base.ff.wav import RIFFFile, RIFFChunk_Wave_fmt
      wd = self.get_waf_data()
      
      if (wd.bits_per_sample != 4):
         raise ValueError('Invalid WAF bits/sample value {!r}.'.format(wd.bits_per_sample))
      
      return RIFFFile.build_wav(wd.body_dref.get_pcm_dref(), fmt=RIFFChunk_Wave_fmt.FMT_MS_PCM, channels=wd.channels,
         sfreq=wd.sfreq, blockalign=4*wd.blockalign, abyterate=4*wd.ass, bits_per_sample=16, fsd=b'')

data_handler_reg(b'waf')(WAFDataSegment)

def _main():
   import optparse
   op = optparse.OptionParser()
   op.add_option('-w', '--wav', dest='wav', action='store_true', default=False, help='Dump data to wav files.')
   op.add_option('-p', '--pcm', dest='wav_attrname', default='get_wav', action='store_const', const='get_wav_pcm', help='Convert audio data to PCM codec before writing to wav files.')
   
   (opts, args) = op.parse_args()
   for fn in args:
      fn = fn.encode()
      print('-------------------------------- Processing {}.'.format(fn))
      f = open(fn, 'rb')
      waf = WAFDataSegment(DataRefFile(f, 0, f.seek(0,2)))
      
      wav = getattr(waf,opts.wav_attrname)()
      print('---- wav info: {}'.format(wav))
      if (opts.wav):
         fn2 = fn + b'.wav'
         print('-- Writing: {}.'.format(fn2))
         f2 = open(fn2, 'wb')
         wav.write_to_file(f2.write)

if (__name__ == '__main__'):
   _main()
