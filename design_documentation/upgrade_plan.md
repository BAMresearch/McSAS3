# McSAS3 Upgrade Plan

Last updated: 2026-03-29

This is the living implementation plan for upgrading McSAS3 and coordinating the required changes
with the sibling `McSAS3GUI` repository.

## Working assumptions

- `McSAS3GUI` is a separate repo in the same workspace and must be treated as a client of McSAS3.
- The target internal data model is MoDaCor `ProcessingData` / `DataBundle` / `BaseData`.
- We should not keep `measData` as a long-term public or stored data model.
- `McData`, `McData1D`, and `McData2D` have now been removed from the maintained core repo; GUI
  and downstream callers must use canonical workflows and `ProcessingData` directly.
- Input data should be converted to canonical internal units during ingestion so unit handling does
  not add avoidable overhead in optimizer hot paths.
- The canonical carrier needs an explicit concept for the selected analysis stage; `measDataLink`
  has been replaced and should not reappear.
- If a temporary bridge is needed during migration, keep it private, local, and short-lived.
- The default developer feedback loop must be fast.
  Slow integration tests should become opt-in.
- Ruff is the lint/format source of truth, with flake8-style linting and Black-style formatting.
- Maximum line length is 120.

## Current status

- [x] Internal architecture and migration notes written in `design_documentation/`.
- [x] McSAS3 lint/format config moved toward Ruff and 120-column formatting.
- [x] Ruff/pre-commit hooks validated in both `McSAS3` and `McSAS3GUI`.
- [x] The Ruff/pre-commit rule set has been mirrored into `McSAS3GUI`.
- [x] `tox -e check` validated under the new Ruff-based setup.
- [x] McSAS3 now has an explicit fast default pytest path plus opt-in `integration` / `slow`
  lanes.
- [x] MoDaCor data classes introduced into McSAS3 behind a stable import layer.
- [x] Canonical 1D/2D `ProcessingData` bundle shapes and stage names defined in code and docs.
- [x] `McData1D` now uses canonical `ProcessingData` stage storage.
- [x] `McData2D` now uses canonical `ProcessingData` stage storage.
- [x] `McData` now holds `ProcessingData` as the canonical in-memory representation.
- [x] Lightweight preprocessing helpers extracted so `McData*` classes can be retired.
- [x] The selected analysis stage is represented canonically without `measData` terminology.
- [x] `McAnalysis`, plotting, and the CLI histogram path now accept canonical selected-stage input.
- [x] Optimizer, analysis, and histogramming now accept direct `DataBundle` / `BaseData` input.
- [x] Input units normalized to standard internal units at ingestion.
- [x] HDF5 persistence migrated to full archival `ProcessingData` output without duplicated legacy
  stage groups in new files.
- [x] Public `ProcessingData` workflow helpers exist, and the CLI optimize/histogram path now uses
  them instead of constructing `McData*` directly.
- [x] Public 1D file ingestion now goes through shared canonical helpers instead of routing through
  `McData1D`.
- [x] Public 2D file ingestion now goes through shared canonical helpers instead of routing through
  `McData2D`.
- [x] Transitional wrapper naming now uses `analysisData` / `analysisStage` instead of
  `measData` / `measDataLink` on maintained paths.
- [x] `McData*` no longer maintain a parallel flat analysis-data state; that view is now derived on
  demand from the selected canonical bundle.
- [x] A supported top-level public Python API now points notebooks/scripts at canonical workflow
  functions instead of `McData*`.
- [x] The main in-repo example notebook now uses canonical workflow helpers instead of `McData1D`.
- [x] `McData*` preprocessing now runs from canonical stage bundles instead of wrapper-maintained
  compatibility views.
- [x] `McData*` compatibility views are now derived on demand from canonical stage bundles instead
  of being stored as long-lived wrapper state on supported paths.
- [x] NXsas I/O tests now use temporary files instead of regenerating `testdata/test_nexus_io.nxs`.
- [x] `McData2D` now has an explicit raw-stage ingestion helper so supported tests no longer seed
  it by mutating `rawData2D` / `rawData` directly.
- [x] `McData*` wrapper methods now require canonical raw stages instead of bootstrapping from
  compatibility-view caches or manual `rawData*` assignment.
- [x] Remaining 2D wrapper stubs and mutable-stage helpers have been trimmed further; unsupported
  dataframe-style seed paths are no longer part of the wrapper API.
- [x] Wrapper-specific loader aliases have been collapsed away; transitional wrappers now use
  `from_file()` for file ingest, with only `McData1D.from_pandas()` and `McData2D.from_stage()`
  remaining as non-file seed helpers.
- [x] Wrapper-only convenience methods such as `is2D()` have been removed from the supported
  transition surface.
- [x] Wrapper compatibility-view attributes (`rawData`, `rawData2D`, `clippedData`, `binnedData`,
  `measData`) have been removed; wrappers now fail explicitly if old code tries to use them.
- [x] Unused legacy stage-link adapter helpers have been removed from `data_adapters.py`.
- [x] `McData`, `McData1D`, and `McData2D` have been deleted from `src/mcsas3`.
- [x] Wrapper-specific unit tests have been removed or rewritten to assert against canonical
  workflows, bundles, and preprocessing helpers directly.
- [x] `qNudge` has been removed from maintained McSAS3 adapter and optimizer-input APIs.
- [x] Core-owned stop / interrupt control is now implemented in `McHat` / `McCore`.
- [x] Core API hardening pass `8A` completed on the canonical surface before GUI migration.
- [x] McSAS3GUI updated to the new McSAS3 APIs and storage layout.

## Phase 0: Tooling and test baseline

Goal: make the repo easier to change safely before touching the data model.

### Step 0.1: Ruff and pre-commit baseline

Status: complete.

Deliverables:

- Ruff-based `.pre-commit-config.yaml`
- `pyproject.toml` updated to 120 columns
- `tox -e check` aligned with Ruff

Acceptance criteria:

- `pre-commit run --all-files` passes
- `tox -e check` passes
- The same lint/format rules can be mirrored in `McSAS3GUI`

Notes:

- `pre-commit run --all-files` now passes in both repos.
- The mirror into `McSAS3GUI` caused the expected formatting churn there as well.
- `tox -e check` now passes in `McSAS3`.
- `MANIFEST.in` now includes `design_documentation/` and excludes the ignored local
  `testdata/test.yaml` file so `check-manifest` is stable.
- Ruff now excludes `notebooks/` from the enforced baseline. Notebook cleanup remains separate
  technical debt and should not block core refactoring work.

### Step 0.2: Test suite timing baseline

Status: established for the fast default path and current integration collection cost.

Deliverables:

- a short timing summary for the current test suite
- identification of the slowest files and the slowest individual tests

Acceptance criteria:

- we can point to the current default wall-clock time
- we know which tests dominate runtime and why

Notes:

- current fast default path:
  - `python -m pytest tests`
  - 28 tests passed in about 2.7 s
- current default collection:
  - `python -m pytest tests --collect-only -q`
  - 28 tests collected in about 1.0 s
- current opt-in integration collection:
  - `python -m pytest tests --run-integration --collect-only -q`
  - 37 of 38 tests collected in about 17 s, with the remaining one gated by `--run-slow`
- current opt-in integration execution:
  - `python -m pytest tests/test_optimizer_integraltest.py --run-integration -q`
  - 9 tests passed, 1 deselected, in about 34 s
- main known cost center remains `tests/test_optimizer_integraltest.py`

### Step 0.3: Test taxonomy

Status: implemented for the main heavy optimizer coverage.

Deliverables:

- explicit `slow` and `integration` markers
- default local test command that stays fast
- separate command for expensive end-to-end checks

Acceptance criteria:

- unmarked/default tests finish quickly enough for normal iteration
- expensive optimizer and multiprocess coverage is still available in a separate lane

Notes:

- `tests/test_optimizer_integraltest.py` is now marked as `integration`.
- `test_optimizer_1D_sphere_accuratestate` is additionally marked as `slow`.
- default local runs skip both categories unless explicitly enabled.
- current command patterns:
  - fast default: `python -m pytest tests`
  - integration lane: `python -m pytest tests --run-integration`
  - full heavy lane: `python -m pytest tests --run-integration --run-slow`

## Phase 1: Make McSAS3 tests cheap enough to support refactoring

Goal: move from a monolithic slow suite to layered tests with fast deterministic coverage.

### Step 1.1: Split test layers

Tasks:

- move file-backed, multiprocess, large-iteration tests behind `integration` and/or `slow`
- keep fast logic tests unmarked
- stop using the huge `tests/test_optimizer_integraltest.py` file as the main place for all
  behavior checks

Acceptance criteria:

- default `pytest` no longer runs the full optimizer stress suite
- integration coverage still exists in a separate command

Status:

- the main optimizer integration file is now off the default path
- further splitting and reorganization of that file is still pending

### Step 1.2: Add synthetic fast tests

Status: complete.

Tasks:

- add small deterministic tests for `mc_hdf.py`
- add small deterministic tests for data clipping, omission, binning, and load/restore logic
- add focused tests for optimizer state transitions that do not need large `nRep` or `maxIter`

Acceptance criteria:

- core behaviors are covered without requiring large HDF5 fixtures or long optimizer runs

Notes:

- the fast lane now includes synthetic tests for:
  - `mc_hdf` key/value round-trips and dataframe reconstruction
  - `McData1D` clip/omit/rebin behavior from in-memory dataframes
  - `McData1D` store/load round-trips from synthetic state files
  - `McData2D` clip/mask/q-nudge/reconstruct behavior from synthetic 2D arrays
  - `McData2D` store/load round-trips from synthetic 2D state files
  - `McHat.fillFitParameterLimits` and `McCore.accept` state bookkeeping
- `McData.loadKeys` now includes `qNudge` so restored processed state matches stored state.
- the synthetic coverage also exposed and fixed two HDF/state issues:
  - `ResultIndex` now preserves the requested result index instead of collapsing back to `1`
  - `loadKV(..., default=...)` now returns the default when the target HDF5 file is missing
- the 2D stabilization pass also fixed:
  - `McData2D(loadFromFile=...)` so it now actually loads prior state
  - `McData2D` storage of 2D-only state such as `rawData2D` and orthogonal crop ranges
  - `McData2D.clip()` crop bounds so the last valid row/column is not silently dropped
  - `McData2D.reBin()` now returns a detached copy of `clippedData` instead of aliasing it
- `McData.load()` now tolerates missing stored `csvargs`, which matters for 2D state files that
  intentionally store no CSV reader configuration.
- remaining 2D limitations are still explicit:
  - direct 2D dataframe / CSV wrapper ingest was never completed and has since been removed from
    the supported wrapper surface
  - `McData2D.omit()` remains a warning/no-op

### Step 1.3: Shrink the expensive tests

Status: complete.

Tasks:

- reduce `nRep`, `maxIter`, and large SasModels usage in tests where the exact heavy load is not
  the thing being tested
- prefer one or two representative integration tests over many near-duplicates
- isolate any environment-specific SasModels/OpenCL behavior

Acceptance criteria:

- integration coverage remains meaningful
- total CI runtime drops substantially

Notes:

- the main integration file now uses lean smoke-test defaults for most optimizer runs:
  - `nContrib=96`
  - `maxIter=1500`
  - `nRep=1` for ordinary smoke coverage, with explicit overrides where multiprocessing is the
    thing being exercised
  - a fixed seed for the smoke-style coverage
- the statistically meaningful histogram regression test remains the dedicated `slow` case.
- the integration module now sets:
  - `MPLBACKEND=Agg`
  - `SAS_OPENCL=none`
  - a repo-local `SAS_DLL_PATH`
  so the tests do not depend on GUI backends, OpenCL availability, or writing compiled SasModels
  kernels into the user home directory.
- the simulated-data histogram test no longer depends on prior test order; it can bootstrap its
  own state when run alone, while reusing the multicore fit output during a full file run.
- current integration hot spots after this reduction pass:
  - `test_optimizer_1D_sim1_multicore` about 5.3 s
  - `test_optimizer_1D_sim0_singlecore` about 4.2 s
  - `test_optimizer_1D_sphere_poor_inital_guess` about 2.5 s
- near-duplicate sphere smoke tests were collapsed so the integration file now focuses on distinct
  behaviors:
  - 2D fitting
  - internal sphere model plus re-histogramming/plotting
  - poor-initial-guess robustness
  - hard-sphere structure factor
  - single-core and multi-core simulated-data fitting
  - restore-state / re-histogramming from saved output
  - alternate SasModels kernels and in-place NXsas I/O

## Phase 2: Introduce the shared data-model boundary

Goal: make the MoDaCor types available in McSAS3 without immediately rewriting the whole package.

### Step 2.1: Add a McSAS3 data-model import layer

Status: complete.

Tasks:

- add a local McSAS3 module that imports or re-exports MoDaCor `BaseData`, `DataBundle`, and
  `ProcessingData`
- decide whether the dependency is direct package dependency or transitional workspace coupling

Acceptance criteria:

- the rest of McSAS3 imports the data classes through one stable local module

Notes:

- `src/mcsas3/data_model.py` is now the single McSAS3 import boundary for MoDaCor
  `BaseData` / `DataBundle` / `ProcessingData`.
- the shim prefers an installed `modacor` package and falls back to the sibling workspace
  checkout at `../MoDaCor/src`.
- fast tests now validate the shim against the real MoDaCor types instead of placeholder local
  stand-ins.

### Step 2.2: Define canonical scattering bundle shapes

Status: complete.

Tasks:

- lock down the canonical 1D bundle contract
- lock down the canonical 2D bundle contract
- define stage naming for raw/clipped/binned data in `ProcessingData`

Acceptance criteria:

- all later migration work uses the same agreed bundle keys and units

Notes:

- the canonical contract is now documented in `design_documentation/canonical_data_contract.md`.
- `src/mcsas3/data_adapters.py` defines the shared stage names:
  - `sample_raw`
  - `sample_clipped`
  - `sample_binned`
- the same module now centralizes the transitional conversions between:
  - legacy 1D `DataFrame` state
  - legacy 2D dict-of-arrays state
  - canonical MoDaCor `DataBundle` / `ProcessingData`
  - legacy `measData` and plotting `DataFrame` views
- `McData.to_processing_data()` now exposes a derived canonical `ProcessingData` view without
  changing the current legacy source of truth. This is the intended seam for Phase 3.

## Phase 3: Refactor `McData` to canonical `ProcessingData`

Goal: make data loading/preprocessing use the shared model internally.

### Step 3.1: Canonicalize `McData1D`

Status: complete.

Tasks:

- represent raw, clipped, and binned 1D data as `ProcessingData`
- derive plotting or tabular views from that, rather than storing `DataFrame` as primary state
- remove `measData` from the canonical in-memory path

Acceptance criteria:

- `McData1D` has one real source of truth
- unit and uncertainty handling is explicit in the `BaseData` objects

Notes:

- `McData1D` now keeps `ProcessingData` as its canonical in-memory stage store.
- `rawData`, `clippedData`, `binnedData`, and `measData` remain compatibility outputs, but
  `linkMeasData()` now derives from canonical bundles rather than from `DataFrame` state.
- stage construction now flows through the shared adapter layer for:
  - raw input
  - clipped data
  - rebinned data
- with the breaking migration now accepted, the 1D rebinner no longer carries unused legacy table
  statistics such as `IStd`, `ISEM`, `IError`, `QStd`, `QSEM`, and `QError`; the maintained
  output contract is now the smaller `Q`, `I`, `ISigma`, `QSigma` table plus the canonical
  bundle.
- fast tests now assert that mutating a legacy `rawData` view does not mutate the canonical
  `ProcessingData` bundle state.
- this was an intermediate resting point only; reusable preprocessing has since been extracted and
  the wrapper module has since been removed.

### Step 3.2: Canonicalize `McData2D`

Status: complete.

Tasks:

- represent 2D signal, `Qx`, `Qy`, and mask as bundle entries
- stop treating flattened fit arrays as the primary stored form
- make the 2D path structurally consistent with the 1D path

Acceptance criteria:

- 1D and 2D data loaders produce the same kind of canonical object graph

Notes:

- `McData2D` now keeps `ProcessingData` as its canonical stage store for raw, clipped, and
  rebinned image data.
- canonical 2D stages now carry image-shaped `signal`, `Qx`, `Qy`, and optional `mask` bundle
  entries; flattened fit vectors are derived compatibility output only.
- `rawData2D`, flattened `rawData`, `clippedData`, `binnedData`, and `measData` remain available
  as compatibility views during the optimizer and GUI migration.
- the 2D adapter layer now centralizes the reverse translations from canonical bundles back to:
  - `rawData2D`
  - flattened `rawData`
  - cropped `clippedData` / `binnedData` dictionaries with `invMask`, `Qextent`, and flattened
    fit vectors
- fast tests now assert that mutating the legacy `rawData2D` compatibility dict does not mutate
  the canonical 2D bundle state.
- this was an intermediate resting point only; reusable preprocessing has since been extracted and
  the wrapper module has since been removed.

## Phase 4: Replace `measData` at the optimizer boundary

Goal: stop passing the legacy dict through the execution core.

### Step 4.1: Introduce an explicit optimizer input view

Status: complete.

Tasks:

- define a narrow optimizer-facing adapter or typed view derived from `DataBundle`
- make `McHat`, `McCore`, and `optimizeScalingAndBackground` consume that contract

Acceptance criteria:

- the optimizer no longer depends on `measData`
- there is one well-defined translation from bundle data to execution arrays

Notes:

- `src/mcsas3/optimizer_input.py` now defines `OptimizerInput` plus the canonical conversions from:
  - legacy `measData`
  - canonical `DataBundle`
- `McData.to_optimizer_input()` initially provided the preferred bridge from canonical stage data
  into the optimizer boundary during the migration.
- `McHat`, `McCore`, and `optimizeScalingAndBackground` now consume `OptimizerInput` internally.
- `McAnalysis` and `mc_plot` now read the same typed optimizer input instead of the legacy dict.
- the CLI flow now passes `McData.to_optimizer_input()` into optimization and histogramming, so
  the canonical path is exercised in normal McSAS3 usage.

### Step 4.2: Remove `measData` from stored state

Status: complete.

Tasks:

- stop persisting `measData` as a primary HDF5 concept
- only retain temporary compatibility shims if absolutely necessary during migration

Acceptance criteria:

- no new code relies on `measData`

Notes:

- `McData.store()` no longer writes `measData` into the result HDF5 schema.
- overwrite paths now delete any stale legacy `/mcdata/measData` group before writing current
  state, so refreshed result files do not carry the deprecated structure forward.
- fast 1D and 2D persistence tests now assert that stored files do not contain a `measData`
  group, while reload still reconstructs the compatibility view from canonical stage data plus
  stored preprocessing settings.

## Phase 5: Migrate analysis, histogramming, and plotting

Goal: use the same data model everywhere around optimization and make `ProcessingData` the real
entry point.

Status: in progress.

Tasks:

- move `McAnalysis` and `McModelHistogrammer` to the same canonical measurement contract
- make plotting read bundle-derived views instead of internal `DataFrame` state
- simplify assumptions around `Q`, `I`, and `ISigma` packing
- replace `measDataLink` with a better canonical concept for the selected analysis stage
- make `McHat` / `McCore` accept a canonical sample `DataBundle` or selected `ProcessingData`
  stage directly, with `OptimizerInput` retained only as a private last-mile execution adapter if
  still needed for SasModels kernel setup
- make reduced chi-square, scaling/background fitting, and related optimizer math operate against
  `BaseData`-backed signal and uncertainty without repeated unit-conversion overhead in hot paths
- move input-unit normalization to ingestion / preprocessing boundaries instead of late execution
  stages
- expose the unique clipping / omission / rebinning logic in a form that can be reused directly
  from canonical workflows
- switch CLI and notebook-style entry points from the old `McData*` objects to
  `ProcessingData`-based carriers as a deliberate breaking API change
- add a stop / interrupt mechanism for `McHat` orchestration so GUI or CLI callers can cancel a
  running analysis and all spawned repetition workers terminate cleanly

Acceptance criteria:

- optimization and post-processing consume the same data model
- a fit can start from `ProcessingData` plus an explicit selected stage without any wrapper object

Notes:

- `ProcessingData.analysis_stage` is now the canonical selected-stage marker, replacing the old
  `measDataLink` concept in new code.
- `McData.to_processing_data()` now stamps `analysis_stage`, and `McData.to_analysis_bundle()`
  now returns the selected canonical bundle.
- `McAnalysis` now accepts canonical `ProcessingData` or `DataBundle` input, and the CLI
  histogram path now uses `ProcessingData` instead of legacy `measData`.
- `McPlot.resultCard()` now reads the measurement series from the canonical analysis bundle when it
  is available.
- `McHat` and `McCore` now accept canonical selected-analysis bundles directly.
- `McCore` now derives SasModels kernel Q arrays and scaling/background fit arrays from the
  canonical bundle path, while legacy dict support remains a temporary fallback.
- `optimizeScalingAndBackground` now accepts canonical bundle input directly for the optimizer hot
  path.
- `OptimizerInput` is now reduced to a private compatibility/execution bridge rather than the
  preferred public optimizer contract.
- fast regression coverage now checks that the internal-unit to SasModels-unit bridge preserves
  the expected recovered volume fraction for a sphere model with fixed SLD contrast.
- raw 1D and 2D ingestion now normalizes declared or detected source units into canonical
  internal units before legacy compatibility views are published.
- `McData.sourceQUnits` and `McData.sourceIntensityUnits` now record the original source-unit
  declaration or NeXus unit metadata for reproducibility, while preprocessing operates on
  canonical-unit values.
- clipping and omission ranges now apply in canonical internal units because normalization happens
  before preprocessing.
- Review of MoDaCor processing modules indicates that the reusable value for this migration is the
  `BaseData` / `DataBundle` / `ProcessingData` model itself, not the `ProcessStep` pipeline layer.
- MoDaCor does not currently provide a direct drop-in replacement for McSAS3's 1D clip / omit /
  rebin flow. Its closest related pieces are the scattering-specific `IndexPixels` and
  `IndexedAverager` modules, which assume `Q`, `Psi`, `pixel_index`, and `ProcessStep`
  configuration plumbing.
- For McSAS3, the cleaner path is to extract small local preprocessing helpers that operate
  directly on canonical `DataBundle` objects and preserve current McSAS3 semantics such as
  `IEmin`, `QEMin`, log-Q binning, and the existing tabular uncertainty statistics.
- We should only revisit MoDaCor module reuse later if McSAS3 grows a fuller scattering
  preprocessing pipeline with canonical geometry bundles where `IndexPixels` /
  `IndexedAverager` can be adopted without adapter-heavy glue code.
- That helper layer now lives in `mcsas3.preprocessing`:
  - `prepare_1d_bundle()` for clip / omit / rebin over canonical 1D bundles
  - `prepare_2d_bundle()` for clip plus current 2D pass-through rebin behavior
  - standalone helper functions for clip / omit / rebin so the logic can be reused outside
    `McData*`
- `src/mcsas3/workflows.py` now exposes the direct canonical workflow helpers for:
  - preparing 1D or 2D `ProcessingData`
  - loading/storing canonical `ProcessingData` from result files
  - running optimization from canonical `ProcessingData`
- `src/mcsas3/cli_tools.py` now uses that workflow layer for both optimization and histogramming,
  so the supported CLI path no longer constructs `McData1D` directly.
- `src/mcsas3/ingestion.py` now owns shared 1D file ingestion for CSV, PDH, and 1D NeXus inputs,
  including detected source-unit metadata and rejection of 2D NeXus data on the 1D path.
- `src/mcsas3/ingestion.py` now also owns shared 2D NeXus ingestion, including:
  - default-path discovery from NeXus metadata
  - resolution of combined `Q` datasets into canonical `Qx` / `Qy`
  - optional explicit `pathDict` support for either combined `Q` or split `Qx` / `Qy` datasets
  - detected source-unit metadata for canonical unit normalization
- `prepare_1d_processing_data_from_file()` now reads files directly through that ingestion helper
  instead of constructing `McData1D`.
- `prepare_2d_processing_data_from_file()` now reads files directly through the shared 2D
  ingestion helper instead of constructing `McData2D`.
- `mcsas3.workflows` no longer accepts `measDataLink` in read-config input; canonical config must
  use `analysisStage`.
- adapter and optimizer-bridge naming now follows the same convention on maintained paths:
  - `analysis_data_from_bundle()`
  - `optimizer_input_from_analysis_data()`
- top-level `mcsas3` now re-exports the maintained canonical workflow entry points and carrier
  types, so notebook/script code can stay on:
  - `prepare_*_processing_data*`
  - `optimize_processing_data()`
  - `load_result_processing_data()`
  - `BaseData` / `DataBundle` / `ProcessingData`
- the README now documents that as the supported Python API and explicitly removes the old
  `McData*` wrappers from the maintained surface.
- the main in-repo `notebooks/McSAS3.ipynb` example now uses `prepare_1d_processing_data_from_file`
  plus canonical workflow helpers instead of constructing any wrapper carrier.
- the 1D compatibility tables now expose only canonical stage columns, rather than trying to
  preserve arbitrary extra source columns from the original input dataframe.
- the NXsas read/write tests now copy source data into per-test temporary files and no longer
  leave generated `.nxs` artifacts in `testdata/`.
- `reconstruct_2d_from_clipped_bundle()` now provides the maintained canonical replacement for
  the old 2D wrapper-side `reconstruct2D()` helper.
- the wrapper modules and their dedicated unit-test files have now been removed entirely from the
  repo; maintained tests assert against canonical stage bundles, workflow helpers, and
  preprocessing functions directly.
- the old legacy-stage naming bridge in `data_adapters.py` (`rawData` / `clippedData` /
  `binnedData` stage-link helpers) has been removed because no maintained code still uses it.
- interrupt / stop control should be owned by the McSAS3 core runner lifecycle even if the first
  user-facing trigger is implemented in `McSAS3GUI`; the requirement is to stop all active
  repetition workers launched by `McHat`.
- the 1D integration lane now exercises the canonical workflow helpers for file ingest, result-file
  persistence, and result reload instead of routing those paths through `McData1D`.
- the supported 2D integration lane now also exercises the canonical workflow helper for file
  ingest instead of routing the fit setup through `McData2D`.

## Phase 6: HDF5 schema and persistence cleanup

Goal: make the result file reflect the real domain model instead of implementation artifacts.

Status: implemented with canonical-only writes and canonical-only loads.

Tasks:

- design a `ProcessingData`-oriented persistence layout
- add readers/writers for canonical bundle data
- write the full archival `ProcessingData` state for original, clipped, and binned stages
- persist the selected analysis stage, preprocessing settings, canonical units, and enough
  metadata to reproduce how the fit input was derived
- keep any temporary migration bridge as short as possible

Notes:

- result files now store first-class canonical `ProcessingData` under
  `/analyses/MCResult*/mcdata/processingData`, including:
  - stage bundles for `sample_raw`, `sample_clipped`, and `sample_binned`
  - `BaseData` signal arrays, weights, uncertainties, units, and `rank_of_data`
  - bundle metadata such as `default_plot` and `description`
  - the selected `analysis_stage`
- new result files no longer duplicate legacy `rawData`, `rawData2D`, `clippedData`, or
  `binnedData` groups.
- `load_result_processing_data()` now requires canonical `processingData` and raises if a result
  file only contains the legacy stage-group layout.

Acceptance criteria:

- HDF5 schema maps cleanly onto canonical McSAS3 data objects
- file readers are explicit about requiring the canonical schema
- the result file is archival enough to trace and reproduce how the fit was produced from the
  stored canonical data

## Phase 7: McSAS3GUI coordination

Status: complete.

Goal: move the GUI off direct coupling to McSAS3 internals.

Tasks:

- replace GUI use of `McData1D.rawData`, `clippedData`, `binnedData` internals with stable
  McSAS3 canonical workflow and bundle APIs
- replace GUI reliance on exact HDF5 internal paths where feasible
- update GUI optimization preview and histogram preview to consume new APIs

Acceptance criteria:

- McSAS3GUI no longer depends on McSAS3 implementation details that we intend to remove

Notes:

- `McSAS3GUI` now centralizes its McSAS3 coupling in a small bridge module instead of importing
  removed wrapper types or embedding HDF5 path strings in widgets
- the data-loading tab now prepares canonical `ProcessingData` via McSAS3 workflow helpers and
  derives plotting frames from canonical stage bundles rather than `McData1D.rawData`,
  `clippedData`, and `binnedData`
- the run-settings tab now triggers preview optimizations through
  `optimize_processing_data(...)` and loads preview metrics through the GUI bridge instead of
  calling `McHat.run(mds.measData.copy(), ...)` and reading `/analyses/.../mcdata/measData/...`
  directly
- the GUI optimization and preview buttons now enter an explicit running/abort state and use the
  core-owned `McHat.request_stop()` hook instead of relying on subprocess termination
- targeted GUI bridge tests and GUI-side Ruff checks were run against the current McSAS3 source
  tree on `PYTHONPATH`, confirming that the GUI now works against the stabilized canonical API
- GUI-side `pytest` collection now bootstraps the sibling `McSAS3/src` checkout automatically via
  `tests/conftest.py`, so local development no longer depends on manually exporting `PYTHONPATH`
  just to keep the GUI tests on the current core source tree

## Phase 8: Maintainability and API hardening

Goal: make the codebase easier to reason about, safer to change, and cheaper to maintain after
the core migration lands.

Status: split into `8A` before `McSAS3GUI` migration and `8B` after the GUI validates the
stabilized core API.

Tasks:

- simplify module boundaries and reduce duplicated 1D / 2D logic where the behavior is genuinely
  shared
- factor clipping, omission, rebinning, optimizer preparation, and persistence translation into
  smaller, testable units with clearer ownership
- remove transitional or redundant compatibility code once the replacement path is proven
- tighten `attrs` model definitions:
  - add validators and converters where configuration enters the system
  - avoid mutable class-level defaults and hidden shared state
  - prefer explicit initialization and post-init normalization over ad hoc mutation in methods
- add type hints to remaining untyped methods and narrow overly broad `dict` / `object` usage
- add modest docstrings to public classes and methods, plus non-obvious internal helpers where the
  behavior is easy to misread
- replace user-facing `assert` validation with explicit exceptions where the failure mode is part
  of normal input or file handling rather than an internal invariant
- replace leftover `print` debugging with structured logging at appropriate levels
- streamline data copying and compatibility-view generation so the code does not maintain more
  parallel state than necessary
- normalize naming and API surfaces across the canonical workflow, optimizer, analysis, and
  plotting layers
- consider a lightweight static typing gate in CI once the codebase has broad enough annotations
  to make it useful

### Step 8A: Core API hardening before GUI migration

Status: complete.

Tasks:

- remove remaining legacy naming such as `analysisData` on maintained public and semi-public core
  paths
- replace user-facing `assert` validation with explicit exceptions on the maintained canonical
  surface
- tighten validation and modest typing/docstrings on the canonical workflow, optimizer, analysis,
  and histogramming entry points
- define the core-owned stop / interrupt interface for `McHat` orchestration

Acceptance criteria:

- the canonical core API is explicit enough that `McSAS3GUI` can migrate against it without
  guessing intent from old names or assertion failures
- the remaining breaking changes are deliberate and documented before GUI harmonization starts

Notes:

- maintained entry points now use `analysis_input` naming on the core path
- assertion-style validation has been replaced with explicit `ValueError` / `TypeError` failures
  across the maintained canonical/public surface, including CLI config handling, HDF helpers,
  optimizer preparation, analysis, histogramming, and model configuration
- canonical analysis-data and optimizer-input helpers now use authoritative canonical Q
  coordinates directly; `qNudge` has been removed from the maintained surface
- `McHat` now exposes a core-owned stop request path (`request_stop()`, `clear_stop_request()`,
  `stop_requested()`, `isRunning`, `lastRunStopped`) and `McCore.optimize()` now honors that stop
  callback so in-flight repetitions exit cleanly instead of only stopping between repetitions
- default tests, opt-in integration tests, and `tox -e check` all pass after the hardening pass,
  so `McSAS3GUI` can now migrate against the stabilized core API

### Step 8B: Post-GUI cleanup and simplification

Status: pending.

Tasks:

- use the `McSAS3GUI` migration as the final client review of the core API
- remove any cleanup targets that turned out not to matter to the GUI or supported workflows
- continue de-duplication, typing, logging cleanup, and structural simplification after the GUI is
  off internal assumptions

Acceptance criteria:

- major modules have clearer single responsibilities and less duplicated logic
- object validation is explicit and reliable at API boundaries
- most maintained code paths have meaningful type hints and concise docstrings
- internal state transitions are easier to follow and require fewer compatibility shims

## Phase 9: Documentation and release delivery

Goal: leave McSAS3 in a form that users can install, understand, and run without reading the
source tree.

Tasks:

- refresh top-level documentation once the new data model and public APIs are stable
- add a concise quickstart covering:
  - installation
  - preparing input data
  - running a basic optimization
  - inspecting or plotting results
- document the supported workflows for CLI, Python usage, and result-file handling
- add migration notes where user-visible behavior changed during the refactor
- document the breaking transition from `McData*` / `measData` notebook workflows to
  `ProcessingData`-based workflows
- define a release engineering path for packaged user distributions on:
  - macOS
  - Windows
  - Linux
- choose and implement the packaging approach for standalone user-facing builds
- validate packaged builds on each target platform with a minimal smoke-test workflow

Acceptance criteria:

- a new user can get from install to first result using the quickstart documentation
- release artifacts exist in a reproducible form for macOS, Windows, and Linux
- the documented workflows match the actual supported interfaces

## Phase 10: Final cleanup

Goal: remove temporary bridges and freeze the new model.

Tasks:

- remove any remaining private compatibility shims
- remove obsolete config and tests tied to the legacy model
- refresh internal docs and user docs

Acceptance criteria:

- there is one canonical internal data model
- test and tooling defaults are fast enough to support ongoing maintenance

## Phase 11: McSAS3GUI follow-on

Goal: apply the same architectural cleanup, API hardening, testing discipline, documentation, and
release readiness to McSAS3GUI after the McSAS3 core contract is stable.

Tasks:

- realign McSAS3GUI against the stabilized McSAS3 public APIs instead of internal implementation
  details
- repeat the same maintainability pass in the GUI repo:
  - simplify module boundaries
  - improve typing and validation
  - remove unnecessary legacy code
  - strengthen tests and tooling
- refresh McSAS3GUI user documentation and quickstart material
- provide packaged user-facing GUI builds for macOS, Windows, and Linux if that remains the chosen
  delivery model

Acceptance criteria:

- McSAS3GUI depends only on stable McSAS3 interfaces
- the GUI repo reaches the same baseline for maintainability, testing, docs, and packaging as the
  core repo

## Immediate next steps

These are the next three steps I recommend working on in order:

1. Finish `8A` on the maintained core API:
   - remove remaining legacy naming such as `analysisData`
   - replace assertion-style validation with explicit exceptions on maintained entry points
   - define stop / interrupt control for `McHat`
2. Update `McSAS3GUI` to the canonical McSAS3 APIs, selected-stage model, and canonical HDF5
   layout now that `McData*` modules are gone from the core repo.
3. Finish the user-facing documentation and release track: quickstart, migration notes, and
   packaged builds for macOS, Windows, and Linux.

## Update rule for this file

Whenever a step is started or completed:

- update the `Current status` checklist
- update the relevant phase/step status line
- add or adjust acceptance criteria if the scope changed
- keep the ordering stable unless there is a strong reason to resequence work
