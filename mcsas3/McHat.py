import numpy as np
from .mcopt import McOpt
from .mcmodel import McModel
from .mccore import McCore

class McHat(object): 
    """
    The hat sits on top of the McCore. It takes care of parallel processing of each repetition. 
    """
    
    _measData = None  # measurement data dict with entries for Q, I, ISigma
    _modelArgs = None # dict with settings to be passed on to the model instance
    _optArgs = None   # dict with optimization settings to be passed on to the optimization instance
    _model = None     # McModel instance for multiple repetitions
    _opt = None       # McOpt instance for multiple repetitions
    nCores = 2        # number of cores to use for parallelization
    nRep = 10         # number of independent repetitions to opitimize

    storeKeys = [ # keys to store in an output file
        "nCores",
        "nRep",
    ]
    loadKeys = storeKeys

    def __init__(self, loadFromFile=None, **kwargs):
        """kwargs accepts all parameters from McModel and McOpt."""
        if loadFromFile is not None:
            self.load(loadFromFile)

        self._optArgs = dict([(key, kwargs.pop(key))
                                for key in McOpt.storeKeys if key in kwargs])
        self._modelArgs = dict([(key, kwargs.pop(key))
                                for key in McModel.settables if key in kwargs])

        for key, value in kwargs.items():
            assert (key in self.storeKeys), "Key {} is not a valid option".format(key)
            setattr(self, key, value)

    def run(self, measData=None, filename=None):
        """runs the full sequence: multiple repetitions of optimizations, to be parallelized. 
        This probably needs to be taken out of core, and into a new parent"""

        for rep in range(self.nRep):
            self.runOnce(measData, filename, rep)

    def runOnce(self, measData=None, filename=None, repetition=0):
        """runs the full sequence: multiple repetitions of optimizations, to be parallelized. 
        This probably needs to be taken out of core, and into a new parent"""

        if self._opt is None:
            self._opt = McOpt(**self._optArgs)
        if self._model is None:
            self._model = McModel(**self._modelArgs)

        self._opt.repetition = repetition
        self._model.resetParameterSet()
        mc = McCore(measData, model = self._model, opt = self._opt)
        mc.optimize()
        self._model.kernel.release()
        print("Final chiSqr: {}, N accepted: {}"
              .format(self._opt.gof, self._opt.accepted))
        print("x0", self._opt.x0)
        # storing the results
        mc.store(filename = filename)

    def store(self, filename = None, path = '/entry1/analysis/MCResult1/optimization/'):
        """stores the settings in an output file (HDF5)"""
        assert filename is not None
        for key in self.storeKeys:
            value = getattr(self, key, None)
            self._HDFstoreKV(filename = filename, path = path, key = key, value = value)

    def load(self, filename = None, path = '/entry1/analysis/MCResult1/optimization/'):
        assert filename is not None
        for key in self.loadKeys:
            with h5py.File(filename) as h5f:
                setattr(self, key, h5f["{}/{}".format(path, key)][()])