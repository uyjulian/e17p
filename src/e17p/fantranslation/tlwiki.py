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

import logging
import re
import urllib.request


class TLWikiPage:
   BASE_URL = 'http://tlwiki.tsukuru.info/index.php?title='
   re_a = re.compile('<a(?:[^>"]*|"[^"]*")*>.*?</a>')
   re_ap = re.compile('<a href="/index.php\?title=([^"]*)" title="([^"]*)">(<[^>]+>)*([^<]*)(<[^>]+>)*</a>')
   
   re_psplit = re.compile('<p>([^<]*?)</p>', re.DOTALL)
   
   logger = logging.getLogger('TLWikiProject')
   log = logger.log
   def __init__(self, name, linktitle=None, linktext=None, uo=None):
      if (uo is None):
         uo = urllib.request.build_opener()
      self.name = name
      self._uo = uo
      self._ltitle = linktitle
      self._ltext = linktext
   
   def __repr__(self):
      return '{}{}'.format(type(self).__name__, (self.name, self._ltitle, self._ltext))
   
   def get_paragraphs(self):
      data = self._fetch_body_data()
      return [p.strip() for p in self.re_psplit.findall(data)]
   
   def get_url(self):
      return (self.BASE_URL + urllib.request.quote(self.name, safe=''))
   
   @staticmethod
   def _parse_http_dt(dt_raw):
      from time import mktime, strptime
      return mktime(strptime(dt_raw, '%a, %d %b %Y %H:%M:%S %Z'))
   
   def stat_page(self):
      from urllib.parse import splittype, splithost
      from http.client import HTTPConnection
      
      url = self.get_url()
      self.log(20, 'Statting page {!r} at {!r}.'.format(self.name, url))
      
      (_, dp) = splittype(url)
      (host, path) = splithost(dp)
      conn = HTTPConnection(host)
      conn.request('HEAD', path)
      res = conn.getresponse()
      lmt_raw = res.getheader('last-modified')
      lm_dts = self._parse_http_dt(lmt_raw)
      
      return lm_dts
   
   def _fetch_body_data(self):
      url = self.get_url()
      self.log(20, 'Fetching data for page {!r} from {!r}.'.format(self.name, url))
      req = self._uo.open(url)
      data = req.read()
      if (isinstance(data, bytes)):
         data = data.decode('utf-8')
      (_, data) = data.split('<!-- start content -->',1)
      (data,_) = data.split('<div class="printfooter">',1)
      return data

   def get_linked_pages(self):       
      data = self._fetch_body_data()
      l_fragments = self.re_a.findall(data)
      
      rv = []
      cls = type(self)
      for line in l_fragments:
         m = self.re_ap.match(line)
         if (m is None):
            continue
         (url, title, _, text, _) = m.groups()
         if (url.startswith('User:')):
            continue
         if (title.split(':',1)[0] in ('Edit section', 'Special', 'Category')):
            continue
         
         rv.append(cls(url, title, text, self._uo))
      return rv
   
   def cache_linked_pages_pp(self):
      from os.path import basename
      from os import stat, utime
      
      page_list = self.get_linked_pages()
      for page in page_list:
         lm = page.stat_page()
         fn = basename(page.name)
         try:
            sdata = stat(fn)
         except OSError:
            lm_cache = 0
         else:
            lm_cache = sdata.st_mtime
         
         if (lm == lm_cache):
            self.log(20, 'Current version for {!r} is already cached; not reretrieving.'.format(page.name))
            continue
         
         lines = page.get_paragraphs()
         self.log(20, 'Write: {!r} -->> {!r}.'.format(page.name, fn))
         f = open(fn, 'w+b')
         f.write(b'\n'.join([l.encode('utf-8') for l in lines]))
         f.close()
         
         utime(fn, (lm, lm))

def _main():
   import os
   import sys
   import optparse
   
   op = optparse.OptionParser()
   op.add_option('-o', '--outdir', default=None, help="Directory to write output to.")
   (opts, args) = op.parse_args()
   
   if not (opts.outdir is None):
      os.chdir(opts.outdir)
   
   logging.getLogger().setLevel(10)
   logging.basicConfig(format='%(asctime)s %(levelno)s %(message)s', stream=sys.stdout)
   
   (name,) = args
   p0 = TLWikiPage(name)
   p0.cache_linked_pages_pp()

if (__name__ == '__main__'):
   _main()
