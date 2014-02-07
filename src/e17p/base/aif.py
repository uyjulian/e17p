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

# Simple framework to simplify overrides from associated C modules, when available.

class _Container:
   pass

class AIFuncs:
   def __init__(self, name=None):
      import sys
      import inspect
      # We import the specified module name (or the caller's module prefixed with '_', if None) from the caller's context.
      # This is fairly hackish, but probably makes for the most convenient interface we can easily build.
      
      caller_globals = inspect.stack()[1][0].f_globals
      if (name is None):
         name_split = caller_globals['__name__'].split('.')
         name_split[-1] = '_' + name_split[-1]
         name = '.'.join(name_split)
      
      try:
         __import__(name, globals=caller_globals)
      except ImportError:
         self.aim = None
      else:
         self.aim = sys.modules[name]
      
      self.py = _Container()
      del(caller_globals)

   def add(self, func):
      """Add function with alternative implementation."""
      name = func.__name__
      setattr(self.py, name, func)
      if not (self.aim is None):
         func = getattr(self.aim, name)
         
      return func
