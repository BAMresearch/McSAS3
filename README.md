# McSAS3 (v1.2.0)

[![PyPI Package latest release](https://img.shields.io/pypi/v/mcsas3.svg)](https://pypi.org/project/mcsas3)
[![Commits since latest release](https://img.shields.io/github/commits-since/BAMresearch/McSAS3/v1.2.0.svg)](https://github.com/BAMresearch/McSAS3/compare/v1.2.0...main)
[![License](https://img.shields.io/pypi/l/mcsas3.svg)](https://en.wikipedia.org/wiki/GPL-3.0-or-later)
[![Supported versions](https://img.shields.io/pypi/pyversions/mcsas3.svg)](https://pypi.org/project/mcsas3)
[![PyPI Wheel](https://img.shields.io/pypi/wheel/mcsas3.svg)](https://pypi.org/project/mcsas3#files)
[![Weekly PyPI downloads](https://img.shields.io/pypi/dw/mcsas3.svg)](https://pypi.org/project/mcsas3/)
[![Continuous Integration and Deployment Status](https://github.com/BAMresearch/McSAS3/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/BAMresearch/McSAS3/actions/workflows/ci-cd.yml)
[![Coverage report](https://img.shields.io/endpoint?url=https://BAMresearch.github.io/McSAS3/coverage-report/cov.json)](https://BAMresearch.github.io/McSAS3/coverage-report/)

McSAS3 analyzes small-angle scattering data with the Monte Carlo method used by
the original McSAS project. It fits scattering patterns and turns the accepted
model parameters into size distributions without assuming a Gaussian, lognormal,
or other fixed distribution shape.

This repository is the calculation engine. If you mainly want a desktop
application with tabs, example datasets, and buttons, start with
[McSAS3GUI](https://github.com/BAMresearch/mcsas3gui).

![Example results plot](https://user-images.githubusercontent.com/5449929/156196219-72472a71-bbd6-4506-a12b-134216deeef6.jpg)

## Start Here

### I want the graphical interface

Use the GUI package instead of installing this calculation engine directly.
With [`uv`](https://docs.astral.sh/uv/), the whole GUI can be launched with one
command using the current recommended Python runtime:

```bash
uvx --python 3.14 --from mcsas3gui m3gui
```

The first run may take a few minutes. `uvx` creates an isolated Python
environment, installs McSAS3GUI and McSAS3, and then starts the `m3gui` desktop
application. There is no environment to activate.

If `uv` is not installed yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### I want the command line

Run the built-in quick-start optimization from any folder where you want the
result files to appear:

```bash
uvx --python 3.14 --from mcsas3 mcsas3-runner -d -r quickstart.nxs
uvx --python 3.14 --from mcsas3 mcsas3-histogrammer -r quickstart.nxs
```

This writes an optimization result file, `quickstart.nxs`, and a histogram plot,
`quickstart.pdf`. For repeated command-line use, install the tools once:

```bash
uv tool install --python 3.14 mcsas3
mcsas3-runner --help
mcsas3-histogrammer --help
```

## What It Does

McSAS3 works in two steps:

1. **Optimization** fits many independent model contributions to the measured
   scattering pattern.
2. **Histogramming** converts the optimized model parameters into one or more
   distributions. You can change the histogram settings and re-run this step
   without repeating the optimization.

Results are stored in an HDF5/NeXus-style file so the full calculation state can
be inspected later. A PDF summary plot is written alongside the result file when
the histogrammer is run.

## Current Capabilities

- Reads simple three-column text/CSV files and NeXus/HDF5 files.
- Supports 1D and 2D data workflows.
- Uses SasModels for a wide range of scattering models.
- Includes an internal sphere model for normal runs where SasModels compilation
  is inconvenient.
- Can use simulated scattering curves as fitting models for special shapes.
- Runs repetitions in parallel over available CPU cores.
- Stores optimization state and histogram results in one organized result file.
- Observability limits are not included yet.

## Installation

McSAS3 requires Python 3.12 or newer. Package dependencies such as SasModels,
`attrs`, and `pandas` are installed automatically. The examples in this README
use Python 3.14.

For a normal Python environment:

```bash
pip install mcsas3
```

With `uv` and an activated project environment:

```bash
uv venv --python 3.14
source .venv/bin/activate
uv pip install mcsas3
```

On Windows, activate the environment with `.venv\Scripts\activate` instead of
`source`.

You can also install the in-development version with:

```bash
pip install git+https://github.com/BAMresearch/McSAS3.git
```

or, with `uv`:

```bash
uv pip install git+https://github.com/BAMresearch/McSAS3.git
```

Check the installed command-line entry points with:

```bash
mcsas3-runner --help
mcsas3-histogrammer --help
```

On Windows, if you want to use SasModels, installing `tinycc` can help provide a
compatible compiler:

```bash
pip install tinycc
```

## Troubleshooting

If a SasModels fit does not match the data at all, OpenCL may be selecting a
problematic execution path. Try disabling SasModels OpenCL in the terminal before
running McSAS3:

```bash
export SAS_OPENCL=none
```

On Windows PowerShell:

```powershell
$env:SAS_OPENCL = "none"
```

## Usage

The command-line tools can be used with no arguments for the packaged test data,
or with explicit data and YAML configuration files for your own measurements.

To run the packaged test case after installing McSAS3:

```bash
mcsas3-runner -d -r test.nxs
mcsas3-histogrammer -r test.nxs
```

This stores the optimization result in `test.nxs` and writes the histogram plot
to `test.pdf`. The result should look similar to the figure shown earlier.

### Python API

The supported Python entry point is the canonical `ProcessingData` workflow API. For scripts or
notebooks, prefer the top-level `mcsas3` workflow functions:

```python
from pathlib import Path

from mcsas3 import (
    STAGE_CLIPPED,
    load_result_processing_data,
    optimize_processing_data,
    prepare_1d_processing_data_from_file,
    selected_bundle_from_processing,
)

processing = prepare_1d_processing_data_from_file(
    Path("testdata", "quickstartdemo1.csv"),
    csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
    nbins=100,
    analysis_stage=STAGE_CLIPPED,
)

optimize_processing_data(
    processing,
    Path("result.h5"),
    modelName="mcsas_sphere",
    fitParameterLimits={"radius": "auto"},
    staticParameters={"background": 0.0, "scale": 1.0, "sld": 33.4, "sld_solvent": 0.0},
    maxIter=1000,
    convCrit=1.0,
    nRep=2,
    nCores=1,
    logRandom=True,
)

restored = load_result_processing_data(Path("result.h5"))
selected_bundle = selected_bundle_from_processing(restored)
q = selected_bundle["Q"].signal
intensity = selected_bundle["signal"].signal
```

This keeps the public path on canonical `ProcessingData` / `DataBundle` objects. For reusable
clipping, omission, rebinning, and 2D reconstruction helpers, use `mcsas3.preprocessing`. If you
are updating older notebooks or scripts, see the migration notes in the user documentation.

To do the same for real measurements, you need to configure McSAS3 by supplying it with three configuration files (two for the optimization, one for the histogramming):

### Data read configuration file

This file contains the parameters necessary to read a data file. The example file for reading a three-column ASCII file, for example, contains:

```yaml
    --- # configuration used to read files into McSAS3. this is assumed to be a 1D file in csv format
    # Override QUnits and IUnits here when the source file uses different units.
    QUnits: "1/nm"
    IUnits: "1/(m sr)"
    nbins: 100
    dataRange:
      - 0.0 # minimum
      - .inf # maximum. Positive infinity starts with a dot. negative infinity is -.inf
    csvargs:
      sep: ";"
      header: null # null translates to a Python "None", used for files without a header
      names: # column names
        - "Q"
        - "I"
        - "ISigma"
```

Here, *nbins* is the number of binned datapoints to apply to the data clipped to within the dataRange Q limits. We normally rebin the data to reduce the number of datapoints used for the optimization procedure. Typically 100 datapoints per decade is more than sufficient. The uncertainties are propagated and means calculated from the datapoints within a bin.

The *csvargs* is the dictionary of options passed on to `pandas.read_csv()`. The loaded columns
should at least contain columns named `Q`, `I`, and `ISigma` (the uncertainty on `I`).

You can also directly load NeXus or HDF5 files, for example you can directly load the processed files that come out of the DAWN software package. The file read configuration for a NeXus or HDF5 file is slightly different. The reader can follow either the 'default' attributes to the data to use, or you can supply a dictionary of HDF5 paths to the datasets to fit (this is the more robust option). For example:

```yaml
    --- # configuration used to read nexus files into McSAS3. this is assumed to be a 1D file in nexus
    # if necessary, the paths to the datasets can be indicated, and units can be overridden.
    QUnits: "1/nm"
    IUnits: "1/(m sr)"
    nbins: 100
    dataRange:
      - 0.0 # minimum
      - 1.0 # maximum for this dataset. Positive infinity starts with a dot. negative infinity is -.inf
    pathDict: # optional, if not provided will follow the "default" attributes in the nexus file
      Q: '/entry/result/Q'
      I: '/entry/result/I'
      ISigma: '/entry/result/ISigma'
```

### Optimization parameters

The second required configuration file sets the optimization parameters for the Monte Carlo approach. The default settings (shown below) can be largely maintained. You might, however, want to adjust the convergence criterion 'convCrit' for datasets where the uncertainty estimate is not an accurate representation of the datapoint uncertainty. 'nrep' indicates the number of independent optimizations that are run. For tests, we recommend using a small number, from 2-10. For publication-quality averages, however, we usually increase this to 50 or 100 repetitions to improve the averages and the uncertainty estimates on the final distribution. 'nCores' defines the maximum number of threads to use, the repetitions are split over this number of threads.

```yaml
    modelName: "mcsas_sphere"
    nContrib: 300
    modelDType: "default"
    fitParameterLimits:
      radius: 'auto' # automatic determination of radius limits based on the data limits. This is replaced in McHat by actual limits
      #   - 3.14
      #   - 314
    staticParameters:
      sld: 33.4 # units of 1e-6 A^-2
      sld_solvent: 0
    maxIter: 100000
    convCrit: 1
    nRep: 10
    nCores: 5
    logRandom: true
```

McSAS3 is set up so that if the maximum number of iterations 'maxIter' is reached before the convergence criterion is reached, the result is still stored in the McSAS output state file, and can still be histogrammed. This is done so you can use McSAS3 as a part of a data processing workflow, to give you a first result even if the McSAS settings or data has not been configured perfectly yet.

The fit parameter limits are best left to automatic. In this case the size range for the MC optimization is automatically set by the Q range of your data, using pi/q_max for the lower radius limit and 2*pi/q_min for the upper radius limit. This requires the data to be valid throughout its loaded data or preset data limits. Likewise a zero Q value is to be avoided for automatic size range determination.

Length-like fit parameter limits, such as `radius`, `length` and `thickness`, are specified in McSAS3 canonical units of nm. SasModels uses Angstrom internally for these parameters, so McSAS3 converts canonical nm values to Angstrom with Pint at the SasModels execution boundary.

Keep `logRandom: true` enabled for standard operation so fit parameters are sampled log-uniformly over their configured ranges.

As for models, the mcsas_sphere model is an internal sphere model that does not rely on a functioning SasModels. Other model names are discovered within the SasModel library.

Absolute intensity calculation has been lightly tested for data in canonical units of 1/nm for Q and 1/(m sr) for I. The SLD should be entered in the SasModels convention of $1e-6 1/A^2$. However, bugs in absolute volume determination may remain for a while.

### Histogramming parameters

The histogramming configuration example looks like this:

```yaml
    --- # Histogramming configuration:
      parameter: "radius"
      nBin: 50
      binScale: "log"
      presetRangeMin: 3.14
      presetRangeMax: 314
      binWeighting: "vol"
      autoRange: True
    --- # second histogram
      parameter: "radius"
      nBin: 50
      binScale: "linear"
      presetRangeMin: 10
      presetRangeMax: 100
      binWeighting: "vol"
      autoRange: False
```

Lastly, the histogramming ranges have to be configured. This can be done by adding as many entries as requiredd in the histogramming configuration yaml file. Parameter ranges can be set automatic (using the autoRange flag, thus ignoring the presetRangeMin and presetRangeMax values), or by setting fixed limits and leaving autoRange as False.

at the moment, the only bin weighting scheme implemented is the volume-weighted binning scheme, as it is the most reliable. Please leave an issue ticket if you need number-weighting to return.

For each histogramming range, histogram-independent population statistics are also calculated and provided, both in the PDF as well as in the McSAS output state file. These can be read automatically from there later on.

## Documentation

https://BAMresearch.github.io/McSAS3

The docs now also cover:

- quickstart workflows for the maintained CLI and canonical Python API
- upgrade notes for older notebooks and scripts
- generated module-structure diagrams
- release delivery for Python packages and standalone CLI bundles

## Project structure

The maintained code structure is documented in the design docs, including a generated Mermaid
module dependency diagram:

- [canonical data contract](design_documentation/canonical_data_contract.md)
- [upgrade plan](design_documentation/upgrade_plan.md)
- [generated module dependency diagram](design_documentation/generated_module_dependencies.md)

To regenerate the dependency diagram after structural changes, run:

```bash
./.venv/bin/python tools/generate_dependency_diagram.py
```

## Development

### Testing

See which tests are available (arguments after `--` get passed to *pytest* which runs the tests):

    tox -e py -- --co

Run a specific test only:

    tox -e py -- -k <test_name from listing before>

Run all tests with:

    tox -e py

### Project template

Update the project configuration from the *copier* template:

    copier update --trust --skip-answered
