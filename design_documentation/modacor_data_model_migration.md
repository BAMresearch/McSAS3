# McSAS3 Migration to MoDaCor Data Classes

## Goal

Replace McSAS3's ad hoc mixture of `pandas.DataFrame`, dict-of-arrays, and plain `measData`
dicts with the MoDaCor data stack:

- `BaseData`: signal + uncertainties + units + metadata
- `DataBundle`: associated `BaseData` objects for one logical dataset
- `ProcessingData`: named collection of bundles

This should reduce duplicated data-handling logic between McSAS3 and MoDaCor and make 1D and 2D
paths look like the same problem again.

## What MoDaCor Gives Us

From the current MoDaCor implementation:

- `BaseData` is the real value object.
  It already carries units, uncertainties, weights, optional axis metadata, copying, slicing,
  and arithmetic support.
- `DataBundle` is a light dictionary for associated datasets.
  Typical scattering usage is a bundle with keys such as `signal`, `Q`, `Psi`, `mask`, etc.
- `ProcessingData` is a light dictionary of `DataBundle` objects.

This means the migration target is not "replace McSAS3 with a new framework". It is mostly
"replace McSAS3's measurement containers with an already-existing shared contract".

## Recommended McSAS3 Mapping

## 1D bundle shape

Recommended bundle contents for one 1D dataset:

```text
DataBundle(
  signal = BaseData(
    signal=I,
    units=1 / (m sr),
    uncertainties={"propagate_to_all": ISigma},
    rank_of_data=1,
  ),
  Q = BaseData(
    signal=Q,
    units=1 / nm,
    uncertainties={"propagate_to_all": QSigma?},
    rank_of_data=1,
  ),
  mask = BaseData(...)             # optional
)
```

Notes:

- `signal` should always mean the dependent intensity.
- `Q` should always mean the independent scattering vector for 1D data.
- Use `propagate_to_all` when the uncertainty is already a single combined one-sigma array.
  That matches current McSAS3 behavior well.
- Keep additional rebinning statistics outside the optimizer contract unless they are actively
  needed.

## 2D bundle shape

Recommended bundle contents for one 2D dataset:

```text
DataBundle(
  signal = BaseData(signal=I2D, units=1 / (m sr), uncertainties={"propagate_to_all": ISigma2D}, rank_of_data=2),
  Qx = BaseData(signal=Qx2D, units=1 / nm, rank_of_data=2),
  Qy = BaseData(signal=Qy2D, units=1 / nm, rank_of_data=2),
  mask = BaseData(signal=mask2D, units=dimensionless, rank_of_data=2),
)
```

Notes:

- For 2D scattering, `Qx` and `Qy` should remain first-class bundle entries rather than trying to
  force them into `axes`.
- Flattened fit vectors should become derived adapter output, not the canonical storage form.

## Stage representation

Today `McData` stores three stages for the same measurement:

- raw
- clipped
- binned

Recommended `ProcessingData` layout:

```text
processing["sample_raw"]
processing["sample_clipped"]
processing["sample_binned"]
```

This is clearer than mixing stage names into bundle keys and will scale better if background,
reference, or calibration bundles are added later.

## Compatibility Strategy

Do not try to make every consumer speak `ProcessingData` on day one.

The lowest-risk migration is:

1. Make `ProcessingData` / `DataBundle` / `BaseData` the canonical internal representation inside
   `McData`.
2. Keep adapters that derive legacy `DataFrame` and `measData` views for old callers.
3. Migrate consumers one boundary at a time.

## Proposed Adapter Layer

Add a small compatibility module in McSAS3, for example:

- `src/mcsas3/data_model.py`
  Re-export or import-shim MoDaCor types.
- `src/mcsas3/data_adapters.py`
  Conversion helpers between McSAS3 legacy structures and MoDaCor bundles.

Suggested helper functions:

- `bundle_from_1d_dataframe(df, *, q_units, i_units) -> DataBundle`
- `bundle_from_2d_arrays(...) -> DataBundle`
- `processing_from_mcdata_stages(...) -> ProcessingData`
- `legacy_measdata_from_bundle(bundle) -> dict`
- `legacy_dataframe_from_bundle(bundle) -> pandas.DataFrame`

The important point is to centralize the legacy translation. Right now the translation logic is
spread over `McData1D`, `McData2D`, the GUI, and tests.

## Module-by-Module Impact

## `McData`, `McData1D`, `McData2D`

This is the primary refactor site.

Recommended new responsibility:

- load source data,
- create `ProcessingData` stages,
- provide compatibility views for legacy callers,
- persist both domain data and processing metadata.

Recommended de-emphasis:

- stop treating `DataFrame` as the primary 1D representation,
- stop treating flattened 2D arrays as the primary 2D representation.

## `McHat` and `McCore`

These can migrate in two steps.

### Step 1

Leave the optimizer contract alone and keep accepting legacy `measData`.

### Step 2

Change the optimizer boundary to accept a `DataBundle` instead of a plain dict and move the
legacy extraction into a single adapter function.

That will let `McCore` explicitly request:

- intensity signal
- intensity uncertainty
- 1D Q or 2D `(Qx, Qy)`

without caring about the source file format.

## `McAnalysis` and `McModelHistogrammer`

These currently re-use the same legacy measurement dict contract.

They should move to the same adapter boundary as the optimizer so that histogramming and
re-analysis operate on the same canonical bundle representation.

## `mc_plot.py`

Plotting should not depend on `pandas.DataFrame` objects being present on `McData`.
It should accept either:

- a `DataBundle`, or
- a thin plotting DTO derived from a `DataBundle`.

## HDF5 persistence

Current HDF5 storage mirrors implementation details. The migration is a good opportunity to make
the stored schema more domain-oriented.

Recommended transitional approach:

1. Keep writing the existing HDF5 groups required by old code and the current GUI.
2. Add a parallel, more structured `ProcessingData`-oriented representation.
3. Move readers to the new representation.
4. Remove dual-write only after the GUI and tests stop depending on legacy paths.

## GUI Impact

The sibling `McSAS3GUI` repo currently depends on:

- `McData1D.rawData`, `clippedData`, and `binnedData` being `DataFrame` objects,
- `mds.measData.copy()` existing,
- exact HDF5 paths inside `/analyses/MCResult1/...`.

That means the GUI should be treated as an external client of this migration, even though it
shares the same project goal.

Recommended GUI transition plan:

1. Add a stable McSAS3 API for "get plot-ready datasets" and "get fit preview data".
2. Update the GUI to call those APIs instead of reaching into `DataFrame` attributes and HDF5
   paths.
3. Only then remove the legacy internals.

## Suggested Staged Plan

## Stage 0: Introduce a compatibility import layer

- Decide whether McSAS3 imports MoDaCor directly or through a thin local shim.
- Hide that decision behind one McSAS3 module so the rest of the repo does not care.

## Stage 1: Canonicalize measurement storage in `McData`

- Represent raw, clipped, and binned states as `ProcessingData` bundles.
- Keep `rawData`, `clippedData`, `binnedData`, and `measData` as derived compatibility views.

This should deliver the biggest cleanup for the least optimizer risk.

## Stage 2: Move the optimizer boundary

- Change `McHat.run(...)` and `McCore(...)` to accept a `DataBundle` or a small typed adapter
  object instead of the raw dict.
- Keep one translation function for legacy callers during the transition.

## Stage 3: Move analysis and plotting

- Make `McAnalysis` and `McPlot` consume the same new measurement contract.
- Remove duplicated assumptions about `Q`, `I`, and `ISigma` field packing.

## Stage 4: Move persistence

- Add structured HDF5 writing for bundle-based data.
- Keep dual-write until the GUI and result-file readers are migrated.

## Stage 5: Remove legacy compatibility

- Remove `measData` as a primary state container.
- Reduce `pandas` usage to places where table semantics are actually useful, such as histogram
  summaries.

## Immediate Risks and Design Decisions

## 1. Dependency boundary

Need to decide whether McSAS3 will:

- depend directly on `modacor`, or
- temporarily import it from a sibling checkout in development only.

For maintainability, a normal package dependency is better. For short-term local refactoring, a
shim can hide that decision.

## 2. Result-file compatibility

Old result files and GUI tooling likely assume the current HDF5 layout. A flag-day storage change
would create avoidable breakage.

## 3. 2D canonical shape

The migration should treat 2D as a first-class case, not as a flattened special case.
Otherwise the same technical debt will reappear under new types.

## 4. Unit normalization

McSAS3 currently relies heavily on comments and convention for units. Once `BaseData` is used,
unit conversions and checks should become explicit at the data-loading boundary.

## Recommended First Implementation Slice

The best first code change is not in the optimizer.

The best first slice is:

1. add a McSAS3 import shim for MoDaCor data classes,
2. make `McData1D` build `ProcessingData` internally,
3. derive legacy `rawData`, `clippedData`, `binnedData`, and `measData` from that,
4. leave `McHat`, `McCore`, `McAnalysis`, and the GUI untouched for the first pass.

That would immediately deduplicate the data handling direction without putting the Monte Carlo
core at risk.
