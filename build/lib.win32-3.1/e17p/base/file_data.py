#!/usr/bin/env python3
# Copyright (C) 2010  Sebastian Hagen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Media container I/O: Base types

import struct

class ContainerError(Exception):
   pass

class ContainerParserError(ContainerError):
   pass

class ContainerCodecError(ContainerError):
   pass

class DataRef:
   __slots__ = ()

class DataRefFile(DataRef):
   def __init__(self, f, off, size):
      self.f = f
      self.off = off
      self.size = size
   
   def get_data(self, l=None, off=None):
      if (off is None):
         off = 0
      
      if (l is None):
         l = self.size - off
      elif ((l + off) > self.size):
         raise ValueError('Attempted to read {:d} bytes ({:d}/{:d}) from domain of length {:d}.'.format(l+off, off, l, self.size))
      
      off += self.off
      self.f.seek(off)
      
      return self.f.read(l)
   
   def get_dref_plain(self):
      """Return dref to access this data in plaintext (i.e. unobfuscated and decompressed at this layer)."""
      return self
   
   def get_size(self):
      return self.size
   
   @classmethod
   def build_from_similar(cls, src, *args, **kwargs):
      return cls(src.f, src.off, src.size, *args, **kwargs)
   
   def __format__(self, fs):
      return '{0}{1}'.format(type(self).__name__, (self.f, self.off, self.size))

#class DataRefBytes(DataRef, bytes):
   #def __init__(self, *args, **kwargs):
      #bytes.__init__(self)
   
   #def get_data(self):
      #return self
      
   #def get_size(self):
      #return len(self)

#class DataRefMemoryView(DataRef):
   #def __init__(self, data):
      #self._data = data
   
   #def get_data(self):
      #return self._data
   
   #def get_size(self):
      #return len(self._data)

#class DataRefNull(DataRef):
   #__slots__ = ('_size',)
   #def __init__(self, size):
      #self._size = size
   
   #def get_data(self):
      #return (b'\x00'*self._size)
   
   #def get_size(self):
      #return self._size


class FourCC(int):
   def __new__(cls, x):
      if (isinstance(x, str)):
         x = x.encode('ascii')
      if (isinstance(x, bytes)):
         (x,) = struct.unpack('>L', x)
      
      assert(struct.pack('>L', x))
      return int.__new__(cls, x)
   
   def get_bytes(self):
      return struct.pack('>L', self)
   
   def __format__(self, s):
      rv = struct.pack('>L', self)
      return ascii(rv)

