import numpy as np

class McHat(object): 
    """
    The hat sits on top of the McCore. It takes care of parallel processing of each repetition. 
    """
    
    _measData = None             # measurement data dict with entries for Q, I, ISigma
    _outputFilename = None       # store output data in here (HDF5)
    _modelSettings = None        # dict with settings to be passed on to the model instance
    _optimizationSettings = None # dict with optimization settings to be passed on to the optimization instance
    _nCores = 2                  # number of cores to use for parallelization
    _nRep = 10                   # number of independent repetitions to opitimize. not sure how to square with nRep stored in McOpt

    def __init__(self):
        pass

    def run(self, measData = None, filename = None):
        """runs the full sequence: multiple repetitions of optimizations, to be parallelized. 
        This probably needs to be taken out of core, and into a new parent"""
        self._outputFilename = filename

        assert self._outputFilename is not None, "Output filename must be specified!"
        for rep in range(self._opt.nRep):
            self._opt.repetition = rep # set running variable (important for storage)
            self.optimize()
            self.store()
            