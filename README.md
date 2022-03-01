# McSAS3

Refactoring of the McSAS core for cleanup and Python3 support. 

McSAS3 now fits scattering patterns to obtain size distributions without assumptions on the size distribution form. It now has some neat features:
  - Multiprocessing is included, spread out over as many cores as number of repetitions!
  - Full state of the optimization is stored in an organized HDF5 state file. 
  - Histogramming is separate from optimization and a result can be re-histogrammed as many times as desired.
  - SasModels allow a wide range of models to be used
  - If SasModels does not work (e.g. because of gcc compiler issues on Windows or Mac), an internal sphere model is supplied
  - Simulated data of the scattering of a special shape can also be used as a McSAS fitting model. Your models are infinite!
  - 2D fitting also works. 

## Current state:
  1. McSAS3 now has an internal sphere model as well, and so no longer absolutely requires SasModels for normal runs. 
  2. There are launchers that can work from the command line, for optimization and (separately) histogramming. These use minimal configuration files for setting up the different parts of the code. Adjust these for your output files and optimization requirements, and then you can use these to automatically provide a McSAS3 analysis for every measurement. 
  3. Currently, it reads three-column ascii / CSV files, or NeXus/HDF5 files. example read configurations are provided. 
  4. Observability limits are not included yet
  5. A GUI is not available (yet). 
  6. Some bugs remain. Feel free to add bugs to the issues. They will be fixed as time permits. 

## Installation
This package can be installed by ensuring you have SasModels (pip install sasmodels) and the most recent 21.4+ version of attrs installed. After that, you can do
'''git clone https://github.com/BAMresearch/McSAS3.git''' in an appropriate location to install McSAS3

## Usage:
To run the optimizer from the command line using the test settings and test data, you can run the following command
'''python mcsas3_cli_runner.py'''
This stores the optimization result in a file named test.nxs. This can subsequently be histogrammed and plotted using the following commmand:
'''python mcsas3_cli_histogrammer.py -r test.nxs'''

This is, of course, a mere test case. To do the same for real measurements, you need to configure McSAS3 by supplying it with three configuration files (two for the optimization, one for the histogramming):

### Data read configuration file
This file contains the parameters necessary to read a data file. The example file for reading a three-column ASCII file, for example, contains:

Here, nbins is the number of binned datapoints to apply to the data clipped to within the dataRange Q limits. We normally rebin the data to reduce the number of datapoints used for the optimization procedure. Typically 100 datapoints per decade is more than sufficient. The uncertainties are propagated and means calculated from the datapoints within a bin. 

'''
--- # configuration used to read files into McSAS3. this is assumed to be a 1D file in csv format
# Note that the units are assumed to be 1/(m sr) for I and 1/nm for Q
nbins: 100
dataRange:
  - 0.0 # minimum
  - .inf # maximum. Positive infinity starts with a dot. negative infinity is -.inf
csvargs: 
  sep: ";" 
  header: null # null translates to a Python "None"
  names: # column names
    - "Q"
    - "I"
    - "ISigma"
'''

Whereas the configuration for reading a NeXus file is slightly different, and can contain a dictionary of paths to the datasets to fit. 
''' 
--- # configuration used to read nexus files into McSAS3. this is assumed to be a 1D file in nexus
# Note that the units are assumed to be 1/(m sr) for I and 1/nm for Q
# if necessary, the paths to the datasets can be indicated. 
nbins: 100
dataRange:
  - 0.0 # minimum
  - 1.0 # maximum for this dataset. Positive infinity starts with a dot. negative infinity is -.inf
pathDict: # optional, if not provided will follow the "default" attributes in the nexus file
  Q: '/entry/result/Q'
  I: '/entry/result/I'
  ISigma: '/entry/result/ISigma'
'''

### Optimization parameters

'''
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
'''

### Histogramming parameters 

'''
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

'''
