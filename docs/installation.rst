============
Installation
============

Install McSAS3 from PyPI:

.. code-block:: bash

   pip install mcsas3

Notes
=====

- McSAS3 depends on ``sasmodels``, ``attrs``, ``pandas``, ``h5py``, ``pint``, and ``pyyaml``.
- If SasModels / OpenCL causes clearly wrong fits, disable OpenCL before launching McSAS3:

.. code-block:: bash

   export SAS_OPENCL=none

- On Windows, ``pip install tinycc`` can still be useful if SasModels needs a working compiler.

Development install
===================

For local development from a checkout:

.. code-block:: bash

   pip install -e .
