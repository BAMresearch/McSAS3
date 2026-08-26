# McSAS3 (v1.1.0)

[![PyPI Package latest release](https://img.shields.io/pypi/v/mcsas3.svg)](https://pypi.org/project/mcsas3)
[![Commits since latest release](https://img.shields.io/github/commits-since/BAMresearch/McSAS3/v1.1.0.svg)](https://github.com/BAMresearch/McSAS3/compare/v1.1.0...main)
[![License](https://img.shields.io/pypi/l/mcsas3.svg)](https://en.wikipedia.org/wiki/GPL-3.0-or-later)
[![Supported versions](https://img.shields.io/pypi/pyversions/mcsas3.svg)](https://pypi.org/project/mcsas3)
[![PyPI Wheel](https://img.shields.io/pypi/wheel/mcsas3.svg)](https://pypi.org/project/mcsas3#files)
[![Weekly PyPI downloads](https://img.shields.io/pypi/dw/mcsas3.svg)](https://pypi.org/project/mcsas3/)
[![Continuous Integration and Deployment Status](https://github.com/BAMresearch/McSAS3/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/BAMresearch/McSAS3/actions/workflows/ci-cd.yml)
[![Coverage report](https://img.shields.io/endpoint?url=https://BAMresearch.github.io/McSAS3/coverage-report/cov.json)](https://BAMresearch.github.io/McSAS3/coverage-report/)

McSAS3 (a refactored version of the original McSAS) fits scattering patterns to obtain size distributions without assumptions on the size distribution form. The refactored version has some neat features:

- Multiprocessing is included, spread out over as many cores as number of repetitions!
- Full state of the optimization is stored in an organized HDF5 state file.
- Histogramming is separate from optimization and a result can be re-histogrammed as many times as desired.
- SasModels allow a wide range of models to be used
- If SasModels does not work (e.g. because of gcc compiler issues on Windows or Mac), an internal sphere model is supplied
- Simulated data of the scattering of a special shape can also be used as a McSAS fitting model. Your models are infinite!
- 2D fitting also works.

![Example results plot](https://user-images.githubusercontent.com/5449929/156196219-72472a71-bbd6-4506-a12b-134216deeef6.jpg)

### Important note:

Due to an issue with sasmodels when using OpenCL: if you see problems with the fit not matching up at all to the data, disable sasmodels opencl by setting the environment variable SAS_OPENCL=none in the terminal you are launching McSAS3 from.

## Current state

1. McSAS3 now has an internal sphere model as well, and so no longer absolutely requires SasModels for normal runs.
2. There are launchers that can work from the command line, for optimization and (separately) histogramming. These use minimal configuration files for setting up the different parts of the code. Adjust these for your output files and optimization requirements, and then you can use these to automatically provide a McSAS3 analysis for every measurement.
3. Currently, it reads three-column ascii / CSV files, or NeXus/HDF5 files. example read configurations are provided.
4. Observability limits are not included yet
5. A separate GUI client exists in the sibling `McSAS3GUI` repository. The core documentation here
   focuses on the maintained CLI and canonical Python workflow APIs.
6. Some bugs remain. Feel free to add bugs to the issues. They will be fixed as time permits.

## Installation

McSAS3 requires Python 3.12 or newer. Package dependencies such as SasModels,
`attrs`, and `pandas` are installed automatically. On Windows, if you want to
use the sasmodels library, it is highly recommended to run `pip install tinycc`
so that there's a compatible compiler available.

Install *McSAS3* in your Python environment by running:

```bash
pip install mcsas3
```

If you use `uv`, create and activate a Python 3.12+ environment, then install the same package with:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install mcsas3
```

On Windows, activate the environment with `.venv\Scripts\activate` instead of `source`.

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

## Usage

To run the optimizer from the command line using the test settings and test data, you can run the following command `mcsas3-runner`. This stores the optimization result in a file named test.nxs. This can subsequently be histogrammed and plotted using the following commmand:

    mcsas3-histogrammer -r test.nxs

This is, of course, a mere test case. The result should look like the Figure shown earlier.

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
