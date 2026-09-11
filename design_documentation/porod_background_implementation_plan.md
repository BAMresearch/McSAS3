# Optional Fitted Porod Background: Implementation Plan

Last updated: 2026-09-11

This is the living implementation record for coordinated changes in the `McSAS3` and
`McSAS3GUI` repositories. Update the status checklist and implementation log whenever work starts,
stops, changes direction, or completes so another session can resume without reconstructing the
design from source history.

## Current status

- [x] Existing core and GUI data flow inspected
- [x] Mathematical and configuration contract agreed
- [x] Persistence and backward-compatibility requirements identified
- [x] Phase 1: core fit representation and configuration
- [x] Phase 2: Porod-aware optimizer
- [x] Phase 3: result persistence, reload, and analysis
- [x] Phase 4: GUI preview and packaged configurations
- [x] Phase 5: documentation, compatibility, and full validation
- [x] Visualization follow-up: fitted background curves

Feature implementation, including the fitted-background visualization follow-up, is complete. Core
and GUI test suites, package-isolated tox, check-manifest, Ruff, and Sphinx checks pass. The local
Homebrew Python/libexpat mismatch remains an environment issue, but validation was completed with
a clean isolated Python 3.12 environment; details are recorded in the implementation log.

## Goal

Optionally fit an additive Porod-shaped background alongside the existing overall model scale and
flat background during every inner least-squares optimization:

```text
I_fit(q) = scale * I_model(q) + background + porodCoefficient * q^-4
```

Constraints:

- `scale >= 0`, preserving the existing scale constraint;
- `background` keeps its existing bounds;
- `porodCoefficient >= 0`;
- the new contribution is disabled by default;
- disabling it preserves the existing two-parameter behavior and result representation;
- the coefficient and complete fitted curve remain available after reload and histogram analysis.

The fitted quantity is named `porodCoefficient`, not “Porod slope,” because the exponent/slope is
fixed at `-4`. The term is an independent additive background and is not multiplied by the model
scale.

## Non-goals

- Do not fit the power-law exponent in this change.
- Do not add negative Porod contributions.
- Do not reuse `McSimPseudoModel.extrapScaling`. That setting controls extrapolation beyond a
  simulated model's tabulated high-Q range; it is not a measurement-background fit parameter.
- Do not place this option in `staticParameters`, which are model/kernel parameters.
- Do not change the Monte Carlo proposal or acceptance algorithm.
- Do not change the existing GOF normalization or convergence interpretation as part of this
  feature.
- A dedicated GUI checkbox is not required initially. The maintained GUI configuration surface is
  the run-settings YAML editor. A checkbox can be considered separately if it can remain reliably
  synchronized with the YAML document.

## Configuration contract

Add one top-level run option:

```yaml
fitPorodBackground: false
```

Rules:

- default: `false`;
- accepted values: booleans only;
- `false` produces the current `[scale, background]` fit;
- `true` produces `[scale, background, porodCoefficient]`;
- the option is owned by `McOpt`, allowing the existing `McHat` keyword routing to pass it through
  without a new CLI or GUI worker protocol;
- shipped examples should show the option as `false` or include a concise commented example.

The model's static `background` should remain zero in normal configurations so the base optimizer
is the single owner of additive backgrounds.

## Q and units contract

Use canonical optimizer Q coordinates. McSAS3 canonical Q is expressed numerically in `1/nm`.

- For 1D data, use `abs(Q)`.
- For 2D data, use the radial magnitude `sqrt(Qx**2 + Qy**2)`.
- All fitted Q magnitudes must be finite and strictly positive when the feature is enabled.
- If an unmasked `Q == 0` point reaches the optimizer, fail with a clear validation error rather
  than silently clipping Q or inventing a floor. A beam-centre pixel can instead be masked during
  preprocessing.
- The stored coefficient is defined against canonical Q: reconstruct the contribution exactly as
  `porodCoefficient * q_support**-4`.

Because raw `q^-4` values can span many orders of magnitude, the optimizer must normalize the
Porod basis internally. A suitable internal parameter is the contribution at the smallest fitted
positive Q:

```text
normalizedBasis(q) = (q_min / q)^4
internalAmplitude = porodCoefficient / q_min^4
```

The internal amplitude is optimized with a lower bound of zero. Convert it back to
`porodCoefficient` before returning or storing fit parameters. Internal normalization must not
change the public reconstruction formula.

## Result and compatibility contract

The current optimizer state stores a positional `x0` array. Preserve the existing positions:

```text
x0[0] = scale
x0[1] = background
x0[2] = porodCoefficient  # present only when enabled
```

Also store parameter-name metadata, proposed as:

```text
x0ParameterNames = ["scale", "background", "porodCoefficient"]
```

Compatibility rules:

- Old files without `fitPorodBackground` or `x0ParameterNames` load as the two-parameter form.
- New files with the feature disabled continue to store a two-element `x0`.
- A three-element legacy-style vector without name metadata may be inferred as the Porod-enabled
  form, but new output must always include names.
- New optional HDF fields must be loaded through optional/default-aware reads. Do not append them
  blindly to the current required `loadKVPairs` list because that would break old files.
- The analysis layer should report `porodCoefficient` as an optimization statistic. For old and
  disabled results its value is zero.
- Histogram volume-fraction scaling continues to use only `x0[0]`; the Porod coefficient must not
  affect histogram normalization.

Introduce one core helper for reconstructing fitted intensity from model intensity, Q support,
and fit parameters. Use it in core tests and `McAnalysis`. McSAS3GUI may call the public helper
after its minimum McSAS3 version is advanced, avoiding a third independent copy of the formula.

## Current code map

### McSAS3

- `src/mcsas3/osb.py`
  - currently discards Q while coercing measurement input;
  - constructs two bounds and a two-element initial guess;
  - minimizes `scale * modelI + background` with TNC.
- `src/mcsas3/optimizer_input.py`
  - already exposes dimension-independent radial `q_support`.
- `src/mcsas3/mc_opt.py`
  - owns optimization configuration/state and HDF store/load keys;
  - currently stores positional `x0` without names.
- `src/mcsas3/mc_hat.py`
  - routes recognized `McOpt.storeKeys` from run YAML into `McOpt`.
- `src/mcsas3/mc_core.py`
  - constructs the scale/background optimizer and carries `x0` between accepted moves.
- `src/mcsas3/mc_analysis.py`
  - currently reports only scaling/background and reconstructs intensity with a duplicated
    two-term expression.
- `src/mcsas3/mc_model_histogrammer.py`
  - uses `x0[0]` for volume-fraction scaling; this behavior must remain unchanged.
- `tests/test_mc_core_fast.py`
  - contains the current optimizer, core state, and HDF-backed analysis regression coverage.

### McSAS3GUI

- `src/mcsas3gui/gui/optimization_worker.py`
  - already forwards top-level run YAML to `McHat`; no special new transport should be needed.
- `src/mcsas3gui/gui/mcsas3_bridge.py`
  - loads raw `modelI`, Q, and positional `x0` for previews.
- `src/mcsas3gui/gui/run_settings_tab.py`
  - currently plots `x0[0] * modelI + x0[1]` and must use Porod-aware reconstruction.
- `src/mcsas3gui/configurations/run/` and inline prefab run configurations
  - should document the default-off switch without enabling it silently for existing examples.
- `tests/test_mcsas3_bridge.py`, `tests/test_run_settings_tab.py`, and
  `tests/test_optimization_worker.py`
  - are the main GUI regression targets.
- `pyproject.toml`
  - must require the first McSAS3 release containing the shared reconstruction API before the GUI
    imports it.

## Implementation phases

### Phase 1: core fit representation and configuration

- [x] Add validated `fitPorodBackground: bool = False` state to `McOpt`.
- [x] Route the option into `optimizeScalingAndBackground` from `McCore`.
- [x] Define constants or a small named accessor for fit-vector indices; avoid introducing more
  unexplained positional indexing.
- [x] Add `x0ParameterNames` persistence state.
- [x] Add a shared fitted-intensity reconstruction helper supporting both two- and three-parameter
  results.
- [x] Add focused tests proving the disabled path retains two parameters and the existing formula.

Checkpoint: top-level YAML accepts the option, but no production path enables a Porod fit until
Phase 2 is complete.

### Phase 2: Porod-aware optimizer

- [x] Preserve Q when canonical bundles or `OptimizerInput` instances are coerced in `osb.py`.
- [x] Keep raw-array construction backward compatible; require an explicit Q array only if the
  Porod option is enabled.
- [x] Build 1D/2D radial Q support and validate shape, finiteness, and strict positivity.
- [x] Add the normalized Porod predictor and non-negative coefficient bound.
- [x] Retain initial-vector shape validation. The selected bounded linear solver does not require a
  warm start; stored external coefficients are converted only at the normalized result/bounds
  boundary.
- [x] Decide after a focused benchmark whether to extend the current TNC minimization or use a
  bounded linear least-squares solve for the three linear base parameters. Prefer the lowest-risk
  option that is numerically stable and does not slow the Monte Carlo hot loop materially.
- [x] Check optimizer success explicitly and raise or log a useful failure instead of silently
  consuming an unsuccessful result.
- [x] Add synthetic recovery and bound tests.

Checkpoint: a direct core run can fit a known non-negative Porod coefficient, while feature-off
results remain equivalent to the baseline within existing tolerances.

### Phase 3: persistence, reload, and analysis

- [x] Store `fitPorodBackground`, `x0ParameterNames`, and the optional third `x0` value per
  repetition.
- [x] Implement optional/default-aware loading for old result files.
- [x] Ensure `McCore(loadFromFile=...)` reconstructs the correct optimizer before reevaluation.
- [x] Add `porodCoefficient` to repetition and averaged optimization statistics.
- [x] Reconstruct each repetition's complete fitted intensity, including the Porod contribution,
  before averaging in `McAnalysis`.
- [x] Confirm histogram scaling and modes still use model scale only.
- [x] Add old-file, disabled-new-file, and enabled-new-file HDF round-trip tests.

Checkpoint: histogramming/reanalysis works for both pre-feature files and new Porod-enabled files,
and stored averaged curves match their component formula.

### Phase 4: McSAS3GUI integration

- [x] Load fit-parameter names or equivalent Porod metadata in `OptimizationPreview1D`.
- [x] Use the shared core reconstruction helper for preview fit curves.
- [x] Keep preview loading compatible with old two-element `x0` files.
- [x] Show `fitPorodBackground` in run-settings configuration details/help.
- [x] Add default-off examples to maintained run configurations and relevant prefabs.
- [x] Add bridge/plot-helper tests for disabled, enabled, and legacy previews.
- [x] Advance the minimum `mcsas3` dependency to `>=1.3.0`, the next feature release after the
  current core `1.2.0` version.

Checkpoint: GUI test optimization and full optimization accept the same YAML option, and the
preview curve includes the Porod term when enabled.

### Phase 5: documentation and validation

- [x] Document the equation, coefficient name, canonical-Q convention, zero-Q restriction, and
  opt-in YAML setting in McSAS3 user documentation.
- [x] Document the option in McSAS3GUI run-settings/usage material.
- [x] Note the scientific correlation risk: an additive `q^-4` term can take intensity otherwise
  represented by large-particle or low-Q parts of the recovered distribution.
- [x] Run focused and complete core test suites.
- [x] Run focused and complete GUI test suites against the modified core checkout.
- [x] Run Ruff and format checks in both repositories.
- [x] Rerun tox/check-manifest and Sphinx in a clean isolated Python environment.
- [x] Record validation results and any accepted deviations below.

Checkpoint: both repositories pass their required checks and the feature is documented as
default-off and backward compatible.

## Test matrix

Required core cases:

1. Feature disabled: exact two-element public representation and unchanged fitted formula.
2. Feature enabled with positive synthetic coefficient: recover scale, background, and coefficient
   within numerical tolerance.
3. Feature enabled where the unconstrained coefficient would be negative: return zero, never a
   negative value.
4. Feature enabled with a true zero coefficient: stable boundary solution.
5. Non-finite or zero radial Q: clear validation error only when the feature is enabled.
6. Negative signed 1D Q: use its absolute magnitude.
7. 2D Q: use `sqrt(Qx**2 + Qy**2)` and respect the flattened/masked fit arrays.
8. Custom optimizer bounds: validate the expected number and apply the Porod lower bound.
9. Warm start: accept stored external coefficients and convert normalization correctly.
10. Persistence: old two-parameter, new disabled, and new enabled result files all reload.
11. Analysis: reported coefficient and averaged full fitted intensity are correct.
12. Histogramming: volume-fraction results remain dependent only on model scale.

Required GUI cases:

1. Preview of a two-parameter legacy result is unchanged.
2. Preview of a three-parameter result includes `porodCoefficient * q^-4`.
3. Preview/run workers forward `fitPorodBackground` unchanged.
4. Shipped run configurations remain valid YAML and leave the feature disabled by default.
5. The test-optimization preview plots the full fitted curve and the combined flat plus optional
   Porod background as a grey dotted line.

Required visualization cases:

1. Analysis retains a background-only curve for every repetition and stores its mean and standard
   deviation alongside the full fitted intensity.
2. The leftmost result-card plot shows the averaged combined background as a grey dotted line.
3. With the Porod option disabled, the same line reduces to the fitted constant background.

## Validation commands

Use the available project environments, adjusting only if the local environment differs:

```text
# McSAS3 focused feedback
env PYTHONPATH=src ./.tox/py314/bin/python -m pytest \
  tests/test_mc_core_fast.py tests/test_optimizer_input_fast.py

# McSAS3 complete validation
env PYTHONPATH=src ./.tox/py314/bin/python -m pytest
./.venv/bin/tox -e check

# McSAS3GUI focused feedback
env PYTHONPATH=../McSAS3/src:src ./.tox/py314/bin/python -m pytest \
  tests/test_mcsas3_bridge.py tests/test_optimization_worker.py \
  tests/test_run_settings_helpers.py tests/test_example_configurations.py

# McSAS3GUI complete validation
env PYTHONPATH=../McSAS3/src:src ./.tox/py314/bin/python -m pytest
./.venv/bin/tox -e check
```

Run GUI commands from the `McSAS3GUI` repository and ensure its environment is using the modified
McSAS3 checkout rather than the last published package.

## Risks and decisions still to verify

- **Numerical conditioning:** raw `q^-4` is poorly scaled at small Q. Internal normalization is
  mandatory; benchmark the hot loop before settling on the solver.
- **Parameter correlation:** the Porod term can correlate with particle contributions, especially
  over a narrow Q interval. It remains explicitly opt-in and must be included in result reports.
- **Result ambiguity:** a third unnamed positional value would be fragile. Store names and retain
  legacy inference only for compatibility.
- **2D beam centre:** do not manufacture a Q floor. Require masking or exclusion of `Q == 0`.
- **Static model background:** existing configurations sometimes explicitly set the SasModels
  background to zero. Documentation must distinguish that model setting from fitted base terms.
- **Solver change:** all three base parameters are linear, so bounded linear least squares may be
  faster and more deterministic than TNC. Do not change the disabled solver path without regression
  and performance evidence.

## Implementation log

Add newest entries at the bottom. Each entry should state the phase, files changed, tests run, and
the next concrete step.

### 2026-09-10 — planning complete

- Inspected the core optimizer, optimizer input, state persistence, analysis reconstruction,
  histogram scaling, GUI configuration forwarding, preview bridge, and preview plotting.
- Chose a default-off top-level `fitPorodBackground` setting and a non-negative stored
  `porodCoefficient` against canonical radial Q.
- Defined backward compatibility for two-element `x0` arrays and older HDF5 files.
- No implementation code or tests changed.
- Next step: begin Phase 1 in `McOpt`, `McCore`, and shared fit reconstruction tests.

### 2026-09-10 — Phase 1 started

- Began the core fit representation, configuration, and compatibility work.
- Next step: add the `McOpt` fields and shared fit reconstruction API, then cover them with focused
  tests before changing optimizer behavior.

### 2026-09-10 — Phases 1–4 implemented

- Core changes:
  - added the validated default-off switch and named fit-vector metadata in `mc_opt.py`;
  - preserved canonical radial Q in `osb.py`, added strict positive-Q validation, normalized the
    Porod predictor, and constrained the coefficient to zero or positive;
  - added public `fit_parameter_names()` and `fitted_intensity()` helpers;
  - routed the switch through `McCore`, retained the two-element disabled representation, and
    added optional legacy HDF loading;
  - included `porodCoefficient` and the full fitted curve in repetition analysis and averages;
  - regenerated the module dependency diagram.
- Solver decision:
  - retained the existing TNC path unchanged when the feature is disabled;
  - selected `scipy.optimize.lsq_linear` for the enabled three-parameter fit because all three
    base terms are linear and bounded;
  - a 256-point local microbenchmark measured approximately 0.066 ms per enabled bounded-LS fit
    versus 4.53 ms per legacy TNC fit. This is evidence for the solver choice, not a general
    cross-platform performance guarantee.
- GUI changes:
  - preview results load parameter names and reconstruct curves with the shared core helper;
  - run-settings details and live preview status show whether the term is enabled;
  - maintained run configurations and prefabs explicitly default the switch to false;
  - the minimum core dependency is now `mcsas3>=1.3.0`.
- Documentation now covers the equation, canonical units, zero-Q restriction, default-off setting,
  and distribution-correlation risk in both repositories.

### 2026-09-10 — validation checkpoint

- Passed: `env PYTHONPATH=src ./.tox/py314/bin/python -m pytest -q` in McSAS3 — 110 tests.
- Passed: `env PYTHONPATH=../McSAS3/src:src ./.tox/py314/bin/python -m pytest -q` in McSAS3GUI —
  85 tests.
- Passed in both repositories: `.tox/check/bin/ruff check .` and
  `.tox/check/bin/ruff format --check .`.
- Passed in both repositories: `git diff --check` for tracked changes; the new plan was also
  checked explicitly for trailing whitespace.
- Environment limitation: `.venv/bin/tox -e check` cannot initialize because the local Homebrew
  Python 3.13 `pyexpat` extension expects `_XML_SetAllocTrackerActivationThreshold`, which is not
  present in the loaded system `libexpat`.
- The existing Python 3.14 environment has the same XML parser linkage issue, so a GUI Sphinx build
  stops with `xml.sax._exceptions.SAXReaderNotAvailable: No parsers found`.
- Direct check-manifest with build isolation reaches the same `pyexpat` failure through pip;
  `--no-build-isolation` cannot complete because the check environment lacks its declared `wheel`
  build dependency. These are environment/tool bootstrap failures rather than test failures.
- Next step: repair/recreate the local Python environments, rerun tox/check-manifest and Sphinx,
  then mark Phase 5 complete. No feature code remains to implement.

### 2026-09-10 — background visualization follow-up started

- Requested extension: show the combined flat plus optional Porod background as a grey dotted line
  in the result-card data plot and the GUI test-optimization preview.
- Next step: add shared background-only reconstruction, retain per-repetition background curves in
  `McAnalysis`, and cover core/GUI reconstruction with regression tests.

### 2026-09-10 — background visualization follow-up complete

- Added public `background_intensity()` reconstruction in `osb.py`; it uses the same parameter and
  Q validation as the complete fitted-intensity reconstruction and returns the fitted flat plus
  optional `porodCoefficient * q^-4` contribution.
- `McAnalysis` now retains the background-only curve for each repetition and writes
  `backgroundIMean` and `backgroundIStd` with the averaged model-intensity result.
- The leftmost histogram result-card plot draws `backgroundIMean` as a grey dotted line labelled
  `Fitted background (flat + Porod)`.
- `OptimizationPreview1D` exposes the reconstructed background curve, and the McSAS3GUI data plot
  draws it as the same grey dotted line whenever it draws `Test McSAS3 Optimization`.
- Passed focused checks:
  - McSAS3 `tests/test_mc_core_fast.py` — 45 tests;
  - McSAS3GUI bridge and run-settings-helper tests — 13 tests.
- Passed complete checks:
  - McSAS3 test suite — 111 tests;
  - McSAS3GUI test suite against the modified core checkout — 86 tests;
  - Ruff lint and format checks over `src` and `tests` in both repositories.
- The previously recorded local Python/libexpat limitation remains the only tooling follow-up.
- Next step: repair/recreate the local Python environments, then rerun tox/check-manifest and
  Sphinx to close Phase 5. No Porod feature or visualization code remains to implement.

### 2026-09-11 — McSAS3 CI follow-up started

- GitHub Actions run 34568123514 failed only in the Python 3.12, 3.13, and 3.14 test jobs; all
  downstream release, build, standalone, documentation, coverage, and publish jobs were skipped.
- Reproduced the Python 3.12 tox command in an isolated environment: 110 tests passed and only
  `test_generated_dependency_diagram_is_current` failed.
- Root cause: `generate_dependency_diagram.py` embedded `date.today()` in its output, making the
  checked-in generated document stale at midnight even when its dependency graph was unchanged.
- Replaced the volatile date with a stable generated-file notice and regenerated the tracked
  document.
- Next step: rerun the exact test job plus check and documentation tox environments, then record
  the results here.

### 2026-09-11 — McSAS3 CI follow-up complete

- The stable dependency-diagram generator fix passes its focused regression test.
- The exact GitHub matrix test command now passes all 111 tests in package-isolated Python 3.12,
  3.13, and 3.14 tox environments: `tox -e py312,py313,py314 -v -- -k 'not testOptimizer'`.
- `tox -e check -v` passes check-manifest, Ruff lint, and Ruff format validation.
- `tox -e docs -v` completes both the Sphinx HTML and link-check builds. Existing non-fatal
  documentation warnings remain unchanged and do not fail CI.
- Removing the wall-clock date fixes the common root cause for Python 3.12, 3.13, and 3.14; the
  complete matrix was reproduced successfully after the change.
- Phase 5 is complete. Next step: commit and push these McSAS3 CI-fix changes so GitHub Actions can
  verify the branch, then investigate McSAS3GUI separately.

### 2026-09-11 — result-card report layout follow-up

- Shortened only the displayed optimization-statistics label from `porodCoefficient` to `porod`;
  the configuration, persisted field, analysis key, and public coefficient name remain unchanged.
- Combined the average accepted-move and total-step values on one compact line:
  `accepted  ≈ [accepted],   total  ≈ [steps]`.
- Added a focused regression test for the compact labels and single progress line.
- Passed the focused `test_mc_core_fast.py` suite (46 tests), complete McSAS3 suite (112 tests),
  Ruff lint, and Ruff format validation.
- Next step: commit and push the result-card layout change with the pending CI fix, then verify the
  GitHub Actions run.

### 2026-09-11 — core optimization performance follow-up complete

- Profiled 500 complete `McCore.iterate()` calls with 256 Q points and the custom sphere model.
  The legacy TNC scale/background minimization consumed about 1.41 s of the 1.52 s total runtime.
- A 1,000-call synthetic microbenchmark measured approximately 1.65 ms per TNC fit versus 0.028 ms
  for bounded linear least squares, a 58.7x improvement in the inner base fit on this machine.
- Both base parameters are linear. Generalized the existing Porod-enabled bounded linear solver to
  handle the default two-parameter scale/background fit while preserving its bounds and public
  result vector.
- Removed the duplicate calculation of contribution zero during initial model-intensity assembly.
- Reused one list of parameter records during initialization and replaced accepted-row pandas
  assignment with scalar updates; a three-parameter microbenchmark measured about 67 microseconds
  for the old row assignment versus 18 microseconds for scalar updates.
- A SasModels sphere profile identified repeated Pint quantity construction for the fixed
  nm-to-Angstrom conversion as about 19% of the optimized loop. The unit factors are now resolved
  once at import time and applied with NumPy multiplication to scalar or array values.
- After all low-risk changes, the same custom-model benchmark completed 500 iterations in 0.098 s,
  down from 1.522 s (about 15.5x faster on this machine). This workload deliberately makes the
  base fit dominant, so the gain for production models will depend on their kernel cost.
- In a separate profile using the actual SasModels sphere kernel, replacing repeated Pint
  conversions reduced 300 iterations from 0.160 s to 0.135 s (about 16% on top of the solver and
  pandas improvements). The remaining profile is dominated by genuine SasModels kernel work.
- Passed the complete default test suite (115 tests), the optimizer integration suite (9 tests,
  1 deselected), and Ruff lint and format checks over `src` and `tests`.
- Larger gains may be possible by caching each contribution's calculated intensity, but that adds
  O(contributions x Q-points) memory—especially significant for 2D data—and more complex cache
  invalidation. It is intentionally outside this easy-win pass.
- Next step: commit and push the measured core optimization improvements, then benchmark a
  representative production configuration before considering contribution-intensity caching.

### 2026-09-11 — optimization-limit robustness follow-up complete

- User reports showed that omitting `maxAccept` retained the historical infinite default in the
  result file. McSAS3GUI then crashed while converting that value to an integer for its preview.
- Normalize optimizer limits in McSAS3 before a run or loaded state is used: an omitted
  `maxAccept` becomes `maxIter`, an omitted `maxIter` becomes the larger of 5,000 and an explicitly
  supplied `maxAccept`, and `maxAccept` is always capped at `maxIter`.
- Emit a warning for each omitted limit so implicit run bounds remain visible to CLI and GUI users.
- Defensively normalize limits while loading McSAS3GUI previews so result files written by older
  McSAS3 releases with an infinite `maxAccept` remain readable.
- McSAS3GUI preview headers and progress messages now display the same resolved finite limits as
  the core instead of showing the historical `default` and infinity placeholders.
- Updated the README, quickstart, and bundled run configurations to describe or explicitly set the
  finite limits, avoiding warnings in the supplied examples.
- Added regression coverage for both limits omitted, either limit omitted, configured clipping,
  legacy core HDF loading, and legacy GUI preview loading.
- Passed the complete McSAS3 suite (120 tests), optimizer integration suite (9 tests, 1 deselected),
  complete McSAS3GUI suite (92 tests), and Ruff lint, format, and diff checks in both repositories.
- The local Sphinx tox environment could not be created because of the previously recorded
  Homebrew Python/libexpat mismatch; failure occurred in virtualenv startup before Sphinx ran.
- Next step: release the McSAS3 normalization before or together with the McSAS3GUI legacy-preview
  fallback, then collect the next reported issue.

### 2026-09-11 — misplaced Porod option and preview-thread follow-up complete

- A user traceback showed `fitPorodBackground` reaching SasModels as an unused kernel parameter.
  This identifies a tab/indentation error that placed the optimizer option below
  `staticParameters` instead of at the run configuration's top level.
- Add early McSAS3 validation that reports the misplaced option and its correct YAML location
  before model initialization reaches SasModels.
- A separate `QThread: Destroyed while thread is still running` abort originates from clearing the
  final `PreviewOptimizationWorker` reference in response to its custom result signal, before
  `QThread.run()` has returned. Retain the reference and temporary result until Qt's built-in
  `finished` signal confirms termination.
- Strengthen the GUI bootstrap compatibility test to require the fitted-background API, reducing
  the chance of combining a Porod-enabled GUI checkout with an older installed McSAS3 core.
- McSAS3 now rejects `fitPorodBackground` below `staticParameters` before loading or evaluating the
  scattering model, with an error that directs users to the top-level YAML location and warns
  against tabs.
- McSAS3GUI now keeps its worker reference and preview result until the built-in `QThread.finished`
  signal; custom success/error signals update the UI but can no longer destroy a running thread.
  Runtime import failures are also caught and reported through the normal preview error signal.
- The GUI bootstrap now requires `background_intensity`, `fit_parameter_names`, and
  `fitted_intensity` in addition to the canonical workflow modules, and falls back to a compatible
  source checkout or raises a direct installation error.
- Passed the complete McSAS3 suite (121 tests), optimizer integration suite (9 tests, 1 deselected),
  complete McSAS3GUI suite (96 tests), and Ruff lint, format, and diff checks in both repositories.
- Next step: release matching McSAS3 and McSAS3GUI versions so users receive the configuration,
  compatibility, and QThread-lifecycle fixes together.

## Update rule

Whenever implementation work is started or completed:

- update `Last updated` if the calendar date changed;
- check off only completed tasks;
- append an implementation-log entry before ending the work session;
- record exact validation commands and outcomes;
- record newly discovered constraints or changed decisions in this document;
- leave a single explicit “Next step” that can be picked up without relying on chat history.
