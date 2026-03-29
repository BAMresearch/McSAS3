# McSAS3 Upgrade Plan

Last updated: 2026-03-29

This is the living implementation plan for upgrading McSAS3 and coordinating the required changes
with the sibling `McSAS3GUI` repository.

## Working assumptions

- `McSAS3GUI` is a separate repo in the same workspace and must be treated as a client of McSAS3.
- The target internal data model is MoDaCor `ProcessingData` / `DataBundle` / `BaseData`.
- We should not keep `measData` as a long-term public or stored data model.
- `McData`, `McData1D`, and `McData2D` are temporary migration scaffolding, not the desired final
  user-facing carrier types.
- Input data should be converted to canonical internal units during ingestion so unit handling does
  not add avoidable overhead in optimizer hot paths.
- The canonical carrier needs an explicit concept for the selected analysis stage; `measDataLink`
  is temporary naming and should be replaced.
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
- [x] `McData1D` now uses canonical `ProcessingData` stage storage with legacy compatibility views.
- [x] `McData2D` now uses canonical `ProcessingData` stage storage with legacy compatibility views.
- [x] `McData` now holds `ProcessingData` as the canonical in-memory representation.
- [ ] Lightweight preprocessing helpers extracted so `McData*` classes can be retired.
- [x] The selected analysis stage is represented canonically without `measData` terminology.
- [x] `McAnalysis`, plotting, and the CLI histogram path now accept canonical selected-stage input.
- [x] Optimizer, analysis, and histogramming now accept direct `DataBundle` / `BaseData` input.
- [x] Input units normalized to standard internal units at ingestion.
- [ ] HDF5 persistence migrated to full archival `ProcessingData` output.
- [ ] McSAS3GUI updated to the new McSAS3 APIs and storage layout.

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
  - `McData2D.from_pandas()` is not implemented
  - `McData2D.from_csv()` is not implemented
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
- legacy tabular views still preserve noncanonical rebin statistics such as `IStd`, `ISEM`,
  `IError`, `QStd`, `QSEM`, and `QError` so existing callers are not broken while the optimizer
  and GUI migration is still pending.
- fast tests now assert that mutating a legacy `rawData` view does not mutate the canonical
  `ProcessingData` bundle state.
- this is an intermediate resting point only; the final target is to extract reusable preprocessing
  helpers and remove `McData1D` as a required carrier type.

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
- this is an intermediate resting point only; the final target is to extract reusable preprocessing
  helpers and remove `McData2D` as a required carrier type.

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
- `McData.to_optimizer_input()` now provides the preferred bridge from canonical stage data into
  the optimizer boundary while preserving `qNudge`.
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
- expose the unique clipping / omission / rebinning logic in a form that can be reused without
  routing every canonical caller through the full `McData` state machine
- switch CLI and notebook-style entry points from `McData*` objects to `ProcessingData`-based
  carriers as a deliberate breaking API change

Acceptance criteria:

- optimization and post-processing consume the same data model
- a fit can start from `ProcessingData` plus an explicit selected stage without constructing a
  `McData*` object

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
- raw 1D and 2D ingestion now normalizes declared or detected source units into canonical
  internal units before legacy compatibility views are published.
- `McData.sourceQUnits` and `McData.sourceIntensityUnits` now record the original source-unit
  declaration or NeXus unit metadata for reproducibility, while preprocessing operates on
  canonical-unit values.
- clipping and omission ranges now apply in canonical internal units because normalization happens
  before preprocessing.

## Phase 6: HDF5 schema and persistence cleanup

Goal: make the result file reflect the real domain model instead of implementation artifacts.

Tasks:

- design a `ProcessingData`-oriented persistence layout
- add readers/writers for canonical bundle data
- write the full archival `ProcessingData` state for original, clipped, and binned stages
- persist the selected analysis stage, preprocessing settings, canonical units, and enough
  metadata to reproduce how the fit input was derived
- keep any temporary migration bridge as short as possible

Notes:

- current status: result files still store legacy compatibility views such as `rawData`,
  `clippedData`, and `binnedData` plus preprocessing settings; canonical `ProcessingData` is
  reconstructed in memory on load rather than stored as a first-class HDF5 schema

Acceptance criteria:

- HDF5 schema maps cleanly onto canonical McSAS3 data objects
- file readers are explicit about old vs. new schema handling
- the result file is archival enough to trace and reproduce how the fit was produced from the
  stored canonical data

## Phase 7: McSAS3GUI coordination

Goal: move the GUI off direct coupling to McSAS3 internals.

Tasks:

- replace GUI use of `McData1D.rawData`, `clippedData`, `binnedData` internals with stable
  McSAS3 APIs
- replace GUI reliance on exact HDF5 internal paths where feasible
- update GUI optimization preview and histogram preview to consume new APIs

Acceptance criteria:

- McSAS3GUI no longer depends on McSAS3 implementation details that we intend to remove

## Phase 8: Maintainability and API hardening

Goal: make the codebase easier to reason about, safer to change, and cheaper to maintain after
the core migration lands.

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
- normalize naming and API surfaces across `McData`, optimizer, analysis, and plotting layers
- consider a lightweight static typing gate in CI once the codebase has broad enough annotations
  to make it useful

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
- remove `qNudge` from McSAS3 APIs, adapters, persistence, and tests; canonical Q coordinates
  should be treated as authoritative and not post-shifted during translation
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

1. Design the archival HDF5 bridge for full `ProcessingData` persistence, including stage
   selection, preprocessing provenance, canonical units, and the metadata needed to reproduce the
   fit input without a `McData*` carrier.
2. Extract lightweight preprocessing helpers so clipping, omission, and rebinning no longer require
   `McData*` carrier objects, then update notebook/CLI-facing workflows to use those helpers plus
   `ProcessingData`.
3. Start removing public notebook and CLI dependence on `McData*` by introducing a direct
   `ProcessingData` preprocessing-and-fit path that can replace the current transitional carrier.

## Update rule for this file

Whenever a step is started or completed:

- update the `Current status` checklist
- update the relevant phase/step status line
- add or adjust acceptance criteria if the scope changed
- keep the ordering stable unless there is a strong reason to resequence work
