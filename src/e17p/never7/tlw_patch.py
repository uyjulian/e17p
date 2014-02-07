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

import logging

from ..base.file_data import DataRefFile
from ..base.text_fmt import hexs
from ..ever17.ff.lnk import LNKParser
from ..ever17.ff.scr import E17ScriptParser


class X7ScriptPatcher(E17ScriptParser):
   def count_cb(self):
      return len(self._data_cbc)
   
   def set_cs(self, idx, dref):
      self._data_cbc[idx] = dref

class AVInt(int):
   def __init__(self, *args, **kwargs):
      if ((self < 0x00) or (self >= 0x100000000)):
         raise ValueError('Unencodable value {!r}.'.format(self))
   
   def as_av(self):
      from struct import pack
      if (self <= 0x0f):
         return pack('<Bxx', 0x80 | self)
      if (self <= 0x0fff):
         return pack('<BBxx', 0xa0 | (self >> 8), self & 0xff)
      if (self <= 0x0fffff):
         return pack('<BHxx', 0xc0 | (self >> 16), self & 0xffff)
      
      return pack(b'<BLxx', 0xe0, self)

class PatchSegment:
   logger = logging.getLogger('PatchSegment')
   log = logger.log
   def __init__(self, idx, line_orig, line_patched):
      self.idx = idx
      self.line_orig = line_orig
      self.line_patched = line_patched
   
   def get_dref(self):
      from io import BytesIO
      b = BytesIO(self.line_patched)
      return DataRefFile(b, 0, len(self.line_patched))
   
   @classmethod
   def build_from_lines(cls, idx, lines):
      if (len(lines) == 0):
         raise ValueError('Need at least one line.')
      if (len(lines) < 2):
         line_patched = None
      else:
         if (len(lines) > 2):
            cls.log(30, 'Segment {}: got {} instead of 2 lines: {}.'.format(idx, len(lines), lines))
         line_patched = lines[-1]
      
      return cls(idx, lines[0], line_patched)
   

class TLWRPTPatchParser:
   logger = logging.getLogger('TLWRPTPatchParser')
   log = logger.log
   
   FC_MAP = {
      'N': 0x01,
      'P': 0x02,
      'E': 0x03,
      '4': 0x04,
      '5': 0x05,
      'C': 0x0b,
      'Z': 0x0c
   }
   
   def __init__(self, f):
      self.f = f
   
   @classmethod
   def _rpl2bytes(cls, data):
      from struct import pack
      
      buf = list()
      odata = bytearray()
      i = 0
      while (i < len(data)):
         char = data[i]
         i += 1
         if (char != '\\'):
            buf.append(char)
            continue
         # FIXME: This isn't exactly accurate. Change it to use the correct encoding.
         odata.extend(''.join(buf).encode('shift_jisx0213'))
         buf = []
         
         # Decode escape sequence.
         tchar = data[i]
         i += 1
         if (i < len(data)):
            tc_next = data[i]
            if (tc_next != '{'):
               edata = None
            else:
               i += 1
               i_end = data.index('}', i)
               edata = [AVInt(frag.strip(),16) for frag in data[i:i_end].split(',')]
               i = i_end + 1
         else:
            edata = None         
         
         oc_byte = cls.FC_MAP[tchar]
         odata.append(oc_byte)
         
         if (tchar == 'C'):
            if (len(edata) != 1):
               raise ValueError('Invalid \C data: {!r}'.format(edata))
            odata.append(edata[0])
         elif not (edata is None):
            for ival in edata:
               odata.extend(ival.as_av())
      # The segment terminator codes aren't included in this format; add them manually.
      odata.append(0x00)
      return bytes(odata)
   
   def __iter__(self):
      idx_last = None
      ldata = []
      for line in self.f:
         if ((line == '') or (line.isspace()) or line.startswith('//')):
            continue
         if (not line.startswith('STR_')):
            if (line != 'No text'):
               self.log(30, 'Ignoring line with unknown fmt in {!r}: {!r}'.format(self.f, line))
            continue
         
         (prefix, data) = line[4:].split(':',1)
         prefix = prefix.strip()
         data = data.strip()
         
         idx = int(prefix.strip(), 16)
         #if not (data.startswith("'") and data.endswith("'")):
            #self.log(30, 'Ignoring line with unknown fmt in {!r}: {!r}'.format(self.f, line))
            #continue
         #data = data[1:-1]
         # Be more tolerant for the moment, at least until the wiki content stabilizes.
         data = data.strip('\n \'')
         
         
         if (idx != idx_last):
            if (ldata):
               yield(PatchSegment.build_from_lines(idx_last, ldata))
            idx_last = idx
            ldata = []
         
         try:
            bdata = self._rpl2bytes(data)
         except Exception as exc:
            self.log(30, 'Failed to parse line {}({!r}): {!r}.'.format(idx, data, exc))
            continue
         ldata.append(bdata)
      
      if (ldata):
         yield(PatchSegment.build_from_lines(idx_last, ldata))

class X7LNKScriptPatcher(LNKParser):
   logger = logging.getLogger('X7LNKScriptPatcher')
   log = logger.log
   prepatch_verify = True
   
   def patch_by_dir(self, path):
      from os import listdir
      from os.path import join
      
      self.log(20, '---------------- Processing {}.'.format(self))
      if (isinstance(path, str)):
         path = path.encode()
      
      fns = listdir(path)
      fn_map = {}
      for fn in fns:
         try:
            (_,fnl) = fn.split(b':',1)
         except ValueError:
            continue
         fnl = fnl.lower()
         
         if (fnl in fn_map):
            raise ValueError('Case fn collision: {!r} vs. {!r}.'.format(fn_map[fnl], fn))
         fn_map[fnl] = fn
      
      tcbc = 0
      tcbc_have_patch = 0
      tcbc_patched = 0
      
      for chunk in self:
         name = chunk.name.lower()
         sp = X7ScriptPatcher.build_from_dataref(chunk.get_dref_plain())
         cbc = sp.count_cb()
         tcbc += cbc
         
         patch_fn = fn_map.get(name)
         if (patch_fn is None):
            self.log(20, '-------- {!r:16}: {:5d} / {:5d} / {:5d}     (No patch available.)'.format(chunk.name, 0, 0, cbc))
            continue
         
         patch_path = join(path, patch_fn)
         patch = TLWRPTPatchParser(open(patch_path,'rt', encoding='utf-8'))
         try:
            patch_segments = list(patch)
         except Exception as exc:
            raise ValueError('Failed to parse patch file {!r}.'.format(patch_path)) from exc
         
         cb = sp.count_cb()
         lines_patched = 0
         have_patch = 0
         for s in patch_segments:
            if (s.line_patched is None):
               continue
            have_patch += 1
            
            if (s.idx >= cb):
               self.log(30, '---- Invalid patch against line {} / {}.'.format(s.idx, cb))
               continue
            
            conv = sp.get_cs(s.idx)
            pp_data = conv.get_data()
            if ((not (s.line_orig is None)) and (pp_data != s.line_orig)):
               if (self.prepatch_verify):
                  self.log(30, '---- Invalid patch against line {}:\n    orig: {}\n   patch: {}.'.format(s.idx, hexs(pp_data), hexs(s.line_orig)))
                  continue
               else:
                  self.log(30, '---- Invalid patch against line {} (data mismatch); applying anyway.'.format(s.idx))
                  
            sp.set_cs(s.idx, s.get_dref())
            lines_patched += 1
            
         tcbc_patched += lines_patched
         tcbc_have_patch += have_patch
         
         sp_dref = sp.build_dref()
         chunk.f = sp_dref.f
         chunk.off = sp_dref.off
         chunk.size = sp_dref.size
         chunk.is_compressed = False
         
         self.log(20, '-------- {!r:16}: {:5d} / {:5d} / {:5d}'.format(chunk.name, lines_patched, have_patch, cbc))
      
      if (tcbc):
         pratio = tcbc_patched/tcbc
      else:
         pratio = 0
      
      self.log(20, '------------ total: patched {:5d} / {:5d} ({:.2%}) lines.'.format(tcbc_patched, tcbc, pratio))


def _main():
   import sys
   import optparse
   op = optparse.OptionParser()
   op.add_option('-f', '--force', action='store_true', default=False, help='Force patching of mismatched lines.')
   op.add_option('-o', '--outfile', default=None, help='Filename to write output to.')
   (opts, args) = op.parse_args()
   
   logging.getLogger().setLevel(10)
   logging.basicConfig(format='%(message)s', stream=sys.stdout)
   
   (fn,cache_dir) = args
   cache_dir = cache_dir.encode()
   
   lnk = X7LNKScriptPatcher.build_from_file(open(fn,'rb'))   
   lnk.prepatch_verify = (not opts.force)
   
   lnk.patch_by_dir(cache_dir)
   fno = opts.outfile
   if not (fno is None):
      print('--->>> {!r}'.format(fno))
      f_out = open(fno, 'wb')
      lnk.write(f_out)
      f_out.close()


if (__name__ == '__main__'):
   _main()
