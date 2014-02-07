#!/usr/bin/env python3
#Copyright 2010 Svein Ove Aas <svein.ove@aas.no>
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

from pygame import display
from pygame import font
import pygame

from math import cos, sin
from time import sleep, time
import logging
import random
import re
import traceback

from .data import get_data_path


def tryInt(s):
    ret = None
    try:
        ret = int(s)
    except:
        pass
    return ret

shader = None

basic_shader = """
#version 120

uniform float fade;
uniform sampler2D tex;

void main() {
  gl_FragColor = vec4(1,1,1,fade) * texture2D(tex, gl_TexCoord[0].xy);
}
"""

flat_shader = """
#version 120

void main() {
  gl_FragColor = gl_Color;
}
"""


class Textbox:
    # Textbox types
    standard = 0
    choice = 1
    auto = 2
    
    def __init__(self, font, typ = standard):
        self.font = font
        self.words = {}
        self.text = [""]
        self.line = 0
        self.dirty = True
        self.voice = None
        self.w = self.h = self.x = self.y = -1

        self.boxw = 0.85 if typ == self.auto else 0.9
        self.boxh = 0 if typ == self.auto else 0.3
        if typ == self.choice:
            self.list = gl.Texture.displayList(-self.boxw, self.boxw,
                                                -self.boxh, self.boxh)
        else:
            self.list = gl.Texture.displayList(-self.boxw, self.boxw,
                                                -0.9, -0.9 + self.boxh * 2)

    def add_voice(self, sound):
        self.voice = sound
        sound.play()

    def __del__(self):
        self.voice and self.voice.stop()
    
    def append(self, text, newlines = False):
        if newlines and self.text[self.line]:
            self.newline()
        for word in text.split():
            image = self.font.render(word, True, (255,255,255))
            self.words[word] = image
        self.text[self.line] += " " + text
        if newlines:
            self.newline()
        self.dirty = True

    def newline(self):
        self.line += 1
        self.text.append("")

    def height(self, w, h):
        # Given a window size, computes used textbox size
        if (self.w, self.h) != (w, h):
            return self.reflow(w, h, auto_recurse=True)
        else:
            return self.used_h

    def reflow(self, w, h, auto_recurse=False):
        # Compute textbox size based on window size
        w = w * self.boxw
        if not self.boxh and not auto_recurse:
            # Box height=auto, so compute it here
            h = self.reflow(w, h, auto_recurse=True)
        else:
            h = h * self.boxh
        if not auto_recurse:
            # Copy the words onto the surface, respecting formatting
            surface = pygame.Surface((w, h), depth = 32, flags = pygame.SRCALPHA)
            # Transparent gray covers the bg image
            surface.fill((50,50,50,192))
        x = y = 5
        line_height = 0
        for line in self.text:
            for word in line.split():
                image = self.words[word]
                # Check for line overflow
                if image.get_width() + x + 5 >= w:
                    if image.get_width() + 10 >= w:
                        print("Horizontal textbox overflow: ", word)
                    x = 5
                    y += line_height + 1
                    line_height = 0
                # Or vertical overflow
                if y >= h:
                    if auto_recurse:
                        h = y+1
                    else:
                        print("Vertical textbox overflow")
                        break
                # 'kay, it should fit.
                if not auto_recurse:
                    surface.blit(image, (x,y))
                x += image.get_width() + 4 # Leave space for a space
                line_height = max(line_height, image.get_height())
            # Create a new line at the end of each append call regardless
            x = 5
            y += line_height + 1
            line_height = 0
        # Create a new texture from the surface
        # TODO: Reuse the old one and blit into it, when doing incremental updates
        if not auto_recurse:
            self.texture = gl.Texture(surface)
            self.dirty = False
        # Return the height actually used
        self.used_h = y
        return y
    
    def display(self, w, h):
        # Regenerate texture
        if (self.w, self.h) != (w, h):
            self.dirty = True
            self.w = w
            self.h = h
        if self.dirty:
            self.reflow(w, h)
        # Display it
        self.texture.bind()
        gl.texEnvi(gl.texture_env, gl.texture_env_mode, gl.replace)
        self.list()
        gl.check()


class CPSTexture:
    class default_viewport:
        @staticmethod
        def get_coords_opengl(unused): return (0,1,0,1)

    def __init__(self, cps, viewport = default_viewport(), pos_data = None):
        self._cps = cps
        width, height, depth, data = cps.get_rgba()
        # Compute GL coordinates based on the 800x600 E17 coordinates
        self.bottom = -1
        self.top    = height / 300 - 1        
        (self.left, self.right) = cps.get_coords_opengl(pos_data)
        print(self.left, self.right, self.bottom, self.top, width, height, depth)

        # Convert data to GL texture
        data = memoryview(data)
        if depth == 24:
            format = "RGB"
        elif depth == 32:
            format = "RGBA"
        else:
            raise ValueError("Color depth {} is unsupported.".format(depth))
        surface = pygame.image.fromstring(data.tobytes(), (width,height), format, True)
        self.tex = gl.Texture(surface, format = gl.bgra)
        self.next_viewport = None
        self.viewport = None
        self.panzoom(viewport)

    def panzoom(self, viewport, delay = 0):
        assert not self.next_viewport
        if delay:
            self.next_viewport = viewport.get_coords_opengl(self._cps)
            self.start_zoom = time()
            self.delay = delay
        else:
            self.viewport = viewport.get_coords_opengl(self._cps)
            self.list = self.tex.displayList(self.left, self.right, self.bottom,
                                             self.top, self.viewport)
        
    def display(self, w, h):
        self.tex.bind()
        if self.next_viewport:
            clock = time() - self.start_zoom
            if clock >= self.delay:
                self.viewport = self.next_viewport
                self.next_viewport = None
                self.list = self.tex.displayList(self.left, self.right, self.bottom,
                                                 self.top, self.viewport)
                self.list()
            else:
                # Interpolate between the two viewports
                fraction = clock / self.delay
                viewport = [old*(1-fraction) + new*fraction for old, new in
                            zip(self.viewport, self.next_viewport)]
                self.tex.immediate(self.left, self.right, self.bottom, self.top, viewport)
                return True
        else:
            self.list()

class SolidColor(CPSTexture):
    class FakeCPS:
        width = 800
        height = 600
        def __init__(self, color):
            self.color = [color[0]*255, color[1]*255, color[2]*255]
        def get_rgba(self):
            return (self.width,self.height,24,bytes(self.color)*800*600)
        def get_base_off_opengl(self):
            return -1
        @staticmethod
        def get_coords_opengl(unused):
            return (-1,1)
    def __init__(self, color):
        CPSTexture.__init__(self, self.FakeCPS(color))


class DecoratorDict(dict):
    def __call__(self, k):
        def set(f):
            if k in self:
                self[k].append(f)
            else:
                self[k] = [f]
            return f
        return set


class PlayPause:
    def __init__(self):
        sz = 0.05
        x = -0.9
        y = 0.85
        with gl.DisplayList(gl.triangles) as self.list:
            gl.color(1,1,1,0.5)
            gl.vertex(x,y)
            gl.vertex(x+sz,y+sz)
            gl.vertex(x,y+sz*2)

    def display(self, w,h):
        self.list()


# Keys to the visuals; they're displayed in sorted order
background = 0
charart = 1
charart_end = 99
textbox = 100
choices = 101
osd = 102

# Other textures
overlay_texidx = 1


class Timeline:
    def __init__(self):
        self.processing = False
        self.slots = {} # slot -> (visual, start, target, delay)
        self.old = {}   # slot -> visual

    def insert(self, visual, slot, delay=0):
        if slot in self.old:
            del self.old[slot]
        if slot in self.slots and delay:
            (old, u1, u2, u3) = self.slots[slot]
            self.old[slot] = old
        self.slots[slot] = (visual, time(), 1, delay)

    def remove(self, slot, delay=0):
        if delay:
            self.set_fade(slot, 0, delay)
        else:
            if slot in self.old:
                del self.old[slot]
            if slot in self.slots:
                del self.slots[slot]

    def set_fade(self, slot, target, delay):
        if slot not in self.slots:
            logging.info("Ignoring fade for unknown slot %s", slot)
        else:
            (visual, u1, u2, u3) = self.slots[slot]
            self.slots[slot] = (visual, time(), target, delay)

    def remove_range(self, start, end, delay=0):
        for slot in list(self.slots):
            if slot >= start and slot <= end:
                del self.slots[slot]

    def get(self, slot):
        (visual, u1, u2, u3) = self.slots[slot]
        return visual

    def display(self, w, h):
        now = time()
        self.processing = False
        to_remove = []
        for slot in sorted(self.slots):
            (visual, start, target, delay) = self.slots[slot]
            if delay:
                period = now - start
                fade = period / delay
                fade = fade if target else 1-fade
                fade = min(max(fade,0),1)
            else:
                fade = target
            if fade < 1:
                self.processing = True
                if slot in self.old:
                    shader["fade"] = 1
                    self.old[slot].display(w, h)
            if fade:
                shader["fade"] = fade
                self.processing = visual.display(w, h) or self.processing
            else:
                to_remove.append(slot)
        for slot in to_remove:
            self.remove(slot)


def build_shader(source, w, h):
    (source, unused) = re.subn("SCREENX", str(w), source)
    (source, unused) = re.subn("SCREENY", str(h), source)
    return gl.Shader(fragment=[source])


class Delay:
    def __init__(self, delay):
        self.delay = delay
    def __enter__(self):
        self.start = time()
    def __exit__(self, *unused):
        sleep(max(0, self.start + self.delay - time()))


class VN_Renderer:
    event_functions = DecoratorDict()
    backlog_functions = DecoratorDict()
    
    def __init__(self):
        pygame.init()
        self.input_handlers = []
        self.fast_forward = False
        self.display_textboxes = True

    __csn = 'VN pygame frontend options'
    def init_frontend_from_config(self, cs):
        scs = cs.get_scs(self.__csn)
        self.init_frontend(**scs.get_settings())
    
    @classmethod
    def add_config(cls, cs):
        ace = cs.get_scs(cls.__csn).add_ce
        ace('sound_playback', longopt='nosound', default=True, const=False)
        ace('movie_playback', longopt='nomovie', default=True, const=False)
        super().add_config(cs)
    
    def init_frontend(self, sound_playback, movie_playback):
        self._play_sounds = sound_playback
        self._play_movies = movie_playback

    def run(self):
        self.pb_done = False
        self.font = font.Font(get_data_path('fonts/font.ttf'), 16)
        self.choicefont = font.Font(get_data_path('fonts/font.ttf'), 18)
        self.timeline = Timeline()
        self.auto_mode = False
        self.auto_deadline = None
        self.refootprint(pygame.event.Event(pygame.VIDEORESIZE, w=800, h=600))
        gl.enable(gl.blend)
        gl.blendFunc(gl.src_alpha, gl.one_minus_src_alpha)
        gl.check()
 
        while not self.pb_done:
            with Delay(1/60):
                self.handle_events(self.event_functions)
                if ((not self.input_handlers) or
                    (self.auto_mode and self.auto_deadline and self.auto_deadline <= time())):
                    if ((not self.pb_done) and
                        (not (self.timeline.processing and rc == self.ptrc.graphics_op))):
                        rc = self.process_tokens()
                        self.pb_done = (rc == self.ptrc.end)
                    if (not self.fast_forward and rc != self.ptrc.graphics_op and
                        not self.input_handlers):
                        self.input_handlers.append(lambda x: None)
                self.display()

    def handle_events(self, event_dict):
        while not self.pb_done:
            event = pygame.event.poll()
            if event.type == pygame.NOEVENT:
                break
            elif event.type in event_dict:
                for fun in event_dict[event.type]:
                    if fun(self, event): break
            else:
                break

    def new_choice(self, choice):
        choicebox = Textbox(self.choicefont, Textbox.choice)
        i = 0
        for option in choice.options:
            i += 1
            choicebox.append("%d: %s\n" % (i, option.text))
            choicebox.newline()
        self.timeline.insert(choicebox, choices)
        def chooser(ev):
            if ev.type == pygame.KEYDOWN:
                digit = tryInt(ev.unicode)
                if digit and digit <= len(choice.options):
                    choice.choose_option(choice.options[digit-1])
                    self.timeline.remove(choices)
                    return
            return True
        self.input_handlers.append(chooser)
        self.auto_deadline = 0


    def new_textblock(self, tb):
        box = Textbox(self.font)
        self.timeline.insert(box, textbox)
        total = 0
        for line in tb.text:
            box.append(line, line and line[0] == '[' and line[-1] == ']')
            total += len(line)
        self.auto_deadline = total / 30 + 2
        if tb.voice_data and self._play_sounds:
            try:
                sound = tb.voice_data.get_pygame_sound()
            except pygame.error as e:
                logging.error(e)
            else:
                box.add_voice(sound)
                self.auto_deadline = sound.get_length() + 0.3
        self.auto_deadline += time()

    def display_bgi(self, chunk, viewport, delay):
        print("display bgi")
        if self.fast_forward: delay = 0
        img = chunk.get_img()
        visual = CPSTexture(img, viewport = viewport)
        self.timeline.insert(visual, background, delay)

    def panzoom_bgi(self, viewport, delay):
        # print("pan/zoom")
        if self.fast_forward: delay = 0
        self.timeline.get(background).panzoom(viewport, 0 if self.fast_forward else delay)

    def display_charart(self, chunk, slot, x0, delay):
        # print("charart", slot, delay)
        if self.fast_forward: delay = 0
        visual = CPSTexture(chunk.get_img(), pos_data = x0)
        self.timeline.insert(visual, charart, delay)
    
    def clear_charart(self, slot, delay):
        # print("clear charart", slot, delay)
        if self.fast_forward: delay = 0
        self.timeline.remove(charart+slot, delay)

    def clear_charart_all(self, delay):
        # print("clear all charart")
        if self.fast_forward: delay = 0
        self.timeline.remove_range(charart, charart_end, delay)

    def fade_textbox(self, delay):
        # print("fade textbox")
        if self.fast_forward: delay = 0
        self.timeline.set_fade(textbox, 0, delay)

    def unfade_textbox(self, delay):
        # print("unfade textbox")
        if self.fast_forward: delay = 0
        self.timeline.set_fade(textbox, 1, delay)

    def fade_bg_fill(self, color, delay):
        # print("fade bg fill")
        if self.fast_forward: delay = 0
        visual = SolidColor(color)
        self.timeline.insert(visual, background, delay)

    def display(self):
        gl.clear(gl.color_buffer_bit)
        self.timeline.display(self.w, self.h)
        if True: # If we should display a sunlight overlay
            idx = int((time() * 10) % 512)
            self.sunlight[idx].bind()
            gl.blendFunc(gl.one, gl.one)
            self.sunlight_dl()
            gl.blendFunc(gl.src_alpha, gl.one_minus_src_alpha)
        display.flip()

    def play_movie(self, file):
        import subprocess
        # TODO(svein): Make a proper movie player of this
        if (self._play_movies):
           subprocess.Popen(["mplayer","-quiet","-"], stdin=file)
        else:
           self.log(20, 'Skipping movie: {!r}.'.format(file))

    @backlog_functions(pygame.VIDEORESIZE)
    @event_functions(pygame.VIDEORESIZE)
    def refootprint(self, ev):
        # Clear the window
        # display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        # display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
        self.screen = display.set_mode((ev.w, ev.h),
                                       pygame.OPENGL | pygame.RESIZABLE | pygame.DOUBLEBUF)
        global gl
        from . import opengl as gl
        gl.viewport(0, 0, ev.w, ev.h)
        gl.clear(gl.color_buffer_bit)
        # Compute a 4:3 viewport
        sz = min(ev.w*3, ev.h*4)
        self.w = sz // 3
        self.h = sz // 4
        offx = (ev.w - self.w) // 2
        offy = (ev.h - self.h) // 2
        gl.viewport(offx, offy, self.w, self.h)
        self.basic_shader = build_shader(basic_shader, self.w, self.h)
        self.sunlight = gl.sunlightTextures(128, 128, 512)
        self.sunlight_dl = self.sunlight[0].displayList(-1, 1, -1, 1)
        global shader
        shader = self.basic_shader
        shader.attach()
        shader.seti("tex", 0)
        self.backlog_dirty = True

    @backlog_functions(pygame.QUIT)
    @event_functions(pygame.QUIT)
    def set_quit(self, ev):
        self.pb_done = True

    @event_functions(pygame.KEYDOWN)
    def handle_keys(self, ev):
        if ev.key == pygame.K_a:
            self.auto_mode = not self.auto_mode
            if self.auto_mode:
                self.timeline.insert(PlayPause(), osd, 0.3)
            else:
                self.timeline.remove(osd, 0.3)
            return not self.auto_mode
        elif ev.key == pygame.K_l:
            choice = self.backlog_loop()
            if choice != None:
                print("Jumping to ", choice)
                self.jump_back(choice)
            return True

    @event_functions(pygame.KEYDOWN)
    @event_functions(pygame.KEYUP)
    def handle_toggles(self, ev):
        val = ev.type == pygame.KEYDOWN
        if ev.key == pygame.K_LCTRL:
            self.fast_forward = val
        elif ev.key == pygame.K_LALT:
            self.display_textboxes = not val
            return True

    @backlog_functions(pygame.KEYDOWN)
    @backlog_functions(pygame.MOUSEBUTTONDOWN)
    @event_functions(pygame.KEYDOWN)
    @event_functions(pygame.MOUSEBUTTONDOWN)
    def handle_input(self, ev):
        if self.input_handlers:
            if not self.input_handlers[-1](ev):
                self.input_handlers = self.input_handlers[:-1]

    def backlog_loop(self):
        backlog_cache = {}
        running = True
        selected = None
        self.backlog_dirty = True
        playing = False
        # Figure out the starting index
        star = SeleStar()
        index = len(self.backlog)-1 #TODO
        # Attach an input handler
        def go_up():
            nonlocal index
            if index > 0:
                index -= 1
                self.backlog_dirty = True
        def go_down():
            nonlocal index
            if index < len(self.backlog) - 1:
                index += 1
                self.backlog_dirty = True
        def input_handler(ev):
            nonlocal running
            nonlocal selected
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_UP:
                    go_up()
                elif ev.key == pygame.K_DOWN:
                    go_down()
                elif ev.key == pygame.K_ESCAPE or ev.key == pygame.K_q:
                    running = False
                    return False
                elif ev.key == pygame.K_RETURN:
                    running = False
                    selected = index
                    return False
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 4:
                    go_up()
                elif ev.button == 5:
                    go_down()
            return True
        self.input_handlers.append(input_handler)
        # Backlog showing loop
        def pxToGL(y):
            return -((y / self.h) * 2 - 1)
        while running and not self.pb_done:
            with Delay(1/60):
                self.handle_events(self.backlog_functions)
                selected = index
                gl.clear(gl.color_buffer_bit)
                shader["fade"] = 1
                # Draw a suitable background
                # Render backlog
                y = self.h / 20
                for i in range(index, len(self.backlog)):
                    if i not in backlog_cache:
                        box = Textbox(self.font, Textbox.auto)
                        for line in self.backlog[i].text:
                            box.append(line)
                        backlog_cache[i] = box
                    box = backlog_cache[i]
                    height = box.height(self.w, self.h)
                    if y + height >= self.h:
                        break
                    if self.backlog_dirty:
                        box.list = gl.Texture.displayList(-box.boxw, box.boxw, pxToGL(y + height), pxToGL(y))
                    if i == selected:
                        star_pos = (-box.boxw - 0.07, (pxToGL(y+height) - pxToGL(y)) / 2 + pxToGL(y), 0)
                    y += height
                    box.display(self.w, self.h)
                self.backlog_dirty = False
                # Render a selestar by the selected log
                now = time()
                star.render(scale=(0.05,0.05,0.05),
                            translate=star_pos,
                            rotate=((now*10)%360, cos(now/3),sin(now/5), cos(now/2)))
                display.flip()
        return selected


class SeleStar:
    def __init__(self):
        self.shader = gl.Shader(fragment=[flat_shader])
        with gl.DisplayList(gl.triangles) as self.list:
            height = 0.8660254037844386
            left  = (-1, -height, 0)
            right = (1, -height, 0)
            top   = (0, height, 0)
            def rnd():
                gl.color(random.random()/2, random.random()/2, random.random(), 0.7)
            def tetrahedron(z):
                point = (0, 0, z)
                rnd()
                gl.vertex(*left)
                gl.vertex(*right)
                gl.vertex(*top)
                rnd()
                gl.vertex(*left)
                gl.vertex(*top)
                gl.vertex(*point)
                rnd()
                gl.vertex(*top)
                gl.vertex(*right)
                gl.vertex(*point)
                rnd()
                gl.vertex(*left)
                gl.vertex(*right)
                gl.vertex(*top)
            tetrahedron(height)
            tetrahedron(-height)

    def render(self, translate=None, scale=None, rotate=None):
        with gl.pushedMatrix():
            self.shader.attach()
            translate and gl.translate(*translate)
            scale     and gl.scale(*scale)
            rotate    and gl.rotate(*rotate)
            gl.enable(gl.multisample)
            self.list()
            gl.disable(gl.multisample)
            shader.attach()
