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

/* E17 RLE decoding functions */

#define PY_SSIZE_T_CLEAN 1
#include "Python.h"

/* Give productive feedback to people trying to link this with Python 2.x */
#if PY_MAJOR_VERSION < 3
#error This file requires python >= 3.0
#endif

static PyObject *e17_rle_unpack(PyObject *self, PyObject *args) {
   Py_buffer buf_i, buf_o;
   PyObject *pybuf_i, *pyout_len, *rv;
   
   if (!PyArg_ParseTuple(args, "OO", &pybuf_i, &pyout_len)) return NULL;
   if (PyObject_GetBuffer(pybuf_i, &buf_i, PyBUF_SIMPLE)) return NULL;
   if (!(rv = PyByteArray_FromObject(pyout_len))) goto error_out1;
   if (PyObject_GetBuffer(rv, &buf_o, PyBUF_SIMPLE|PyBUF_WRITABLE)) goto error_out2;
   
   size_t inspace_left, outspace_left, run_length, count, i, off;
   unsigned char op;
   char dbyte;
   unsigned char *out_p, *in_p, *out_p_end, *out_p_lim, *in_p_lim, *out_p2, *in_p2;
   
   in_p = buf_i.buf;
   out_p = buf_o.buf;
   out_p_end = out_p + buf_o.len;
   
   outspace_left = buf_o.len;
   inspace_left = buf_i.len;
   
   while (out_p < out_p_end) {
      op = *(in_p++);
      if (!(inspace_left -= 1)) goto error_out3;
      //printf("%hhu %zu %zu\n", op, inspace_left, outspace_left);
      if (op & 0x80) {
         if (op & 0x40) {
            // Repeated byte
            run_length = (op & 0x1F) + 2;
            if (op & 0x20) {
               run_length += *(in_p++) << 5;
               inspace_left--;
            }
            
            if (inspace_left <= 0) goto error_out3;
            dbyte = *(in_p++);
            inspace_left--;
            
            if (run_length > outspace_left) goto error_out3;
            
            memset(out_p, dbyte, run_length);
            
            out_p += run_length;
            outspace_left -= run_length;
         } else {
            // Reference to an earlier version of the same byte sequence
            run_length = ((op >> 2) & 0xF) + 2;
            off = ((op & 3) << 8) + *(in_p++) + 1;
            inspace_left -= 1;
            out_p2 = out_p - off;
            if (((out_p2 - (unsigned char*) buf_o.buf) + run_length > buf_o.len) || (run_length > outspace_left))
               goto error_out3;
            out_p_lim = out_p + run_length;
            
            while (out_p < out_p_lim) *(out_p++) = *(out_p2++);
            
            outspace_left -= run_length;
         }
      } else {
         if (op & 0x40) {
            // Repeated multi-byte sequence
            run_length = (op & 0x3F) + 2;
            count = *(in_p++) + 1;
            inspace_left--;
            if (inspace_left < run_length) goto error_out3;
            
            in_p_lim = in_p + run_length;
            for (i = count; i && outspace_left; i--) {
               in_p2 = in_p;
               // N7 has files that use such sequences in situations where they will overrun the available outspace; check
               // for that here and compensate accordingly.
               if (outspace_left < run_length) run_length = outspace_left;
               outspace_left -= run_length;
               while (in_p2 < in_p_lim) *(out_p++) = *(in_p2++);
            }
            in_p = in_p_lim;
            inspace_left -= run_length;
         } else {
            // Literal sequence
            run_length = (op & 0x1F) + 1;
            if (op & 0x20) {
               run_length += *(in_p++) << 5;
               inspace_left--;
            }

            if ((run_length > inspace_left) || (run_length > outspace_left)) goto error_out3;
            
            out_p_lim = out_p + run_length;
            while (out_p < out_p_lim) *(out_p++) = *(in_p++);
            
            inspace_left -= run_length;
            outspace_left -= run_length;
         }
      }
   }
   
   PyBuffer_Release(&buf_i);
   PyBuffer_Release(&buf_o);
   return rv;
   
   error_out3:
    PyErr_SetString(PyExc_ValueError, "RLE decompression failed.");
    PyBuffer_Release(&buf_o);
   error_out2:
    Py_DECREF(rv);
   error_out1:
    PyBuffer_Release(&buf_i);
    return NULL;
}

static PyMethodDef _rle_methods[] = {
    {"e17_rle_unpack", (PyCFunction)e17_rle_unpack, METH_VARARGS, "Decompress E17 RLE-encoded data."},
    {NULL, NULL, 0, NULL}
};


static struct PyModuleDef _rlemodule = {
   PyModuleDef_HEAD_INIT,
   "_rle",
   NULL,
   -1,
   _rle_methods
};

PyMODINIT_FUNC
PyInit__rle(void) {
    return PyModule_Create(&_rlemodule);
}
