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

# Base Tokenization structures.

import optparse
import struct

from .file_data import DataRefFile
from .text_fmt import *
from .text_markup import *

class StopTokenization(Exception):
   pass

class UnknownTokenError(KeyError):
   pass

class TTHierarchy(dict):
   def reg(self, val):
      self[val.type] = val
      return val
   
   def __getinitargs__(self):
      return (tuple(self.items()),)
   
   def get_types(self):
      rv = set()
      for arg in self.values():
         rv.update(arg.get_types())
      return rv
   
   def build(self, f, get_dref=False, *args, **kwargs):
      if (get_dref):
         off_0 = f.get_off()
      
      tt = ord(f.read(1))
      
      try:
         b = self[tt]
      except KeyError as exc:
         raise UnknownTokenError('Unknown opcode {:02x}.'.format(tt)) from exc
      
      rv = b.build(f, *args, **kwargs)
      
      if (get_dref):
         size = f.get_off() - off_0
         rv._dref = DataRefFile(f.f, off_0, size)
      
      return rv

# ---------------------------------------------------------------- Graph classes
class CallgraphNode:
   def __init__(self, id_):
      self.id = id_

   def get_decl(self):
      return self.get_name() + ' [label="{}"]'.format(self.id[-1])

   def get_name(self):
      return '"n{:x}"'.format(id(self))

class CallgraphEdge:
   def __init__(self, src, dst):
      self.src_id = src
      self.dst_id = dst
   
   @classmethod
   def fromdst(cls, *args, **kwargs):
      return cls(None, *args, **kwargs)
   
   def update_pos(self, node):
      if (self.src_id is None):
         self.src_id = node.id
      self.dst_id = tuple((b if (a is None) else a) for (a,b) in zip(self.dst_id, node.id))
   
   def __eq__(self, other):
      return ((self.src_id == other.src_id) and (self.dst_id == other.dst_id))
   
   def __ne__(self, other):
      return ((self.src_id != other.src_id) or (self.dst_id != other.dst_id))
   
   def fmt_dot(self, cg):
      return '{} -> {}'.format(cg._get_nn(self.src_id), cg._get_nn(self.dst_id))
   
   def __hash__(self):
      return hash((self.src_id, self.dst_id))

class Callgraph:
   edges = ()
   node_map = ()
   def __init__(self, *, _is_subgraph=False):
      self.nodes = {}
      self.subgraphs = {}
      if not (_is_subgraph):
         self.edges = set()
         self.node_map = {}
   
   def _get_subgraph(self, gid):
      try:
         rv = self.subgraphs[gid]
      except KeyError:
         rv = self.subgraphs[gid] = type(self)(_is_subgraph=True)
      return rv
   
   def _add_node(self, nid, idx, idx_lim, node):
      nid_sub = nid[idx]
      if (idx == idx_lim):
         self.nodes[nid_sub] = node
         return
      return self._get_subgraph(nid_sub)._add_node(nid, idx+1, idx_lim, node)
   
   def add_node(self, node):
      self.node_map[node.id] = node
      return self._add_node(node.id, 0, len(node.id)-1, node)
   
   def add_edge(self, edge):
      self.edges.add(edge)
   
   _SG_FMT = '''subgraph "cluster_sg_{:x}" {{
   //node [style=filled, color=white];
   label="{}";
   style=filled;
   color=lightgrey;
   {}
}}'''
   def _fmt_dot_body(self):
      rseq = [self._SG_FMT.format(id(sg), name, sg._fmt_dot_body()) for (name, sg) in self.subgraphs.items()]
      rseq.extend([format(n.get_decl()) for n in self.nodes.values()])
      return ';\n'.join(rseq)
   
   _G_FMT = '''digraph main {{
   {}
}}'''
   def _get_nn(self, nid):
      return self.node_map[nid].get_name()

   def get_dot_data(self, f=None):
      rseq = [e.fmt_dot(self) for e in self.edges]
      rseq.append(self._fmt_dot_body())
      return self._G_FMT.format(';\n'.join(rseq))
   
   def __repr__(self):
      return '<{} @ {}; {} nodes, {} sg, {} edges>'.format(type(self).__name__, id(self), len(self.nodes), len(self.subgraphs),
         len(self.edges))

# ---------------------------------------------------------------- Token classes
class BaseTokenType(tuple):
   def __format__(self, fmt):
      if (fmt != ''):
         raise ValueError('Invalid fmt {!r}.'.format(fmt))
      return '-'.join('{:02x}'.format(st) for st in self)

class BaseToken:
   _dref = None
   def _get_off(self):
      return self._dref.off
   
   @classmethod
   def _format_delem(cls, e, *args, **kwargs):
      if (hasattr(e, 'format_hr')):
         return e.format_hr(*args, **kwargs)
      if (isinstance(e, tuple)):
         return '({})'.format(', '.join(cls._format_delem(x,*args, **kwargs) for x in e))
      if (isinstance(e,str)):
         return repr(e)
      return str(e)
   
   def format_hr_type(self):
      cls = type(self)
      tl = []
      while (not (cls is object)):
         try:
            tl.append(cls.__dict__['type'])
         except KeyError:
            pass
         (cls,) = cls.__bases__
      
      return '-'.join('{0:02x}'.format(x) for x in reversed(tl))
   
   def format_hr_val(self, p):
      if (self.data is None):
         return ''
      if (isinstance(self.data, tuple)):
         fv = self._format_delem(self.data, p)
      else:
         fv = str(self.data)
      return '({0})'.format(fv)
      
   def format_hr(self, p, color=False, dump_raw=False, html_order=False):
      ts = self.format_hr_type()
      
      rv = ['{}{}'.format(ts, self.format_hr_val(p))]
      
      if (dump_raw):
         raw_data = self._dref.get_data()
         
         if (html_order):
            raw_data = self._dref.get_data()
            rv.insert(0, 'RAW: {!r}  '.format(hexs(raw_data)))
         
         else:
            if (len(raw_data) > 1):
               rv.append('RAW: {!r}'.format(hexs(raw_data)))
      
      rv = [FT_String(x) for x in rv]
      if (color):
         c = self._get_color()
         if (c):
            rv = [FT_GStr(x, c) for x in rv]
      
      return rv
   
   def _get_color(self):
      return TF_NONE
   
   def do_tokendisplay_linebreak(self):
      return False
   
   def get_edges(self, p):
      return ()
   
   @classmethod
   def get_type(cls):
      return BaseTokenType((cls.type,))
   
   @classmethod
   def get_types(cls):
      return set((cls.get_type(),))


class TokenizerDataRef(DataRefFile):
   segment_name = None
   _end_forced = None
   def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self._off_lim = self.off + self.size
      self._off_bookmark = None
   
   def get_segment_name(self, i):
      """Return name for token data segment based on idx in list."""
      return i
   
   def get_cg_node(self, i):
      """Return callgraph node id for token data segment based on idx in list."""
      raise NotImplementedError()
   
   def get_cg_extra_edges(self):
      """Return extra callgraph edges related to this node."""
      return ()
   
   def read_bval(self, fmt):
      from struct import calcsize, unpack
      d = struct.calcsize(fmt)
      return unpack(fmt, self.read(d))

   def read(self, l):
      rv = self.f.read(l)
      if ((len(rv) != l) or (self._off > self._off_lim)):
         raise ValueError('Read beyond domain wall.')
      self._off += len(rv)
      return rv

   def seek_back(self, i):
      self.f.seek(-1*i,1)
      self._off -= i

   def set_end(self):
      """Stop parsing at current position."""
      if (self._off > self._off_lim):
         raise ValueError('Had already read {} bytes beyond domain wall at {:x}.'.format(f._off - f._off_lim, f._off_lim))
      self._off_lim = self._off
      self.size = self._off - self.off
      self._end_forced = True

   def eat_const(self, s):
      """Read and verify specified fixed byte sequence."""
      d = self.read(len(s))
      if (d != s):
         raise ValueError('Unexpected data {!a} instead of {!a}.'.format(d, s))
   
   def eat_nulls(self, c):
      """Read and verify specified number of x00 bytes."""
      d = self.read(c)
      if (d != b'\x00'*c):
         raise ValueError('Unexpected non-null data {!a}.'.format(d))

   def get_off(self):
      """Return current offset."""
      return self._off

   def set_off_mark(self):
      """Mark this offset for data reread purposes."""
      if not (self._off_bookmark is None):
         raise ValueError('I already have a marked offset.')
      self._off_bookmark = self._off
   
   def clear_off_mark(self):
      """Clear marked offset."""
      self._off_bookmark = None
   
   def read_from_off_mark(self):
      """Return data starting from marked offset, and clear mark"""
      self.f.seek(self._off_bookmark)
      l = self._off - self._off_bookmark
      self._off_bookmark = None
      return self.f.read(l)
   
   def _get_tokdata_off(self):
      return self.off
   
   def _build_token(self, *args, **kwargs):
      return self.TH.build(self, *args, **kwargs)
   
   # High-level tokenization functions
   def get_tokens(self, get_dref=False):      
      self._off = self._get_tokdata_off()
      self.f.seek(self._off)
      tokens = []
      try:
         while (self._off < self._off_lim):
            ol = self._off
            try:
               tok = self._build_token(get_dref=get_dref)
            except StopTokenization:
               break
            except UnknownTokenError as exc:
               self._off = ol
               self.f.seek(ol)
               tc = self.read(1)
               if not (self.char_is_text_tok(tc)):
                  raise
               self.seek_back(1)
               off_0 = self._off
               (val,_) = self.read_string()
               self.seek_back(1)
               tok = self.TTYPE_STR(val)
               tok._dref = DataRefFile(self.f, off_0, self._off-off_0)
            
            tokens.append(tok)
      except Exception as exc:
         exc.tokens = tokens
         raise
      return tokens
   
   def char_is_text_tok(self, c):
      return False


class TokenizerDataRefLE(TokenizerDataRef):
   def read_u8(self):
      (val,) = struct.unpack('<B', self.read(1))
      return val

   def read_u16(self):
      (val,) = struct.unpack('<H', self.read(2))
      return val

   def read_s16(self):
      (val,) = struct.unpack('<h', self.read(2))
      return val

# ---------------------------------------------------------------- Human-readable token dump structures
class _FreqDict(dict):
   def inc(self, key, v=1):
      try:
         self[key] += v
      except KeyError:
         self[key] = v
   
   def make_ft(self, sortkey=lambda e: e[1]):
      dl = list(self.items())      
      dl.sort(key=sortkey)
      rv = FT_Table()
      for (s,c) in dl:
         rv.add_row((FT_String(format(c)), FT_String(format(s))))
      return rv

class _TokenFormatterOG(optparse.OptionGroup):
   def __init__(self, *args, _tf_cls, **kwargs):
      super().__init__(*args, **kwargs)
      self._tf_cls = _tf_cls
   
   def build_tf(self, opts, **kwargs2):
      """Build TokenFormatter from specified options."""
      kwargs = {}
      
      for opt in self.option_list:
         name = opt.dest
         kwargs[name] = getattr(opts, name)
      
      if (kwargs2):
         kwargs.update(kwargs2)
      
      return self._tf_cls(**kwargs)

class TokenFormatter:
   def __init__(self, *, FTD, want_tt_f=False, want_tt_ff=False, esf_len=None, pre_error_len=None, want_nas=False, dump_tok=False,
         tok_fail_continue=False, want_tok_fail_stats=True, want_elf=False, debl=None, tok_cls=None, color=False,
         get_raw=False, pe_tracebacks=False, get_offs=False, callgraph_fn=None, html=False, outname=''):
      self.tok_fail_cont = tok_fail_continue
      self.want_strings = bool(want_nas)
      if (want_nas):
         self.nas = []
      else:
         self.nas = None
      
      self.outname = outname
      
      if (not want_tt_f):
         self.tt_f = None
      else:
         self.tt_f = tok_freq = dict.fromkeys(tuple(tok_cls.TH.get_types()),0)
      
      if (not want_tt_ff):
         self.tt_ff = None
         self._tts = None
      else:
         self.tt_ff = {}
         self._tts = [None] + sorted(tuple(tok_cls.TH.get_types()))
         for tt1 in self._tts:
            for tt2 in self._tts:
               self.tt_ff[(tt1,tt2)] = 0
      
      self.esf_len = esf_len
      if not (esf_len is None):
         self.esf = _FreqDict()
      if not (pre_error_len is None):
         self.pel = pre_error_len
         self.ped = _FreqDict()
      else:
         self.pel = None
         self.ped = None
      
      self.dump_tok = dump_tok
      if (want_tok_fail_stats):
         self.tok_parse_fail = 0
         self.tok_parse_fail_l = 0
         self.tok_parse_succ = 0
         self.tok_parse_succ_l = 0
      else:
         self.tok_parse_fail = self.tok_parse_succ = None
      
      if (want_elf):
         self.elf = _FreqDict()
      else:
         self.elf = None
      self.debl = debl
      if not (debl is None):
         self.debl_data = _FreqDict()
      self.color = color
      self.get_raw = get_raw
      self.get_offs = get_offs
      self.pe_tracebacks = pe_tracebacks
      
      self._want_tok_dref = get_raw or get_offs
      
      if not (callgraph_fn is None):
         self.callgraph = Callgraph()
         self.callgraph_fn = callgraph_fn
      else:
         self.callgraph = self.callgraph_fn = None
      
      self._of_html = html
      self.outdoc = FTD
   
   __csn = 'Token output options'
   @classmethod
   def add_config(cls, cs, html_opt=True): 
      scs = cs.get_scs(cls.__csn)
      ace = scs.add_ce
      #g = _TokenFormatterOG(op, cls._sgname, _tf_cls=cls)
      ace('dump tokens', shortopt='-t', dest='dump_tok', default=False, const=True, help='Dump tokenized data.')
      ace('get raw', shortopt='-r', default=False, const=True, help='Dump raw hex data for each token.')
      ace('color', shortopt='-u', default=False, const=True, help='Color output based on token type.')
      ace('dump offsets', shortopt='-q', dest='get_offs', default=False, const=True, help='Print offsets for each token line.')
      ace('want_tt_f', longopt='--ttf', default=False, const=True, help='Dump token type frequency data')
      ace('want_tt_ff', longopt='--ttff', default=False, const=True, help='Dump token type follow frequency data')
      ace('want_elf', longopt='--elf', default=False, const=True, help='Dump element length frequencies.')
      ace('esf_len', longopt='--esflen', default=None, converter=int, metavar='INT', help='Element start sequence length over which to calculate frequencies')
      ace('pre_error_len', longopt='--pre-error-len', default=None, converter=int, metavar='INT', help='Number of pre-error tokens to consider for pre-error frequency calculation')
      #g.add_option('--errfflen', default=None, dest='errff_len', action='store', type='int', metavar='INT', help='Element tokenization error follow sequence length over which to calculate frequencies')
      #g.add_option('--dnas', default=False, dest='want_nas', action='store_true', help='Dump non-ascii strings')
      ace('tok_fail_continue', longopt='--cont-on-tok-failure', default=False, const=True, help="Do not abort parsing on tokenization failures")
      ace('debl', default=None, converter=int, metavar='INT', help='Dump elements with specified length.')
      ace('tracebacks', dest='pe_tracebacks', default=False, const=True, help='When using --cont-on-tok-failure, print full parsing error tracebacks.')
      ace('callgraph-out', dest='callgraph_fn', default=None, metavar='PATH', help='Filename to write callgraph information in DOT format to.')
      if (html_opt):
         ace('html', default=False, const=True, help='Write output as HTML.')
   
   def finish_output(self, out):
      self.outdoc.write_output(out)
   
   @classmethod
   def _get_settings(cls, cs):
      return cs.get_scs(cls.__csn).get_settings()
   
   @classmethod
   def build_from_config(cls, cs, **kwargs):
      from sys import stdout
      kwargs2 = cls._get_settings(cs)
      kwargs2.update(kwargs)
      
      if not ('FTD' in kwargs2):
         if kwargs2['html']:
            kwargs2['FTD'] = FTD_HTML()
         else:
            kwargs2['FTD'] = FTD_ANSIIncremental(stdout.write)
      
      return cls(FTD=kwargs2.pop('FTD'), **kwargs2)
   
   def out_str(self, s):
      return self.outdoc.add_str(s)
   
   def output(self, e):
      self.outdoc.add_data(e)
   
   def process_tokenize_error(self, e, segment_name, exc):
      self.out_str('-------- Failed to tokenize({}): {}\n  {!a}\n  {}.\n'.format(segment_name, exc, e.get_data(), hexs(e.get_data())))
      
      if not (self.tok_fail_cont):
         raise
      elif (self.pe_tracebacks):
         from traceback import format_exception
         self.out_str(''.join(format_exception(type(exc),exc,exc.__traceback__)))
   
   def process_elements(self, s, p):
      if (len(s) < 1):
         return
      
      if (self.dump_tok):
         self.out_str('-------- tokenized {0}:\n'.format(self.outname))
      
      if (self.callgraph is None):
         cg_node = None
      
      for (i,e) in enumerate(s):
         if not (self.esf_len is None):
            self.esf.inc(e.get_data()[:self.esf_len])
         if not (self.elf is None):
            self.elf.inc(e.get_size())
         if (e.get_size() == self.debl):
            self.debl_data.inc(e.get_data())

         sname = e.get_segment_name(i)
         if not (self.callgraph is None):
            cg_node = e.get_cg_node(i)
            if not (cg_node is None):
               self.callgraph.add_node(cg_node)
         try:
            tokens = e.get_tokens(get_dref=self._want_tok_dref)
         except Exception as exc:
            if not (self.tok_parse_fail is None):
               self.tok_parse_fail += 1
               self.tok_parse_fail_l += e.get_size()
            
            self.process_tokenize_error(e,sname,exc)
            if (exc.tokens):
               if not (self.pel is None):
                  for tok in exc.tokens[-1*self.pel:]:
                     self.ped.inc(tok.format_hr_type())
               
               self.process_tokens(exc.tokens, i, p, cg_node, print_heading=False)
            continue
         
         if not (self.tok_parse_succ is None):
            self.tok_parse_succ += 1
            self.tok_parse_succ_l += e.get_size()
         
         self.process_tokens(tokens, sname, p, cg_node)
         
         if (self.callgraph):
            for cg_edge in e.get_cg_extra_edges():
               self.callgraph.add_edge(cg_edge)
   
   def process_tokens(self, tokens, segment_name, p, cg_node, print_heading=True):
      tt_prev = None
      if (self.dump_tok and print_heading):
         self.out_str('-------- {} tokens({})\n'.format(self.outname,segment_name))
      
      strings = []
      if (self.want_strings):
         for tok in tokens:
            if (tok.get_type() == E17ConvScriptTokenizer.TTYPE_STR):
               strings.append(tok.data)
            
      if not (self.tt_ff is None):
         for tok in tokens:
            self.tt_ff[(tt_prev, tok.get_type())] = self.tt_ff.get((tt_prev, tok.get_type()), 0) + 1
            tt_prev = tok.get_type()
            
         self.tt_ff[(tt_prev, None)] = self.tt_ff.get((tt_prev, None), 0) + 1
         
      if not (self.tt_f is None):
         for tok in tokens:
            t = tok.get_type()
            self.tt_f[t] = self.tt_f.get(t,0) + 1
            
      if (self.dump_tok):
         ttable = self.format_tokens_hr(tokens, p)
         self.output(ttable)
         
      if not (self.nas is None):
         nas = []
         for s in strings:
            try:
               s.encode('ascii')
            except UnicodeEncodeError:
               nas.append(s)
         if (nas):
            self.out_str('-------- non-ascii strings:\n')
         for s in nas:
            self.out_str(repr(s))
      
      if not (self.callgraph is None):
         for tok in tokens:
            for edge in tok.get_edges(p):
               edge.update_pos(cg_node)
               self.callgraph.add_edge(edge)
   
   def dump_summary(self):
      self.out_str('---------------- Summary ({0}):\n'.format(self.outname))
      if not (self.tok_parse_fail is None):
         tc = self.tok_parse_fail + self.tok_parse_succ
         fc = self.tok_parse_fail
         ff = fc
         if (ff):
            ff /= tc
         ttl = self.tok_parse_fail_l + self.tok_parse_succ_l
         fl =  self.tok_parse_fail_l
         rfl = fl
         if (rfl):
            rfl /= ttl
            
         self.out_str('-------- Failed to parse {0:d}/{1:d}({2:.2f}%) data blocks containing {3:d}/{4:d}({5:.2f}%) bytes\n'.format(
            fc,tc,ff*100.0, fl,ttl,rfl*100.0))
      
      if not (self.elf is None):
         self.out_str('-------- Element length frequency dump:\n')
         self.output(self.elf.make_ft(sortkey=lambda e: -1*e[0]))
         
      if (self.tt_f):
         self.out_str('-------- token frequency dump:\n')
         tfreqs = list(self.tt_f.items())
         tfreqs.sort(key=lambda e:e[1])
         table = FT_Table()
         for (tt,f) in tfreqs:
            table.add_row((FT_String('{:8}'.format(format(tt))), FT_String('{:6}'.format(f))))
         self.output(table)
      
      if (self.tt_ff):
         self.out_str('-------- token follow frequency dump:\n')
         #cell_fmt = '{0:>5} '
         
         table = FT_Table()
         def format_tt(tt):
            return FT_String(format(format(format(tt))))
         
         table.add_row(format_tt(tt1) for tt1 in chain(('p\\suc',), self._tts))
         for tt1 in self._tts:
            table.add_row(chain((format_tt(tt1),), (FT_String(format(self.tt_ff[(tt1,tt2)])) for tt2 in self._tts)))
         
         self.output(table)
      
      if (self.esf_len):
         self.out_str('-------- element start frequencies:\n')
         self.output(self.esf.make_ft())
      
      if not (self.debl is None):
         self.out_str('-------- Elements with length {0:d}:\n'.format(self.debl))
         self.output(self.debl_data.make_ft())

      if not (self.ped is None):
         self.out_str('-------- Pre-error token frequencies:\n')
         self.output(self.ped.make_ft())
      
      if not (self.callgraph_fn is None):
         self.out_str('-------- Dumping callgraph:\n')
         self.out_str('--->>> {!r}\n'.format(self.callgraph_fn))
         f_out = open(self.callgraph_fn,'wt',encoding='utf-8')
         f_out.write(self.callgraph.get_dot_data())
         f_out.close()

   def format_tokens_hr(self, tokens, p):
      row = []
      table = FT_Table(max_col_wf=64, cell_spacing=2)
      for tok in tokens:
         if (tok.do_tokendisplay_linebreak() and row):
            table.add_row(row)
            row = []
      
         if (not row):
            if (self.get_offs):
               row = [FT_String('{0:#x}'.format(tok._get_off()))]
            else:
               row = []
         
         row.extend(tok.format_hr(p, color=self.color, dump_raw=self.get_raw, html_order=self._of_html))
      
      if (row):
         table.add_row(row)
      
      return FT_Indented(table, 2)
