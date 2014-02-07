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

from itertools import chain

# ---------------------------------------------------------------- Formatted Text structures
class _FT_GData:
   def __init__(self, wrappee, fmt):
      self._fmt = fmt
      self._wrappee = wrappee

class FT_GStr(_FT_GData):
   def format_ansi(self):
      return self._fmt.format_ansi(self._wrappee)
   
   def __len__(self):
      return len(self._wrappee)
   
   def len_plain(self):
      return self._wrappee.len_plain()
   
   def format_html(self, d):
      return self._fmt.format_html(self._wrappee, d)

class FT_String(str):
   def format_ansi(self):
      return self
   
   def format_html(self, d):
      from xml.sax.saxutils import escape
      return escape(self).replace('\n', '<br />')
   
   def len_plain(self):
      return len(self)

class FT_TableRow(tuple):   
   def format_html(self, d):
      c = max(len(e) for e in self)
      return ''.join(chain(('<tr>\n',), (chain(*(('<td>', e.format_html(d) ,'</td>\n') for e in self))), ('</tr>',)))

class FT_Table(list):
   def __new__(cls, *args, **kwargs):
      return super().__new__(cls, *args)
   
   def __init__(self, *args, max_col_wf=None, cell_spacing=1):
      super().__init__(*args)
      self._max_col_wf = max_col_wf
      self._cell_spacing = cell_spacing
   
   def format_ansi(self):
      from itertools import zip_longest
      cell_lengths = tuple(tuple(c.len_plain() for c in r) for r in self)
      col_widths = list(max(l) for l in zip_longest(*cell_lengths, fillvalue=0))
      
      mcw = self._max_col_wf
      if not (mcw is None):
         col_widths = tuple(min(w, mcw) for w in col_widths)
      
      rv = []
      for row in self:
         for (w,cell) in zip(col_widths,row):
            l = cell.len_plain()
            pad_len = max(w-l,0)
            rv.append(cell.format_ansi())
            rv.append(' '*(pad_len+self._cell_spacing))
         
         rv.append('\n')
      
      return ''.join(rv)
   
   def format_html(self, d):
      return '\n'.join(chain(('<table border=1>',), (e.format_html(d) for e in self), ('</table>',)))

   def add_row(self, *args, **kwargs):
      rv = FT_TableRow(*args, **kwargs)
      self.append(rv)
      return rv
   
   def len_plain(self):
      return sum(r.len_plain() for r in self)

class FT_Indented:
   def __init__(self, wrappee, depth):
      self._wrappee = wrappee
      self._depth = depth
   
   def _get_ansi_lines(self):
      prefix = '{:{}}'.format('', self._depth)
      for line in self._wrappee.format_ansi().split('\n'):
         if (line):
            line = prefix + line
         yield line
   
   def len_plain(self):
      return self._wrappee.len_plain()
   
   def format_html(self, d):
      # TODO: Add actual indenting here?
      return self._wrappee.format_html(d)
   
   def format_ansi(self):
      return '\n'.join(self._get_ansi_lines())

# ---------------------------------------------------------------- Text format structures
class _TF_None:
   def __init__(self, name):
      self.name = name
   
   def format_html(self, data, d):
      return data.format_html(d)
   
   def format_ansi(self, text):
      return text.format_ansi()

class _TF_Color:
   def __init__(self, name, ansi_cc, html_cc):
      self.name = name
      self._ansi_cc = ansi_cc
      self._html_cc = html_cc

   def __repr__(self):
      return '{0}.{1}'.format(_AnsiFormatCode.__module__, self.name)
   
   def __str__(self):
      return self.name
   
   def format_html(self, data, doc):
      doc.add_class(self.name, 'color: #{:06x};'.format(self._html_cc))
      return '<span class="{}">{}</span>'.format(self.name, data.format_html(doc))
   
   def format_ansi(self, text):
      if (isinstance(text, bytes)):
         cseq = b''.join((b'\x1b[', self._ansi_cc.encode('ascii'), b'm'))
         rv = b''.join((cseq, text.replace(b'\n', b'\n' + cseq), b'\x1b[m'))
      else:
         cseq = '\x1b[{}m'.format(self._ansi_cc)
         rv = '{}{}\x1b[m'.format(cseq,text.replace('\n','\n' + cseq))
      return rv

# ---------------------------------------------------------------- document structures
class FTDBase:
   def add_str(self, s):
      return self.add_data(FT_String(s))

class FTD_HTML(FTDBase):
   HTML_HEADER = '''
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>{title}</title>
    <style type="text/css">
        body {{
          background-color:#000000;
          font-family:monospace;
          color:#FFFFFF;
        }}
        table {{
          border-width:1px;
          border-style:solid;
          border-color:#444444;
          border-collapse:collapse;
          empty-cells:hide;
          white-space:nowrap;
        }}
        td {{
           padding-left:32px;
        }}
        {css_data}
    </style>
  </head>
  <body>
'''
   HTML_FOOTER = '''  </body>
</html>
'''
   def __init__(self, title=''):
      self._title = title
      self._classes = {}
      self._body_data = []
   
   def add_class(self, name, css):
      self._classes[name] = css
   
   def add_data(self, d):
      self._body_data.append(d)
   
   def _get_css_data(self):
      from xml.sax.saxutils import escape
      return ''.join('.{} {{{}}}\n'.format(key, val) for (key, val) in self._classes.items())
   
   def write_output(self, out):
      from xml.sax.saxutils import escape
      bd_out = []
      for bdf in self._body_data:
         bd_out.append(bdf.format_html(self))
         bd_out.append('\n')
      
      rv = out(self.HTML_HEADER.format(title=escape(self._title), css_data=escape(self._get_css_data())))
      for d in bd_out:
         rv += out(d)
      
      rv += out(self.HTML_FOOTER)
      return rv

class FTD_ANSIIncremental(FTDBase):
   def __init__(self, out):
      self._out = out
   
   def add_data(self, d):
      self._out(d.format_ansi())
   
   def write_output(self, out):
      pass

def __init():
   codes = (
      ('TFC_RED_D', '0;31', 0x800000),
      ('TFC_GREEN_D', '0;32', 0x008000),
      ('TFC_YELLOW_D', '0;33', 0x808000),
      ('TFC_BLUE_D', '0;34', 0x0000FF),
      ('TFC_PURPLE_D', '0;35', 0x800080),
      ('TFC_CYAN_D', '0;36', 0x008080),
      ('TFC_GREY', '0;37', 0x808080),
      ('TFC_GREY_D', '1;30', 0x202020),
      ('TFC_RED', '1;31', 0xFF5454),
      ('TFC_GREEN', '1;32', 0x00FF00),
      ('TFC_YELLOW', '1;33', 0xFFFF00),
      ('TFC_BLUE', '1;34', 0x5454FF),
      ('TFC_PURPLE', '1;35', 0xFF00FF),
      ('TFC_CYAN', '1;36', 0x00FFFF)
   )
   gv = globals()
   for args in codes:
      acc = _TF_Color(*args)
      gv[args[0]] = acc
   gv['TF_NONE'] = _TF_None('TF_NONE')
__init()

