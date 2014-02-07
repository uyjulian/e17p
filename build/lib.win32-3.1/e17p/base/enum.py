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

class EnumElement(int):
   def __new__(cls, i, name):
      return super().__new__(cls, i)
   
   def __getstate__(self):
      pass
   def __setstate__(self, state):
      pass
   
   def __getnewargs__(self):
      return (int(self), self.name)
   
   def __init__(self, i, name):
      self.name = name
   
   def __str__(self):
      return self.name

class Enum(set):
   def __init__(self, name, v0=0, vd=1, names=()):
      self.__name = name
      self.__v = v0
      self.__vd = vd
      for name in names:
         self.add(name)
   
   def add(self, name):
      v = self.__v
      ename = '{}.{}'.format(self.__name, name)
      e = EnumElement(v, ename)
      self.__v += self.__vd
      super().add(e)
      setattr(self, name, e)

