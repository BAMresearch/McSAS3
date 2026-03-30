=====
Usage
=====

Supported interfaces
====================

McSAS3 currently supports three maintained user-facing paths:

- 1D CLI optimization via ``mcsas3-runner``
- histogramming of stored results via ``mcsas3-histogrammer``
- canonical Python workflows built on ``ProcessingData`` and ``DataBundle``

CLI workflows
=============

The CLI uses YAML configuration files:

- a read configuration for source data
- a run configuration for the optimizer
- a histogram configuration for post-processing

See :doc:`quickstart` for a minimal example command sequence.

Python workflows
================

New scripts and notebooks should use the top-level canonical workflow API:

.. code-block:: python

   from mcsas3 import (
       load_result_processing_data,
       optimize_processing_data,
       prepare_1d_processing_data,
       prepare_1d_processing_data_from_file,
       prepare_2d_processing_data,
       prepare_2d_processing_data_from_file,
       selected_bundle_from_processing,
   )

Result files
============

McSAS3 result files now store canonical ``ProcessingData`` at:

- ``/analyses/MCResult*/mcdata/processingData``

The maintained load/store helpers are:

- ``load_result_processing_data(...)``
- ``store_result_processing_data(...)``

Reusable preprocessing helpers
==============================

Canonical preprocessing helpers live in ``mcsas3.preprocessing``:

- clipping
- omission
- 1D rebinning
- 2D reconstruction from clipped bundles

See also
========

- :doc:`quickstart`
- :doc:`migration`
- :doc:`structure`
