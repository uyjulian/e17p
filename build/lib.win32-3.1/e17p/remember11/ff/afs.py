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

# Parser for R11 AFS files.
import struct
from .compression import R11PackedDataRefFile, R11UnpackError
from ...base.text_fmt import *

# -------------------------------------------------------------------------------- parser DS
class AFSAuxData(bytes):
   def get_bip_off_shift(self):
      v = self[0]
      if not (v & 0x2):
         return 4
      if (v & 0x1):
         return 4
      return 2
      
class _AFSChunk:
   def __init__(self, fn, dref, aux_data):
      self.fn = fn
      self.dref = dref
      self.aux_data = aux_data
   
   @classmethod
   def build_from_similar(cls, chunk):
      return cls(chunk.fn, chunk.dref, chunk.aux_data)
   
   def __iter__(self):
      """Ugly hack to make old interfaces happy."""
      yield self.fn
      yield self.dref
      yield self.aux_data
   
   md_table_efmt = '32s16s'
   md_table_elen = struct.calcsize(md_table_efmt)
   def get_md_table_entry(self):
      return struct.pack(self.md_table_efmt, self.fn, self.aux_data)

   def _get_afs_data(self):
      return self.dref.get_data()
   
   def _write_afs_data(self, f):
      d = self._get_afs_data()
      l = f.write(d)
      if (l != len(d)):
         raise ValueError('Only wrote {}/{} bytes to {}.'.format(l, len(d), f))
      return l

class _RepackingAFSChunk(_AFSChunk):
   def _get_afs_data(self):
      try:
         data = self.dref.repack_nullcompression()
      except R11UnpackError:
         data = dref.get_data()
      return data

class AFSParser:
   def __init__(self, chunks):
      self._chunks = chunks
      self._rebuild_chunk_map()
   
   def _rebuild_chunk_map(self):
      self._chunk_map = dict((c.fn, c) for c in self._chunks)
   
   def filter_chunks(self, ccls):
      self._chunks = [ccls(c) for c in self._chunks]
      self._rebuild_chunk_map()
   
   def __len__(self):
      return len(self._chunks)
   
   def __iter__(self):
      for c in self._chunks:
         yield c
   
   off_table_efmt = '<LL'
   off_table_elen = struct.calcsize(off_table_efmt)
   @classmethod
   def build_from_file(cls, f):
      # AFS files start with a static 4 byte preamble, followed by a LE u32 specifying the number of contained chunks.
      preamble = f.read(4)
      if (preamble != b'AFS\x00'):
         raise ValueError('Unexpected preamble {0!r}.'.format(preamble))
      fc_data = f.read(4)
      (fc,) = struct.unpack(b'<L', fc_data)
      
      # Read chunk offset/length table
      # Chunk offsets are presumably relative to beginning of file.      
      # Chunk metadata entries look like the following:
      # - chunk data offset (32bit LE uint)
      # - chunk data length (32bit LE uint)
      files = []
      for i in range(fc):
         clen_data = f.read(8)
         (coff, clen) = struct.unpack(cls.off_table_efmt, clen_data)
         
         dref = R11PackedDataRefFile(f, coff, clen)
         files.append(dref)
      
      chunks = []
      if (files):
         off_fd_end = coff + clen
         off_fn_list = off_fd_end
         # Round up to next kilobyte
         off_fn_l_m = (off_fn_list % 2048)
         #print(off_fn_list, off_fn_l_m, off_fn_list+2048-off_fn_l_m)
         if (off_fn_l_m):
            off_fn_list += 2048-off_fn_l_m
         
         f.seek(off_fn_list)
         for i in range(fc):
            fnd = f.read(48)
            fn = fnd[:32].rstrip(b'\x00')
            chunk = _AFSChunk(fn, files[i], AFSAuxData(fnd[32:]))
            chunks.append(chunk)
      
      td = f.read()
      if (td.rstrip(b'\x00') != b''):
         raise ValueError('Parser failure: Unexpected trailing data {0!a} ({1} bytes.).'.format(td, len(td)))
      
      return cls(chunks)
   
   @staticmethod
   def align_chunk(off):
      """AFS file chunks are aligned on 2048byte boundaries."""
      return ((off + 2047) >> 11) << 11
   
   def write_to_file(self, f):
      off_0 = f.tell()
      fc = len(self._chunks)
      hdr = struct.pack('<4sL', b'AFS\x00', fc)
      
      # We need to reserve space for the metadata table offset table entry here, hence fc + 1.
      otl = (fc + 1) * self.off_table_elen
      off_data = [None]*fc
      
      body_off = self.align_chunk(len(hdr) + otl)
      off = body_off
      for (i,c) in enumerate(self._chunks):
         off = self.align_chunk(off)
         f.seek(off_0 + off)
         l = c._write_afs_data(f)
         off_data[i] = (off,l)
         off += l

      mdt_off = self.align_chunk(off)
      f.seek(off_0 + mdt_off)
      for c in self._chunks:
         f.write(c.get_md_table_entry())
      
      off_end = f.tell()
      mdt_len = off_end - mdt_off
      
      f.seek(off_0)
      f.write(hdr)
      for (coff, clen) in off_data:
         f.write(struct.pack(self.off_table_efmt, coff, clen))
      
      # The metadata table data isn't just added to the end of the offset table, it's instead always written right before its
      # (aligned) end.
      
      # First let's check that we haven't written more than we expected to for some reason ...
      if ((f.tell() - off_0) > (body_off-8)):
         raise ValueError('Off table overrun: end is at {}/{}.'.format(f.tell()-off_0, body_off-8))
      
      f.seek(body_off - 8)
      f.write(struct.pack(self.off_table_efmt, mdt_off, mdt_len))
      
      if (off_end % 2048):
         off_end = self.align_chunk(off_end)
         f.seek(off_end-1)
         f.write(b'\x00')
      
      return (off_end - off_0)

def _main():
   import os
   import os.path
   import sys
   import optparse
   from io import BytesIO
   
   op = optparse.OptionParser()
   op.add_option('-o', '--outdir', dest='outpath', default='./', action='store', metavar='PATH', help='Path to write output to.')
   op.add_option('-r', '--dump-raw', dest='dump_raw', default=False, action='store_true', help='Dump raw files.')
   op.add_option('-b', '--list-bip-chunks', dest='list_bip', default=False, action='store_true', help='List BIP file chunks.')
   op.add_option('-s', '--dump-bip-chunks', dest='dump_bip', default=False, action='store_true', help='Dump BIP file chunks to individual files.')
   op.add_option('-u', '--unpack', default=False, action='store_true')
   op.add_option('--ar', dest='rafs', default=False, action='store_true', help='Repack contents into new AFS archive file.')
   op.add_option('--ar-rc-nc', dest='rafs_rc_nc', default=False, action='store_true', help="On repacking, repack compressed chunks using nullcompression.")
   (opts, args) = op.parse_args()
   
   unpack = opts.unpack
   
   rddir = opts.outpath.encode('ascii')
   split_bip = opts.list_bip or opts.dump_bip
   
   if (split_bip):
      from .bip import BIPFile
   
   for fn in args:
      f = open(fn, 'rb')
      lp = AFSParser.build_from_file(f)
      
      for ((cfn, dref, ad),i) in zip(lp,range(len(lp))):
         ofn = cfn
         unpacked = False
         #data = b''
         try:
            if (unpack):
               data = dref.unpack()
               unpacked = True
            else:
               data = dref.get_data()
         except R11UnpackError:
            data = dref.get_data()
         
         print('File: {:20} ({:10} ->{:10} bytes; aux data {!a}) [{}]'.format(cfn, dref.get_size(), len(data), hexs(ad), int(unpacked)))
         
         if (unpacked):
            ofn += b'.d'
         
         opath = os.path.join(rddir, ofn)
         
         if (opts.dump_raw):
            of = open(opath, 'wb')
            of.write(data)
            of.close()
         
         if (split_bip and cfn.endswith(b'BIP')):
            bfio = BytesIO(data)
            bf = BIPFile.build_from_file(bfio, bip_off_shift=ad.get_bip_off_shift())
            if (opts.list_bip):
               bf.dump_chunks_hr()
            if (opts.dump_bip):
               bf.dump_chunk_files(opath)
      
      if (opts.rafs):
         if (opts.rafs_rc_nc):
            lp.filter_chunks(_RepackingAFSChunk.build_from_similar)
         
         ofn = fn + '.repack'
         print('Writing new AFS file to {!r}.'.format(ofn))
         of = open(ofn, 'wb')
         l = lp.write_to_file(of)
            

if (__name__ == '__main__'):
   _main()
