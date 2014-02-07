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

# 12R event scripts.

import struct

from ...base.text_fmt import *
from ...base.text_markup import *
from ...base.tok_structures import BaseToken, TokenizerDataRefLE, TTHierarchy, UnknownTokenError
from ...base.file_data import DataRefFile
from ...remember11.ff.event_script import R11ScriptParser

# ------------------------------------------------------------------------------------------------ Token types
class R12Token(BaseToken):
   def __init__(self, f, tt, data):
      self.data = HexFormattedBytes(data)
   
   @staticmethod
   def do_tokendisplay_linebreak():
      return True

class R12TokenUnknown(R12Token):
   def __init__(self, f, tt, data):
      self.type = tt
      super().__init__(f, tt, data)
   
   def format_hr_type(self):
      return str('UK:{:02x}'.format(self.type))
   
   def format_hr_val(self, p):
      return '({})'.format(self.data)
   
   @staticmethod
   def _get_color():
      return TFC_GREY

r12th = TTHierarchy()
_r12th_reg_tt = r12th.reg
r12th.default_cls = R12TokenUnknown

class R12TokenNodata(R12Token):
   data = None
   def __init__(self, f, tt, data):
      if (len(data) != 0):
         raise ValueError('Invalid nodata token data {!r}.'.format(data))

@_r12th_reg_tt
class R12Token0d(R12TokenNodata):
   """0d: Block end marker?"""
   type = 0x0d
   def __init__(self, f, tt, data):
      f.set_end()

   @staticmethod
   def _get_color():
      return TFC_BLUE
   
   def format_hr_val(self, p):
      return '< end? >'

@_r12th_reg_tt
class R12Token1a(R12Token):
   """1a: Textbox off?"""
   type = 0x1a
   def format_hr_val(self, p):
      return '< ?text delay? {} >'.format(self.data)

@_r12th_reg_tt
class R12Token18(R12Token):
   """18: Conversation text block"""
   type = 0x18
   def __init__(self, f, tt, data):
      (uk0, va_idx, text_off, idx, cid) = struct.unpack(b'<HhHhH', data[:10])
      uk_r = LE16Sequence(data[10:]).unpack_u()
      self.text_ref = f.get_text_by_off(text_off)
      self.va_idx = va_idx
      self.idx = idx
      self.cid = cid
      self.data = (uk0,) + uk_r
   
   def format_hr_val(self, p):
      return '< Text: Idx {:d}: {} (char: {} voice: {} aux: {})>'.format(self.idx, self.text_ref, self.cid, self.va_idx,
         self.data)
   
   @staticmethod
   def _get_color():
      return TFC_CYAN_D

@_r12th_reg_tt
class R12Token1a(R12Token):
   """1a: Textbox off?"""
   type = 0x1a
   def format_hr_val(self, p):
      return '< ?textbox off? {} >'.format(self.data)
   
   @staticmethod
   def _get_color():
      return TFC_CYAN

@_r12th_reg_tt
class R12Token22(R12TokenNodata):
   """21: Conversation text block"""
   type = 0x21
   
   def format_hr_val(self, p):
      return '< enable full-screen text mode >'

   @staticmethod
   def _get_color():
      return TFC_CYAN

@_r12th_reg_tt
class R12Token22(R12TokenNodata):
   """22: Conversation text block"""
   type = 0x22
   def format_hr_val(self, p):
      return '< disable full-screen text mode >'

   @staticmethod
   def _get_color():
      return TFC_CYAN

@_r12th_reg_tt
class R12Token30(R12Token):
   """30: BGI fade out?"""
   type = 0x30
   def format_hr_val(self, p):
      return '< ?BGI fade out?: {} >'.format(self.data)

   @staticmethod
   def _get_color():
      return TFC_PURPLE

@_r12th_reg_tt
class R12Token31(R12Token):
   """31: BGI fade in?"""
   type = 0x31
   def format_hr_val(self, p):
      return '< ?BGI fade in?: {} >'.format(self.data)

   @staticmethod
   def _get_color():
      return TFC_PURPLE

@_r12th_reg_tt
class R12Token42(R12Token):
   """42: Charart manipulation"""
   type = 0x42
   def __init__(self, f, tt, data):
      self.data = data.unpack_s()
   
   def format_hr_val(self, p):
      return '< charart: {} >'.format(self.data)
   
   @staticmethod
   def _get_color():
      return TFC_PURPLE

@_r12th_reg_tt
class R12Token43(R12Token):
   """43: Charart clear"""
   type = 0x43
   def __init__(self, f, tt, data):
      self.data = data.unpack_u()

   def format_hr_val(self, p):
      return '< clear charart: {} >'.format(self.data)
   
   @staticmethod
   def _get_color():
      return TFC_PURPLE

@_r12th_reg_tt
class R12Token62(R12Token):
   """62: ??text / image preloader??"""
   type = 0x62
   # TODO: Investigate this further. The intro typewriter time display events seem like a good starting point.

@_r12th_reg_tt
class R12Token6c(R12Token):
   """6c: ??single char text/graphics tile display??"""
   type = 0x6c
   def __init__(self, f, tt, data):
      self.data = data.unpack_u(6)

   @staticmethod
   def _get_color():
      return TFC_PURPLE

@_r12th_reg_tt
class R12Token91(R12Token):
   """91: Set background image"""
   type = 0x91
   def __init__(self, f, tt, data):
      self.data = data.unpack_s()
   
   def format_hr_val(self, p):
      return '< BGI: {} >'.format(self.data)
   
   @staticmethod
   def _get_color():
      return TFC_PURPLE

@_r12th_reg_tt
class R12Token92(R12Token):
   """92: Set background image"""
   type = 0x92
   def __init__(self, f, tt, data):
      self.data = data.unpack_u()
   
   def format_hr_val(self, p):
      return '< BGI: {} >'.format(self.data)
   
   @staticmethod
   def _get_color():
      return TFC_PURPLE

@_r12th_reg_tt
class R12Tokena1(R12Token):
   """a1: Visual effects control?"""
   type = 0xa1
   def __init__(self, f, tt, data):
      self.data = data.unpack_u(6)

   def format_hr_val(self, p):
      return '< ?visual effect control?: {} >'.format(self.data)

   @staticmethod
   def _get_color():
      return TFC_PURPLE


@_r12th_reg_tt
class R12Tokenc9(R12Token):
   """c9: Audio"""
   type = 0xc9
   def __init__(self, f, tt, data):
      (at, *data) = data.unpack_u(5)
      # Audio types:
      #  0: sound effect
      #  1: BGM stop?
      #  2: BGM start?
      self.at = at
      self.data = data
   
   def format_hr_val(self, p):
      return '< Audio: type: {} data: {} >'.format(self.at, self.data)
   
   @staticmethod
   def _get_color():
      return TFC_PURPLE_D


# ------------------------------------------------------------------------------------------------ Parser classes
class LE16Sequence(bytes):
   def unpack_u(self, count=None):
      from struct import unpack
      if (count is None):
         count = len(self)//2
      return unpack(b'<' + b'h'*count, self)

   def unpack_s(self, count=None):
      from struct import unpack
      if (count is None):
         count = len(self)//2
      return unpack(b'<' + b'h'*count, self)

class R12ESTokenizer(TokenizerDataRefLE):
   TH = r12th
   def __init__(self, parser, f, off_base, off_rel, size):
      self._p = parser
      self.off_base = off_base
      off_abs = off_base + off_rel
      super().__init__(f, off_abs, size)

   def set_end(self):
      """Stop parsing at current position."""
      if (self._off > self._off_lim):
         raise ValueError('Had already read {} bytes beyond domain wall at {:x}.'.format(self._off - self._off_lim, self._off_lim))
      self._off_lim = self._off
      self.size = self._off - self.off

   def get_text_by_off(self, off):
      rv = self._p.get_text_by_off(self.off_base + off)
      self.f.seek(self._off)
      return rv

   def _build_token(self, get_dref):
      if (get_dref):
         off0 = self._off
      (tt, tlen) = struct.unpack('<BB', self.read(2))
      
      if (tlen < 2):
         raise ValueError('Insufficient tlen {!r}.'.format(tlen))
      else:
         tdata = LE16Sequence(self.read(tlen-2))
      
      try:
         tcls = self.TH[tt]
      except KeyError:
         tcls = self.TH.default_cls
      
      tok = tcls(self, tt, tdata)
      
      if (get_dref):
         tok._dref = DataRefFile(self.f, off0, tlen)
      
      return tok


class R12ScriptParser(R11ScriptParser):
   EST = R12ESTokenizer
   
   def __init__(self, dref, es_off):
      self.dref = dref
      self.es_off = es_off
   
   def get_est(self):
      return R12ESTokenizer(self, self.dref.f, self.dref.off, self.es_off, self.dref.size - self.es_off)

   def _es2tf(self, tf):
      tf.process_elements((self.get_est(),), self)

   @classmethod
   def build_from_dref(cls, dref):
      (v0, v1) = struct.unpack('<HH', dref.get_data(4))
      if (v1 != 0):
         es_off = v1
      else:
         es_off = v0
      
      return cls(dref, es_off)

_main = R12ScriptParser._dump_tokens_main

if (__name__ == '__main__'):
   _main()
