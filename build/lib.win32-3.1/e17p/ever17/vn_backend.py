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

# Base VN engine classes.

import collections
import logging
import os
import os.path
import random

from ..base.enum import Enum

# ---------------------------------------------------------------- VN backend types
class E17VNMediaStorageLNK:
   logger = logging.getLogger('E17VNMediaStorageLNK')
   log = logger.log
   
   def __init__(self, lnks, movie_path):
      self._lnks = lnks
      self._files = {}
      for (fn,lnk) in lnks:
         d = self._files[fn] = {}
         for chunk in lnk:
            cn = chunk.name.lower()
            if (cn in d):
               raise ValueError('Duplicated chunk {!a} ({!a}, {!a}).'.format(cn, self._files[cn].f, dref.f))
            d[cn] = self.wrap_dref(cn, chunk)
      
      try:
         fns = os.listdir(movie_path)
      except (ValueError, EnvironmentError):
         self._movies = None
      else:
         self._movies = {}
         for fn in fns:
            self._movies[b'.'.join(fn.lower().split(b'.')[:-1])] = os.path.join(movie_path, fn)

   @staticmethod
   def _get_dhd():
      from .ff import get_full_dhd
      return get_full_dhd()      

   @classmethod
   def build_from_dir(cls, dn, **kwargs):
      from .ff.lnk import LNKParser
      if (isinstance(dn, str)):
         dn = dn.encode('ascii')
      fns = os.listdir(dn)
      lnks = []
      for fn in fns:
         if not (fn.endswith(b'.dat')):
            continue
         pn = os.path.join(dn, fn)
         try:
            lnk = LNKParser.build_from_file(open(pn, 'rb'))
         except ValueError:
            continue
         lnks.append((fn,lnk))
      
      return cls(lnks, movie_path=os.path.join(dn, b'movie'), **kwargs)
   
   def wrap_dref(self, cn, dref):
      ext = cn.split(b'.')[-1]
      rv = self._get_dhd().build(ext, dref)
      if (rv is None):
         rv = dref
      rv.fn = cn

      return rv
   
   def getfile_script(self, fn):
      return self._files[b'script.dat'][fn.lower() + b'.scr']
   
   def getfile_bgi(self, fn):
      return self._files[b'bg.dat'][fn.lower() + b'.cps']
   
   def getfile_chara(self, fn):
      return self._files[b'chara.dat'][fn.lower() + b'.cps']
   
   def getfile_voice(self, fn):
      return self._files[b'voice.dat'][fn.lower() + b'.waf']
   
   
   def getfile_movie(self, fn):
      if (self._movies is None):
         raise EnvironmentError('No movies available.')
      pn = self._movies[fn.lower()]
      f = open(pn, 'rb')
      return f

class VNError(Exception):
   pass

class VNStateError(VNError):
   pass

class E17Memory(list):
   def __init__(cls):
      return super().__init__((0 for _ in range(2048)))

_E17VNChoiceOption = collections.namedtuple('_E17VNChoiceOption', 'text i cidx')

class E17VNChoice:
   def __init__(self, cid):
      super().__init__()
      self.id = cid
      self._ci = 0
      self._chosen_opt = None
      self.options = []

   def _add_option(self, text, display):
      if (display):
         self.options.append(_E17VNChoiceOption(text, len(self.options), self._ci))
      self._ci += 1
   
   def answered(self):
      return not (self._chosen_opt is None)
   
   def choose_option(self, opt):
      if (self.options[opt.i] != opt):
         raise ValueError('Invalid option {} for choice {}.'.format(opt, self))
      self._chosen_opt = opt
   
   def _get_coidx(self):
      return self._chosen_opt.cidx
   
   def __repr__(self):
      return '<{} {} {}>'.format(type(self).__name__, self.id, self.options)

class _VNLinefeed:
   pass

class VNTextblock:
   def __init__(self, text, voice_data):
      self.text = tuple(text) # lines of text
      self.voice_data = voice_data

   def __repr__(self):
      return '<{} {} {}>'.format(type(self).__name__, self.text, self.voice_data)

class E17VNRNGSimple:
   def __init__(self):
      self._r = random.Random()
   
   def randint(self, v):
      return self._r.randint(0, v-1)

class ImageViewport:
   def __init__(self, x0=0, y0=0, w=None, h=None):
      self._x0 = x0
      self._y0 = y0
      self._w = w
      self._h = h
   
   def get_coords_opengl(self, img):
      iw = img.width
      ih = img.height
      
      if (self._w is None):
         w = 1
      else:
         w = self._w/iw
      if (self._h is None):
         h = 1
      else:
         h = self._h/ih
      
      x0 = self._x0/iw
      y1 = (1-self._y0/ih)
      
      return (x0, x0 + w, y1 - h, y1)

class VNBacklog(list):
   pass

class E17VNBackend:
   logger = logging.getLogger('E17VNBackend')
   log = logger.log
   
   ptrc = Enum('ptrc', 0, 1, 
   (
      'undef',
      'error',
      'end',
      'user_ack',
      'choice',
      'graphics_op',
   ))
   
   SCR_START_DEFAULT = b'op00'
   VP_CLS = ImageViewport
   
   STATE_NAMES = ('_mem', '_r1', '_rng',
      '_scr_fn', '_es_i', '_es_n', '_cs_i', '_cs_n', '_callstack',
      '_bgi_fn', '_bgi_color', '_bgi_vp', '_textbox_faded',
      '_charart',
      '_choice', '_cptrc'
   )
   def init_backend(self, media_storage, rng=E17VNRNGSimple(), scr_start=None, continue_on_error=False, *, debug_color=False):
      if (scr_start is None):
         scr_start = self.SCR_START_DEFAULT
      
      self._ms = media_storage
      self._rng = rng
      self._cs = None
      self._cs_i = None
      self._cs_n = None
      self._coe = continue_on_error
      self._debug_color = debug_color
      self._mem = E17Memory()
      self._r1 = None
      self._choice = None
      self._cptrc = None
      self._textbox_faded = False
      self._callstack = None
      self.backlog = VNBacklog()
      
      self.set_scr(scr_start)
      
      # Frontend state tracking
      self._bgi_fn = None
      self._bgi_color = (0,0,0)
      self._bgi_vp = None
      self._charart = {}
   
   __csn = 'Ever17 VN backend options'
   @classmethod
   def add_config(cls, cs):
      ace = cs.get_scs(cls.__csn).add_ce
      ace('color', shortopt='-u', dest='debug_color', default=False, const=True, help='Colorize debug output.')
      ace('quiet', shortopt='-q', default=False, const=True, help='Suppress script processing log output.')
      ace('nocont', default=True, const=False, dest='continue_on_error', help='Do not continue on errors.')
      ace('choice_f0', longopt='--choice-fix0', default=False, const=True, dest='choice_f0', help='Always choose first option in choices.')
   
   @staticmethod
   def __new_choice_f0(choice):
      choice.choose_option(choice.options[0])

   @classmethod
   def build_from_config(cls, cs, **kwargs):
      kwargs2 = cls._get_settings(cs)
      kwargs2.update(kwargs)
      return cls(**kwargs2)

   @classmethod
   def _get_settings(cls, cs):
      return {}

   def init_backend_from_config(self, cs, **kwargs):
      scs = cs.get_scs(self.__csn)
      kw = scs.get_settings()
      kw.update(kwargs)
      if (kw.pop('choice_f0')):
         self.new_choice = self.__new_choice_f0 
      if (kw.pop('quiet')):
         self.logger.setLevel(35)
      
      self.init_backend(**kw)
   
   def get_pos_hr(self):
      return 'es: {}({}) cs: {}({})'.format(self._es_n, self._es_i, self._cs_n, self._cs_i)
   
   def get_path_state(self):
      """Get current VN path state."""
      from copy import deepcopy
      rv = {}
      for name in self.STATE_NAMES:
         rv[name] = deepcopy(getattr(self, name))
      return rv
   
   def set_path_state(self, state):
      """Restore saved VN path state."""
      for (key, val) in state.items():
         setattr(self, key, val)
      self._scr = self._ms.getfile_script(self._scr_fn)
      # Restore ES state
      if (self._es_n is None):
         self._es = None
      else:
         self._es_i -= 1
         self._es = self._scr.get_es(self._es_n).get_tokens()
      # Restore CS state
      if (self._cs_n is None):
         self._cs = None
      else:
         self._cs_i -= 1
         self._cs = self._scr.get_cs(self._cs_n).get_tokens()
      
      # Restore BGI
      self.clear_charart_all(0)
      if (self._bgi_color is None):
         bgi_c = self._ms.getfile_bgi(self._bgi_fn)
         self.display_bgi(bgi_c, self._bgi_vp, 0)
      else:
         self.fade_bg_fill(self._bgi_color, 0)
      
      # Restore charart
      for (slot, (fn, x0)) in self._charart.items():
         self.display_charart(self._ms.getfile_chara(fn), slot, x0, 0)
      
      # Textboxing
      if (self._textbox_faded):
         self.fade_textbox(0)
      else:
         self.unfade_textbox(0)
      
      return self.process_tokens()

   # ------ Token operation interface methods
   def break_token_loop(self, rc):
      self._cptrc = rc
   
   def push_scr_pos(self):
      """Save current script file and position."""
      # This might be a true callstack, but we don't know that yet ... stick with something simpler unless/until we get
      # specific evidence that more than one piece of data is saved.
      csn = (self._scr, self._es_n, self._es_i)
      if not (self._callstack is None):
         raise ValueError('Already have callstack {!r} while trying to push {!r}.'.format(self._callstack, csn))
      self._callstack = csn
   
   def return_scr(self):
      """Jump back to saved script position."""
      (self._scr, es_n, es_i) = self._callstack
      self.set_es(es_n)
      self._es_i = es_i
      self._callstack = None
   
   def set_cs(self, idx):
      """Set active conversation script."""
      self.log(20, 'Loading conversation script {:d}.'.format(idx))
      idx = int(idx)
      if not (self._cs is None):
         raise VNStateError('I already have an active conv script.')
      self._cs = self._scr.get_cs(idx).get_tokens()
      self._cs_i = 0
      self._cs_n = idx
   
   def set_es(self, idx):
      """Set event script."""
      self.log(20, 'Loading event script {:d}.'.format(idx))
      idx = int(idx)
      self._es = self._scr.get_es(idx).get_tokens()
      self._es_n = idx
      self._es_i = 0
   
   def set_scr(self, scr_fn, i=0):
      """Set active scriptfile."""
      self.log(20, 'Switching to script file {!a}.'.format(scr_fn))
      scr = self._ms.getfile_script(scr_fn)
      self._scr = scr
      self._scr_fn = scr_fn
      self.set_es(i)
   
   def _new_choice(self, *args, **kwargs):
      """Initialize new choice."""
      if not (self._choice is None):
         raise ValueError('{} already has an active choice {}.'.format(self, self._choice))

      rv = E17VNChoice(*args, **kwargs)
      self._choice = rv
      return rv
   
   def _reap_choice(self):
      rv = self._choice
      if ((rv is None) or (not rv.answered())):
         raise VNStateError('No finished choice available.')
      self._choice = None
      return rv
   
   def _new_textblock(self, text, voice_fn):
      """Make new textblock."""
      if (voice_fn is None):
         vd = None
      else:
         vd = self._ms.getfile_voice(voice_fn)
      
      tb = VNTextblock(text, vd)
      self.new_textblock(tb)
      self.backlog.append(tb)
      self._unfade_textbox()
      # FIXME: Do this more efficiently.
      tb.__state = self.get_path_state()
   
   def _randint(self, v):
      return self._rng.randint(v)
   
   def _display_bgi(self, fn, *args, **kwargs):
      """Display background image by fn."""
      c = self._ms.getfile_bgi(fn)
      self._clear_charart_all(0)
      vp = self.VP_CLS(*args, **kwargs)
      self.display_bgi(c, vp, 0.1)
      self._bgi_fn = fn
      self._bgi_vp = vp
      self._bgi_color = None
      self._cptrc = self.ptrc.graphics_op
   
   def _panzoom_bgi(self, delay, *args, **kwargs):
      """Change viewport on background image through a pan/zoom operation."""
      vp = self.VP_CLS(*args, **kwargs)
      self.panzoom_bgi(vp, delay)
      self._bgi_vp = vp
      self._cptrc = self.ptrc.graphics_op
   
   def _fade_bg_fill(self, color, delay):
      """Fade BG to constant color."""
      self.fade_bg_fill(color, delay)
      self._bgi_color = color
   
   def _play_movie(self, fn):
      try:
         f = self._ms.getfile_movie(fn)
      except (ValueError, EnvironmentError) as exc:
         self.log(40, 'Unable to play movie {!r}: {}.'.format(fn, exc))
         return
      self.play_movie(f)
   
   # R1 stuff is rather iffy. More likely this is part of a bigger memory block the access rules for which we don't understand
   # yet.
   def _r1_set(self, v):
      self._r1 = v
   
   def _r1_get(self):
      return self._r1

   def get_memory(self, i):
      """Read value of a memory cell and return it."""
      return self._mem[i]
   
   def set_memory(self, i, v):
      """Write value to a memory cell."""
      self._mem[i] = int(v)

   def set_fatal_error(self):
      """Note fatal error, blocking further playback."""
      self._cptrc = self.ptrc.error

   def _end_vn(self):
      """Note regular end of VN path, blocking further playback."""
      self._cptrc = self.ptrc.end
      self.log(20, 'VN playback finished.')
   
   def _draw_charart(self, fn, slot, x0):
      """Display character art image."""
      self.display_charart(self._ms.getfile_chara(fn), slot, x0, 0.1)
      self._charart[slot] = (fn, x0)
      self._cptrc = self.ptrc.graphics_op
   
   def _clear_charart(self, slot):
      """Stop displaying character art image."""
      self.clear_charart(slot, 0.1)
      try:
         del(self._charart[slot])
      except KeyError:
         self.log(38, 'Charart slot management mismatch: Attempting to delete from empty slot {!r} at {}.'.format(slot, self.get_pos_hr()))
      self._cptrc = self.ptrc.graphics_op
   
   def _clear_charart_all(self, delay):
      """Stop displaying all character art images."""
      self.clear_charart_all(delay)
      self._charart.clear()
      self._cptrc = self.ptrc.graphics_op
   
   def _unfade_textbox(self, delay=0.1):
      if (self._textbox_faded):
         self.unfade_textbox(delay)
         self._textbox_faded = False
         self._cptrc = self.ptrc.graphics_op
   
   def _fade_textbox(self, delay=0.1):
      """Fade out textbox."""
      self.fade_textbox(delay)
      self._textbox_faded = True
      self._cptrc = self.ptrc.graphics_op
   
   def _process_token(self, tok):
      try:
         p = tok.process
      except AttributeError as exc:
         if not (self._coe):
            raise
         self.log(34, 'Unsupported tok type: {}'.format(tok.format_hr(self._scr, color=self._debug_color)))
      else:
         p(self)
         self.log(20, 'Processed token {}.'.format(tok.format_hr(self._scr, color=self._debug_color)))
   
   # ------ UI input methods
   def jump_back(self, idx):
      m = self.backlog[idx]
      # FIXME: Do this more efficiently.
      self.set_path_state(m.__state)
      del(self.backlog[idx:])
      #print(self.get_pos_hr())
      #print(self._cs)
   
   def process_tokens(self):
      if not ((self._choice is None) or self._choice.answered()):
         raise VNStateError('Unable to continue: Choice pending.')

      if (self._cptrc is self.ptrc.end):
         raise VNStateError('Path playback is finished.')
      
      if not (self._cptrc is self.ptrc.error):
         self._cptrc = None
      
      while (self._cptrc is None):
         if (self._cs):
            # Get conversation script token
            try:
               tok = self._cs[self._cs_i]
            except IndexError:
               # conversation script finished
               self._cs = None
               self._cs_n = None
               if not (self._choice is None):
                  if (len(self._choice.options) == 0):
                     raise VNError('Bytecode-level bug / parser failure: Tried to pose question without valid options.')

                  self.new_choice(self._choice)
                  self.backlog.append(self._choice)
                  self._cptrc = self.ptrc.choice
                  break
               # continue with event script processing
               continue
            else:
               self._cs_i += 1
         else:
            # Get event script token
            try:
               tok = self._es[self._es_i]
            except IndexError:
               # event script finished; continue with next block
               self.set_es(self._es_n + 1)
               continue
            else:
               self._es_i += 1
         
         self._process_token(tok)
      
      if (self._cptrc is self.ptrc.error):
         raise VNError('Bytecode processing failure.')
      
      return self._cptrc

# ---------------------------------------------------------------- Debug classes
class _ESState(tuple):
   def __format__(self, s):
      return '({}, {:2d}, {:d})'.format(*self)
   
   def same_es(self, o):
      return (self[:2] == o[:2])

class _E17Memory_I(E17Memory):
   def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self._am = [0]*len(self)
   
   def __setitem__(self, i, v):
      rv = super().__setitem__(i,v)
      self._am[i] += 1
      return rv
   
   def __getitem__(self, i):
      rv = super().__getitem__(i)
      self._am[i] += 1
      return rv

class E17VNBackendInstrumentationMixin(E17VNBackend):
   def init_backend(self, *args, **kwargs):
      super().init_backend(*args, **kwargs)
      self._mem = _E17Memory_I()

   def _get_es_state(self):
      return _ESState((self._scr.fn, self._es_n, self._es_i))
   
   def _process_token(self, tok):
      s1 = self._get_es_state()
      tf = tok.format_hr(self._scr, color=self._debug_color)
      super()._process_token(tok)
      s2 = self._get_es_state()
      if not (s1.same_es(s2)):
         self.log(20, 'JUMP:{} {} --> {}'.format(s1, tf, s2))
   
   def run(self, *args, **kwargs):
      rv = super().run(*args, **kwargs)
      print('MAM: {}'.format(self._mem._am))
      print('MEM: {}'.format(self._mem))
      return rv

def _cls_mix(vn_classes):
   return 


# ---------------------------------------------------------------- Test code
def main(vn_backend, vn_frontend=None, ms_cls=E17VNMediaStorageLNK):
   import sys
   import optparse
   from ..base.config import ConfigSet
   
   if (vn_frontend is None):
      from ..ui.text_dummy_renderer import DummyTextPlayer as vn_frontend
   
   vn_cls = type('__MixedVNPlayer', (vn_frontend, vn_backend), {})
   conf = ConfigSet()
   vn_cls.add_config(conf)
   
   op = optparse.OptionParser()
   conf.setup_optparse(op)
   
   (opts, args) = op.parse_args()
   (ddir,) = args
   
   logging.getLogger().setLevel(10)
   logging.basicConfig(format='%(asctime)s %(levelno)s %(message)s', stream=sys.stdout)
   
   ms = ms_cls.build_from_dir(ddir)
   
   vnp = vn_cls.build_from_config(conf)
   vnp.init_backend_from_config(conf, media_storage=ms)
   vnp.init_frontend_from_config(conf)
   vnp.run()

def _main():
   main(E17VNBackendInstrumentationMixin)

if (__name__ == '__main__'):
   _main()
