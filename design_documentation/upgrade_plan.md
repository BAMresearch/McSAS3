# McSAS3 Upgrade Plan

Last updated: 2026-03-28

This is the living implementation plan for upgrading McSAS3 and coordinating the required changes
with the sibling `McSAS3GUI` repository.

## Working assumptions

- `McSAS3GUI` is a separate repo in the same workspace and must be treated as a client of McSAS3.
- The target internal data model is MoDaCor `ProcessingData` / `DataBundle` / `BaseData`.
- We should not keep `measData` as a long-term public or stored data model.
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
- [ ] MoDaCor data classes introduced into McSAS3 behind a stable import layer.
- [ ] `McData` refactored to use `ProcessingData` as the canonical internal representation.
- [ ] Optimizer, analysis, and histogramming migrated off `measData`.
- [ ] HDF5 persistence migrated to the new canonical data model.
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
  - 26 of 27 tests collected in about 16 s, with the remaining one gated by `--run-slow`
- current opt-in integration execution:
  - `python -m pytest tests/test_optimizer_integraltest.py --run-integration -q`
  - 12 tests passed, 1 deselected, in about 51 s
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

Status: partially complete.

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
  - `nRep=2`
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
  - `test_optimizer_1D_sim0_singlecore` about 8.3 s
  - `test_optimizer_1D_sim1_multicore` about 5.4 s
  - `test_optimizer_1D_sphere_poor_inital_guess` about 4.9 s
- near-duplicate sphere-based integration tests still exist, so further consolidation remains
  possible if we want to push the integration lane down further.

## Phase 2: Introduce the shared data-model boundary

Goal: make the MoDaCor types available in McSAS3 without immediately rewriting the whole package.

### Step 2.1: Add a McSAS3 data-model import layer

Tasks:

- add a local McSAS3 module that imports or re-exports MoDaCor `BaseData`, `DataBundle`, and
  `ProcessingData`
- decide whether the dependency is direct package dependency or transitional workspace coupling

Acceptance criteria:

- the rest of McSAS3 imports the data classes through one stable local module

### Step 2.2: Define canonical scattering bundle shapes

Tasks:

- lock down the canonical 1D bundle contract
- lock down the canonical 2D bundle contract
- define stage naming for raw/clipped/binned data in `ProcessingData`

Acceptance criteria:

- all later migration work uses the same agreed bundle keys and units

## Phase 3: Refactor `McData` to canonical `ProcessingData`

Goal: make data loading/preprocessing use the shared model internally.

### Step 3.1: Canonicalize `McData1D`

Tasks:

- represent raw, clipped, and binned 1D data as `ProcessingData`
- derive plotting or tabular views from that, rather than storing `DataFrame` as primary state
- remove `measData` from the canonical in-memory path

Acceptance criteria:

- `McData1D` has one real source of truth
- unit and uncertainty handling is explicit in the `BaseData` objects

### Step 3.2: Canonicalize `McData2D`

Tasks:

- represent 2D signal, `Qx`, `Qy`, and mask as bundle entries
- stop treating flattened fit arrays as the primary stored form
- make the 2D path structurally consistent with the 1D path

Acceptance criteria:

- 1D and 2D data loaders produce the same kind of canonical object graph

## Phase 4: Replace `measData` at the optimizer boundary

Goal: stop passing the legacy dict through the execution core.

### Step 4.1: Introduce an explicit optimizer input view

Tasks:

- define a narrow optimizer-facing adapter or typed view derived from `DataBundle`
- make `McHat`, `McCore`, and `optimizeScalingAndBackground` consume that contract

Acceptance criteria:

- the optimizer no longer depends on `measData`
- there is one well-defined translation from bundle data to execution arrays

### Step 4.2: Remove `measData` from stored state

Tasks:

- stop persisting `measData` as a primary HDF5 concept
- only retain temporary compatibility shims if absolutely necessary during migration

Acceptance criteria:

- no new code relies on `measData`

## Phase 5: Migrate analysis, histogramming, and plotting

Goal: use the same data model everywhere after optimization.

Tasks:

- move `McAnalysis` and `McModelHistogrammer` to the same canonical measurement contract
- make plotting read bundle-derived views instead of internal `DataFrame` state
- simplify assumptions around `Q`, `I`, and `ISigma` packing

Acceptance criteria:

- optimization and post-processing consume the same data model

## Phase 6: HDF5 schema and persistence cleanup

Goal: make the result file reflect the real domain model instead of implementation artifacts.

Tasks:

- design a `ProcessingData`-oriented persistence layout
- add readers/writers for canonical bundle data
- keep any temporary migration bridge as short as possible

Acceptance criteria:

- HDF5 schema maps cleanly onto canonical McSAS3 data objects
- file readers are explicit about old vs. new schema handling

## Phase 7: McSAS3GUI coordination

Goal: move the GUI off direct coupling to McSAS3 internals.

Tasks:

- replace GUI use of `McData1D.rawData`, `clippedData`, `binnedData` internals with stable
  McSAS3 APIs
- replace GUI reliance on exact HDF5 internal paths where feasible
- update GUI optimization preview and histogram preview to consume new APIs

Acceptance criteria:

- McSAS3GUI no longer depends on McSAS3 implementation details that we intend to remove

## Phase 8: Final cleanup

Goal: remove temporary bridges and freeze the new model.

Tasks:

- remove any remaining private compatibility shims
- remove obsolete config and tests tied to the legacy model
- refresh internal docs and user docs

Acceptance criteria:

- there is one canonical internal data model
- test and tooling defaults are fast enough to support ongoing maintenance

## Immediate next steps

These are the next three steps I recommend working on in order:

1. Validate `tox -e check` under the new Ruff-based setup.
2. Add synthetic fast tests for HDF5, clipping, omission, binning, and small optimizer state transitions.
3. Reduce and reorganize the expensive integration coverage in `tests/test_optimizer_integraltest.py`.

## Update rule for this file

Whenever a step is started or completed:

- update the `Current status` checklist
- update the relevant phase/step status line
- add or adjust acceptance criteria if the scope changed
- keep the ordering stable unless there is a strong reason to resequence work
