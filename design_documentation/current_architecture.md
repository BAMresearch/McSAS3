# McSAS3 Current Architecture

## Scope

The current `McSAS3` repository is the optimizer, result persistence layer, and
histogramming/plotting pipeline. It does not contain the GUI itself. The GUI currently lives in
the sibling `McSAS3GUI` repository and depends on several McSAS3 internals.

At a high level, McSAS3 is a small library plus CLI wrappers around a Monte Carlo acceptance /
rejection optimizer for scattering data.

## Package Map

### Entry points

- `src/mcsas3/__main__.py`
  Runs optimization and histogramming in sequence.
- `src/mcsas3/mcsas3_cli_runner.py`
  Optimization-only CLI.
- `src/mcsas3/mcsas3_cli_histogrammer.py`
  Histogramming-only CLI.
- `src/mcsas3/cli_tools.py`
  Thin orchestration layer used by the CLIs.

Important current limitation:

- the CLI path is effectively 1D-only today because `cli_tools.py` instantiates `McData1D`
  directly for both optimization input and histogramming reload.

### Data loading and preprocessing

- `src/mcsas3/mc_data.py`
  Base class for file loading, clipping, binning, `measData` creation, and HDF5
  serialization.
- `src/mcsas3/mc_data_1d.py`
  Main production path today. Uses `pandas.DataFrame` for raw, clipped, and binned data.
- `src/mcsas3/mc_data_2d.py`
  Partial 2D support. Uses a mix of flattened `DataFrame` data and dict-based 2D arrays.

### Optimization

- `src/mcsas3/mc_hat.py`
  Repetition-level orchestration and multiprocessing.
- `src/mcsas3/mc_core.py`
  Inner Monte Carlo loop for one repetition.
- `src/mcsas3/mc_model.py`
  Model abstraction, random parameter generation, and SasModels integration.
- `src/mcsas3/mc_opt.py`
  Optimization state container.
- `src/mcsas3/osb.py`
  Scaling/background fit for measured vs. modeled intensity.

### Analysis and output

- `src/mcsas3/mc_model_histogrammer.py`
  Histograms a single repetition.
- `src/mcsas3/mc_analysis.py`
  Re-loads all repetitions, aggregates histograms and optimization statistics.
- `src/mcsas3/mc_plot.py`
  Produces the PDF result card.
- `src/mcsas3/mc_hdf.py`
  Generic HDF5 persistence helpers and the `ResultIndex` path helper.

### Tests

- `tests/test_McData1D_unittest.py`
  Main coverage of data loading and result-file restore.
- `tests/test_McData2D_unittest.py`
  Minimal 2D smoke coverage.
- `tests/test_optimizer_integraltest.py`
  End-to-end optimization and histogramming tests.

## Runtime Flow

## 1. Optimization flow

1. CLI reads the YAML read configuration and run configuration.
2. `McSAS3_cli_optimize` constructs `McData1D`.
3. `McData1D` loads the source file, clips, omits ranges, rebins, and builds `measData`.
4. `McData.store()` writes the data state into the output HDF5 file.
5. `McHat` builds shared `McModel` and `McOpt` configuration.
6. For each repetition, `McCore`:
   - builds the SasModels kernel,
   - initializes the summed model intensity from all contributions,
   - repeatedly proposes a new contribution,
   - re-fits scaling/background,
   - accepts the move if GOF improves.
7. Each repetition stores model parameters and optimization state to HDF5.

The important execution boundary is:

`McData*` -> `measData` plain dict -> `McHat` / `McCore`

That boundary is the easiest place to introduce a new shared data model without rewriting the
optimizer in one pass.

## 2. Histogramming flow

1. CLI reads the result file and histogram YAML.
2. `McData1D(loadFromFile=...)` reconstructs measurement data from HDF5.
3. `McAnalysis` discovers all stored repetitions.
4. For each repetition, `McAnalysis` rebuilds a `McCore` object from stored model and
   optimization state.
5. `McModelHistogrammer` produces per-range histograms and mode statistics.
6. `McAnalysis` averages histograms, fit statistics, and model intensities over repetitions.
7. `McPlot` writes the PDF summary card.

## Current Data Representations

McSAS3 currently uses several incompatible representations for essentially the same
measurement.

### 1D path

- `rawData`: `pandas.DataFrame` with `Q`, `I`, `ISigma`
- `clippedData`: `pandas.DataFrame`
- `binnedData`: `pandas.DataFrame`, usually with extra statistics columns such as `IStd`,
  `ISEM`, `QStd`, `QSigma`, ...
- `measData`: plain `dict`
  - `Q`: a one-element list containing the Q array
  - `I`: intensity array
  - `ISigma`: uncertainty array

### 2D path

- `rawData2D`: dict of 2D arrays such as `I`, `ISigma`, `Qx`, `Qy`, `mask`
- `rawData`: flattened `DataFrame`
- `clippedData`: dict containing both cropped 2D arrays and flattened fit arrays
- `binnedData`: currently just `clippedData`
- `measData`: plain `dict`
  - `Q`: two-element list `[Qy, Qx]`
  - `I`: flattened intensity array
  - `ISigma`: flattened uncertainty array

### Observations

- The same logical dataset is represented as `DataFrame`, dict-of-arrays, and plain dict.
- The 1D and 2D representations diverge significantly.
- Units exist only by convention and comments, not as a first-class runtime contract.
- Uncertainties are reduced to a single array at the optimizer boundary.
- `McData` combines file IO, preprocessing, transient cache state, and persistence.

## Current HDF5 Layout

The result file is rooted under:

`/analyses/MCResult{resultIndex}`

Main groups:

- `mcdata`
  Stored read/preprocessed data state and configuration.
- `model`
  Shared model configuration plus per-repetition parameter sets and volumes.
- `optimization`
  Global optimization settings plus per-repetition optimization state.
- `histograms`
  Per-range / per-repetition histograms and averaged histogram outputs.

Approximate structure:

```text
/analyses/MCResult1
  /mcdata
    /rawData
    /clippedData
    /binnedData
    /measData
    filename
    loader
    nbins
    ...
  /model
    /fitParameterLimits
    /staticParameters
    modelName
    /repetition0
      /parameterSet
      seed
      volumes
      modelDType
    /repetition1
      ...
  /optimization
    nCores
    nRep
    /repetition0
      modelI
      gof
      x0
      accepted
      acceptedSteps
      acceptedGofs
      ...
    /average
      ...
  /histograms
    /histRange0
      /repetition0
      /average
    /histRange1
      ...
```

## Coupling to McSAS3GUI

The sibling `McSAS3GUI` repository is currently coupled to McSAS3 internals in several ways.

### Direct library coupling

- `DataLoadingTab` imports `McData1D` directly and plots `rawData`, `clippedData`, and
  `binnedData` as `DataFrame` objects.
- `RunSettingsTab` imports `McHat` directly and passes `mds.measData.copy()` into
  `McHat.run(...)`.

### Direct result-file coupling

- The GUI reads HDF5 paths such as
  `/analyses/MCResult1/mcdata/measData/Q` and
  `/analyses/MCResult1/optimization/repetition0/modelI` directly.

### Process-level coupling

- Histogram tests in the GUI shell out to `python -m mcsas3.mcsas3_cli_histogrammer`.

This means a data-model migration inside McSAS3 should assume:

- temporary compatibility for `measData`,
- temporary compatibility for result-file structure,
- or a coordinated update in `McSAS3GUI` at the same time.

## Strengths of the Current Design

- The optimization core is relatively isolated from file-format specifics once it receives
  `measData`.
- The result file already acts as a reproducible state bundle for re-histogramming.
- SasModels integration is encapsulated behind `McModel`.
- Histogramming is already decoupled from optimization execution.

## Main Technical Debt Areas

### Data model fragmentation

This is the central issue. The same measurement changes shape several times before the optimizer
sees it, and the representations are only loosely documented.

### `McData` does too much

`McData` mixes:

- source loading,
- preprocessing,
- stage caching,
- legacy execution contract generation,
- and HDF5 serialization.

### 1D and 2D are structurally inconsistent

2D support exists, but its internal contract is not the same as the 1D path and several
methods remain partial or unimplemented. In particular, the current CLI flow does not route
through `McData2D`, `McData2D.reBin()` is still a no-op passthrough, and restore/load handling is
less complete than the 1D path.

### Storage schema is implementation-shaped

The HDF5 layout mirrors current Python structures rather than a stable domain model.

### GUI depends on internals, not stable APIs

The GUI currently assumes both in-memory representations and exact HDF5 paths.

## Immediate Refactor Conclusion

The best seam for introducing the MoDaCor model is not inside `McCore` first. It is between
`McData` and the rest of the pipeline:

- replace internal raw/clipped/binned containers with `BaseData`-based structures,
- keep a compatibility adapter that still produces legacy `measData`,
- then migrate optimizer, analysis, storage, and GUI incrementally.
