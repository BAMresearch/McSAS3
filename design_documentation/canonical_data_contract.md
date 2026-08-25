# McSAS3 Canonical Data Contract

Last updated: 2026-04-01

This document defines the maintained McSAS3 data contract.
It is the source of truth for the canonical bundle keys, stage names, and supported adapter/helper
rules.

## Dependency boundary

McSAS3 now imports MoDaCor data classes through `mcsas3.data_model`.

Import strategy:

- require a normal installed `modacor` package

McSAS3 no longer uses sibling-checkout fallback import plumbing for MoDaCor.

Supported public Python API:

- top-level `mcsas3` exports now expose the maintained canonical workflow entry points:
  - `prepare_1d_processing_data`
  - `prepare_1d_processing_data_from_file`
  - `prepare_2d_processing_data`
  - `prepare_2d_processing_data_from_file`
  - `optimize_processing_data`
  - `load_result_processing_data`
  - `store_result_processing_data`
- top-level `mcsas3` also re-exports the canonical carrier types and stage constants:
  - `BaseData`
  - `DataBundle`
  - `ProcessingData`
  - `STAGE_RAW`
  - `STAGE_CLIPPED`
  - `STAGE_BINNED`
- reusable canonical preprocessing helpers live in `mcsas3.preprocessing`
- new notebook and script usage should import the top-level workflow functions and canonical
  helpers directly

## Canonical stage names

`ProcessingData` stage names are:

- `sample_raw`
- `sample_clipped`
- `sample_binned`

These names are represented in code by:

- `mcsas3.data_adapters.STAGE_RAW`
- `mcsas3.data_adapters.STAGE_CLIPPED`
- `mcsas3.data_adapters.STAGE_BINNED`

## Canonical selected analysis stage

`ProcessingData` now carries the selected stage for fitting or analysis via the instance attribute:

- `processing.analysis_stage`

Current rules:

- the value must be one of the canonical stage names
- the default is `sample_binned`
- this selects which stage feeds fitting and histogramming

## Canonical 1D bundle contract

Each 1D stage is a `DataBundle` with these keys:

- `signal`: intensity data
- `Q`: scattering vector
- `mask`: optional boolean mask

Current default units:

- `signal.units = 1 / (m sr)`
- `Q.units = 1 / nm`
- `mask.units = dimensionless`

Current uncertainty rules:

- intensity uncertainties live on `signal.uncertainties["propagate_to_all"]`
- optional `QSigma` lives on `Q.uncertainties["propagate_to_all"]`

Notes:

- McSAS3 uses absolute scattering cross-section units for the canonical signal representation.
- `1 / nm` matches the existing McSAS3 optimizer and reporting convention.
- source data is normalized to these canonical units at ingestion time

Open unit-contract issue:

- Fit parameter limits currently rely on the canonical `Q` unit convention, so length-like
  optimization parameters such as `radius` are effectively interpreted in `nm` after ingestion.
- SasModels parameters use their own model-unit convention internally, including SLD values in
  `10^-6 / angstrom^2`, and McSAS3 bridges some of these quantities implicitly.
- A future PR should make optimization parameter units explicit in the run configuration, store
  those units with results, and convert to model-specific units through `pint` before calling the
  underlying model. This is especially important for absolute volume-fraction calculations.

## Canonical 2D bundle contract

Each 2D stage is a `DataBundle` with these keys:

- `signal`: 2D intensity image
- `Qx`: horizontal reciprocal-space coordinate
- `Qy`: vertical reciprocal-space coordinate
- `mask`: optional boolean mask image

Current default units:

- `signal.units = 1 / (m sr)`
- `Qx.units = 1 / nm`
- `Qy.units = 1 / nm`
- `mask.units = dimensionless`

Current uncertainty rules:

- intensity uncertainties live on `signal.uncertainties["propagate_to_all"]`
- `Qx` and `Qy` currently carry no uncertainty arrays in the adapter layer

Notes:

- the canonical 2D representation remains image-shaped
- flattened fit vectors are derived adapter output, not the stored canonical representation
- source data is normalized to these canonical units at ingestion time

## Adapter rules

The adapter layer lives in `mcsas3.data_adapters`.

Supported conversions:

- 1D `DataFrame` -> canonical `DataBundle`
- 2D stage dict-of-arrays -> canonical `DataBundle`
- canonical `ProcessingData` + `analysis_stage` -> selected analysis `DataBundle`
- canonical selected analysis `DataBundle` -> optimizer fit arrays
- canonical `DataBundle` -> derived stage `DataFrame` via `frame_from_bundle()`

Current normalization rules:

- adapter entry points accept optional source-unit declarations for `Q` and `signal`
- read-configuration YAML and canonical file-ingest helpers may provide these as `QUnits` /
  `IUnits` (preferred, matching the existing config style) or `Q_units` / `I_units` (accepted
  alias)
- canonical bundles are always stored in `1 / nm` and `1 / (m sr)` regardless of input units
- uncertainty arrays are converted alongside their parent `BaseData`

SasModels bridge rules:

- canonical McSAS3 data stays in `1 / nm` and `1 / (m sr)`
- the SasModels execution boundary converts reciprocal-space and size-like parameters to the
  angstrom-based conventions expected by SasModels, then converts intensity back to canonical
  McSAS3 units
- fast regression coverage checks that this bridge preserves the expected recovered volume
  fraction for a sphere model at fixed SLD contrast

## Canonical workflow and preprocessing surface

McSAS3 now uses canonical workflows directly:

- `mcsas3.workflows` owns supported file ingestion, preprocessing orchestration, HDF5
  load/store, and optimization entry points
- `mcsas3.preprocessing` owns the reusable clip / omit / rebin / reconstruct helpers over
  canonical `DataBundle` objects
- `mcsas3.ingestion` owns shared 1D and 2D file loading plus source-unit detection
- `mcsas3.data_adapters.fit_arrays_from_bundle()` is the maintained bridge from canonical bundles
  to flattened optimizer arrays; the maintained execution path no longer accepts flat fit-data
  dicts as input

## Canonical HDF5 persistence

McSAS3 now stores first-class canonical processing data at:

- `/analyses/MCResult*/mcdata/processingData`

Current storage rules:

- `ProcessingData.analysis_stage` is stored with the processing-data group
- each canonical stage is stored as its own `DataBundle` subgroup
- each `BaseData` entry stores:
  - `signal`
  - `weights`
  - `uncertainties/*`
  - `units`
  - `rank_of_data`
- bundle metadata such as `default_plot` and `description` is preserved

Current load rules:

- `load_result_processing_data()` requires the canonical `processingData` schema
- result files store canonical stage bundles under `processingData` without duplicate stage-table
  groups
- the maintained load path expects that canonical `processingData` schema
