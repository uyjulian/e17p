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

# R11 event script parser

import collections
import struct

from ...base.text_markup import *
from ...base.tok_structures import *

# ---------------------------------------------------------------- Helper classes
class _FormattingList(list):
   def __format__(self, p):
      if (p.startswith('p')):
         p = p[1:]
      else:
         p = ''
      
      return '[{}]'.format(', '.join((p + format(e)) for e in self))

class _FormattingTuple(tuple):
   def __format__(self, p):
      if (p.startswith('p')):
         p = p[1:]
      else:
         p = ''
      
      if (len(self) == 1):
         return '({},)'.format(self[0])
      
      return '({})'.format(', '.join(p + format(e) for e in self))

# ---------------------------------------------------------------- Script tokenization structures
r11esth = TTHierarchy()
_r11esth_reg_tt = r11esth.reg

class R11ESToken(BaseToken):
   @classmethod
   def build(cls, *args, **kwargs):
      return cls(*args, **kwargs)

   def do_tokendisplay_linebreak(self):
      return True

class R11ESTokenNodata(R11ESToken):
   data = None
   def __init__(self, f):
      pass

@_r11esth_reg_tt
class R11ESToken00(R11ESTokenNodata):
   type = 0x00
   def _get_color(self):
      return TFC_GREY_D

   def do_tokendisplay_linebreak(self):
      return False

@_r11esth_reg_tt
class R11ESToken01(R11ESToken):
   type = 0x01
   def __init__(self, f):
      self.data = (f.read(1),)

@_r11esth_reg_tt
class R11ESToken02(R11ESToken):
   """02: Conditional jumps."""
   type = 0x02
   op_map = {
      # Solid.
      0x00:(None, '=='),
      # Active RE results:
      0x01:(None, '!='),
      0x03:(None, '>='),
      0x04:(None, '<'),
      0x05:(None, '>'),
      #0x06: Another == ??
      0x07:(None, '<=')
   }
   
   def __init__(self, f):
      self.d0 = f.read_u8()
      self.jmp_target = f.read_jmp_target(self.d0 == 0)
      self.arg0 = f.read_smval()
      self.arg1 = f.read_smval()
      self.op = f.read_u16()

   def format_hr_val(self, p):
      try:
         (_,osym) = self.op_map[self.op]
      except KeyError:
         osym = '~{}~'.format(self.op)
      
      return '< CONDJMP({} // ({} {} {})) --> {} >'.format(self.d0, self.arg0, osym, self.arg1, self.jmp_target)

   def _get_color(self):
      return TFC_YELLOW

@_r11esth_reg_tt
class R11ESToken03(R11ESToken):
   """03: Unconditional jump?"""
   type = 0x03
   def __init__(self, f):
      self.d0 = f.read_u8()
      self.jmp_target = f.read_jmp_target(self.d0 == 0)
      f.set_end()
   
   def format_hr_val(self, p):
      return '< JMP({}) --> {} >'.format(self.d0, self.jmp_target)
   
   def _get_color(self):
      return TFC_YELLOW

@_r11esth_reg_tt
class R11ESToken03(R11ESToken):
   type = 0x04
   # Highly Iffy. Only 4 apparent uses in the game.
   def __init__(self, f):
      self.data = (f.read(13),)

#@_r11esth_reg_tt
#class R11ESToken05(R11ESTokenNodata):
   #"""05: ?End marker?"""
   #type = 0x05   
   #def format_hr_val(self, p):
      #return '< ?END? >'
   
   #def _get_color(self):
      #return TFC_BLUE

@_r11esth_reg_tt
class R11ESToken06(R11ESTokenNodata):
   """06: End marker?"""
   type = 0x06
   def __init__(self, f):
      f.set_end()
   
   def format_hr_val(self, p):
      return '< ?END? >'
   
   def _get_color(self):
      return TFC_BLUE

@_r11esth_reg_tt
class R11ESToken09(R11ESToken):
   """09: Memory manipulation"""
   type = 0x09
   op_map = {
      # Fairly solid.
      0x00:(None,'{} = {}'),
      # IFFY!
      0x01:(None,'{} += {}'),
      0x02:(None,'{} -= {}'),
      # Guesswork. Only used in the basketball scene?
      0x10:(None,'{} = random({})'),
      # Fairly solid.
      0x15:(None,'set_scene({})')
   }
   
   def __init__(self, f):
      self.op = f.read_u8()
      self.arg0 = f.read_smval()
      self.arg1 = f.read_smval()
   
   def format_hr_val(self, p):
      try:
         (_,osym) = self.op_map[self.op]
      except KeyError:
         osym = '{{}} (={}=) {{}}'.format(self.op)
      
      return '< MEMOP: {} >'.format(osym.format(self.arg0, self.arg1))
   
   def _get_color(self):
      return TFC_GREEN

@_r11esth_reg_tt
class R11ESToken0c(R11ESToken):
   """0a: Start/End of enforced time delay mode (end of Kokoro arc only)?"""
   type = 0x0a
   def __init__(self, f):
      self.data = (f.read(1),)

   def format_hr_val(self, p):
      return '< ?Forced time delay mode toggle? >'

   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken0c(R11ESToken):
   """0b: Enforced time delays (end of Kokoro arc only)?"""
   type = 0x0b
   def __init__(self, f):
      f.eat_nulls(1)
      self.v0 = f.read_u16()

   def format_hr_val(self, p):
      return '< ?Time delay ({})? >'.format(self.v0)
   
   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken0c(R11ESToken):
   type = 0x0c
   def __init__(self, f):
      self.data = (f.read(3),)

@_r11esth_reg_tt
class R11ESToken0c(R11ESToken):
   type = 0x0f
   def __init__(self, f):
      self.data = (f.read_u8(), f.read_u16(), f.read_u16())
   
   def format_hr_val(self, p):
      return '< ?looping audio / next-es-file-set / etc?: {} >'.format(self.data)
   
   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken12(R11ESToken):
   type = 0x12
   def __init__(self, f):
      self.data = (f.read(5),)

@_r11esth_reg_tt
class R11ESToken13(R11ESToken):
   """13: Fullscreen text mode set."""
   type = 0x13
   def __init__(self, f):
      self.mode = f.read_u8()
   
   def format_hr_val(self, p):
      return '< set fullscreen (no-box) text mode: {} >'.format(self.mode)

   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken16(R11ESToken):
   type = 0x16
   def __init__(self, f):
      # 0: misc
      # 1: Kokoro
      # 2: Satoru
      self.chr_id = f.read_u8()
   
   def format_hr_val(self, p):
      return '< set perspective: {} >'.format(self.chr_id)
   
   def _get_color(self):
      return TFC_BLUE

@_r11esth_reg_tt
class R11ESToken1f(R11ESToken):
   """1f: Some kind of (debug only) text-display?"""
   type = 0x1f
   def __init__(self, f):
      f.eat_nulls(1)
      
      self.data = _FormattingTuple((f.get_text(), f.read_s16(), f.read_s16()))
   
   def format_hr_val(self, p):
      return '< {} >'.format(self.data)

   def _get_color(self):
      return TFC_CYAN_D

@_r11esth_reg_tt
class R11ESToken16(R11ESToken):
   type = 0x2e
   def __init__(self, f):
      self.data = (f.read(3),)

@_r11esth_reg_tt
class R11ESToken25(R11ESToken):
   """25: Jump-choice combo."""
   type = 0x25
   def __init__(self, f):
      count = f.read_u8()
      self.addr = f.read_smval()
      self.data = _FormattingList([_FormattingTuple((f.get_text(), f.read_jmp_target(True), f.read_u16(), f.read_s16()))
         for _ in range(count)])
   
   def format_hr_val(self, p):
      return '< Choice: Addr: {} Options: {:p\n  }>'.format(self.addr, self.data)

   def _get_color(self):
      return TFC_RED

@_r11esth_reg_tt
class R11ESToken2c(R11ESToken):
   type = 0x2c
   def __init__(self, f):
      self.data = (f.read(5),)

@_r11esth_reg_tt
class R11ESToken2c(R11ESToken):
   # Highly iffy. Only one apparent use in the game.
   type = 0x2f
   def __init__(self, f):
      self.data = (f.read(3),)

@_r11esth_reg_tt
class R11ESToken2c(R11ESToken):
   type = 0x30
   def __init__(self, f):
      self.data = (f.read(3),)

@_r11esth_reg_tt
class R11ESToken33(R11ESToken):
   type = 0x33
   def __init__(self, f):
      count = f.read_u8()
      self.data = _FormattingTuple((f.read_u8(), f.read_s16(), f.read_u8(), f.read_s16(), f.read_u8(), f.read_u8(),
        f.read_u16(), f.read_u16()) for _ in range(count))
   
   def format_hr_val(self, p):
      return '< image: {} >'.format(self.data)
   
   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken33(R11ESToken):
   type = 0x34
   def __init__(self, f):
      self.data = _FormattingTuple((f.read_u8(), f.read_smval(), f.read_s16(), f.read_u16(), f.read_s16(), f.read_s16()))

   def format_hr_val(self, p):
      return '< {} >'.format(self.data)

@_r11esth_reg_tt
class R11ESToken33(R11ESToken):
   type = 0x35
   def __init__(self, f):
      self.data = f.read(5)

@_r11esth_reg_tt
class R11ESToken37(R11ESToken):
   type = 0x37
   def __init__(self, f):
      self.data = (f.read(5),)

@_r11esth_reg_tt
class R11ESToken37(R11ESTokenNodata):
   type = 0x38
   def __init__(self, f):
      f.eat_nulls(1)

@_r11esth_reg_tt
class R11ESToken3a(R11ESTokenNodata):
   type = 0x3a
   def __init__(self, f):
      f.eat_nulls(1)

@_r11esth_reg_tt
class R11ESToken3b(R11ESToken):
   type = 0x3b
   def __init__(self, f):
      self.data = (f.read(5),)

@_r11esth_reg_tt
class R11ESToken3c(R11ESToken):
   type = 0x3c
   def __init__(self, f):
      self.data = (f.read(1),)

@_r11esth_reg_tt
class R11ESToken3c(R11ESToken):
   type = 0x3d
   def __init__(self, f):
      self.data = f.read_u8()

   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken3e(R11ESToken):
   type = 0x3e
   def __init__(self, f):
      self.data = f.read_u8()

   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken3f(R11ESToken):
   type = 0x3f
   def __init__(self, f):
      self.data = (f.read_u8(), f.read_u16())

   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken40(R11ESToken):
   type = 0x40
   def __init__(self, f):
      self.data = (f.read_u8(), f.read_u16())

   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken41(R11ESToken):
   """41: Sound effect."""
   type = 0x41
   def __init__(self, f):
      self.sid = f.read_u8()
      self.val = f.read_smval()

   def format_hr_val(self, p):
      return '< sound effect: {}, {} >'.format(self.sid, self.val)
   
   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken42(R11ESToken):
   type = 0x42
   def __init__(self, f):
      self.sid = f.read_u8()
      self.val = f.read_u16()

   def format_hr_val(self, p):
      return '< {}, {} >'.format(self.sid, self.val)

   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken45(R11ESToken):
   type = 0x44
   def __init__(self, f):
      self.data = (f.read(3),)

@_r11esth_reg_tt
class R11ESToken45(R11ESToken):
   type = 0x45
   def __init__(self, f):
      self.data = (f.read(3),)

@_r11esth_reg_tt
class R11ESToken49(R11ESToken):
   type = 0x49
   def __init__(self, f):
      self.data = (f.read(1),)

@_r11esth_reg_tt
class R11ESToken4a(R11ESToken):
   """4a: Text display mode switch?"""
   type = 0x4a
   def __init__(self, f):
      # 0: Normal display?
      # 1: Centred?
      self.mode = f.read_u8()

   def _get_color(self):
      return TFC_PURPLE

   def format_hr_val(self, p):
      return '< ?set text display mode?: {} >'.format(self.mode)

@_r11esth_reg_tt
class R11ESToken4a(R11ESToken):
   type = 0x4b
   def __init__(self, f):
      self.data = f.read(11)

@_r11esth_reg_tt
class R11ESToken53(R11ESToken):
   type = 0x53
   data = None
   def __init__(self, f):
      f.eat_nulls(1)

@_r11esth_reg_tt
class R11ESToken53(R11ESToken):
   type = 0x54
   def __init__(self, f):
      self.data = (f.read(3), f.read_u16(), f.read_u16(), f.read_s16(), f.read_s16())

@_r11esth_reg_tt
class R11ESToken53(R11ESToken):
   type = 0x55
   def __init__(self, f):
      self.data = f.read(4)

@_r11esth_reg_tt
class R11ESToken60(R11ESToken):
   """60: Play movie."""
   type = 0x60
   def __init__(self, f):
      # See DBG_MENU.BIP:0x10e for most of the list for these.
      # TODO: Figure out how the game does this mapping. There's probably something in init.bin for that.
      self.mv_idx = f.read_u8()
   
   def format_hr_val(self, p):
      return '< movie: {} >'.format(self.mv_idx)
   
   def _get_color(self):
      return TFC_BLUE

@_r11esth_reg_tt
class R11ESToken61(R11ESToken):
   type = 0x61
   def __init__(self, f):
      self.data = (f.read(11),)

@_r11esth_reg_tt
class R11ESToken62(R11ESToken):
   type = 0x62
   def __init__(self, f):
      self.data = f.read_u8()

@_r11esth_reg_tt
class R11ESToken63(R11ESToken):
   type = 0x63
   def __init__(self, f):
      self.data = (f.read(15),)

@_r11esth_reg_tt
class R11ESToken64(R11ESToken):
   type = 0x64
   def __init__(self, f):
      self.data = (f.read(1),)

@_r11esth_reg_tt
class R11ESToken65(R11ESToken):
   """65: ?large image display formatting?"""
   type = 0x65
   def __init__(self, f):
      self.data = f.read(37)
   
   def format_hr_val(self, p):
      return '< ?image display reformat?: {} >'.format(hexs(self.data))
   
   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken67(R11ESToken):
   type = 0x67
   def __init__(self, f):
      self.data = (f.read(5),)

@_r11esth_reg_tt
class R11ESToken68(R11ESToken):
   type = 0x68
   def __init__(self, f):
      self.data = (f.read(5),)

@_r11esth_reg_tt
class R11ESToken69(R11ESToken):
   """69: Background image switch?"""
   type = 0x69
   def __init__(self, f):
      v0 = f.read_u8()
      if (v0 != 1):
         raise ValueError('0x69 reader got unexpected initial value {:#x}.'.format(v0))
      self.data = f.read(20)

   def format_hr_val(self, p):
      return '< background image: {} >'.format(hexs(self.data))

   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken6d(R11ESToken):
   """6d: scene title display?"""
   type = 0x6d
   def __init__(self, f):
      v0 = f.read_u8()
      if (v0 != 2):
         raise ValueError('0x6d reader got unexpected initial value {:#x}.'.format(v0))
   
   def format_hr_val(self, p):
      return '< display scene title >'
      
   def _get_color(self):
      return TFC_PURPLE

@_r11esth_reg_tt
class R11ESToken6e(R11ESToken):
   type = 0x6e
   def __init__(self, f):
      self.data = (f.read(1),)

@_r11esth_reg_tt
class R11ESToken6f(R11ESToken):
   type = 0x6f
   def __init__(self, f):
      f.eat_nulls(1)
      self.data = (f.read(2),)

@_r11esth_reg_tt
class R11ESToken70(R11ESToken):
   type = 0x70
   def __init__(self, f):
      self.data = (f.read(1),)

@_r11esth_reg_tt
class R11ESToken70(R11ESToken):
   type = 0x71
   def __init__(self, f):
      self.data = (f.read(1),)

@_r11esth_reg_tt
class R11ESToken73Text(R11ESToken):
   """73: Conversation text."""
   type = 0x73
   def __init__(self, f):
      f.eat_nulls(1)
      self.text_ref = f.get_text()
      self.idx = f.read_s16()
      self.va_idx = f.read_s16()
      # Character ids:
      #  0: (None)
      #  1: Kokoro
      #  2: Satoru
      #  3: Mayuzumi
      #  4: Yomogi
      #  6: Hotori
      #  7: Yuni
      #  8: ?Hotori original? (system sounds only?)
      #  9: Enomoto
      # 10: Girl
      self.cid = f.read_u16()
   
   def format_hr_val(self, p):
      return '< Text: Idx {:d} {} (Voice: {} character: {})>'.format(self.idx, self.text_ref, self.va_idx, self.cid)
   
   def _get_color(self):
      return TFC_CYAN_D

@_r11esth_reg_tt
class R11ESToken74(R11ESToken):
   """74: Choice spec."""
   type = 0x74
   def __init__(self, f):
      option_count = f.read_u8()
      self.addr = f.read_smval()
      f.eat_nulls(2)
      self.opts = tuple((f.get_text(), f.read_jmp_target(), f.read_u16(), f.read_u16()) for _ in range(option_count))
   
   def format_hr_val(self, p):
      return '< Choice: Addr: {} Data: Opts: {} >'.format(self.addr,
         ''.join('\n    ({})'.format(' '.join(format(x) for x in o)) for o in self.opts))

   def _get_color(self):
      return TFC_RED

@_r11esth_reg_tt
class R11ESToken7f(R11ESToken):
   type = 0x7f
   def __init__(self, f):
      self.data = (f.read(1),)

@_r11esth_reg_tt
class R11ESToken81(R11ESToken):
   type = 0x81
   def __init__(self, f):
      self.data = (f.read(15),)

@_r11esth_reg_tt
class R11ESToken82(R11ESToken):
   type = 0x82
   def __init__(self, f):
      self.data = (f.read(11),)

@_r11esth_reg_tt
class R11ESToken82(R11ESToken):
   type = 0x83
   def __init__(self, f):
      self.data = (f.read(1),)

@_r11esth_reg_tt
class R11ESToken84(R11ESToken):
   type = 0x84
   def __init__(self, f):
      self.data = (f.read(5),)

@_r11esth_reg_tt
class R11ESToken85(R11ESTokenNodata):
   type = 0x85
   def __init__(self, f):
      f.eat_nulls(1)

@_r11esth_reg_tt
class R11ESToken85(R11ESToken):
   type = 0x86
   def __init__(self, f):
      self.data = (f.read(1),)


class R11TextRef(DataRefFile):
   def __format__(self, s):
      data = self.get_data()
      try:
         d_out = data.decode('shift-jis')
      except ValueError:
         d_out = str(data)
      
      return '({:d}){!r}'.format(self.off, d_out)


class R11SMVal(int):
   def __format__(self, s):
      # Judging by the distribution of these numbers, this is probably not so much a flat memory model as a segmented one,
      # with the lowest 'memory segment' instead coding for literal int values.
      # Differences between other segments have so far not been established.
      v = int(self)
      sval = (v & 0xe000) >> 13
      v &= 0x1fff
      if (sval):
         rv = 'mem[{}][{}]'.format(sval, v)
      else:
         rv = format(v)
      return rv


class R11ESTokenizer(TokenizerDataRefLE):
   TH = r11esth
   def __init__(self, parser, f, off_base, off_rel, size):
      off_abs = off_base + off_rel
      self.off_base = off_base
      self.off_rel = off_rel
      super().__init__(f, off_abs, size)
      self._p = parser
   
   def get_segment_name(self, i):
      return '{:#x}'.format(self.off_rel)
   
   def _build_token(self, *args, **kwargs):
      if (self._off in self._p.data_offs):
         raise StopTokenization()
      self._p._mark_es_off_processed(self._off)
      return self.TH.build(self, *args, **kwargs)
   
   def read_smval(self):
      """Read R11 ?segmented memory? value."""
      return R11SMVal(self.read_u16())
   
   def read_jmp_target(self, es_data=True):
      """Read 16bit jump offset."""
      # IFFY:
      # Is this really a signed value? 0xFFFF is apparently used to indicate None, but that might simply be
      # special-cased. For now leave the paranoid sanity check in, and see if we ever find something that triggers it.
      rv = self.read_s16()
      if (rv == -1):
         return None
      elif (rv < 0):
         raise ValueError('Unexpected jmp target val {!r}.'.format(rv))
      
      if (es_data):
         self._p._add_es_off(rv)
      else:
         self._p._add_data_off(rv)
      return HexInt(rv)
   
   def get_text(self):
      off = self.read_u16()
      return self.get_text_by_off(off)
   
   def get_text_by_off(self, off):
      rv = self._p.get_text_by_off(self.off_base + off)
      self.f.seek(self._off)
      return rv

class R11ScriptParser:
   EST = R11ESTokenizer
   
   def __init__(self, dref, es_oi, menu_data):
      self.dref = dref
      self.es_oi = es_oi # Event script offset info
      self.es_data = None
      self.data_offs = None
      self.es_pending = None
      self.menu_data = menu_data

   def dump_menu_data(self, output):
      if (self.menu_data is None):
         return
      
      def fmt_text(off):
         # Not actually the correct codec for nonstandard shift-jis codepoints. Use it here as a preliminary hack until (if)
         # we figure out the full correct mapping.
         return FT_String('{:#x}({!r})'.format(off, self.get_text_by_off(off).get_data().decode('shift_jisx0213')))
      
      output(FT_String('-------- file-level menu:\n'))
      table = FT_Table()
      for entry in self.menu_data:
         table.add_row((fmt_text(entry.text1_off), fmt_text(entry.text2_off), FT_String('{:#x}'.format(entry.esd_off))))
      output(FT_Indented(table,2))

   def get_text_by_off(self, off):
      if (off >= self.dref.size):
         raise ValueError('Offset {!r} starts beyond domain wall.'.format(off))
      
      off_abs = self.dref.off + off
      data = bytearray(1024)
      f = self.dref.f
      f.seek(off_abs)
      i = 1024
      size = 0
      while (i == 1024):
         i = f.readinto(data)
         i2 = data.find(b'\x00')
         if (i2 != -1):
            i = i2
         size += i
      
      return R11TextRef(f, off_abs, size)

   def _mark_es_off_processed(self, off):
      try:
         v = self.es_data[off]
      except KeyError:
         pass
      else:
         if not (v is None):
            raise ValueError('Off {} has been parsed before: {}'.format(off, v))
      self.es_data[off] = True
   
   def _add_data_off(self, off):
      self.data_offs.add(off)
   
   def _add_es_off(self, off):
      if (off in self.es_data):
         return
      self.es_data[off] = None
      self.es_pending.append(off)
   
   def enumerate_es(self, est_cb):
      self.es_data = es_data = {}
      self.data_offs = set()
      self.es_pending = es_pending = list(self.es_oi)
      
      for off in self.es_oi:
         es_data[off] = None
      
      while (es_pending):
         es_pending.sort()
         i = 0
         while ((i < len(es_pending)) and (es_data[es_pending[i]])):
            i += 1
         
         if (i >= len(es_pending)):
            break
         
         off = es_pending[i]
         del(es_pending[:i+1])
         
         est = R11ESTokenizer(self, self.dref.f, self.dref.off, off, self.dref.size - off)
         est_cb(est)
         es_data[off] = est
      
      self.es_data = None
      self.es_pending = None
      self.data_offs = None
      
   
   _R11ESE = collections.namedtuple('_R11ESE', 'text1_off text2_off esd_off o3 uk0 uk1 uk2 uk3 uk4 uk5 uk6 uk7 uk8 uk9 uk10 uk11 uk12 idx uk14')
   @classmethod
   def build_from_dref(cls, dref):
      f = dref.f
      off = dref.off
      f.seek(off)
      # TODO: ... there must be a better way to test this than that. Find it.
      d = f.read(4)      
      if (d == b'\x09\x0f\x06\x00'):
         (uk0, s_off) = struct.unpack('<HH', f.read(4))
         # TODO: Process data between header and script.
         es_oi = [s_off]
         menu_data = None
      else:
         f.seek(off)
         esd_offs = set()
         es_oi = []
         menu_data = []
         while (True):
            data = cls._R11ESE(*struct.unpack('<HHHHLHHHHHHLHHLHHLL', f.read(48)))
            if (data.text1_off == 0):
               break
            menu_data.append(data)
            
            if (data.esd_off in esd_offs):
               continue
            esd_offs.add(data.esd_off)
            es_oi.append(data.esd_off)
         menu_data = tuple(menu_data)
      
      return cls(dref, es_oi, menu_data)

   def _es2tf(self, tf):
      self.enumerate_es(lambda est: (tf.process_elements((est,), self)))

   @classmethod
   def _dump_tokens_main(cls):
      import sys
      import optparse
      import os.path
      from ...base.config import ConfigSet
      
      op = optparse.OptionParser()
      op.add_option('--afs', dest='afs', default=False, action='store_true', help='Parse data from AFS files')

      conf = ConfigSet()
      TokenFormatter.add_config(conf)
      conf.setup_optparse(op)
      
      (opts, args) = op.parse_args()
      fn_list = args
      
      tf = TokenFormatter.build_from_config(conf, outname='event script data', tok_cls=cls.EST)
      
      def process_fragment(dref):
         pass
      
      if (opts.afs):
         from .afs import AFSParser
         def make_file_reader(f):
            afsp = AFSParser.build_from_file(f)
            for (cfn, dref, ad) in afsp:
               yield (cfn, cls.build_from_dref(dref.get_data_unpacked()))
         
      else:
         def make_file_reader(f):
            return [(f.name, cls.build_from_dref(DataRefFile(f, 0, f.seek(0,2))))]
      
      for fn in fn_list:
         f = open(fn, 'rb')
         for (name, p) in make_file_reader(f):
            fn_l = os.path.basename(name)
            tf.out_str('---------------- Parsed {!r}:\n'.format(fn_l))
            p.dump_menu_data(tf.output)
            p._es2tf(tf)
      
      tf.dump_summary()
      tf.finish_output(sys.stdout.write)


# ---------------------------------------------------------------- UI code
_main = R11ScriptParser._dump_tokens_main

if (__name__ == '__main__'):
   _main()
