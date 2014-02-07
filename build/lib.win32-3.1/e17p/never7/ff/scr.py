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

# Never7 event scripts.

import copy

from . import data_handler_reg
from ...base.file_data import DataRefFile
from ...base.text_markup import *
from ...base.tok_structures import TTHierarchy
from ...ever17.ff.scr import (E17ScriptParser, E17ScriptTokenizer, E17ConvScriptTokenizer, e17stth, e17ctth, E17TokenE,
   E17TokenCSynthTextblock, E17TokenE10, E17TokenConvLike, E17TokenCString, E17TokenE00, E17TokenE01, E17TokenE80)


# -------------------------------------------------------------------------------- Event script token types
class N7TokenE(E17TokenE):
   pass

class N7TokenENodata(N7TokenE):
   data = None
   def __init__(self, f):
      pass

class N7TokenE10(E17TokenE10):
   pass

class N7TokenE10Nodata(N7TokenE10):
   data = None
   def __init__(self, f):
      pass

n7stth = TTHierarchy() # copy.deepcopy(e17stth)
_n7_reg_tt = n7stth.reg

n7stth[0x10] = n7stth_10 = copy.deepcopy(e17stth[0x10])
_n7_reg_tt_10 = n7stth_10.reg

n7stth[0x00] = n7stth_00 = TTHierarchy()
_n7_reg_tt_00 = n7stth_00.reg
n7stth[0x01] = n7stth_01 = copy.deepcopy(e17stth[0x01])
_n7_reg_tt_01 = n7stth_01.reg

_n7_reg_tt_10 = n7stth_10.reg
for oc in (
      0x00, 0x01, 0x03, 0x05, 0x06, 0x07, 0x08, 0x0a, 0x0b, 0x0d, 0x0e, 0x0f, 
      0x10, 0x11, 0x13, 0x15, 0x19, 0x1a
   ):
   n7stth_00[oc] = e17stth[0x00][oc]
del(oc)
n7stth[0x80] = n7stth_80 = copy.deepcopy(e17stth[0x80])
_n7_reg_tt_80 = n7stth_80.reg
n7stth[0xfe] = e17stth[0xfe]
n7stth[0xff] = e17stth[0xff]

class N7TokenE80(E17TokenE80):
   pass

class N7TokenE00(E17TokenE00):
   pass

class N7TokenE01(E17TokenE01):
   pass

class N7TokenE00Nodata(N7TokenE00):
   data = None
   def __init__(self, f):
      pass

class N7TokenE01Nodata(N7TokenE01):
   data = None
   def __init__(self, f):
      pass

# ---------------- <00>
@_n7_reg_tt_00
class N7TokenE00_04(N7TokenE00Nodata):
   """00-04: special-purpose inter-file jump."""
   type = 0x04
   def __init__(self, f):
      self.data = (f.read_u8(), f.read_av(), f.read_esr(True))
      
   def _get_color(self):
      return TFC_YELLOW

@_n7_reg_tt_00
class N7TokenE00_0c(N7TokenE00):
   type = 0x0c
   def __init__(self, f):
      self.data = f.read_av()
      f.eat_nulls(2)

@_n7_reg_tt_00
class N7TokenE00_0e(N7TokenE00Nodata):
   """00-0e: SCR return"""
   type = 0x0e
   
   def __init__(self, f):
      f.set_end()
   
   def process(self, engine):
      engine.return_scr()
      
   def format_hr_val(self, p):
      return '< RETURN >'
   
   def _get_color(self):
      return TFC_YELLOW

@_n7_reg_tt_00
class N7TokenE00_12(N7TokenE00):
   type = 0x12
   def __init__(self, f):
      self.data = f.read_av()

@_n7_reg_tt_00
class N7TokenE00_20(N7TokenE00Nodata):
   type = 0x20

@_n7_reg_tt_00
class N7TokenE00_21(N7TokenE00Nodata):
   type = 0x21

@_n7_reg_tt_00
class N7TokenE00_22(N7TokenE00):
   type = 0x22
   def __init__(self, f):
      # stack push operation?
      self.data = f.read_av()
   
   def format_hr_val(self, p):
      return '( AV: {} )'.format(self.data)

# ---------------- </00>
# ---------------- <01>
@_n7_reg_tt_01
class N7TokenE01_02(N7TokenE01):
   type = 0x02
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av(), f.read_fnr(), f.read_av(),  f.read_esr(True))

@_n7_reg_tt_01
class N7TokenE01_03(N7TokenE01):
   type = 0x03
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av(), f.read_av(), f.read_av(), f.read_esr(True))

@_n7_reg_tt_01
class N7TokenE01_13(N7TokenE01):
   type = 0x13
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av(), f.read_fnr(), f.read_av(), f.read_esr(True))

@_n7_reg_tt_01
class N7TokenE01_17(N7TokenE01):
   type = 0x17
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())

# ---------------- </01>
# ---------------- <10>
@_n7_reg_tt_10
class N7TokenE10_00(N7TokenE10Nodata):
   type = 0x00

@_n7_reg_tt_10
class N7TokenE10_01(N7TokenE10):
   """10-01: Visual effect"""
   type = 0x01
   def __init__(self, f):
      # effect types:
      #  0: ?none?
      # 28: rays of light (upper right)
      # 32: White edges (system::filter.cps) overlay
      self.effect_type = f.read_av()

   def _get_color(self):
      return TFC_PURPLE

   def format_hr_val(self, p):
      return '< visual (bgi) effect: {} >'.format(self.effect_type)

@_n7_reg_tt_10
class N7TokenE10_02(N7TokenE10):
   type = 0x02
   def __init__(self, f):
      self.data = f.read_av()
      
   def format_hr_val(self, p):
      return '({})'.format(self.data)
      
   #def _get_color(self):
   #   return TFC_PURPLE

@_n7_reg_tt_10
class N7TokenE10_03(N7TokenE10):
   """10-03: Choice result store."""
   type = 0x03
   def __init__(self, f):
      self.addr = f.read_av()
   
   def format_hr_val(self, p):
      return '< Store choice response: --> mem<{}> >'.format(self.addr)
   
   def process(self, engine):
      (addr,) = self.addr.process(engine, 1)
      addr = int(addr)
      engine.set_memory(addr, engine._reap_choice()._get_coidx())
   
   def _get_color(self):
      return TFC_RED

@_n7_reg_tt_10
class N7TokenE10_04(N7TokenE10):
   """10-04: Inter-file jump."""
   type = 0x04
   def __init__(self, f):
      self.fn = f.read_bytes_fixedterm(b'\x00')
      f.set_end()

   def process(self, engine):
      engine.set_scr(self.fn)

   def format_hr_val(self, p):
      return '< JMP: {!r} >'.format(self.fn)

   def _get_color(self):
      return TFC_YELLOW

@_n7_reg_tt_10
class N7TokenE10_05(N7TokenE10):
   """10-05: Inter-file jump that saves current position for return."""
   type = 0x05
   def __init__(self, f):
      self.aux = f.read_av()
      self.fn = f.read_bytes_fixedterm(b'\x00')
   
   def process(self, engine):
      # FIXME:
      # What about the associated data? Is this thing conditional?
      engine.push_scr_pos()
      engine.set_scr(self.fn)
   
   def format_hr_val(self, p):
      return '< returnable JMP: {!r} ({}) >'.format(self.fn, self.aux)

   def _get_color(self):
      return TFC_YELLOW

@_n7_reg_tt_10
class N7TokenE10_06(N7TokenE10):
   type = 0x06
   def __init__(self, f):
      self.data = f.read_av()

@_n7_reg_tt_10
class N7TokenE10_07(N7TokenE10Nodata):
   type = 0x07

@_n7_reg_tt_10
class N7TokenE10_08(N7TokenE10):
   """10-03: Sound effect."""
   type = 0x08
   def __init__(self, f):
      self.fn = f.read_bytes_fixedterm(b'\x00')
      self.data = f.read_av()
   
   def format_hr_val(self, p):
      return '< sound effect: {} {} >'.format(self.fn, self.data)

   def _get_color(self):
      return TFC_PURPLE_D

@_n7_reg_tt_10
class N7TokenE10_09(N7TokenE10Nodata):
   type = 0x09

@_n7_reg_tt_10
class N7TokenE10_0a(N7TokenE10Nodata):
   type = 0x0a

@_n7_reg_tt_10
class N7TokenE10_0b(N7TokenE10):
   """10-0b: VA reference."""
   type = 0x0b
   def __init__(self, f):
      self.fn  = f.read_bytes_fixedterm(b'\x00')
   
   def format_hr_val(self, p):
      return '< voice: {} >'.format(self.fn)

   def process(self, engine):
      engine._push_vad(self.fn)

   def _get_color(self):
      return TFC_PURPLE_D

@_n7_reg_tt_10
class N7TokenE10_0c(N7TokenE10):
   """10-0c: set panzoomed bgi"""
   type = 0x0c
   def __init__(self, f):
      self.fnr = f.read_fnr()
      self.ivp = f.read_av()
      self.te = f.read_av()
      self.data = f.read_av()

   def process(self, engine):
      y_off = int(self.ivp.process(engine._scr, 1)[0])
      engine._display_bgi(self.fnr.get_refdata(engine._scr), y_off)

   def format_hr_val(self, p):
      return '< bgi: {} vp: {} transition effect: {} aux: {} >'.format(self.fnr.format_hr(p), self.ivp, self.te, self.data)

   def _get_color(self):
      return TFC_PURPLE

@_n7_reg_tt_10
class N7TokenE10_0d(N7TokenE10):
   type = 0x0d
   def __init__(self, f):
      self.data = f.read_av()

@_n7_reg_tt_10
class N7TokenE10_0e(N7TokenE10):
   """10-0e: bgi panzoom"""
   type = 0x0e
   def __init__(self, f):
      self.vp = f.read_av()
      self.delay = f.read_av()
   
   def process(self, engine):
      engine._panzoom_bgi(
         # FIXME: The time scale here is merely a guess. We need more research to determine the precise one.
         self.delay.process(engine, 1)[0]/20,
         self.vp.process(engine, 1)[0]
      )
   
   def format_hr_val(self, p):
      return '< bgi panzoom: vp: {} delay: {} >'.format(self.vp, self.delay)

   def _get_color(self):
      return TFC_PURPLE

@_n7_reg_tt_10
class N7TokenE10_0f(N7TokenE10Nodata):
   type = 0x0f
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av(), f.read_av())

   def format_hr_val(self, p):
      return '< ?bgi effect (preparation)? {} >'.format(self.data)

   def _get_color(self):
      return TFC_PURPLE

@_n7_reg_tt_10
class N7TokenE10_10(N7TokenE10Nodata):
   """10-10: set BGI"""
   type = 0x10
   def __init__(self, f):
      self.fnr = f.read_fnr()
      # transition effects:
      #  0: quick crossfade
      #  4: vertical rotating bars effect
      #  5: Like 4, but rotating the other way?
      self.te = f.read_av()
      self.data = f.read_av()

   def process(self, engine):
      engine._display_bgi(self.fnr.get_refdata(engine._scr))

   def format_hr_val(self, p):
      return '< bgi: {} transition effect: {} data: {} >'.format(self.fnr.format_hr(p), self.te, self.data)

   def _get_color(self):
      return TFC_PURPLE

@_n7_reg_tt_10
class N7TokenE10_11(N7TokenE10):
   """10-11: Charart display"""
   type = 0x11
   def __init__(self, f):
      self.slot = f.read_av()
      self.fnr = f.read_fnr()
      self.pos = f.read_av()
      self.data = f.read_av()

   def format_hr_val(self, p):
      return '< charart: {} slot: {} pos: {} aux: {} >'.format(self.fnr.format_hr(p), self.slot, self.pos, self.data)

   def process(self, engine):
      fn = self.fnr.get_refdata(engine._scr)
      pos = int(self.pos.process(engine, 1)[0])
      slot = int(self.pos.process(engine, 1)[0])
      engine._draw_charart(fn, slot, pos)

   def _get_color(self):
      return TFC_PURPLE

@_n7_reg_tt_10
class N7TokenE10_12(N7TokenE10):
   """10-12: Charart clear"""
   type = 0x12
   def __init__(self, f):
      self.slot = f.read_av()
      self.data = f.read_av()

   def process(self, engine):
      (img_slot,) = self.slot.process(engine, 1)
      engine._clear_charart(int(img_slot))

   def format_hr_val(self, p):
      return '< clear charart slot: {} aux: {} >'.format(self.slot, self.data)

   def _get_color(self):
      return TFC_PURPLE

@_n7_reg_tt_10
class N7TokenE10_14(N7TokenE10):
   type = 0x14
   def __init__(self, f):
      f.eat_nulls(4)
      v1_1 = f.read_u16()
      v1_2 = f.read_av()
      f.eat_nulls(4)
      v2_1 = f.read_u16()
      v2_2 = f.read_av()
      self.data = (v1_1, v1_2, v2_1, v2_2)

@_n7_reg_tt_10
class N7TokenE10_15(N7TokenE10):
   """10-15: full charart clear?"""
   type = 0x15
   def __init__(self, f):
      self.data = f.read_av()

   def format_hr_val(self, p):
      return '< clear all charart: {} >'.format(self.data)

   def process(self, engine):
      # TODO: What about the data?
      engine._clear_charart_all(0)

   def _get_color(self):
      return TFC_PURPLE

@_n7_reg_tt_10
class N7TokenE10_16(N7TokenE10):
   type = 0x16
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())

@_n7_reg_tt_10
class N7TokenE10_17(N7TokenE10Nodata):
   """10-17: Time display."""
   type = 0x17
   data = None
   def __init__(self, f):
      pass
   
   def format_hr_val(self, p):
      return '< time display: (mem[252]:mem[253]) >'
   
   def _get_color(self):
      return TFC_PURPLE

@_n7_reg_tt_10
class N7TokenE10_1a(N7TokenE10):
   type = 0x1a
   def __init__(self, f):
      self.data = f.read_av()

@_n7_reg_tt_10
class N7TokenE10_1b(N7TokenE10):
   type = 0x1b
   def __init__(self, f):
      self.fnr = f.read_fnr()
   
   def format_hr_val(self, p):
      return '< bgi: {} >'.format(self.fnr.format_hr(p))

   def _get_color(self):
      return TFC_PURPLE

@_n7_reg_tt_10
class N7TokenE10_1c(N7TokenE10Nodata):
   type = 0x1c

@_n7_reg_tt_10
class N7TokenE10_1e(N7TokenE10Nodata):
   type = 0x1e

@_n7_reg_tt_10
class N7TokenE10_22(N7TokenE10Nodata):
   """10-22: Movie playback"""
   type = 0x22
   def __init__(self, f):
      self.fn = f.read_bytes_fixedterm(b'\x00')

   def process(self, engine):
      engine._play_movie(self.fn)

   def format_hr_val(self, p):
      return '< Movie: {} >'.format(self.fn)

   def _get_color(self):
      return TFC_BLUE

@_n7_reg_tt_10
class N7TokenE10_23(N7TokenE10Nodata):
   type = 0x23

@_n7_reg_tt_10
class N7TokenE10_27(N7TokenE10):
   type = 0x27
   def __init__(self, f):
      self.data = f.read_av()

@_n7_reg_tt_10
class N7TokenE10_2d(N7TokenE10Nodata):
   type = 0x2d

@_n7_reg_tt_10
class N7TokenE10_2e(N7TokenE10Nodata):
   type = 0x2e
   def __init__(self, f):
      self.data = f.read_av()

@_n7_reg_tt_10
class N7TokenE10_28(N7TokenE10Nodata):
   type = 0x28

@_n7_reg_tt_10
class N7TokenE10_29(N7TokenE10Nodata):
   type = 0x29

@_n7_reg_tt_10
class N7TokenE10_2c(N7TokenE10):
   type = 0x2c
   def __init__(self, f):
      self.data = f.read_av()

# ---------------- </10>
# ---------------- <80>
@_n7_reg_tt_80
class N7TokenE80_01(N7TokenE80):
   """80-01: ?returnable intra-file jump?"""
   type = 0x01
   def __init__(self, f):
      self.data = (f.read_u16(), f.read_esr())
   
   def _get_color(self):
      return TFC_YELLOW

@_n7_reg_tt_80
class N7TokenE80_11(N7TokenE80):
   type = 0x11
   def __init__(self, f):
      self.data = f.read(3)

@_n7_reg_tt_80
class N7TokenE80_12(N7TokenE80):
   type = 0x12
   def __init__(self, f):
      self.data = f.read_u16()
# ---------------- </80>

# -------------------------------------------------------------------------------- Conversation script token types
n7ctth = TTHierarchy()
_n7_reg_ctt = n7ctth.reg

class N7TokenC(E17TokenConvLike):
   pass
   def do_tokendisplay_linebreak(self):
      return True

class N7TokenCNodata(N7TokenC):
   data = None
   def __init__(self, f):
      pass

@_n7_reg_ctt
class N7TokenC_01(N7TokenCNodata):
   # End of block marker?
   type = 0x00
   def _get_color(self):
      return TFC_BLUE
   
   def format_hr_val(self, p):
      return '< ?end? >'

@_n7_reg_ctt
class N7TokenC_01(N7TokenCNodata):
   type = 0x01

@_n7_reg_ctt
class N7TokenC_02(N7TokenCNodata):
   """C02: Wait-for-user-ack breakpoint."""
   type = 0x02
   def process(self, engine):
      engine.break_token_loop(engine.ptrc.user_ack)
   
   def do_tokendisplay_linebreak(self):
      return False

@_n7_reg_ctt
class N7TokenC_03(N7TokenCNodata):
   type = 0x03
   def do_tokendisplay_linebreak(self):
      return False

@_n7_reg_ctt
class N7TokenC_03(N7TokenC):
   type = 0x04
   def __init__(self, f):
      self.data = f.read_av()

@_n7_reg_ctt
class N7TokenC_05(N7TokenC):
   type = 0x05
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())

@_n7_reg_ctt
class N7TokenC_0b(N7TokenC):
   """C0b: Choice option."""
   type = 0x0b
   def __init__(self, f):
      self.opt_idx = f.read_u8()
      (self.text, _) = f.read_string()
      f.seek_back(1)

   def process(self, engine):
      choice = engine._choice
      if (choice is None):
         choice = engine._new_choice(None)

      choice._add_option(self.text, display=True)

   def format_hr_val(self, p):
      return '< choice option({}): {} >'.format(self.opt_idx, self.text)

   def get_text_lines(self):
      return (self.text,)

@_n7_reg_ctt
class N7TokenC_0c(N7TokenCNodata):
   type = 0x0c

# -------------------------------------------------------------------------------- Script parser types
class N7TokenCString(E17TokenCString):
   pass

class N7TokenCSynthTextblock(E17TokenCSynthTextblock):
   def __init__(self, text):
      self.text = text
      self.voice_ref = None
   
   def process(self, engine):
      self.voice_ref = engine._pop_vad()
      engine._new_textblock(self.text, self.voice_ref)
   
   def do_tokendisplay_linebreak(self):
      return False

class N7ESTokenizer(E17ScriptTokenizer):
   TH = n7stth

class N7CSTokenizer(E17ConvScriptTokenizer):
   TH = n7ctth
   TTYPE_STR = N7TokenCString
   
   def get_tokens(self, get_dref=False, *args, **kwargs):
      tokens = N7ESTokenizer.get_tokens(self, *args, get_dref=get_dref, **kwargs)
      tc = len(tokens)
      i = 0
      def get_tok():
         nonlocal i
         rv = tokens[i]
         i += 1
         return rv
      
      rv = []
      while (i < tc):
         tok = get_tok()
         tt = tok.get_type()
         if (isinstance(tok, N7TokenCString)):
            text = [tok.val]
            tt2 = None
            while (True):
               tok2 = get_tok()
               if (isinstance(tok2, N7TokenCString)):
                  text[-1] += tok2.val
               elif (tok2.get_type() == (0x01,)):
                  # Line break.
                  text.append('')
               elif (tok2.get_type() == (0x04,)):
                  # TODO: Determine if there's significant semantics here - could be text draw delay?
                  # If so, we'll probably have to intersperse them into the text list ... in any case splitting up messages
                  # over this is not feasible, since voice data is associated with the whole thing.
                  continue
               else:
                  break
            i -= 1
            
            if (text and (text[-1] == '')):
               del(text[-1])
            stb = N7TokenCSynthTextblock(text)
            if (get_dref):
               stb._dref = DataRefFile(tok._dref.f, tok._dref.off, tok2._dref.off-tok._dref.off+tok2._dref.size)
            rv.append(stb)
         else:
            rv.append(tok)
      return rv
            
   
   def read_string(self):
      data = bytearray()
      while (True):
         b = self.read(1)
         if (not self.char_is_text(b)):
            break
         data.extend(b)
      
      # FIXME: The nonstandard shift-jis parts of this are likely incorrect. Identify them and fix this.
      return (data.decode('shift_jisx0213'), b)

class N7ScriptParser(E17ScriptParser):
   EST = N7ESTokenizer
   CST = N7CSTokenizer

data_handler_reg(b'scr')(N7ScriptParser.build_from_dataref)

_main = N7ScriptParser._main

if (__name__ == '__main__'):
   _main()
