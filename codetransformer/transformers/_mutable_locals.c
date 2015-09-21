#include "Python.h"
#include "frameobject.h"

static PyObject *
set_locals_dict(PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *frame;
    PyObject *new_locals;
    const char *const kwds[] = {"frame", "new_locals", NULL};

    int result = PyArg_ParseTupleAndKeywords(args,
                                             kwargs,
                                             "OO:set_locals_dict",
                                             (char**) kwds,
                                             &frame, &new_locals);
    if (!result)
    {
        return NULL;
    }
    if (!PyObject_IsInstance(frame, (PyObject *) &PyFrame_Type))
    {
        PyErr_SetString(PyExc_TypeError, "frame is not a frame object");
        return NULL;
    }

    ((PyFrameObject *) frame)->f_locals = new_locals;
    Py_INCREF(new_locals);
    Py_RETURN_NONE;
}


PyMethodDef methods[] = {
    {"set_locals_dict", (PyCFunction) set_locals_dict, METH_VARARGS, ""},
    {NULL},
};


static struct PyModuleDef _mutable_locals_module = {
    PyModuleDef_HEAD_INIT,
    "codetransformer.transformers._mutable_locals",
    "",
    -1,
    methods,
    NULL,
    NULL,
    NULL,
    NULL
};


PyMODINIT_FUNC
PyInit__mutable_locals(void)
{
    return PyModule_Create(&_mutable_locals_module);
}
