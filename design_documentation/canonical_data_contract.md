# McSAS3 Canonical Data Contract

Last updated: 2026-03-28

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

## Canonical stage names

`ProcessingData` stage names are:

- `sample_raw`
- `sample_clipped`
- `sample_binned`

These names are represented in code by:

- `mcsas3.data_adapters.STAGE_RAW`
- `mcsas3.data_adapters.STAGE_CLIPPED`
- `mcsas3.data_adapters.STAGE_BINNED`

## Canonical 1D bundle contract

Each 1D stage is a `DataBundle` with these keys:

- `signal`: intensity data
- `Q`: scattering vector
- `mask`: optional boolean mask

Current default units:

- `signal.units = AFU`
- `Q.units = 1 / nm`
- `mask.units = dimensionless`

Current uncertainty rules:

- intensity uncertainties live on `signal.uncertainties["propagate_to_all"]`
- optional `QSigma` lives on `Q.uncertainties["propagate_to_all"]`

Notes:

- `AFU` is MoDaCor's arbitrary flux unit and is the safest current default until McSAS3 loaders
  consistently carry real intensity metadata.
- `1 / nm` matches the existing McSAS3 optimizer and reporting convention.

## Canonical 2D bundle contract

Each 2D stage is a `DataBundle` with these keys:

- `signal`: 2D intensity image
- `Qx`: horizontal reciprocal-space coordinate
- `Qy`: vertical reciprocal-space coordinate
- `mask`: optional boolean mask image

Current default units:

- `signal.units = AFU`
- `Qx.units = 1 / nm`
- `Qy.units = 1 / nm`
- `mask.units = dimensionless`

Current uncertainty rules:

- intensity uncertainties live on `signal.uncertainties["propagate_to_all"]`
- `Qx` and `Qy` currently carry no uncertainty arrays in the transitional adapter layer

Notes:

- the canonical 2D representation remains image-shaped
- flattened fit vectors are derived adapter output, not the stored canonical representation

## Transitional adapter rules

The transitional adapter layer lives in `mcsas3.data_adapters`.

Supported conversions:

- 1D `DataFrame` -> canonical `DataBundle`
- legacy 2D dict-of-arrays -> canonical `DataBundle`
- legacy raw/clipped/binned stage objects -> canonical `ProcessingData`
- canonical `DataBundle` -> legacy `measData`
- canonical `DataBundle` -> legacy plotting `DataFrame`

Legacy `measData` derivation rules:

- 1D bundles produce `{"Q": [Q], "I": I, "ISigma": sigma}`
- 2D bundles produce flattened fit vectors from unmasked, finite, nonzero-uncertainty pixels
- if multiple uncertainty sources exist on a `BaseData`, the legacy adapter combines them in
  quadrature

## Current bridge in McData

`McData.to_processing_data()` now provides a derived canonical view of the current legacy state:

- 1D uses `rawData`, `clippedData`, and `binnedData`
- 2D uses `rawData2D` for the raw stage plus `clippedData` and `binnedData`

This is intentionally one-way for now:

- canonical data is available to new code
- legacy internals still remain the source of truth until Phase 3
