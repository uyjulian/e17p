#!/usr/bin/env python3
# Copyright (C) 2010 Svein Ove Aas <svein.ove@aas.no>
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

# Minimalistic OpenGL binding for E17P
# 

from ctypes import *
from contextlib import contextmanager
from platform import system

import logging
import pygame

if system() == "Windows":
    opengl = windll.opengl32
    glu = windll.glu32
    gpa = opengl.wglGetProcAddress
    gpa.argtypes = [c_char_p]
    def getter(name, args):
        glf = gpa(name)
        if glf == 0:
            try:
                func = getattr(opengl, name)
            except AttributeError:
                func = getattr(glu, name)
            func.argtypes = args
            return func
        else:
            return WINFUNCTYPE(c_int, *args)(glf)
    glget = getter
else:
    opengl = CDLL("libGL.so")
    glu = CDLL("libGLU.so")
    def getter(name, args):
        try:
            func = getattr(opengl, name)
        except AttributeError:
            func = getattr(glu, name)
        func.argtypes = args
        return func
    glget = getter

# Constants (from gl.h)
from .constants import *
# Effects
from . import _effects

# GL types
enum = c_uint
floats = lambda n: [c_float]*n
sizei = c_int

# Parameters
enable = glget("glEnable", [enum])
disable = glget("glDisable", [enum])
hint = glget("glHint", [enum]*2)
blendFunc = glget("glBlendFunc", [enum, enum])

# Primitives
begin = glget("glBegin", [enum])
end = glget("glEnd", [])

@contextmanager
def immediate(e):
    begin(e)
    yield
    end()

@contextmanager
def pushedMatrix():
    glPushMatrix()
    yield
    glPopMatrix()

glPushmatrix = glget("glPushMatrix", [])
glPopMatrix = glget("glPopMatrix", [])
rotate = glget("glRotatef", floats(4))
translate = glget("glTranslatef", floats(3))
scale = glget("glScalef", floats(3))
_color = glget("glColor4f", floats(4))

def color(r, g, b, a=1.0):
    _color(r, g, b, a)

vertex3 = glget("glVertex3f", floats(3))

def vertex(v1, v2, v3 = 0):
    vertex3(v1,v2,v3)

texCoord = glget("glTexCoord2f", floats(2))
clear = glget("glClear", [c_uint])

# Display lists
genLists = glget("glGenLists", [sizei])
newList = glget("glNewList", [c_uint, enum])
endList = glget("glEndList", [])
callList = glget("glCallList", [c_uint])
delLists = glget("glDeleteLists", [c_uint, sizei])

class DisplayList:
    def __init__(self, type):
        self.list = genLists(1)
        self.type = type

    def __enter__(self):
        newList(self.list, compile)
        self.type and begin(self.type)
        return self

    def __exit__(self, a, b, c):
        self.type and end()
        endList()

    def __call__(self):
        callList(self.list)

    def __del__(self):
        delLists(self.list, 1)


# Textures
_genTextures = glget("glGenTextures", [sizei, POINTER(c_uint)])
        
def genTextures(n):
    arr = (c_uint * n)()
    _genTextures(n, arr)
    return arr

def genTexture():
    return genTextures(1)[0]

_delTextures = glget("glDeleteTextures", [sizei, POINTER(c_uint)])

def delTextures(arr):
    carr = (c_uint * len(arr))(*arr)
    _delTextures(len(arr), carr)

def delTexture(t):
    delTextures([t])

_bindTexture = glget("glBindTexture", [enum, c_uint])
_texParameteri = glget("glTexParameteri", [enum, enum, c_int])
_texParameterf = glget("glTexParameterf", [enum, enum, c_float])
_texImage2D = glget("glTexImage2D", [enum, c_int, c_int, sizei, sizei, c_int, enum, enum, c_void_p])
_texImage3D = glget("glTexImage3D", [enum, c_int, c_int, sizei, sizei, sizei, c_int, enum, enum, c_void_p])
activeTexture = glget("glActiveTexture", [enum])
texEnvi = glget("glTexEnvi", [enum, enum, c_int])

class TextureWrapper:
    def __init__(self, tex):
        self.t = tex

    def __del__(self):
        delTexture(self.t)

    def bind(self, unit = 0):
        activeTexture(texture0 + unit)
        _bindTexture(texture_2d, self.t)

    @staticmethod
    def displayList(left, right, bottom, top, viewport = (0,1,0,1)):
        with DisplayList(None) as display_list:
            Texture.immediate(left, right, bottom, top, viewport)
        return display_list

    @staticmethod
    def immediate(left, right, bottom, top, viewport):
        begin(triangles)
        texCoord(viewport[0], viewport[2])
        vertex(left, bottom)
        texCoord(viewport[1], viewport[2])
        vertex(right, bottom)
        texCoord(viewport[0], viewport[3])
        vertex(left, top)
        texCoord(viewport[0], viewport[3])
        vertex(left, top)
        texCoord(viewport[1], viewport[3])
        vertex(right, top)
        texCoord(viewport[1], viewport[2])
        vertex(right, bottom)
        end()

class Texture(TextureWrapper):
    def __init__(self, surface, internal_format = rgba, format = rgba,
                 width = None, height = None):
        check()
        tex = genTexture()
        TextureWrapper.__init__(self, tex)
        if width or height:
            textureData = surface
        else:
            textureData = pygame.image.tostring(surface, "RGBA", True)
            width = surface.get_width()
            height = surface.get_height()
        target = texture_2d
        self.bind()
        _texParameteri(target, texture_mag_filter, linear)
        _texParameteri(target, texture_min_filter, linear)
        _texImage2D(target, 0, internal_format, width, height, 0, format, unsigned_byte,
                    textureData)
        check()

        
# Camera transformations and viewport
viewport = glget("glViewport", [c_int, c_int, sizei, sizei])
ortho2D = glget("gluOrtho2D", [c_double]*4)

# Matrixes
pushMatrix = glget("glPushMatrix", [])
popMatrix = glget("glPopMatrix", [])
matrixMode = glget("glMatrixMode", [enum])
_loadMatrix = glget("glLoadMatrixf", [POINTER(c_float)])

def loadMatrix(matrix):
    arr = (c_float * 16)()
    arr[:] = matrix
    _loadMatrix(arr)


# Errors
errors = {
    0x0: "No error",
    0x500: "Invalid enum",
    0x501: "invalid value",
    0x502: "invalid operation",
    0x503: "Stack overflow",
    0x504: "Stack underflow",
    0x505: "Out of memory",
    0x8031: "Table too large"}

_getError = glget("glGetError", [])

class OpenGLError(BaseException):
    def __init__(self, val):
        BaseException.__init__(self)
        if val in errors:
            self.message = errors[val]
        else:
            self.message = "Unknown error: 0x%x" % val
        print(self.message)

def check():
    err = _getError()
    if err:
        raise OpenGLError(err)

# Shaders

glCreateProgram = glget("glCreateProgram", [])
glCreateShader = glget("glCreateShader", [enum])
glShaderSource = glget("glShaderSource", [c_uint, sizei, POINTER(c_char_p), POINTER(c_int)])
glCompileShader = glget("glCompileShader", [c_uint])
glAttachShader = glget("glAttachShader", [c_uint]*2)
glLinkProgram = glget("glLinkProgram", [c_uint])
glDeleteProgram = glget("glDeleteProgram", [c_uint])
glDeleteShader = glget("glDeleteShader", [c_uint])
glGetProgramInfoLog = glget("glGetProgramInfoLog", [c_uint, sizei, POINTER(sizei), c_char_p])
glGetShaderInfoLog = glget("glGetShaderInfoLog", [c_uint, sizei, POINTER(sizei), c_char_p])
glGetProgramiv = glget("glGetProgramiv", [c_uint, enum, POINTER(c_int)])
glGetShaderiv = glget("glGetShaderiv", [c_uint, enum, POINTER(c_int)])
glUseProgram = glget("glUseProgram", [c_uint])
glGetUniformLocation = glget("glGetUniformLocation", [c_uint, c_char_p])
glUniform1f = glget("glUniform1f", [c_int, c_float])
glUniform1i = glget("glUniform1i", [c_int, c_int])

class Shader:
    def __init__(self, fragment=[], vertex=[]):
        self.uniforms = {}
        self.shader = glCreateProgram()
        fragment = [(glCreateShader(fragment_shader),f) for f in fragment]
        check()
        vertex = [(glCreateShader(vertex_shader),v) for v in vertex]
        check()
        for p,s in fragment+vertex:
            source = s.split("\n")
            lines = (c_char_p*len(source))()
            for idx in range(len(source)):
                lines[idx] = c_char_p(source[idx]+"\n")
            glShaderSource(p, len(source), lines, None)
            check()
            glCompileShader(p)
            check()
            status = c_int()
            glGetShaderiv(p, compile_status, byref(status))
            if status.value == 0:
                log_length = c_int()
                glGetShaderiv(p, info_log_length, byref(log_length))
                log = (c_char*log_length.value)()
                glGetShaderInfoLog(p, log_length.value, None, log)
                print(log[:].decode())
                exit(1)
            glAttachShader(self.shader, p)
            check()
            glDeleteShader(p)
            check()
        glLinkProgram(self.shader)
        check()
        log_length = c_int()
        glGetProgramiv(self.shader, info_log_length, byref(log_length))
        log = (c_char*log_length.value)()
        glGetProgramInfoLog(self.shader, log_length.value, None, log)
        print(log[:].decode())

    def __setitem__(self, key, value):
        self.set(key, value, glUniform1f)

    def seti(self, key, value):
        self.set(key, value, glUniform1i)

    def set(self, key, value, setter):
        if key not in self.uniforms:
            pos = glGetUniformLocation(self.shader, key)
            self.uniforms[key] = pos
            if pos == -1:
                logging.info("Couldn't find %s", key)
        pos = self.uniforms[key]
        if pos != -1:
            setter(self.uniforms[key], value)
        
    def __del__(self):
        if self.shader:
            glDeleteProgram(self.shader)
        
    def attach(self):
        glUseProgram(self.shader)

    def detach(self, *unused):
        glUseProgram(0)

    __enter__ = attach
    __exit__  = detach


# Effects

def sunlightTextures(width, height, depth):
    textures = [TextureWrapper(t) for t in _effects.sunlightTextures(width, height, depth)]
    check()
    return textures
