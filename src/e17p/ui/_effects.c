/* Copyright 2010 Svein Ove Aas
 * This file is part of E17p
 *
 * E17p is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 *(at your option) any later version.
 *
 * E17p is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/* Effect texture building functions */

#define PY_SSIZE_T_CLEAN 1
#include "Python.h"

#include <GL/gl.h>
#include <math.h>
#include <stdlib.h>

/* Give productive feedback to people trying to link this with Python 2.x */
#if PY_MAJOR_VERSION < 3
#error This file requires python >= 3.0
#endif

#define MAX(a,b) ((a) > (b) ? (a) : (b))
#define MIN(a,b) ((a) < (b) ? (a) : (b))

static float inline saturate(float x) {
  return MAX(MIN(x,1),0);
}

static float inline smoothstep(float edge0, float edge1, float x) {
  // Scale, bias and saturate x to 0..1 range
  x = saturate((x - edge0) / (edge1 - edge0)); 
  // Evaluate polynomial
  return x*x*(3-2*x);
}

/* Builds a number of width*height textures forming a cycle */
static PyObject *sunlightTextures(PyObject *self, PyObject *args) {
  int width, height, depth;

  if (!PyArg_ParseTuple(args, "iii", &width, &height, &depth))
    return NULL;
  if (width <= 0 || height <= 0 || depth <= 0)
    return NULL;

  GLuint textures[depth];
  glGenTextures(depth, textures);
  PyObject *list = PyList_New(depth);
  {
    int i = 0;
    for (; i < depth; i++)
      PyList_SetItem(list, i, PyLong_FromLong(textures[i]));
  }

  // Build the textures
  {
    int x, y, z, t;
    unsigned char data[width*height*4];
    unsigned char *p;
    for (z = 0; z < depth; z++) {
      t = textures[z];
      p = data;
      glBindTexture(GL_TEXTURE_2D, t);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
      for (y = 0; y < height; y++) {
        for (x = 0; x < width; x++) {
          float xpos = (float)x / width;
          float ypos = (float)y / height;
          float zpos = (float)z / depth * M_PI * 2;
          float limit = MAX(0.3 * (ypos * 2 - xpos * 0.5), 0);
          float strength = 0;

          float t = cosf(zpos * 0.93);
          strength += t * smoothstep(0.8, 1, 1 - fabsf(1 - ypos - xpos*2 + t));
          t = cosf(-zpos * 0.9 + 0.4);
          strength += t * smoothstep(0.8, 1, 1 - fabsf(1 - ypos - xpos*2 + t));
          t = cosf(zpos * 0.85 + 0.8);
          strength += t * smoothstep(0.8, 1, 1 - fabsf(1 - ypos - xpos*2 + t));
          t = cosf(-zpos * 0.87 + 1.7);
          strength += t * smoothstep(0.8, 1, 1 - fabsf(1 - ypos - xpos*2 + t));

          strength *= limit;

          strength = MIN(MAX(strength, 0), 1);
          
          *p++ = strength * 255 * 0.788;
          *p++ = strength * 255 * 0.886;
          *p++ = strength * 255;
          *p++ = 0;
        }
      }
      glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data);
    }
  }

  return list;
}

static PyMethodDef _effects[] = {
    {"sunlightTextures", (PyCFunction)sunlightTextures, METH_VARARGS, "Build sunlight textures"},
    {NULL, NULL, 0, NULL}
};


static struct PyModuleDef _effectsmodule = {
   PyModuleDef_HEAD_INIT,
   "_effects",
   NULL,
   -1,
   _effects
};

PyMODINIT_FUNC
PyInit__effects(void) {
    return PyModule_Create(&_effectsmodule);
}
