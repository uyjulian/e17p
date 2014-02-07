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


# ---------------------------------------------------------------- Sample noninteractive text player
class DummyTextPlayer:
   """Simple VN player sample UI."""
   def __init__(self, default_ack_delay=0):
      self.default_ack_delay = default_ack_delay
   
   __csn = 'VN text dummy frontend options'
   @classmethod
   def add_config(cls, cs):
      super().add_config(cs)
      ace = cs.get_scs(cls.__csn).add_ce
      ace('ACK delay', shortopt='-d', longopt='--ack-delay', default=0, dest='default_ack_delay', converter=float, metavar='SECONDS', help='User text acknowledgement delay')
   
   @classmethod
   def _get_settings(cls, cs):
      rv = super()._get_settings(cs)
      rv.update(cs.get_scs(cls.__csn).get_settings())
      return rv
   
   def init_frontend_from_config(self, cs):
      pass
   def display_bgi(self, chunk, viewport, delay):
      """Display background image by chunk and initial viewport."""
      img = chunk.get_img()
      coords = viewport.get_coords_opengl(img)
   def panzoom_bgi(self, viewport, delay):
      """Pan/zoom over background image."""
      pass
   def fade_bg_fill(self, color, delay):
      """Fade background to solid-color image."""
      pass
   def display_charart(self, chunk, slot, x0, charart):
      """Display character art by slot and chunk."""
      img = chunk.get_img()
      pass
   def clear_charart(self, slot, delay):
      """Stop displaying a character art image."""
      pass
   def clear_charart_all(self, delay):
      """Stop displaying all character art images."""
      pass
   def new_textblock(self, tb):
      """Display new textblock."""
      pass
   def new_choice(self, choice):
      """Pose choice to user."""
      choice.choose_option(choice.options[0])
   def play_movie(self, f):
      """Play movie file."""
      pass
   def fade_textbox(self, delay=None):
      """Remove textbox."""
      pass
   def unfade_textbox(self, delay=None):
      """Redisplay textbox."""
      pass
   def run(self, ack_delay=None, out=print):
      from time import sleep
      self.cp = False
      
      if (ack_delay is None):
         ack_delay = self.default_ack_delay
      
      rc = None
      try:
         while (rc != self.ptrc.end):
            rc = self.process_tokens()            
            sleep(ack_delay)
      except Exception as exc:
         out(self.get_pos_hr())
         raise
