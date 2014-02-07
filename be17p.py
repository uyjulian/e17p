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

# This used to be a simple symlink, but apparently Microsoft totally bothced
# support for these in their older and more popular OSes, so in the interest
# of backwards-compatibility we hack around that deficiency here.

import sys

fn = 'e17p.py'
code = compile(open(fn, 'rt').read(), fn, 'exec')

if (__name__ == '__main__'):
   ns = {'__file__':__file__, '__name__':'e17p'}
   exec(code, ns)
   ns['main'](build=True)

