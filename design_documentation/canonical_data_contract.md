# McSAS3 Canonical Data Contract

Last updated: 2026-03-29

This document defines the Phase 2 contract for introducing MoDaCor data classes into McSAS3.
It is the source of truth for the canonical bundle keys, stage names, and transitional adapter
rules.

## Dependency boundary

McSAS3 now imports MoDaCor data classes through `mcsas3.data_model`.

Import strategy:

- prefer a normal installed `modacor` package
- fall back to the sibling workspace checkout at `../MoDaCor/src`

This keeps the rest of McSAS3 independent from the packaging decision while the migration is in
progress.

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
- new notebook and script usage should import those top-level workflow functions instead of
  importing `McData1D` / `McData2D` directly

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
- this is the canonical replacement for the old `measDataLink` concept
- transitional `McData*` objects now mirror this selection through their `analysisStage` wrapper
  attribute rather than through a separate legacy link name

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
- `rawData`, `clippedData`, and `binnedData` compatibility views now expose canonical-unit values

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
- `Qx` and `Qy` currently carry no uncertainty arrays in the transitional adapter layer

Notes:

- the canonical 2D representation remains image-shaped
- flattened fit vectors are derived adapter output, not the stored canonical representation
- source data is normalized to these canonical units at ingestion time
- `rawData2D`, `clippedData`, and `binnedData` compatibility views now expose canonical-unit values

## Transitional adapter rules

The transitional adapter layer lives in `mcsas3.data_adapters`.

Supported conversions:

- 1D `DataFrame` -> canonical `DataBundle`
- legacy 2D dict-of-arrays -> canonical `DataBundle`
- legacy raw/clipped/binned stage objects -> canonical `ProcessingData`
- canonical `ProcessingData` + `analysis_stage` -> selected analysis `DataBundle`
- canonical selected analysis `DataBundle` -> optimizer fit arrays
- canonical `DataBundle` -> derived flat analysis-data dict when an adapter needs that shape
- canonical `DataBundle` -> legacy plotting `DataFrame`

Current normalization rules:

- adapter entry points accept optional source-unit declarations for `Q` and `signal`
- read-configuration YAML and other `McData*` kwargs may provide these as `QUnits` / `IUnits`
  (preferred, matching the existing config style) or `Q_units` / `I_units` (accepted alias)
- canonical bundles are always stored in `1 / nm` and `1 / (m sr)` regardless of input units
- uncertainty arrays are converted alongside their parent `BaseData`

SasModels bridge rules:

- canonical McSAS3 data stays in `1 / nm` and `1 / (m sr)`
- the SasModels execution boundary converts reciprocal-space and size-like parameters to the
  angstrom-based conventions expected by SasModels, then converts intensity back to canonical
  McSAS3 units
- fast regression coverage checks that this bridge preserves the expected recovered volume
  fraction for a sphere model at fixed SLD contrast

Derived flat analysis-data rules:

- 1D bundles produce `{"Q": [Q], "I": I, "ISigma": sigma}`
- 2D bundles produce flattened fit vectors from unmasked, finite, nonzero-uncertainty pixels
- if multiple uncertainty sources exist on a `BaseData`, the legacy adapter combines them in
  quadrature

## Current bridge in McData

`McData.to_processing_data()` now provides a derived canonical view of the current wrapper state:

- 1D uses `rawData`, `clippedData`, and `binnedData`
- 2D uses `rawData2D` for the raw stage plus `clippedData` and `binnedData`

This is intentionally one-way for now:

- canonical data is available to new code
- legacy internals still remain the source of truth until Phase 3
- `McData.sourceQUnits` and `McData.sourceIntensityUnits` record declared or detected input units
  while legacy compatibility views stay in canonical internal units
- `McData*` no longer keep a long-lived `analysisData` wrapper attribute; flat fit-data dicts are
  derived on demand from the selected canonical bundle via `analysis_data_from_bundle()`

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

- `McData.load()` requires the canonical `processingData` schema
- legacy compatibility views are rebuilt from stored canonical bundles rather than recomputed
- new result files no longer duplicate legacy `rawData` / `rawData2D` / `clippedData` /
  `binnedData` HDF groups
- `McData.load()` now requires canonical `processingData`; legacy-only result files are no longer
  accepted by the migration path
