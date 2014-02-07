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



# Parser for Ever17 script files, based on reverse-engineering of .scr data format.

import optparse
import re
import struct

from collections import deque
from ...base.file_data import *
from ...base.text_fmt import *
from ...base.text_markup import *
from ...base.tok_structures import *
from . import data_handler_reg

# ---------------------------------------------------------------- Unknown data slicer hacks
class PatternSlicer:
   """Ugly hack to split partially REd binary data into small blocks."""
   def __init__(self, pseq):
      self._pseq = pseq
   
   def _lse(self, i, d):
      #print('>>> {0}'.format(i))
      if (i >= len(self._pseq)):
         if (d):
            print('{0:{1}}{2}'.format('', i+1, hexs(d[0])))
         for sd in d[1:]:
            print('{0:{1}}{2}'.format('', i, hexs(self._pseq[i-1])), end='')
            print('{0:{1}}{2}'.format('', i+1, hexs(sd)))
      elif (d):
         p = self._pseq[i]
         self._lse(i+1, d[0].split(p))
         for sd in d[1:]:
            print('{0:{1}}{2}'.format('', i, hexs(self._pseq[i-1])), end='')
            self._lse(i+1, sd.split(p))
      #print('<<< {0}'.format(i))
   
   def dump_parts(self, d):
      self._lse(0, [d])


class ACDataSplitter:
   # (byteval -> bitcount) table
   BCT = tuple(sum(bool(i & (1 << s)) for s in range(8)) for i in range(256))
   
   def __init__(self, wlen_min=4, wlen_max=32, rm_m=0.6):
      self.wlen_min = wlen_min
      self.wlen_max = wlen_max
      self.rm_m = rm_m
   
   def data_format(self, d, out):
      # H1
      ds = self._data_split(memoryview(d))
      if not (ds):
         return
      
      w_m = max(e[0] for e in ds)
      ii_l = 0
      for (w,ii,line) in ds:
         indent = w_m - w
         if ((w > 2) and (ii >= ii_l)):
            out()
         ii_l = ii
         out(' '*indent + hexs(bytes(line)), end=' ')
      out()
      return
   
   def _data_split(self, m):
      w_m = 2
      idx_max = len(m)-w_m+1
      
      ps = [deque() for _ in range(idx_max)]
      iot = {}
      
      for w in range(w_m, len(m)):
         for i in range(idx_max-w+1):
            bd = bytes(m[i:i+w])
            try:
               ii = iot[bd]
            except KeyError:
               iot[bd] = i
            else:
               if (ii < i):
                  ps[i].appendleft((ii,w))
      
      def make_prv(w_max):
         i = 0
         i_l = 0
         w_l = 0
         rv = []
         idx_s = set([0])
         
         while (i < idx_max):
            for (ii,w) in ps[i]:
               if ((w_max >= w >= 4) and (ii in idx_s)):
                  break
            else:
               idx_s.add(i)
               i += 1
               continue
            
            if not (ps[ii]):
               ps[ii].appendleft((ii,w))
            
            # See if this would jump past a longer match; if so, just use that one instead.
            for i2 in range(i,min(i+w,idx_max)):
               for (ii2, w2) in ps[i2]:
                  if (w_max >= w2 >= w) and (ii2 in idx_s):
                     i = i2
                     w = w2
                     break

            idx_s.add(i_l)
            rv.append((w_l, ii, bytes(m[i_l:i])))
            i_l = i
            w_l = w
            i += w
         rv.append((w_l, ii, bytes(m[i_l:])))
         return rv
      
      #def cluster_prv(w_max, seq):
         #w_min = 2
         #i = 0
         #def get_subel(idx):
            #for (i, w) in ps[idx]:
               #if (w_min <= w <= w_max):
                  #return (i,w)
            #return (None, None)
         
         #while (i < len(ps)):
            #for (ii, w) in ps[i]:
               #if (w_min <= w <= w_max):
                  #break
            #else:
               #i += 1
               #continue
            
            #kl = []
            #for j in range(i+1, len(ps)):
               #k = 0
               #tnm = 0
               #(ii1, w1) = (ii,w)
               #(ii2, w2) = get_subel(j)
               #while ((w2 == w) and ((ii2 == ii) or (w2 is None) or (w <= 1))):
                  #k += 1
                  #if ((w2 is None) or (w2 <= 1)):
                     #tnm += 1
                  #else:
                     #tnm = 0
                  #(ii1, w1) = get_subel(i+k)
                  #j2 = k+j+1
                  #if (j2 > len(ps)):
                     #break
                  #(ii2, w2) = get_subel(j+k)
               #k -= tnm
               
               #if (k >= 2):
                  #kl.append((k,j))
            #if (kl):
               #print(i, kl)
            #i += 1
      
      
      def chlh(seq):
         if not (seq):
            return 0
         ld = [len(s) for (_,_,s) in seq]
            
         ll = ld[0]
         rv = 0
         for l in ld[1:]:
            rv += abs(ll-l)
            ll = l
         return rv-len(seq)
      
      sl = []
      try:
         w_mu = max(max(subpse[1] for subpse in pse) for pse in ps if pse)
      except ValueError:
         w_mu = 0
      
      for i in range(4,w_mu):
         seq = make_prv(i)
         #cluster_prv(i, seq)
         sl.append((chlh(seq), seq))
      
      if not (sl):
         return []
      
      return min(sl)[1]


# ---------------------------------------------------------------- Bytecode parsers
# ---- helper classes
class _E17Label:
   def __init__(self, n):
      pass

# ----- E17 ActiveValue classes (aka: the E17 killer joke)
# An E17 active value is a complex datatype used in many places of the E17 event script format, as well as in a very small
# number of places in conversation scripts. At the bitstream level, AVs are lists of sub-elements; these come in different
# types with widely different semantics, groupable roughly as:
# 1. Varint literals, up to 32-bit ones
# 2. Arithmetic operations
# 3. pseudo-random number generation
# 4. ES memory reads
# 5. ES Memory writes(!)
#
# According to the best available model, each such expression can contain at most one op of type 5; most of them contain no
# such ops at all.
# Some of the binary-operators are prefix, while others are infix.
# The memory accesses come in several flavors, one of which appears to operate directly on a binary game-state struct in the
# original implementation.
# The structure of AVs is further complicated by each operation carrying an explicit precedence value for the purposes of
# determining evaulation order.
# 
# AVs, when evaluated, yield sequences of integer values - at least in theory. In practice e.g. 0xFE opcodes typically contain
# an AV for the sole purpose of memory manipulation, and the actual return values seem to be ignored in this context.
#
# The following classes are a best-effort attempt to parse this mess.

class E17ActiveValue:
   def is_memop(self):
      return False

   def process(self, *args, **kwargs):
      """Dummy implementation: raise a useful error message."""
      raise ValueError("{} is missing process() implementation.".format(self))

class E17AVInteger(E17ActiveValue):
   op_type = None
   precedence = None
   def __init__(self, val):
      self.val = val
   
   def get_arity(self):
      return 0
   
   def get_arity_details(self):
      return (0,0)
   
   def process(self, *args, **kwargs):
      """Returns our static value."""
      return self.val
   
   def __repr__(self):
      return '{1}'.format(type(self).__name__, self.val)

class E17AVOperator(E17ActiveValue):
   import operator
   def _d1(func):
      def rv(_, *args, **kwargs):
         return func(*args, **kwargs)
      
      rv.__name__ == '_{}__d1'.format(func.__name__)
      return rv
   
   def _get_gstate(engine, i):
      if (i == 7):
         # Apparently used to check whether there's ongoing movie playback. Since we implement this outside the token
         # processing layer, we can just return False to treat it as immediately finished here.
         return False
      raise NotImplementedError('Unknown gstate index {!r}.'.format(i))
   
   op_map = {
      # The following is mostly based on engine binary reverse-engineering. Detailed investigations based on bytecode only
      # are noted for those cases where they were undertaken.
      # ---- Class 1: binary operators
      0x01:(_d1(operator.mul), '*'),
      0x02:(_d1(operator.truediv), '/'),
      0x03:(_d1(operator.add), '+'),
      0x04:(_d1(operator.sub), '-'),
      0x05:(_d1(operator.mod), '%'),
      0x06:(_d1(operator.lshift), '<<'),
      0x07:(_d1(operator.rshift), '>>'),
      0x08:(_d1(operator.and_), '&'),
      0x09:(_d1(operator.xor), '^'),
      0x0a:(_d1(operator.or_), '|'),
      # Based on op00.scr: (*x ~~ 0) has {(0,True), (1,False)}.
      # Could be <= or & in principle ... equality is far more likely however.
      0x0c:(_d1(operator.eq), '=='),
      
      # Based on s_1c.scr: (*x ~~ 0) has {(1,True), (0,False)} mapping.
      # Could be !=, >, or similar.
      0x0d:(_d1(operator.ne), '!='),
      
      0x0e:(_d1(operator.le), '<='),
      # Based on s_3b:24++: (*x ~~ 3) has {(0,False), (1,False), (2, False), (3, True)}.
      # And based on == being taken, it's probably >=. That *would* be the more robust thing to use here.
      0x0f:(_d1(operator.ge), '>='),
      
      # Based on s_3b:46: (*x ~~ 3) most likely has {(0, True), (1, True), (2, True), (3, False)}.
      # That's definitely < or != then, and < is both more robust and not taken yet.
      0x10:(_d1(operator.lt), '<'),
      
      # Based on t_4a.scr:2: (*x ~~ 9)
      # (Note that 1207 is the Tsu relationship value; higher is better.)
      # Based on t_6b:3++ (*x ~~ 1) has {(1, False), (2, True)}.
      0x11:(_d1(operator.gt), '>'),
      
      # ---- Class 3: unary operators
      0x28:(lambda e, a: e.get_memory(a), 'mem[{}]'), # primary memory access
      0x2d:(_get_gstate, 'e17gstate[{}]'),
      # MISSING: 11, 41, 43, 45, 51
      
      0x33:(lambda e, v: e._randint(v), '<random({})>')
      # ---- Class 4: Unidentified: 42, 44, 46
   }
   del(_d1)
   
   def __init__(self, op_type, precedence, val, data=None):
      self.op_type = op_type
      self.precedence = precedence
      self.val = val
      self.data = data
   
   def process(self, engine):
      """Compute value based on engine state and return it."""
      data = [e.process(engine) for e in self.data]
      op = self.op_map[self.op_type][0]
      return op(engine, *data)
   
   @classmethod
   def build(cls, op_type, *args, **kwargs):
      is_memop = (20 <= op_type <= 33)
      if (is_memop):
         cls = E17AVMemop
      return cls(op_type, *args, **kwargs)
   
   def get_arity_details(self):
      """Return (before, after) tuple specifying number of arguments before and after type element."""
      ot = self.op_type
      if ((1 <= ot <= 17) and (ot != 11)):
         return (1,1)
      if (ot in (11, 40, 41, 43, 45, 51)):
         return (0,1)
      if (ot in (42, 44, 46)):
         return (0,2)
      return (0,0)
   
   def get_arity(self):
      ot = self.op_type
      if ((1 <= ot <= 17) and (ot != 11)):
         return 2
      if (ot in (11, 40, 41, 43, 45, 51)):
         return 1
      if (ot in (42, 44, 46)):
         return 2
      
      return 0
   
   def _get_osym(self):
      try:
         rv = self.op_map[self.op_type][1]
      except KeyError:
         rv = '~{}~'.format(self.op_type)
      return rv
   
   def format_val_hr(self):
      osym = self._get_osym()
      a = self.get_arity()
      if (a == 0):
         return '{}'.format(osym)
      if (a == 1):
         return osym.format(self.data[0])
      if (a == 2):
         return '({} {} {})'.format(self.data[0], osym, self.data[1])
      raise
   
   def __format__(self, s):
      if (self.get_arity() and (self.data is None)):
         return repr(self)
      
      return self.format_val_hr()
   
   def __repr__(self):
       return '{}{}'.format(type(self).__name__, (self.op_type, self.precedence, self.val, self.data))
   
   def __str__(self):
      return self.__format__(None)


class E17AVMemop(E17AVOperator):
   import operator
   op_map = {
      # Class 2: Memory manipulations
      0x14:(lambda _, v: v, '= {}'),
      0x15:(operator.mul, '*= {}'),
      0x16:(operator.truediv, '/= {}'),
      0x17:(operator.add, '+= {}'),
      0x18:(operator.sub, '-= {}'),
      0x19:(operator.mod, '%= {}'),
      0x1a:(operator.lshift, '<<= {}'),
      0x1b:(operator.rshift, '>>= {}'),
      0x1c:(operator.and_, '&= {}'),
      0x1d:(operator.or_, '|= {}'),
      0x1e:(operator.xor, '^= {}'),
      0x20:(lambda v, _: v+1, '+= 1'),
      0x21:(lambda v, _: v-1, '-= 1')
   }
   
   op2_map = {
      # Secondary (memory access type) optypes
      0x28:(lambda e, a: e.get_memory(a), lambda e,a,v: e.set_memory(a,v), 'mem[{}]'),
      0x2d:(None, None, 'e17gstate[{}]')
   }

   def process(self, engine):
      """Perform memory operation."""
      addr = self.mo_addr.process(engine)
      (mget, mset, _) = self.op2_map[self.mo_type]
      (op,_) = self.op_map[self.op_type]
      
      v0 = mget(engine, addr)
      v1 = self.mo_val.process(engine)
      
      rv = op(v0, v1)
      mset(engine, addr, rv)
      
      return None

   def is_memop(self):
      return True
   
   def _is_unary(self):
      return (self.op_type in (32,33))
   
   def set_memop_data(self, data_list, i):
      if (i < 2):
         # ... not good.
         self.mo_type = MissingData()
         self.mo_addr = MissingData()
      else:
         self.mo_type = data_list[0].op_type
         self.mo_addr = data_list[1]
      
      if (self._is_unary()):
         # Unary operators; no need for a data element, so don't even look for it.
         self.mo_val = None
      else:
         try:
            self.mo_val = data_list[i+1]
         except IndexError:
            self.mo_val = MissingData()
   
   def format_val_hr(self):
      if not (hasattr(self, 'mo_val')):
         return repr(self)
      
      osym = self._get_osym()
      #return repr(self)
      rpart = osym.format(self.mo_val)
      try:
         mfmt = self.op2_map[self.mo_type][2]
      except KeyError:
         mfmt = '({}){{}}'.format(self.mo_type)
         
      return '({} {})'.format(mfmt.format(self.mo_addr), rpart)
   
   def get_arity(self):
      return 0
   
   def get_arity_details(self):
      return (0,0)

class MissingData:
   def __repr__(self):
      return 'MissingData'


class E17ActiveValueSequence(list):
   def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self._vals = None
   
   @classmethod
   def build_from_ints(cls, ints):
      vals = tuple(E17AVInteger(i) for i in ints)
      rv = cls(vals)
      rv._vals = vals
      return rv
   
   @classmethod
   def build_from_file(cls, f):
      """Build E17ActiveValueSequence from E17 event script data."""
      rcount = 0
      self = cls()
      while (True):
         v1 = f.read_u8()
         
         if (v1 == 0x00):
            break
      
         elif (v1 & 0x80):
            # Literal integer value
            val = v1 & 0x1F
            vint_len = (v1 & 0x60) >> 5
            if (vint_len == 3):
               # Actually four-byte vints.
               (bv,) = struct.unpack('<l', f.read(4))
               self.append(E17AVInteger(bv))
               f.read(1)
               continue
         
            bd = bytearray(2)
            bd[:vint_len] = f.read(vint_len)
            (bv,) = struct.unpack('<h', bd)
            # ... yes, the vints are middle-endian.
            val <<= 8 * vint_len
            val += bv
         
            if (v1 & 0x10):
               # Negative value.
               # TODO: Verify if this actually works right.
               if (vint_len == 0):
                  val |= 0xFFFFFFE0
               elif (vint_len == 1):
                  val |= 0xFFFFE000
               elif (vint_len == 2):
                  val |= 0xFFE00000
               else:
                  raise ValueError()
               (val,) = struct.unpack('<l', struct.pack('<L', val))
            
            # Discard one byte ...
            f.read(1)
            self.append(E17AVInteger(val))
         else:
            # Operator
            d1 = f.read_u8()
            op_type = 255
            precedence = 0
            val = None
            
            if (v1 == 0x2F):
               # Unsupported.
               val = b'uk1'
            elif (v1 == 0x30):
               # Unsupported.
               val = b'uk2'
            elif (v1 == 0x31):
               # Unsupported.
               val = b'uk3'
            elif (v1 == 0x32):
               pass
            else:
               op_type = v1
               precedence = d1
            
            e = E17AVOperator.build(op_type, precedence, val)
            self.append(e)
      
      #print(self)
      self._preprocess()
      return self
   
   def __format__(self, s):
      srepr = '[{}]'.format(', '.join([format(e,s) for e in self]))
      if (tuple(self) == self._vals):
         return srepr
      else:
         return '<[{}] / {}>'.format(', '.join([format(e,s) for e in self._vals]), 
            srepr)
   
   def process(self, engine, count=None):
      """Compute AVs (performing any memops), and return results."""
      if not (count is None):
         if (count != len(self._vals)):
            raise ValueError('{} was asked for {} values, but has {}.'.format(self, count, len(self._vals)))
      
      try:
         rv = [v.process(engine) for v in self._vals]
      except Exception as exc:
         raise ValueError('{} failed to extract values.'.format(self)) from exc
      
      return rv
   
   def _find_memop(self, imax=None):
      if (imax is None):
         imax = len(self)
      
      for (e,i) in zip(self[:imax],range(imax)):
         if (e.is_memop()):
            return i
      return None
   
   def _do_vint_arithmetic(self, i_min, i_lim):
      mp_last = None
      while (i_lim > i_min):
         mp = self._get_max_precedence(self[i_min:i_lim], mp_last)
         mp_last = mp
         if (mp == 0):
            break
         
         i = i_min
         while (i < min(len(self), i_lim)):
            e = self[i]
            if (e.precedence == mp):
               # Perform vint operation processing.
               op_type = e.op_type
               if (e.is_memop()):
                  raise ValueError('Unexpected op_type {!r}.'.format(op_type))
               
               (ab, aa) = e.get_arity_details()
               #ac = e.get_arity()
               if (ab):
                  if (ab > (i-i_min)):
                     # Insufficient before data. Pad things out ...
                     data = [MissingData()]*ab
                     #raise ValueError('Insufficient before data for operator {!r} (expected {:d} elements).'.format(e, ab))
                  else:
                     data = self[i-ab:i]
                     del(self[i-ab:i])
                     i_lim -= ab
                     i -= ab
               else:
                  data = []
               
               if (aa):
                  aa_slice = self[i+1:i+aa+1]
                  if (len(aa_slice) < aa):
                     aa_slice += [MissingData()]*(aa-len(aa_slice))
                  data.extend(aa_slice)
                  del(self[i+1:i+aa+1])
                  i_lim -= aa
               
               if (aa or ab):
                  e.data = data
            
            i += 1
            
   def _process_memop(self, i):
      e = self[i]
      op_type = e.op_type
      if not (e.is_memop()):
         raise ValueError('Not a memop: {!r} in {!r}.'.format(e, self))
      
      e.set_memop_data(self, i)
            
   @staticmethod
   def _get_max_precedence(l, plim):
      if not (l):
         return 0
      
      if (plim is None):
         gexpr = (val.precedence for val in l if not (val.op_type is None))
      else:
         gexpr = (val.precedence for val in l if not ((val.op_type is None) or (val.precedence >= plim)))
      
      try:
         rv = max(gexpr)
      except ValueError:
         rv = 0
      
      return rv
   
   def _preprocess(self):
      mo1_idx = self._find_memop()
      if (mo1_idx is None):
         base_idx = 0
      else:
         base_idx = mo1_idx+1 # post mo elements
            
      if (mo1_idx is None):
         self._do_vint_arithmetic(0, len(self))
         self._vals = tuple(self)
         return
      
      # Process vint ops before and after memop first.
      self._do_vint_arithmetic(mo1_idx+1, len(self))
      self._do_vint_arithmetic(1, mo1_idx)
      mo2_idx = self._find_memop()
      
      #print(self, mo2_idx)
      self._vals = (self[mo2_idx],)
      self._process_memop(mo2_idx)
      if not (len(self) in (mo2_idx+1, mo2_idx+2)):
         raise ValueError('Invalid memop AV seq {}.'.format(self))


class E17MemoryAddress:
   def __init__(self, addr, v2, v3):
      self.addr = addr
      self.v2 = v2
      self.v3 = v3
   
   def get(self, engine):
      return engine.memory_get(self.addr)
   
   def __repr__(self):
      return self.addr.__str__()
   
   def __str__(self):
      return '*({}-E{}:{})'.format(self.addr, self.v2, self.v3)

class E17DataReference(int):
   def __new__(cls, i, p, *args, **kwargs):
      rv = super().__new__(cls, i)
      return rv

   def __init__(self, i, p):
      self._verify(p)

   def format_hr(self, p):
      return '{}({})'.format(self, self.get_refdata_hr(p))


class E17ConvReference(E17DataReference):
   def get_refdata(self, p):
      return p.get_cs(self).get_data()
   
   def _verify(self, p):
      p.get_cs(self)
   
   @staticmethod
   def text_try_decode(b):
      try:
         rv = b.decode('shift-jis')
      except ValueError:
         rv = str(b)
      return rv

   def get_refdata_hr(self, p):
      ct = p.get_cs(self)
      # Try to give useful output even in cases of conversation tokenizer bugs.
      try:
         rv = ct.get_text_lines()
      except ValueError:
         return (ct.get_data(),)
      
      return rv

class E17FileReference(E17DataReference):
   def __init__(self, i, p, aux_val):
      super().__init__(i, p)
      self.aux_val = aux_val
   
   def get_refdata(self, p):
      return p.get_fn(self).get_data().rstrip(b'\x00')
   
   def _verify(self, p):
      p.get_fn(self)
   
   def get_refdata_hr(self, p):
      return self.get_refdata(p)

class E17EventScriptReference(E17DataReference):
   def __init__(self, *args, non_es_data, **kwargs):
      super().__init__(*args, **kwargs)
      self._ned = non_es_data
   
   def get_refdata(self, p):
      return p.get_es(self).get_data()
   
   def _verify(self, p):
      p.get_es(self)
   
   def get_refdata_hr(self, p):
      d = self.get_refdata(p)
      if (self._ned):
         return d
      else:
         return '...'

# ---- Token types
e17stth = TTHierarchy()
_e17_reg_tt = e17stth.reg

e17stth[0x00] = e17_stth_00 = TTHierarchy()
_e17_reg_tt_00 = e17_stth_00.reg

e17stth[0x01] = e17_stth_01 = TTHierarchy()
_e17_reg_tt_01 = e17_stth_01.reg

e17stth[0x10] = e17_stth_10 = TTHierarchy()
_e17_reg_tt_10 = e17_stth_10.reg

e17stth[0x80] = e17_stth_80 = TTHierarchy()
_e17_reg_tt_80 = e17_stth_80.reg

class E17TokenType(BaseTokenType):
   pass

class E17Token(BaseToken):
   def __init__(self, f):
      raise ValueError('Not instantiable.')
   
   @classmethod
   def build(cls, f):
      return cls(f)

class E17NonTokenData(E17Token):
   def __init__(self, dref):
      self.dref = dref
   
   def format_hr_type(self):
      return 'NonTokenData'
   
   @staticmethod
   def get_type():
      return E17TokenType((-1,))
   
   def format_hr_val(self, p):
      return '({!r})'.format(self.dref.get_data())
   
   def _get_color(self):
      return TFC_YELLOW_D

class E17TokenE(E17Token):
   def do_tokendisplay_linebreak(self):
      return True

class E17TokenENodata(E17TokenE):
   def __init__(self, f):
      self.data = None

# -------- x00 TTs
class E17TokenE00(E17TokenE):
   type = 0x00
   def __init__(self, f):
      raise NotImplementedError()
   @classmethod
   def get_type(cls):
      return E17TokenType((0x00, cls.type))

class E17TokenE00Nodata(E17TokenE00):
   data = None
   def __init__(self, f):
      pass

@_e17_reg_tt_00
class E17TokenE00_00(E17TokenE00Nodata): # Extremely dubious.
   type = 0x00
   def _get_color(self):
      return TFC_GREY

@_e17_reg_tt_00
class E17TokenE00_01(E17TokenE00Nodata):
   type = 0x01
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av(), f.read_esr())
   
   def get_edges(self, p):
      return (CallgraphEdge.fromdst((None, self.data[2])),)
   
   def _get_color(self):
      return TFC_GREY

   def _get_color(self):
      return TFC_YELLOW

@_e17_reg_tt_00
class E17TokenE00_03(E17TokenE00Nodata):
   """00-03: System/startup only thing of unknown meaning."""
   type = 0x03

@_e17_reg_tt_00
class E17TokenE00_04(E17TokenE00):
   """00-04: System/startup ??shortcut scene jump??
   
      Length is quite solid. This thing references filenames embedded as ES chunks, which encode script filenames. Likely
      related to shortcut functionality, and most likely a jump command. More investigation is needed to verify this and
      determine precise semantics."""
   type = 0x04
   def __init__(self, f):
      f.eat_nulls(1)
      v1 = f.read_av()
      fn_es_ref = f.read_esr(True)
      self.data = (v1, fn_es_ref, f.read(2), f.read_av(), f.read_u16())

   def get_edges(self, p):
      fn_base = self.data[1].get_refdata(p).rstrip(b'\x00')
      if (fn_base == b'debug'):
         # Not included in released versions of the game.
         return ()
      
      return (CallgraphEdge.fromdst((fn_base.lower() + b'.scr', 0)),)

   def _get_color(self):
      return TFC_YELLOW

@_e17_reg_tt_00
class E17TokenE00_05(E17TokenE00):
   type = 0x05
   def __init__(self, f):
      self.data = f.read_av()

@_e17_reg_tt_00
class E17TokenE00_06(E17TokenE00Nodata):
   """00-06: End of path marker?"""
   type = 0x06
   def __init__(self, f):
      f.set_end()
   
   def process(self, engine):
      engine._end_vn()
   
   def format_hr_val(self, *args):
      return '< end? >'
   
   def _get_color(self):
      return TFC_BLUE

@_e17_reg_tt_00
class E17TokenE00_07(E17TokenE00):
   """00-07: Unconditional intra-file jump."""
   type = 0x07
   def __init__(self, f):
      self.jmp_target = f.read_esr()
      f.set_end()
   
   def get_edges(self, p):
      return (CallgraphEdge.fromdst((None, self.jmp_target)),)
   
   def _get_color(self):
      return TFC_YELLOW
   
   def format_hr_val(self, *args):
      return '< JMP: {} >'.format(self.jmp_target)
   
   def process(self, engine):
      engine.set_es(self.jmp_target)

@_e17_reg_tt_00
class E17TokenE00_08(E17TokenE00):
   """00-08: Target-selecting jump? (system/startup only)"""
   type = 0x08
   def __init__(self, f):
      self.v1 = f.read_av()
      self.val_ref = f.read_esr(True)
      f.set_end()
   
   def _get_vals(self, p):
      d = self.val_ref.get_refdata(p)
      return [struct.unpack('<H', d[i:i+2])[0] for i in range(0,len(d),2)]
   
   def get_edges(self, p):
      return [CallgraphEdge.fromdst((None, tgt)) for tgt in self._get_vals(p)]
   
   def format_hr_val(self, p):         
      return '({}, {}({}))'.format(self.v1, self.val_ref, self._get_vals(p))

@_e17_reg_tt_00
class E17TokenE00_0b(E17TokenE00):
   """00-0b: Intra-file jump that saves current position for return. System/startup only."""
   type = 0x0b
   def __init__(self, f):
      self.jmp_target = f.read_esr()

   def get_edges(self, p):
      return (CallgraphEdge.fromdst((None, self.jmp_target)),)

   def process(self, engine):
      engine.push_scr_pos()
      engine.set_es(self.jmp_target)
   
   def format_hr_val(self, *args):
      return '< returnable JMP: --> {}  >'.format(self.jmp_target)

   def _get_color(self):
      return TFC_YELLOW

@_e17_reg_tt_00
class E17TokenE00_0D(E17TokenE00):
   type = 0x0d
   def __init__(self, f):
      self.data = (f.read_av(), f.read(2))

@_e17_reg_tt_00
class E17TokenE00_0aConditionalJump(E17TokenE00):
   """00-0a: Conditional jumps based on multi-type memory tests."""
   type = 0x0a
   def __init__(self, f):
      # Always preceded by an \x00. Could be part of the sequence?
      self.inverse = not f.read_u8()
      self.test_av = f.read_av()
      self.jmp_target = f.read_esr()
   
   def get_edges(self, p):
      return (CallgraphEdge.fromdst((None, self.jmp_target)),)
   
   def _get_color(self):
      return TFC_YELLOW
   
   def format_hr_val(self, *args):
      invstring = (self.inverse and '!') or ''
      
      return '< CONDJMP: {}({}) --> {}  >'.format(invstring, self.test_av, self.jmp_target)
   
   def process(self, engine):
      # Conditional jump based on memory equality test?
      do_jmp = bool(self.test_av.process(engine, 1)[0])
      if (do_jmp != self.inverse):
         engine.set_es(self.jmp_target)

@_e17_reg_tt_00
class E17TokenE00_0e(E17TokenE00Nodata):
   """00-0e: Unconditional return (system/startup only)"""
   type = 0x0e
   def __init__(self, f):
      f.set_end()
   
   def _get_color(self):
      return TFC_YELLOW
   
   def format_hr_val(self, *args):
      return '< return >'

@_e17_reg_tt_00
class E17TokenE00_0f(E17TokenE00):
   """00-0f: system/startup only thing of unknown meaning"""
   type = 0x0f
   def __init__(self, f):
      # Dubious. Needs more investigation.
      self.data = (f.read_u16(), f.read_av())


@_e17_reg_tt_00
class E17TokenE00_10(E17TokenE00):
   """00-10: System/startup returnable jump"""
   type = 0x10
   def __init__(self, f):
      self.data = (f.read_u8(), f.read_av(), f.read_esr())
   
   def get_edges(self, p):
      return (CallgraphEdge.fromdst((None, self.data[2])),)
   
   def _get_color(self):
      return TFC_YELLOW

@_e17_reg_tt_00
class E17TokenE00_11(E17TokenE00):
   """00-11: System/startup conditional return?"""
   type = 0x11
   def __init__(self, f):
      self.data = (f.read_u8(), f.read_av())

   def _get_color(self):
      return TFC_YELLOW

@_e17_reg_tt_00
class E17TokenE00_12(E17TokenE00):
   type = 0x12
   def __init__(self, f):
      # Somewhat dubious. Needs more testing.
      self.data = f.read_av()

@_e17_reg_tt_00
class E17TokenE00_13(E17TokenE00):
   type = 0x13
   def __init__(self, f):
      # Somewhat dubious. Needs more testing.
      self.data = (f.read_av(),)

@_e17_reg_tt_00
class E17TokenE00_15_Jump(E17TokenE00):
   """00-15: Jumps of unknown conditionality."""
   type = 0x15
   def __init__(self, f):      
      self.d1 = f.read_u8()
      self.v1 = f.read_av()
      self.d2 = f.read_av() # Always one outside of system/startup, where it's sometimes 0 instead,
      self.jmp_target = f.read_esr()

   def get_edges(self, p):
      return (CallgraphEdge.fromdst((None, self.jmp_target)),)

   def format_hr_val(self, *args):
      return '< JMP({}, {}, {}): {} >'.format(self.v1, self.d1, self.d2, self.jmp_target)

   def process(self, engine):
      # FIXME: Are these real unconditional? If so, what's the data (not that it ever varies much) for?
      engine.set_es(self.jmp_target)

   def _get_color(self):
      return TFC_YELLOW

@_e17_reg_tt_00
class E17TokenE00_19(E17TokenE00):
   type = 0x19
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())

@_e17_reg_tt_00
class E17TokenE00_1a(E17TokenE00Nodata):
   type = 0x1a

@_e17_reg_tt_00
class E17TokenE00_21(E17TokenE00Nodata):
   """00-21: Rare system/startup opcode of unknown meaning."""
   type = 0x21

@_e17_reg_tt_00
class E17TokenE00_23(E17TokenE00Nodata):
   """00-23: Rare system/startup opcode of unknown meaning."""
   type = 0x23
   # Likely correct, even though there is only one occurence.

@_e17_reg_tt_00
class E17TokenE00_24(E17TokenE00Nodata):
   """00-24: Very rare system/startup only opcode of unknown meaning."""
   # Pretty undubious, though - we do have a very clear instance.
   type = 0x24

@_e17_reg_tt_00
class E17TokenE00_25(E17TokenE00):
   type = 0x25
   def __init__(self, f):
      self.data = f.read_u8()

@_e17_reg_tt_00
class E17TokenE00_26(E17TokenE00):
   """00-26: Load value from specified memory address, and place in register?"""
   # If so, 1203 is apparently the conv-choice result register, and 1223 is used for ending selection ...
   type = 0x26
   def __init__(self, f):
      # Very dubious.
      self.av = f.read_av()
   
   def process(self, engine):
      (val,) = self.av.process(engine, 1)
      engine._r1_set(val)
   
   def format_hr_val(self, *args):
      return '< LOAD: {} >'.format(self.av)
   
   def _get_color(self):
      return TFC_RED

@_e17_reg_tt_00
class E17TokenE00_27(E17TokenE00):
   """00-27: Conditional intra-file jump based on register content equality test?"""
   type = 0x27
   def __init__(self, f):
      self.reg_val = f.read_av()
      self.jmp_target = f.read_esr()
   
   def get_edges(self, p):
      return (CallgraphEdge.fromdst((None, self.jmp_target)),)
   
   def process(self, engine):
      (val,) = self.reg_val.process(engine, 1)
      if (engine._r1_get() == val):
         engine.set_es(self.jmp_target)
   
   def format_hr_val(self, *args):
      return '< CONDJMP(r1 == {}): {} >'.format(self.reg_val, self.jmp_target)
   
   def _get_color(self):
      return TFC_YELLOW

@_e17_reg_tt_00
class E17TokenE00_28(E17TokenE00Nodata): # somewhat dubious ... usually followed by 10 19 ff?
   type = 0x28

# /-------- x00 TTs
# -------- x01 TTs
class E17TokenE01(E17TokenE):
   type = 0x01
   def __init__(self, f):
      raise NotImplementedError()
   @classmethod
   def get_type(cls):
      return E17TokenType((0x01, cls.type))

class E17TokenE01Nodata(E17TokenE01):
   data = None
   def __init__(self, f):
      pass

@_e17_reg_tt_01
class E17TokenE01_00(E17TokenE01):
   """01-00: Unconditional intra-file jumps of unknown returnability."""
   type = 0x00
   def __init__(self, f):
      self.data = f.read_esr()
   
   def get_edges(self, p):
      return (CallgraphEdge.fromdst((None, self.data)),)
   
   def _get_color(self):
      return TFC_YELLOW

@_e17_reg_tt_01
class E17TokenE01_01(E17TokenE01):
   type = 0x01
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())

@_e17_reg_tt_01
class E17TokenE01_03(E17TokenE01):
   type = 0x03
   def __init__(self, f):
      # FIXME: EXCEEDINGLY DUBIOUS. One use in the entire game? Really, now?
      self.data = tuple(f.read_av() for i in range(20)) + (f.read_u16(),)

@_e17_reg_tt_01
class E17TokenE01_04(E17TokenE01):
   type = 0x04
   def __init__(self, f):
      self.data = f.read_av()

@_e17_reg_tt_01
class E17TokenE01_06(E17TokenE01):
   type = 0x06
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av(), f.read_esr(True))

@_e17_reg_tt_01
class E17TokenE01_07(E17TokenE01):
   type = 0x07
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())


@_e17_reg_tt_01
class E17TokenE01_13(E17TokenE01):
   type = 0x13
   def __init__(self, f):
      self.data = (f.read(16), f.read_esr(True))

@_e17_reg_tt_01
class E17TokenE01_14(E17TokenE01):
   type = 0x14
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())

@_e17_reg_tt_01
class E17TokenE01_15(E17TokenE01):
   type = 0x15
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())

@_e17_reg_tt_01
class E17TokenE01_16(E17TokenE01):
   type = 0x16
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())

@_e17_reg_tt_01
class E17TokenE01_18(E17TokenE01Nodata):
   type = 0x18

@_e17_reg_tt_01
class E17TokenE01_19(E17TokenE01):
   type = 0x19
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av(), f.read(4))

# /-------- x01 TTs
# -------- x10 TTs
class E17TokenE10(E17TokenE):
   type = 0x10
   def __init__(self, f):
      raise NotImplementedError()
   @classmethod
   def get_type(cls):
      return E17TokenType((0x10, cls.type))

class E17TokenE10_(E17TokenE):
   type = 0x10

@_e17_reg_tt_10
class E17TokenE10Nodata(E17TokenE10):
   data = None
   def __init__(self, f):
      pass

@_e17_reg_tt_10
class E17TokenE10_00(E17TokenE10Nodata):
   """10-00: System/startup only thing of unknown meaning"""
   type = 0x00

@_e17_reg_tt_10
class E17Token_E10_01_Jump(E17TokenE10):
   """10-01: Inter-file jump."""
   type = 0x01
   def __init__(self, f):
      self.jmp_fn = f.read_bytes_fixedterm(b'\x00')
      f.set_end()
   
   def get_edges(self, p):
      return (CallgraphEdge.fromdst((self.jmp_fn.lower() + b'.scr', 0)),)
   
   def _get_color(self):
      return TFC_YELLOW
   
   def format_hr_val(self, *args):
      return '< JMP: {!r} >'.format(self.jmp_fn)
   
   def process(self, engine):
      scr_fn = self.jmp_fn
      engine.set_scr(scr_fn)

@_e17_reg_tt_10
class E17TokenE10_03_BGM(E17TokenE10):
   """10-03: BGM start"""
   type = 0x03
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())
   
   def format_hr_val(self, *args):
      return '< bgm-start: file {}, aux {} >'.format(self.data[0], self.data[1])
   
   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_04_BGM_stop(E17TokenE10):
   """10-04: BGM stop."""
   type = 0x04
   def __init__(self, f):
      self.data = None
   
   def format_hr_val(self, *args):
      return '< bgm-stop >'

   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_05_SoundEffect(E17TokenE10):
   """10-05: Sound Effects."""
   type = 0x05
   def __init__(self, f):
      self.fn = f.read_string_fixedterm(b'\x00')
      self.val = (f.read_av(),f.read_av())
   
   def format_hr_val(self, *args):
      return '< SOUND: {!r} {} >'.format(self.fn, self.val)
   
   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_06(E17TokenE10):
   """10-06: Sounds effect stop??"""
   type = 0x06
   def __init__(self, f):
      self.data = None

   def format_hr_val(self, *args):
      return '< ??SOUND-stop?? >'

   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_07(E17TokenE10):
   """10-07: ?Set up horizontal-lines bgi transition?"""
   type = 0x07
   def __init__(self, f):
      self.data = None
   
   def format_hr_val(self, *args):
      return '< ?prepare horizontal-lines bgi switch? >'
   
   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_08(E17TokenE10):
   type = 0x08
   def __init__(self, f):
      self.data = (f.read_string_fixedterm(b'\x00'), f.read(2))

@_e17_reg_tt_10
class E17TokenE10_0c_BackgroundImage(E17TokenE10):
   """10-0c: Background image display."""
   type = 0x0c
   def __init__(self, f):
      self.fnr = f.read_fnr()
      self.data = (f.read_av(),f.read_av())

   def format_hr_val(self, *args):
      return '< bgi: {} {} >'.format(self.fnr.format_hr(*args), self.data)

   def process(self, engine):
      engine._display_bgi(self.fnr.get_refdata(engine._scr))

   def _get_color(self):
      return TFC_PURPLE
   

@_e17_reg_tt_10
class E17TokenE10_0d(E17TokenE10):
   """10-0d: Background fade to color"""
   type = 0x0d
   def __init__(self, f):
      # color table:
      # 0: Black
      # 1: White
      self.color = f.read_av()
      # Semantics of these is unknown, but they tend to be chosen from {0,6} x {2}
      self.aux = (f.read_av(), f.read_av())
   
   def _get_bg_color(self, e):
      (c,) = self.color.process(e, 1)
      c = int(c)
      if (c == 0):
         return (0,0,0)
      if (c == 1):
         return (1,1,1)
      if (c == 3):
         # TODO: verify this.
         return (1,0,0)
      raise ValueError('Unknown 10-0d color {!r}.'.format(c))
   
   def format_hr_val(self, *args):
      return '< bg fade: color: {} aux: {} >'.format(self.color, self.aux)
   
   def process(self, engine):
      engine._fade_bg_fill(self._get_bg_color(engine), 0.1)
   
   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_0e(E17TokenE10):
   """10-0e: ??"""
   type = 0x0e
   def __init__(self, f):
      self.data = (f.read_av(),)

class E17CharImageSpec:
   def __init__(self, fnr, img_slot, x):
      self.fnr = fnr
      self.img_slot = img_slot
      self.x = x
   
   def format_hr(self, *args):
      return '< CImg: {} slot: {} aux: {}>'.format(self.fnr.format_hr(*args), self.img_slot, self.x)
   
   def process(self, e):
      (slot,) = self.img_slot.process(e)
      slot = int(slot) - 1
      x = int(self.x.process(e,1)[0])
      fn = self.fnr.get_refdata(e._scr)
      e._draw_charart(fn, slot, x)

@_e17_reg_tt_10
class E17TokenE10_0f_CharArt(E17TokenE10):
   """10-0f: Single character art display."""
   type = 0x0f
   def __init__(self, f):
      img_slot = f.read_av()
      self.img = E17CharImageSpec(f.read_fnr(), img_slot, f.read_av())
      self.v1 = f.read_av()

   def format_hr_val(self, *args):
      return '< Charart: {} {} >'.format(self.img.format_hr(*args), self.v1)
   
   def process(self, e):
      self.img.process(e)
   
   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_10(E17TokenE10):
   """10-10: Charart clear?"""
   type = 0x10
   def __init__(self, f):
      self.img_slot = f.read_av()
      self.v1 = f.read_av()
   
   def format_hr_val(self, *args):
      return '< clear charart: {} ({}) >'.format(self.img_slot, self.v1)

   def process(self, e):
      # TODO: What about v1?
      (img_slot,) = self.img_slot.process(e)
      img_slot = int(img_slot) - 1
      e._clear_charart(img_slot)

   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_12_CharArt(E17TokenE10):
   """10-12: Double charart display"""
   type = 0x12
   def __init__(self, f):
      slot_1 = f.read_av()
      slot_2 = f.read_av()
      fnr_1 = f.read_fnr()
      fnr_2 = f.read_fnr()
      x0_1 = f.read_av()
      x0_2 = f.read_av()
      self.imgs = (E17CharImageSpec(fnr_1, slot_1, x0_1), E17CharImageSpec(fnr_2, slot_2, x0_2))
      self.v1 = f.read_av()

   def format_hr_val(self, *args):
      return '< Charart: {}, {}, {} >'.format(
         self.imgs[0].format_hr(*args), self.imgs[1].format_hr(*args), self.v1)

   def process(self, e):
      for img in self.imgs:
         img.process(e)

   def _get_color(self):
      return TFC_PURPLE
   

@_e17_reg_tt_10
class E17TokenE10_13(E17TokenE10):
   """10-13: Full charart clear?"""
   type = 0x13
   def __init__(self, f):
      self.data = (f.read_av(),f.read_av())

   def format_hr_val(self, *args):
      return '< clear all charart: {} >'.format(self.data)

   def process(self, engine):
      # TODO: What about the values?
      engine._clear_charart_all(0)

   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_14(E17TokenE10):
   type = 0x14
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av(), f.read_av())
      
@_e17_reg_tt_10
class E17TokenE10_15(E17TokenE10):
   type = 0x15
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())

@_e17_reg_tt_10
class E17TokenE10_16_CharArt(E17TokenE10):
   """10-16: Triple charart display"""
   type = 0x16
   def __init__(self, f):
      fnr_1 = f.read_fnr()
      fnr_2 = f.read_fnr()
      fnr_3 = f.read_fnr()
      
      x0_1 = f.read_av()
      x0_2 = f.read_av()
      x0_3 = f.read_av()
      
      # TODO: Verify if these slot values are correct.
      self.imgs = (
         E17CharImageSpec(fnr_1, E17ActiveValueSequence.build_from_ints((1,)), x0_1),
         E17CharImageSpec(fnr_2, E17ActiveValueSequence.build_from_ints((2,)), x0_2),
         E17CharImageSpec(fnr_3, E17ActiveValueSequence.build_from_ints((3,)), x0_3),
      )
      
      self.v1 = f.read_av()

   def process(self, e):
      for img in self.imgs:
         img.process(e)

   def format_hr_val(self, *args):
      return '< Charart: {}, {}, {}, {} >'.format(
         self.imgs[0].format_hr(*args),
         self.imgs[1].format_hr(*args),
         self.imgs[2].format_hr(*args),
         self.v1)

   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_18(E17TokenE10):
   """10-18: volatilely remove textbox"""
   type = 0x18
   def __init__(self, f):
      # Pretty solid.
      self.data = None

   def process(self, e):
      e._fade_textbox()

   def format_hr_val(self, p):
      return '< textbox off >'

   def _get_color(self):
      return TFC_GREY

@_e17_reg_tt_10
class E17TokenE10_19(E17TokenE10):
   type = 0x19
   data = None
   def __init__(self, f):
      pass

   def _get_color(self):
      return TFC_CYAN_D

@_e17_reg_tt_10
class E17TokenE10_1a(E17TokenE10):
   """10-1a: Choice result store."""
   type = 0x1a
   def __init__(self, f):
      self.addr = f.read_av()
      self.cidx = f.read_av()
   
   def format_hr_val(self, p):
      return '< Read choice response: mem<{}> = choice{} >'.format(self.addr, self.cidx)

   def process(self, engine):
      (addr,) = self.addr.process(engine, 1)
      (cidx,) = self.cidx.process(engine, 1)
      c = engine._reap_choice()
      if (c.id != cidx):
         raise ValueError('Choice id mismatch: expected {!r}, got {!r}.'.format(cidx, c))
      
      oi = c._get_coidx()
      engine.set_memory(addr, oi)

   def _get_color(self):
      return TFC_RED

@_e17_reg_tt_10
class E17TokenE10_1b(E17TokenE10):
   type = 0x1b
   def __init__(self, f):
      # ... dubious.
      self.data = (f.read_av(),)

@_e17_reg_tt_10
class E17TokenE10_(E17TokenE10):
   """10-1d: Background image display."""
   type = 0x1d
   def __init__(self, f):
      self.fnr = f.read_fnr()

   def format_hr_val(self, *args):
      return '< bgi: {} >'.format(self.fnr.format_hr(*args))
   
   def process(self, engine):
      engine._display_bgi(self.fnr.get_refdata(engine._scr))
   
   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_1e(E17TokenE10):
   """10-1e: Delay."""
   type = 0x1e
   def __init__(self, f):
      self.td = f.read_av()
   
   def format_hr_val(self, *args):
      return '< delay: {} >'.format(self.td)

   def _get_color(self):
      return TFC_GREY

@_e17_reg_tt_10
class E17TokenE10_1f(E17TokenE10):
   """10-1f: Time display"""
   type = 0x1f
   def __init__(self, f):
      self.hval = f.read_av()
      self.mval = f.read_av()
   
   def format_hr_val(self, *args):
      (hval,) = self.hval
      (mval,) = self.mval
      return '< time display: {}:{}>'.format(hval, mval)

   def _get_color(self):
      return TFC_CYAN

@_e17_reg_tt_10
class E17TokenE10_20(E17TokenE10):
   """10-20: Visual effect"""
   type = 0x20
   op_map = {
       4:((), 'shortstrongshake'),
       5:((), 'shortshake'),
      12:((591, 571, 572, 573, 574, 575, 576), 'persistent shake'),
      19:((), '?mist/steam?'),
      27:((568,), 'rays of light'),
      32:((), 'whitewindow'),
      44:((), '?center-zoom?'),
      45:((577, 578, 592), 'lights'),
      # Memory value specifies direction:
      # 0: left->right
      # 1: right->left
      # 2: bidirectional
      47:((570,),'pink bars'),
   }
   
   def __init__(self, f):
      self.etype = f.read_av()
   
   def get_values(self, e):
      addrs = self.op_map[self.etype.process(e,1)[0]][0]
      return [e.get_memory(addr) for addr in addrs]
   
   def format_hr_val(self, *args):
      (v,) = self.etype.process(None)
      try:
         ename = self.op_map[v][1]
      except KeyError:
         ename = '~'
      
      return '< visual effect: {}({}) >'.format(v, ename)
   
   def _get_color(self):
      return TFC_CYAN

@_e17_reg_tt_10
class E17TokenE10_21(E17TokenE10):
   """10-21: Visual effect stop"""
   type = 0x21
   def __init__(self, f):
      self.val = f.read_av()

   def format_hr_val(self, *args):
      return '< visual effect stop: {} >'.format(self.val)

   def _get_color(self):
      return TFC_CYAN

@_e17_reg_tt_10
class E17TokenE10_23(E17TokenE10):
   type = 0x23
   def __init__(self, f):
      self.data = (f.read_av(),)

@_e17_reg_tt_10
class E17TokenE10_24(E17TokenE10):
   type = 0x24
   def __init__(self, f):
      # Weird thing. Also occurs in the blindspot before script sections.
      self.data = f.read_av()

@_e17_reg_tt_10
class E17TokenE10_25(E17TokenE10):
   type = 0x25
   def __init__(self, f):
      # Only on two lines total? ... hum.
      self.data = (f.read_av(),)

@_e17_reg_tt_10
class E17TokenE10_26(E17TokenE10):
   type = 0x26
   def __init__(self, f):
      self.data = (f.read_av(),)

@_e17_reg_tt_10
class E17TokenE10_27_Background(E17TokenE10):
   """10-27: Background image display."""
   type = 0x27
   def __init__(self, f):
      self.fnr = f.read_fnr()
      self.data = (f.read_av(), f.read_av())

   def format_hr_val(self, *args):
      return '< bgi: {} {} >'.format(self.fnr.format_hr(*args), self.data)
   
   def process(self, engine):
      engine._display_bgi(self.fnr.get_refdata(engine._scr))
   
   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_29(E17TokenE10Nodata):
   type = 0x29
@_e17_reg_tt_10
class E17TokenE10_2a(E17TokenE10):
   type = 0x2a
   def __init__(self, f):
      self.data = (f.read_av(),)
@_e17_reg_tt_10
class E17TokenE10_2b(E17TokenE10):
   type = 0x2b
   def __init__(self, f):
      self.data = (f.read_av(),)
@_e17_reg_tt_10
class E17TokenE10_2c(E17TokenE10):
   type = 0x2c
   def __init__(self, f):
      self.data = (f.read_u8(), f.read_av(),)
@_e17_reg_tt_10
class E17TokenE10_2d(E17TokenE10):
   type = 0x2d
   def __init__(self, f):
      self.data = (f.read_av(),)
@_e17_reg_tt_10
class E17TokenE10_2e(E17TokenE10):
   type = 0x2e
   def __init__(self, f):
      self.data = (f.read_av(),f.read_av())
@_e17_reg_tt_10
class E17TokenE10_37_WallpaperUnlock(E17TokenE10):
   """10-37: Wallpaper unlock."""
   type = 0x37
   def __init__(self, f):
      self.fn = f.read_fnr()

   def format_hr_val(self, *args):
      return '< Wallpaper unlock: {} >'.format(self.fn.format_hr(*args))

   def _get_color(self):
      return TFC_BLUE

@_e17_reg_tt_10
class E17TokenE10_38(E17TokenE10Nodata):
   """10-38: system/startup thingie of unknown meaning."""
   type = 0x38
   

@_e17_reg_tt_10
class E17TokenE10_39_Movie(E17TokenE10):
   """10-39: Movie specification"""
   type = 0x39
   def __init__(self, f):
      self.fn = f.read_string_fixedterm(b'\x00').encode('ascii')
   
   def process(self, engine):
      engine._play_movie(self.fn)
   
   def format_hr_val(self, p):
      return '< Movie: {!r} >'.format(self.fn)
      
   def _get_color(self):
      return TFC_GREEN

@_e17_reg_tt_10
class E17TokenE10_3b(E17TokenE10):
   """10-3b: ?"""
   type = 0x3b
   def __init__(self, f):
      self.data = f.read_av()

@_e17_reg_tt_10
class E17TokenE10_3a(E17TokenE10Nodata):
   type = 0x3a
@_e17_reg_tt_10
class E17TokenE10_3c(E17TokenE10Nodata):
   type = 0x3c

@_e17_reg_tt_10
class E17TokenE10_3f(E17TokenE10):
   type = 0x3f
   def __init__(self, f):
      # ... dubious.
      self.data = (f.read_av(),)

@_e17_reg_tt_10
class E17TokenE10_40_Background(E17TokenE10):
   """10-40: Background image (partial) display."""
   type = 0x40
   def __init__(self, f):
      self.fnr = f.read_fnr()
      self.data = (f.read_av(),f.read_av())
      self.x0 = f.read_av()
      self.y0 = f.read_av()
      self.w = f.read_av()
      self.h = f.read_av()

   def format_hr_val(self, *args):
      return '< bgi: {} {} min ({}, {}) dim ({}, {}) >'.format(self.fnr.format_hr(*args), self.data, self.x0, self.y0, self.w,
         self.h)
   
   def process(self, engine):
      engine._display_bgi(
         self.fnr.get_refdata(engine._scr),
         self.x0.process(engine, 1)[0],
         self.y0.process(engine, 1)[0],
         self.w.process(engine, 1)[0],
         self.h.process(engine, 1)[0]
      )
   
   def _get_color(self):
      return TFC_PURPLE

@_e17_reg_tt_10
class E17TokenE10_41(E17TokenE10):
   """Background image pan/zoom."""
   type = 0x41
   def __init__(self, f):
      # (0,0) is the upper left corner; (800,600) is lower right.
      self.x0 = f.read_av()
      self.y0 = f.read_av()
      self.w = f.read_av()
      self.h = f.read_av()
      self.delay = f.read_av()
   
   def format_hr_val(self, *args):
      return '< bgi zoom/pan: min ({}, {}) dim ({}, {}) aux {} >'.format(self.x0, self.y0, self.w, self.h, self.delay)

   def process(self, engine):
      engine._panzoom_bgi(
         self.delay.process(engine, 1)[0]/60,
         self.x0.process(engine, 1)[0],
         self.y0.process(engine, 1)[0],
         self.w.process(engine, 1)[0],
         self.h.process(engine, 1)[0]
      )

   def _get_color(self):
      return TFC_PURPLE

   
@_e17_reg_tt_10
class E17TokenE10_43(E17TokenE10):
   type = 0x43
   def __init__(self, f):
      self.data = f.read_av()

@_e17_reg_tt_10
class E17TokenE10_44(E17TokenE10):
   type = 0x44
   def __init__(self, f):
      self.data = f.read(2)

@_e17_reg_tt_10
class E17TokenE10_45(E17TokenE10):
   type = 0x45
   def __init__(self, f):
      self.data = (f.read_av(), f.read_av())

@_e17_reg_tt_10
class E17TokenE10_46(E17TokenE10):
   """10-46: Perspective setter"""
   type = 0x46
   def __init__(self, f):
      # Perspective values:
      #  0: other   (grey)
      #  1: Takeshi (green)
      #  2: KKid    (blue)
      self.p = f.read_av()
   
   def format_hr_val(self, p):
      return '< set perspective: {} >'.format(self.p)

   def _get_color(self):
      return TFC_BLUE

# /--------x10 tts
# --------x80 tts
class E17TokenE80(E17TokenE):
   type = 0x80
   def __init__(self, f):
      raise NotImplementedError()
   @classmethod
   def get_type(cls):
      return E17TokenType((0x80, cls.type))

@_e17_reg_tt_80
class E17TokenE80_05(E17TokenE80):
   type = 0x05
   def __init__(self, f):
      self.data = f.read(4)

@_e17_reg_tt_80
class E17TokenE80_13(E17TokenE80):
   type = 0x13
   def __init__(self, f):
      self.data = f.read_u16()

@_e17_reg_tt_80
class E17TokenE80_18(E17TokenE80):
   type = 0x18
   def __init__(self, f):
      # Payload syntax is dubious.
      self.data = (f.read_u8(), f.read_s16(), f.read_s16())

# /--------x80 tts
      

@_e17_reg_tt
class E17TokenEfe(E17TokenE):
   """fe: A single ActiveValue memory operation"""
   type = 0xfe
   
   def __init__(self, f):
      self.av = f.read_av()   
   
   def format_hr_val(self, *args):      
      return '< MEMOP: {} >'.format(self.av)
   
   def process(self, engine):
      self.av.process(engine, 1)
   
   def _get_color(self):
      return TFC_RED

@_e17_reg_tt
class E17TokenEff_Convref(E17TokenE):
   """ff: Load conversation script block."""
   type = 0xff
   def __init__(self, f):
      self.conv_ref = f.read_convr()

   def process(self, engine):
      engine.set_cs(self.conv_ref)

   def format_hr_val(self, *args):
      return '< Text: {} >'.format(self.conv_ref.format_hr(*args))

   def _get_color(self):
      return TFC_CYAN_D


# -------------------------------- Conversation-like script token types
e17ctth = TTHierarchy()
_e17_reg_ctt = e17ctth.reg

class E17TokenConvLike(E17Token):
   pass

   @staticmethod
   def textblock_start_type():
      return False
   
   @staticmethod
   def get_text_lines():
      return ()

class E17TokenCNodata(E17TokenConvLike):
   data = None
   def __init__(self, *args, **kwargs):
      pass

@_e17_reg_ctt
class E17TokenC00(E17TokenCNodata):
   type = 0x00

@_e17_reg_ctt
class E17TokenC01(E17TokenCNodata):
   """Line feed."""
   type = 0x01
   # FIXME: Ignoring this completely *will* result in formatting messups in a very few places. Figure out what to do about
   # this.
   #def process(self, engine):
      #engine.conv_line_break()

   @staticmethod
   def textblock_start_type():
      return 1

@_e17_reg_ctt
class E17TokenC02(E17TokenCNodata):
   """Wait-for-user-ack breakpoints?"""
   type = 0x02
   def process(self, engine):
      engine.break_token_loop(engine.ptrc.user_ack)
   
   def _get_color(self):
      return TFC_PURPLE
   
@_e17_reg_ctt
class E17TokenC03(E17TokenCNodata):
   type = 0x03

@_e17_reg_ctt
class E17TokenC04(E17TokenConvLike):
   type = 0x04
   def __init__(self, f):      
      self.data = f.read_av()

@_e17_reg_ctt
class E17TokenC05(E17TokenCNodata):
   """Usually in front of initial conversation text in a box ... but also occurs followed by other tokens."""
   type = 0x05
   def __init__(self, f):
      v = f.read_av()
      if (v.process(None,1)[0] != 0):
         raise ValueError('Unexpected 0x05 data av {}.'.format(v))

   @staticmethod
   def textblock_start_type():
      return 1

@_e17_reg_ctt
class E17TokenC0b(E17TokenConvLike):
   """Choice list entry."""
   type = 0x0b
   def __init__(self, f):
      # Choice list entry designations appear once at the beginning of a choice sequence (with a two-byte parameter?), and
      # once again before each choice.
      st = f.read_u8()
      if (st == 0x00):
         # Question id variant.
         self.text = None
         self.cid = f.read_u16()
         self.av_display = None
      
      else:
         self.cid = None
         if (st == 0x02):
            # Text and address
            addr = f.read_av()
            self.av_display = addr
         elif (st == 0x01):
            # Text, no addr
            self.av_display = None
         else:
            raise ValueError("Unknown \\x0b type {:x}.".format(st))
         
         self.text = f.read_string_fixedterm(b'\x01')

   def get_text_lines(self):
      if (self.text):
         return (self.text,)
      
      return ()

   def process(self, engine):
      # FIXME: Perhaps do something with cid, too?
      # T_1C analysis suggests that addressed options are only supposed to be displayed if the relevant memory address is
      # non-zero. For all other text-carrying ones, display is mandatory.
      if (not self.cid is None):
         choice = engine._new_choice(self.cid)
      else:
         choice = engine._choice

      if (self.text is None):
         return
      
      # Determine if to display this option. If not, we still need to inform the VN engine it exists for bookkeeping purposes.
      if (self.av_display is None):
         display = True
      else:
         (display,) = self.av_display.process(engine, 1)
         display = bool(display)

      choice._add_option(self.text, display=display)

   def format_hr_val(self, *args):
      if (self.text):
         return '({!r}, {})'.format(self.text, self.av_display)
      else:
         return '({})'.format(self.cid)

   def do_tokendisplay_linebreak(self):
      return True


@_e17_reg_ctt
class E17TokenC0c(E17TokenCNodata):
   type = 0x0c

@_e17_reg_ctt
class E17TokenC0d(E17TokenConvLike):
   type = 0x0d
   def __init__(self, f):
      # Voice data file specification
      (s,b) = f.read_string()
      if (b != b'\x00'):
         raise ValueError('Invalid \\x0d terminator {0!a}.'.format(b))
      self.data = s.encode('ascii')
   
   def get_refdata(self):
      return self.data
   
   @staticmethod
   def textblock_start_type():
      return 2

   def process(self, *args, **kwargs):
      raise NotImplementedError("Token {} can't be processed directly.".format(self))

   def _get_color(self):
      return TFC_GREEN

@_e17_reg_ctt
class E17TokenC0e(E17TokenCNodata):
   """New text section command."""
   type = 0x0e      
   def process(self, engine):
      pass
   
   @staticmethod
   def textblock_start_type():
      return 1
   
   def do_tokendisplay_linebreak(self):
      return True
   
   def _get_color(self):
      return TFC_BLUE

class E17TokenCSynthTextblock(E17TokenConvLike):
   def __init__(self, text, voice_ref):
      self.text = text
      self.voice_ref = voice_ref

   def get_text_lines(self):
      return self.text

   @staticmethod
   def format_hr_type():
      return 'Text'
   
   def process(self, engine):
      engine._new_textblock(self.text, self.voice_ref)
   
   def format_hr_val(self, p):      
      return '< {!r} voice: {}>'.format(self.text, self.voice_ref)

   def _get_color(self):
      return TFC_CYAN_D

   def do_tokendisplay_linebreak(self):
      return True

   @staticmethod
   def get_type():
      #Ugly hack, to make --ttf and --ttff work here.
      return E17TokenType((0x21,))


@_e17_reg_ctt
class E17TokenC10(E17TokenConvLike):
   type = 0x10
   def __init__(self, f):
      self.data = f.read_u8()

@_e17_reg_ctt
class E17TokenC11(E17TokenConvLike):
   type = 0x11
   def __init__(self, f):
      hdr = f.read(1)
      if (hdr != b'\x03'):
         raise ValueError('Invalid initial byte {!a} for \\x11 sequence.'.format(hdr))
      (self.data,_) = f.read_string()
      f.seek_back(1)
   
   def get_text_lines(self):
      return (self.data,)

class E17TokenCString(E17TokenConvLike):
   def __init__(self, v):
      self.val = v
   
   def get_text_lines(self):
      return (self.val,)
   
   @staticmethod
   def textblock_start_type():
      return 2
   
   def _get_color(self):
      return TFC_CYAN_D
   
   def format_hr_type(self):
      return 'Rawstring'
   
   def format_hr_val(self, *args):
      return '< {!r} >'.format(self.val)

   def process(self, *args, **kwargs):
      raise NotImplementedError("Token {} can't be processed directly.".format(self))

   @staticmethod
   def get_type():
      #Ugly hack, to make --ttf and --ttff work here.
      return E17TokenType((0x20,))


class E17ScriptDataRef(TokenizerDataRefLE):
   EL_EOLIST = _E17Label('EOLIST')
   TTYPE_STR = E17TokenCString
   def __init__(self, *args, parser, chunk_blacklist, chunk_idx, **kwargs):
      super().__init__(*args, **kwargs)
      self._parser = parser
      self._chunk_idx = chunk_idx
      self._chunk_blacklist = chunk_blacklist

   def get_cg_node(self, i):
      """Return callgraph node id for token data segment based on idx in list."""
      from ...base.tok_structures import CallgraphNode
      if (self._chunk_idx in self._chunk_blacklist):
         return None
      
      nid = (self._parser._fn.lower(), i)
      return CallgraphNode(nid)

   def get_cg_extra_edges(self):
      if ((self._chunk_idx in self._chunk_blacklist) or
          ((self._chunk_idx + 1) in self._chunk_blacklist) or # Ugly hack. Try to come up with something more reasonable.
          (not (self._end_forced is False)) or 
          (self._chunk_idx == len(self._parser._data_es)-1)):
         return ()
      #print(self._parser._fn.lower(), self._chunk_idx, len(self._parser._data_es))
      return (CallgraphEdge((self._parser._fn.lower(), self._chunk_idx), (self._parser._fn.lower(), self._chunk_idx+1)),)

   def read_esr(self, non_es_data=False):
      """Make event script reference from index."""
      v = self.read_u16()
      if (non_es_data):
         self._chunk_blacklist.add(v)
      
      return E17EventScriptReference(v, self._parser, non_es_data=non_es_data)

   def read_convr(self):
      """Read a u16 conv reference."""
      return E17ConvReference(self.read_u16(), self._parser)

   def read_fnr(self):
      """Read 4 bytes of 0x00 followed by a u16 fn reference."""
      # TODO: figure out what to do with the aux info.
      aux_val = (self.read_av(), self.read_av(), self.read_av(), self.read_av())
      if (aux_val == ([],)*4):
         aux_val = None
      return E17FileReference(self.read_u16(), self._parser, aux_val)
   
   def read_av(self):
      """Parse active value sequence."""
      return E17ActiveValueSequence.build_from_file(self)

   def read_string_fixedterm(self, t):
      (s,t_r) = self.read_string()
      if (t != t_r):
         raise ValueError('Got unexpected terminator {!a} instead of {!a} after reading {!a}.'.format(s,t_r,t))
      return s
   
   def read_bytes_fixedterm(self, t):
      rv = bytearray()
      while (True):
         b = self.read(1)
         if (b == t):
            break
         rv.extend(b)
      return bytes(rv)
   
   def read_string(self):
      s_l = [bytearray()]
      b = None
      # TODO: Optimization?
      off_0 = self._off
      while (True):
         b = self.read(1)
         if (not self.char_is_text(b)):
            break
         if (b == b'\x87'):
            # The encoding here isn't pure shift-jis, but some extended variant. The EN version only uses three of the
            # nonstandard codepoints; we hardcode them here.
            b_n = self.read(1)
            if (not self.char_is_text(b_n)):
               self.seek_back(2)
               raise ValueError('Bogus shift-jis escape sequence: Follow value is non-text char {!r}.'.format(b_n))
            if (b_n == b'J'):
               # German umlaut oe.
               c = '\xf6'
            elif (b_n == b'K'):
               # ?German umlaut ue?
               # TODO: Verify whether this is correct.
               c = '\xfc'
            elif (b_n == b'L'):
               # Wide dash.
               c = '\u2015'
            else:
               raise ValueError('Unknown extended shift-jis sequence \\x87\\x{0:x}'.format(ord(b_n)))
            
            s_l.append(c)
            s_l.append(bytearray())
         else:
            s_l[-1] += b
      
      def dec(s):
         if isinstance(s, str):
            return s
         return s.decode('shift-jis')
      
      try:
         rv = ''.join((dec(s) for s in s_l))
      except Exception as exc:
         self.f.seek(off_0)
         d = self.f.read(self._off - off_0)
         raise ValueError('Unable to decode string value {0!a}.'.format(d)) from exc
      return (rv,b)

   # High-level tokenization functions
   def get_tokens(self, *args, **kwargs):
      if (self._chunk_idx in self._chunk_blacklist):
         ntd = E17NonTokenData(self)
         ntd._dref = self
         return [ntd]
      
      rv = super().get_tokens(*args, **kwargs)
      if (self._end_forced is None):
         self._end_forced = False
      return rv
   
   def char_is_text_tok(self, *args, **kwargs):
      raise NotImplementedError()
   
   @classmethod
   def char_is_text(cls, c):
      return (((ord(c) >= 0x20)) or (c in b'\n\t'))

   @classmethod
   def build(cls, *args, **kwargs):
      return cls(*args, **kwargs)

class E17ConvScriptTokenizer(E17ScriptDataRef):
   """E17 Conversation-Like-Bytecode tokenizer."""
   TH = e17ctth
   def char_is_text_tok(cls, c):
      return cls.char_is_text(c)

   def get_text_lines(self):
      rv = []
      for tok in self.get_tokens():
         rv.extend(tok.get_text_lines())
      return rv

   def get_tokens(self, get_dref=False, *args, **kwargs):
      # At the conceptual (and UI) level, an E17 script is built up out of blocks of conversation with optionally attached
      # voice clips.
      # The actual conv bytecode has rather less structure, however, and determining just where a block begins and ends is
      # messy. We perform the appropriate messy operations here.
      
      tokens = super().get_tokens(*args, get_dref=get_dref, **kwargs)
      l = len(tokens)
      tokens_out = []
      i = 0
      while (i < l):
         tok = tokens[i]
         i += 1
         tstart = tok.textblock_start_type()
         
         if (tstart):
            j = i-1
            if (tstart == 2):
               i -= 1
            text = ['']
            voice_data = None
            if (get_dref):
               off_0 = tok._dref.off
            while (i < l):
               tok = tokens[i]
               if (isinstance(tok, E17TokenCString)):
                  text[-1] += tok.val
               elif (tok.type == 0x01):
                  text.append('')
               elif (tok.type in (0x05, 0x10)):
                  pass
               elif (tok.type == 0x0d):
                  if not (voice_data is None):
                     raise ValueError('Dupe voice data in token {}.'.format(i))
                  voice_data = tok.get_refdata()
               else:
                  break
                  
               i += 1
            if (text[-1] == ''):
               del(text[-1])
            
            if (text or not (voice_data is None)):
               stb = E17TokenCSynthTextblock(text, voice_data)
               if (get_dref):
                  stb._dref = DataRefFile(tok._dref.f, off_0, tok._dref.off+tok._dref.size - off_0)
               tokens_out.append(stb)
            else:
               tokens_out.extend(tokens[j:i])
         else:
            tokens_out.append(tok)
      return tokens_out


class E17ScriptTokenizer(E17ScriptDataRef):
   """Class for tokenizing E17 Top Level Data chunks."""
   TH = e17stth
   def char_is_text_tok(self, c):
      return False


# ---------------------------------------------------------------- SCR file parser classes
class E17ScriptParser:
   UINT_FMT = '<{0:d}L'
   UINT_LEN = struct.calcsize(UINT_FMT.format(1))
   CST = E17ConvScriptTokenizer
   EST = E17ScriptTokenizer
   
   def __init__(self, f, base_off, off_lim=None, fn=None):
      self._f = f
      self._fn = fn
      self._base_off = base_off
      self._off = None
      if (off_lim is None):
         self._f.seek(0,2)
         off_lim = self._f.tell()
      self._off_lim = off_lim
      self._parse_data()
   
   @classmethod
   def build_from_dataref(cls, dref, fn=None):
      if (fn is None):
         try:
            fn = dref.name
         except AttributeError:
            pass
      
      dref = dref.get_dref_plain()
      return cls(dref.f, dref.off, dref.off + dref.size, fn)
   
   def _seek(self, i):
      toff = i + self._base_off
      self._f.seek(toff)
      self._off = toff
   
   def _read(self, i, off_inc=True):
      rv = self._f.read(i)
      if (off_inc):
         self._off += len(rv)
      else:
         self._f.seek(-1*len(rv), 1)
      if (self._off > self._off_lim):
         raise ValueError('Attempted to read {} bytes beyond domain wall.'.format(self._off-self._off_lim+1))
      return rv
   
   def _read_uints(self, i, **kwargs):
      data = self._read(i*self.UINT_LEN, **kwargs)
      rv = struct.unpack(self.UINT_FMT.format(i), data)
      return rv
   
   def _read_uint_list(self, off_lim_in=None):
      if (off_lim_in is None):
         (off_lim,) = self._read_uints(1, off_inc=False)
      else:
         off_lim = off_lim_in
      off_lim += self._base_off
      tlen_r = off_lim - self._off
      (tlen, tlen_mod) = divmod(tlen_r, self.UINT_LEN)
      if ((off_lim_in is None) and (tlen_mod)):
         # Apparently for files for which the next element isn't 4-byte aligned (which is almost all of them - the known
         # counterexample are system.scr and startup.scr), not only are the modulo bytes not part of the uint table anymore,
         # but neither are the last four bytes prior to them.
         # Figuring this out by looking at the offset is probably not what the original designers of this format intended,
         # though ... I'm dubious this was ever meant to be parsed apart into lists like this by software who didn't already
         # have limits on the offsets involved through other means. But at the time of writing we don't know what those means
         # are, so this hackjob will have to do.
         tlen -= 1
      rv = self._read_uints(tlen)
      return rv
   
   def _package_list_data(self, data_offs, off_lim=None, ecls=None):
      # 'off_lim' is relative to the beginning of parsed data.
      if (ecls is None):
         ecls = self.CST
      
      if (off_lim is None):
         off_lim = self._off_lim
      else:
         off_lim += self._base_off
      rv = []
      if not (data_offs):
         return rv
      
      idx_blacklist = set()
      
      def make_le():
         le = ecls.build(self._f, coff + self._base_off, coff_next-coff, parser=self, chunk_blacklist=idx_blacklist, chunk_idx=i)
         rv.append(le)
      
      for i in range(len(data_offs)-1):
         (coff,coff_next) = data_offs[i:i+2]         
         make_le()
      
      i = len(data_offs)-1
      coff = data_offs[-1]
      coff_next = off_lim - self._base_off
      make_le()
      
      return rv
   
   def _parse_data(self):
      self._seek(0)

      pre = self._read(4)
      if (pre != b'SC3\x00'):
         raise ValueError('Unexpected preamble {0!r}.'.format(pre))
      
      (off_cs_list, off_fn_list) = self._read_uints(2)
      es_offs = self._read_uint_list()
      es = self._package_list_data(es_offs, off_lim=off_cs_list, ecls=self.EST)
      
      off_lim_rel = self._off_lim - self._base_off
      
      if (off_cs_list != off_lim_rel):
         self._seek(off_cs_list)
         cs_off_lim = self._off_lim
         cs_offs = self._read_uint_list(off_fn_list)
         if (off_fn_list != self._off_lim):
            if (cs_offs):
               fnl_off_lim = cs_offs[0]
            else:
               fnl_off_lim = None
            self._seek(off_fn_list)
            fnl_offs = self._read_uint_list(fnl_off_lim)
            fnl = self._package_list_data(fnl_offs)
            # Ugly hack. This will work ok as long as the filename table directly follows the convscript one, but we have no
            # guarantee to that effect.
            if (fnl_offs):
               cs_off_lim = fnl_offs[0]
            else:
               cs_off_lim = off_lim_rel
         else:
            fnl = ()
         cs = self._package_list_data(cs_offs, off_lim=cs_off_lim)
      else:
         fnl = cs = ()
      
      self._off = None
      self._off_csoff_list = off_cs_list
      self._data_es = es
      self._data_cbc = cs
      self._data_fn = fnl
   
   def get_es(self, idx):
      """Return event script chunk"""
      return self._data_es[idx]
   def get_cs(self, idx):
      """Return conversation script chunk"""
      return self._data_cbc[idx]
   def get_fn(self, idx):
      """Return filename"""
      return self._data_fn[idx]
   
   def write(self, f_out):
      from itertools import chain
      off_0 = f_out.tell()
      
      off = self._base_off
      # Let's keep things simple for now, and not mess with the somewhat tricky ES section at all.
      self._f.seek(self._base_off)
      f_out.write(self._f.read(self._off_csoff_list))
      off += self._off_csoff_list
      
      off_out_tables_csl = f_out.tell()
      cs_data = self._data_cbc
      fn_data = self._data_fn
      
      tlen = len(cs_data) + len(fn_data)
      offs = []
      
      off = f_out.seek(tlen*self.UINT_LEN,1)
      for entry in chain(cs_data, fn_data):
         offs.append(off)
         off += f_out.write(entry.get_data())
      
      t_fmt = self.UINT_FMT.format(tlen)
      f_out.seek(off_out_tables_csl)
      f_out.write(struct.pack(t_fmt, *offs))
      return (off - off_0)
   
   def build_dref(self):
      from io import BytesIO
      b = BytesIO()
      size = self.write(b)
      return DataRefFile(b, 0, size)
   
   @classmethod
   def _main(cls):
      import optparse
      import os.path
      import sys
      from ...base.config import ConfigSet
      
      conf = ConfigSet()
      TokenFormatter.add_config(conf, html_opt=False)
      
      op = optparse.OptionParser()
      op.add_option('-c', '--tok-cl', default=False, dest='tok_cl', action='store_true', help='Tokenize conv-like bytecode.')
      op.add_option('-o', '--out', default=None, dest='outfile', action='store', metavar='PATH', help='File to write script dump output to (defaults to stdout)')
      op.add_option('-s', '--tok-script', default=False, dest='tok_script', action='store_true', help='Tokenize script (top-level) data.')
      op.add_option('-w', '--rewrite', default=False, dest='rewrite', action='store_true', help='Rewrite script files.')
      op.add_option('--hacds', default=False, dest='hacds', action='store_true', help='Perform heuristical auto-correlation based script raw data splitting.')
      op.add_option('--script', default=False, dest='dump_script', action='store_true', help='Dump raw script (top level) data')
      op.add_option('--cbc', default=False, dest='dump_cbc', action='store_true', help='Dump raw conv-like bytecode')
      op.add_option('--fn', default=False, dest='dump_fn', action='store_true', help='Dump raw filename data')
      op.add_option('--tok-disable', default=None, dest='tokpko', action='store', metavar='HEXTOKVAL', help='Disable parser for specified token type.')
      op.add_option('--lnk', default=False, dest='lnk', action='store_true', help='Parse input from LNK archive instead of presplitted scr files.')
      op.add_option('--html', default=False, dest='html', action='store_true', help='Produce HTML-formatted output')
      
      conf.setup_optparse(op)
      
      (opts, args) = op.parse_args()
      
      if not (opts.outfile is None):
         of = open(opts.outfile, 'wb')
         def out(text):
            odata = text.encode('utf-8')
            of.write(odata)
            return len(text)
         
      else:
         out = sys.stdout.write
      
      if not (opts.tokpko is None):
         b = bytes((int(opts.tokpko.encode('ascii'),16),))
         del(cls.CST._PARSERS[b])
      
      fns = args
      fnl_max = max(len(ascii(fn)) for fn in fns)
      
      def make_tf(**kwargs):
         return TokenFormatter.build_from_config(conf, **kwargs)
      
      if (opts.html):
         ftd = FTD_HTML()
      else:
         ftd = FTD_ANSIIncremental(out)
      
      if (opts.tok_cl):
         tf_cl = make_tf(FTD=ftd, outname='conv-like data', tok_cls=cls.CST, html=opts.html)
      else:
         tf_cl = None
      
      if (opts.tok_script):
         tf_script = make_tf(FTD=ftd, outname='Script data', tok_cls=cls.EST, html=opts.html)
      else:
         tf_script = None
      
      def dump_raw_element(e):
         d = e.get_data()
         ftd.add_str(repr(hexs(d)))
         if (opts.hacds):
            ACDataSplitter().data_format(d, print)
      
      if (opts.lnk):
         def make_e17p(f):
            from .lnk import LNKParser
            lnkp = LNKParser.build_from_file(f)
            rv = [(chunk.name,cls.build_from_dataref(chunk)) for chunk in list(lnkp)]
            return rv
            
      else:
         def make_e17p(f):
            return [(f.name.encode(), cls(f,0))]
      
      for fn_c in fns:
         f = open(fn_c, 'rb')
         for (fn, p) in make_e17p(f):
            ftd.add_str('---------------- Parsed {0!a:{1}}: {2:4d} {3:4d} {4:4d}\n'.format(fn, fnl_max, len(p._data_es), len(p._data_cbc),
               len(p._data_fn)))
            if (opts.dump_script):
               ftd.add_str('-------- raw script data:\n')
               for (e,i) in zip(p._data_es,range(len(p._data_es))):
                  tf_script.out_str('----- stbb ({0})\n'.format(i))
                  dump_raw_element(e)
         
            if (opts.dump_cbc):
               ftd.add_str('-------- raw bytecode data:\n')
               for e in p._data_cbc:
                  tf.out_str(e.get_data())
            if (opts.dump_fn):
               ftd.add_str('-------- raw fn data:\n')
               for e in p._data_fn:
                  tf.out_str(e.get_data())
               
            if not (tf_script is None):
               tf_script.process_elements(p._data_es, p)
         
            if not (tf_cl is None):
               tf_cl.process_elements(p._data_cbc, p)
            
            if (opts.rewrite):
               fn_out = os.path.basename(fn) + b'.rewrite'
               ftd.add_str('----->>> {!r}\n'.format(fn_out))
               fo = open(fn_out, 'wb')
               p.write(fo)
               fo.close()
         
      if not (tf_script is None):
         tf_script.dump_summary()
      
      if not (tf_cl is None):
         tf_cl.dump_summary()
      
      ftd.write_output(out)
    
    
data_handler_reg(b'scr')(E17ScriptParser.build_from_dataref)
_main = E17ScriptParser._main

if (__name__ == '__main__'):
   _main()
