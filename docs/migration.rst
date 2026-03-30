=========================
Migration from ``McData*``
=========================

McSAS3 now uses canonical MoDaCor-style ``ProcessingData`` / ``DataBundle`` / ``BaseData``
carriers throughout the maintained core API.

This is a breaking change.

What changed
============

- ``McData``, ``McData1D``, and ``McData2D`` are no longer part of the maintained core package.
- The old ``measData`` / ``measDataLink`` vocabulary has been replaced by canonical selected-stage
  handling on ``ProcessingData``.
- New result files store canonical ``processingData`` rather than duplicated legacy stage groups.

Old to New Mapping
==================

- ``McData1D(...).from_file(...).prepare()``:
  use ``prepare_1d_processing_data_from_file(...)``
- ``McData2D(...).from_file(...).prepare()``:
  use ``prepare_2d_processing_data_from_file(...)``
- manual in-memory ``McData1D`` construction:
  use ``prepare_1d_processing_data(...)``
- manual in-memory ``McData2D`` construction:
  use ``prepare_2d_processing_data(...)``
- ``mcd.store(...)`` / ``mcd.load(...)``:
  use ``store_result_processing_data(...)`` / ``load_result_processing_data(...)``
- ``mcd.measData``:
  use ``selected_bundle_from_processing(processing)``
- ``mcd.clip()``, ``mcd.omit()``, ``mcd.reBin()``:
  use the helpers in ``mcsas3.preprocessing``

Minimal Example
===============

Instead of:

.. code-block:: python

   # old style, no longer maintained
   # mcd = McData1D(...)
   # mcd.prepare()

Use:

.. code-block:: python

   from mcsas3 import prepare_1d_processing_data_from_file, selected_bundle_from_processing

   processing = prepare_1d_processing_data_from_file(...)
   analysis_bundle = selected_bundle_from_processing(processing)

Notes
=====

- The canonical internal units are ``1 / nm`` for ``Q`` and ``1 / (m sr)`` for intensity.
- Input units are normalized at ingestion time.
- If you need the current code structure overview, see :doc:`structure`.
