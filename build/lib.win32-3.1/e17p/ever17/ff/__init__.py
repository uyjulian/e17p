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

# E17p Ever17 file formats.

class _VNDataHandlerDict(dict):
   def register(self, key):
      def reg(f):
         l = self.setdefault(key, [])
         l.append(f)
         return f
      return reg
   
   def build(self, key, val):
      for builder in self.get(key,()):
         try:
            rv = builder(val)
         except ValueError:
            pass
         else:
            return rv
   
   def copy(self):
      from copy import copy
      c = copy(self)
      return type(self)(c)

dhd = _VNDataHandlerDict()
data_handler_reg = dhd.register

def reg_all():
   from . import cps, scr, waf

def get_full_dhd():
   reg_all()
   return dhd
