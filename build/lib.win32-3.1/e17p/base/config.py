#!/usr/bin/env python3
#Copyright 2010 Sebastian Hagen, Svein Ove Aas
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

class ConfigEntry:
   def __init__(self, name, *, const=None, dest=None, default=None, converter=str, shortopt=None, longopt=None, help=None,
         metavar=None):
      if (longopt is None):
         longopt = name.lower().replace(' ','-')
      if not (longopt.startswith('--')):
         longopt = '--' + longopt
      if (shortopt and not shortopt.startswith('-')):
         shortopt = '-' + shortopt
      if (dest is None):
         dest = name.lower().replace(' ', '_')
      
      self.name = name
      self.dest = dest
      self.const = const
      self.default = default
      self.converter = converter
      self.opt_s = shortopt
      self.opt_l = longopt
      self.help = help
      self.metavar = metavar
      
      self.value = default
   
   def _op_cb(self, option, opt_str, val, p):
      if (not (self.const is None) and (val is None)):
         self.value = self.const
         return
      
      try:
         self.value = self.converter(val)
      except ValueError as exc:
         raise OptionValueError('Invalid value {!r} for option {!r}: {}'.format(val, opt_str, exc)) from exc

   def setup_optparse(self, op, og):
      # TODO: Add options for gradual degradation / opt-renaming here.
      if (op.has_option(self.opt_s)):
         raise ValueError('Duped short option {!r} by {}.'.format(self.opt_s, self))

      if (op.has_option(self.opt_l)):
         raise ValueError('Duped long option {!r} by {}.'.format(self.opt_l, self))

      if (self.opt_s):
         args = (self.opt_s, self.opt_l)
      else:
         args = (self.opt_l,)

      if (self.const is None):
         type_ = str
      else:
         type_ = None
      
      og.add_option(*args, help=self.help, action='callback', callback=self._op_cb, type=type_, metavar=self.metavar)


class ConfigSet:
   def __init__(self, name=None):
      from collections import OrderedDict
      self.name = name
      self.elements = OrderedDict()
   
   def get_scs(self, name):
      try:
         rv = self.elements[name]
      except KeyError:
         rv = self.elements[name] = type(self)(name)
      return rv
   
   def get_settings(self):
      return dict((e.dest, e.value) for e in self.elements.values())
   
   def add_element(self, el):
      self.elements[el.name] = el
   
   def setup_optparse(self, op, og=None):
      from optparse import OptionGroup
      if ((og is None) or (og.title is None)):
         name = self.name
      else:
         name = '{}::{}'.format(og.title, self.name)
      
      og = OptionGroup(op, name)
      for el in self.elements.values():
         el.setup_optparse(op, og)
      
      if (name and og._short_opt):
         op.add_option_group(og)
   
   def add_ce(self, *args, **kwargs):
      """Make new config entry and add to set."""
      ce = ConfigEntry(*args, **kwargs)
      self.add_element(ce)
   
   def add_ce_bool(self, *args, **kwargs):
      """Make config entry for boolean option and add to set."""
      ce = ConfigEntry(*args, default=False, converter=bool, **kwargs)
      self.add_element(ce)
      
