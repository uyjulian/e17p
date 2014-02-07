/*
 *Copyright 2010 Sebastian Hagen
 * This file is part of E17p.
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

/* E17 CPS processing functions */

#define PY_SSIZE_T_CLEAN 1
#include "Python.h"
#include <stdint.h>

/* Give productive feedback to people trying to link this with Python 2.x */
#if PY_MAJOR_VERSION < 3
#error This file requires python >= 3.0
#endif

#ifdef WIN32
 #include <Winsock2.h>
#else
 #include <arpa/inet.h>
#endif

// GNU libc has these in the stdlib, but it's not in POSIX, so let's write our own.
static uint32_t _letoh32(uint32_t val_in) {
   uint32_t val_nb;
      
   ((char*)&val_nb)[0] = ((char*)&val_in)[3];
   ((char*)&val_nb)[3] = ((char*)&val_in)[0];
   ((char*)&val_nb)[1] = ((char*)&val_in)[2];
   ((char*)&val_nb)[2] = ((char*)&val_in)[1];
   
   return ntohl(val_nb);
}

static uint32_t _htole32(uint32_t val_in) {
   uint32_t val_nb, rv;
   val_nb = htonl(val_in);
   
   ((char*)&rv)[0] = ((char*)&val_nb)[3];
   ((char*)&rv)[3] = ((char*)&val_nb)[0];
   ((char*)&rv)[1] = ((char*)&val_nb)[2];
   ((char*)&rv)[2] = ((char*)&val_nb)[1];
   
   return rv;
}

static PyObject *cps_unobfuscate(PyObject *self, PyObject *args) {
   Py_buffer buf;
   size_t buflen;
   PyObject *pybuf;
   uint32_t v_off, val_obf;
   uint32_t *dp, *dp_lim, *dp_obf, data_size;
   
   if (!PyArg_ParseTuple(args, "O", &pybuf)) return NULL;
   if (PyObject_GetBuffer(pybuf, &buf, PyBUF_SIMPLE|PyBUF_WRITABLE)) return NULL;
   if ((buf.len < 4) || (buf.len > UINT32_MAX)) goto error_out1;
   
   v_off = _letoh32(*(uint32_t*) &((char*)buf.buf)[buf.len-4]) - 0x7534682;
   if (v_off + 4 > buf.len) goto error_out1;
   
   dp = (uint32_t*) (((char*)buf.buf) + 0x10);
   if ((buf.len >= 20) && v_off) {
      val_obf = _letoh32(*(uint32_t*) (&((char*)buf.buf)[v_off])) + v_off + 0x3786425;
   
      dp_obf = (uint32_t*) ((char*)buf.buf + v_off);
      dp_lim = (uint32_t*) ((char*)buf.buf + buf.len);
      data_size = buf.len;
   
      while (dp < dp_lim) {
         if (dp != dp_obf) {
            *dp = _htole32(_letoh32(*dp) - val_obf - data_size);
         }
         val_obf *= 0x41c64e6d;
         val_obf += 0x9b06;
         dp++;
      }
   }
   
   memset(dp-1, 0, 4);
   buflen = buf.len;
   PyBuffer_Release(&buf);
   if (PySequence_DelSlice(pybuf, buflen-4, buflen)) return NULL;
   Py_RETURN_NONE;
   
   error_out1:
    PyBuffer_Release(&buf);
    return NULL;
}

static PyObject *cps_mix_alpha(PyObject *self, PyObject *args) {
   Py_buffer buf_rgb, buf_alpha, buf_rgba;
   PyObject *pybuf_rgb, *pybuf_alpha, *rv;
   Py_ssize_t width, height, ill;
   char *p_rgb, *p_alpha, *p_rgba;
   size_t x,y;
   
   if (!PyArg_ParseTuple(args, "OOnnn", &pybuf_rgb, &pybuf_alpha, &width, &height, &ill)) return NULL; 
   if ((width < 0) || (height < 0) || (ill < 0)) {
      PyErr_SetString(PyExc_ValueError, "Invalid image dimensions / line length.");
      return NULL;
   }
   if (!(rv = PyByteArray_FromStringAndSize(NULL, 0))) return NULL;
   if (PyByteArray_Resize(rv, width*height*4)) goto error_out0;
   
   if (PyObject_GetBuffer(pybuf_rgb, &buf_rgb, PyBUF_SIMPLE)) return NULL;
   if (PyObject_GetBuffer(pybuf_alpha, &buf_alpha, PyBUF_SIMPLE)) goto error_out1;
   if (PyObject_GetBuffer(rv, &buf_rgba, PyBUF_SIMPLE|PyBUF_WRITABLE)) goto error_out2;
   
   if (buf_rgb.len < 3*width*height) goto error_out3;
   if (buf_alpha.len < width*height) goto error_out3;
   
   p_alpha = ((char*)buf_alpha.buf) + buf_alpha.len - width;
   p_rgba = buf_rgba.buf;
   
   for (y = 0; y < height; y++) {
      p_rgb = &((char*) buf_rgb.buf)[(y*ill)]; // correct for line padding
      for (x = 0; x < width; x++) {
         *(p_rgba++) = *(p_rgb++);
         *(p_rgba++) = *(p_rgb++);
         *(p_rgba++) = *(p_rgb++);
         *(p_rgba++) = *(p_alpha++);
      }
      p_alpha -= 2*width;
   }
   
   PyBuffer_Release(&buf_rgba);
   PyBuffer_Release(&buf_alpha);
   PyBuffer_Release(&buf_rgb);
   return rv;
   
   error_out3:
    PyErr_SetString(PyExc_RuntimeError, "Insufficient input data.");
    PyBuffer_Release(&buf_rgba);
   error_out2:
    PyBuffer_Release(&buf_alpha);
   error_out1:
    PyBuffer_Release(&buf_rgb);
   error_out0:
    Py_DECREF(rv);
    return NULL;
}

static PyObject *cps_map_palette(PyObject *self, PyObject *args) {
   Py_buffer buf_data, buf_palette, buf_rv;
   PyObject *pybuf_data, *pybuf_palette, *rv;
   unsigned char *pb_data, *pb_rv;
   Py_ssize_t width, height, w, h, ill, oll, wr_i, wr_o;
   
   if (!PyArg_ParseTuple(args, "OOnn", &pybuf_data, &pybuf_palette, &width, &height)) return NULL;
   
   if (PyObject_GetBuffer(pybuf_data, &buf_data, PyBUF_SIMPLE)) return NULL;
   
   ill = ((width + 3)/4)*4;
   if (ill * height > buf_data.len) {
      PyErr_SetString(PyExc_ValueError, "Insufficient input data.");
      goto error_out1;
   }
   oll = ((width*3 + 3)/4)*4;
   
   if (!(rv = PyByteArray_FromStringAndSize(NULL, 0))) goto error_out1;
   if (PyByteArray_Resize(rv, oll*height)) goto error_out2;
   if (PyObject_GetBuffer(pybuf_palette, &buf_palette, PyBUF_SIMPLE)) goto error_out2;
   if (PyObject_GetBuffer(rv, &buf_rv, PyBUF_SIMPLE|PyBUF_WRITABLE)) goto error_out3;
   
   pb_data = buf_data.buf;
   pb_rv = buf_rv.buf;
   wr_i = ill - width;
   wr_o = oll - width*3;
   
   for (h = 0; h < height; h++) {
      for (w = 0; w < width; w++) {
         *(pb_rv++) = ((char*)buf_palette.buf)[*(pb_data) << 2];
         *(pb_rv++) = ((char*)buf_palette.buf)[(*(pb_data) << 2) + 1];
         *(pb_rv++) = ((char*)buf_palette.buf)[(*(pb_data++) << 2) + 2];
      }
      pb_data += wr_i;
      pb_rv += wr_o;
   }
   
   PyBuffer_Release(&buf_rv);
   PyBuffer_Release(&buf_palette);
   PyBuffer_Release(&buf_data);
   return rv;
   
   error_out3:
    PyBuffer_Release(&buf_palette);
   error_out2:
    Py_DECREF(rv);
   error_out1:
    PyBuffer_Release(&buf_data);
    return NULL;
}


static PyMethodDef _cps_methods[] = {
    {"cps_unobfuscate", (PyCFunction)cps_unobfuscate, METH_VARARGS, "Unobfuscate E17 CPS file."},
    {"cps_mix_alpha", (PyCFunction)cps_mix_alpha, METH_VARARGS, "Mix CPS color and alpha data."},
    {"cps_map_palette", (PyCFunction) cps_map_palette, METH_VARARGS, "Map 8-bit color data through palette table."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef _cpsmodule = {
   PyModuleDef_HEAD_INIT,
   "_cps",
   NULL,
   -1,
   _cps_methods
};

PyMODINIT_FUNC
PyInit__cps(void) {
    return PyModule_Create(&_cpsmodule);
}
