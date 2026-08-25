================
Release delivery
================

McSAS3 now has two distinct delivery tracks:

- standard Python package delivery via wheel and sdist
- standalone CLI bundles for macOS, Windows, and Linux

Python packages
===============

The existing package build remains:

- ``python -m build``
- ``tox -e build``

This produces:

- a source distribution
- a wheel for normal Python installation

Standalone CLI bundles
======================

The standalone build path packages the maintained command-line tools:

- ``mcsas3-runner``
- ``mcsas3-histogrammer``

Local build command:

.. code-block:: bash

   tox -e standalone

This runs ``tools/build_standalone.py`` and produces:

- ``dist/standalone/<platform-tag>/``: the unpacked standalone bundle
- ``dist/standalone/mcsas3-standalone-<platform-tag>.zip``: the distributable archive

Current implementation notes
============================

- the standalone path uses PyInstaller in ``onedir`` mode
- the standalone build uses the normal ``modacor`` package dependency for canonical data-model
  classes (no sibling source checkout override is required)
- bundled example configurations and ``testdata/quickstartdemo1.csv`` are included so the CLI
  default paths resolve correctly in frozen builds
- the local builder smoke-tests each generated executable with ``--help``
- the repo ships a local PyInstaller ``sasmodels`` hook so the standalone bundles keep the runtime
  model/kernel data without also bundling the full upstream documentation tree
- the runner build excludes histogram-only plotting and notebook extras, so ``mcsas3-runner`` is
  intentionally slimmer than ``mcsas3-histogrammer``

CI workflow
===========

The repo now includes ``.github/workflows/standalone.yml`` which builds standalone archives on:

- Linux
- macOS
- Windows

This workflow is also wired into the top-level CI/CD workflow so the standalone bundles are built
reproducibly alongside the normal package artifacts.

Scope
=====

This page describes standalone delivery for the McSAS3 core CLI only.

Packaged GUI app delivery belongs to the follow-on McSAS3GUI work.
