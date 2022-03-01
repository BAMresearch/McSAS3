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

