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

from ..ever17.vn_backend import E17VNBackend, E17VNMediaStorageLNK, main as main_e17

class ImageViewportN7:
   def __init__(self, y=0):
      self.y = y
   
   def get_coords_opengl(self, img):
      y_off = ((img.height-600) - (self.y*300))/img.height
      height = (600/img.height)
      y_off_ogl = y_off
      return (0,1,y_off_ogl,y_off_ogl+1)


class N7VNBackend(E17VNBackend):
   SCR_START_DEFAULT = b'OP'
   VP_CLS = ImageViewportN7
   def init_backend(self, *args, **kwargs):
      # Track inter-file calls so we can return given the appropriate opcode.
      super().init_backend(*args, **kwargs)
      self._va_tdata = None
   
   def _push_vad(self, fn):
      """Temporarily store a voice clip FN."""
      if not (self._va_tdata is None):
         raise ValueError('Unable to push VA fn {}; already have {}.'.format(fn, self._va_tdata))
      self._va_tdata = fn
   
   def _draw_charart(self, fn, *args, **kwargs):
      try:
         rv = super()._draw_charart(fn, *args, **kwargs)
      except KeyError:
         # FIXME:
         # The meaning of this name mangling is currently unknown. Figure out the details.
         if (fn.endswith(b'NA')):
            dl = 2
         elif (fn.endswith(b'D') or fn.endswith(b'N')):
            dl = 1
         else:
            raise
         
         fn2 = fn[:-1*dl]
         self.log(38, 'No char image named {!r}; falling back to {!r}.'.format(fn, fn2))
         rv = super()._draw_charart(fn2, *args, **kwargs)
      return rv
   
   def _pop_vad(self):
      rv = self._va_tdata
      self._va_tdata = None
      return rv

class N7VNMediaStorageLNK(E17VNMediaStorageLNK):
   @staticmethod
   def _get_dhd():
      from .ff import get_full_dhd
      return get_full_dhd()
   
   def getfile_voice(self, fn):
      return self._files[b'wave.dat'][fn.lower() + b'.waf']


def main(vn_frontend=None):
   main_e17(N7VNBackend, vn_frontend, ms_cls=N7VNMediaStorageLNK)

_main = main
if (__name__ == '__main__'):
   _main()
