#!/usr/bin/env python3
#Copyright 2010 Sebastian Hagen, Svein Ove Aas <svein.ove@aas.no>
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

from . import data_handler_reg
from ...ever17.ff.cps import CPSImageE17, DataRefCPSE17

class CPSImageN7(CPSImageE17):
   def get_coords_opengl(self, pos_data):
      """Return (left, right) offsets in opengl coordinates for specified position data."""
      if (pos_data is None):
         return (-1,1)
      
      off_centre = 0.5 - 0.5*pos_data
      off_w = self.width/800
      return (off_centre-off_w, off_centre + off_w)

class DataRefCPSN7(DataRefCPSE17):
   CPS_CLS = CPSImageN7

data_handler_reg(b'cps')(DataRefCPSN7.build_from_similar)
_main = DataRefCPSN7._main

if (__name__ == '__main__'):
   _main()
