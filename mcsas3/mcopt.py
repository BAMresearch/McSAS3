import numpy as np
import h5py
from .McHDF import McHDF

class McOpt(McHDF):
    """Class to store optimization settings and keep track of running variables"""

    accepted = None    # number of accepted picks
    convCrit = 1       # reduced chi-square before valid return
    gof = None         # continually updated gof value
    maxIter = 100000   # maximum steps before fail
    maxAccept = np.inf # maximum accepted before valid return
    modelI = None      # internal, will be filled later
    repetition = None  # Optimization instance repetition number (defines storage location)
    step = None        # number of iteration steps, should be renamed "iteration"
    testX0 = None      # X0 if test is accepted.
    testModelI = None  # internal, updated intensity after replacing with pick
    testModelV = None  # volume of test object, optionally used for weighted histogramming later on.
    weighting = 0.5    # NOT USED, set to default = volume-weighted.  volume-weighting / compensation factor for the contributions 
    x0 = None          # continually updated new guess for total scaling, background values.
    acceptedSteps = [] # for each accepted pick, write the iteration step number here
    acceptedGofs = []  # for each accepted pick, write the reached GOF here. 

    storeKeys = [ # keys to store in an output file 
        "accepted",
        "convCrit",
        "gof",
        "maxIter",
        "maxAccept",
        "modelI",
        "repetition",
        "step",
        "weighting",
        "x0",
        "acceptedSteps", 
        "acceptedGofs"
        ]
    loadKeys = [ # load (and replace) these settings from a previous run into the current settings
        "convCrit",
        "maxIter",
        "gof",
        "x0",
        "modelI",
        "accepted",
        "step",
        "maxAccept",
        "maxIter",
        "acceptedSteps",
        "acceptedGofs"
        ]

    def __init__(self, loadFromFile = None, **kwargs):
        """initializes the options to the MC algorithm, *or* loads them from a previous run. 
        Note: If the parameters are loaded from a previous file, any additional key-value pairs are updated. """

        # Cleaning the parameters, making sure we do not inherit anything:
        self.accepted = None    # number of accepted picks
        self.convCrit = 1       # reduced chi-square before valid return
        self.gof = None         # continually updated gof value
        self.maxIter = 100000   # maximum steps before fail
        self.maxAccept = np.inf # maximum accepted before valid return
        self.modelI = None      # internal, will be filled later
        self.repetition = None  # Optimization instance repetition number (defines storage location)
        self.step = None        # number of iteration steps, should be renamed "iteration"
        self.testX0 = None      # X0 if test is accepted.
        self.testModelI = None  # internal, updated intensity after replacing with pick
        self.testModelV = None  # volume of test object, optionally used for weighted histogramming later on.
        self.weighting = 0.5    # NOT USED, set to default = volume-weighted.  volume-weighting / compensation factor for the contributions 
        self.x0 = None          # continually updated new guess for total scaling, background values.
        self.acceptedSteps = [] # for each accepted pick, write the iteration step number here
        self.acceptedGofs = []  # for each accepted pick, write the reached GOF here. 

        self.repetition = kwargs.pop("loadFromRepetition", 0)

        if loadFromFile is not None:
            self.load(loadFromFile)

        for key, value in kwargs.items(): 
            assert (key in self.storeKeys), "Key {} is not a valid option".format(key)
            setattr(self, key, value)

    def store(self, filename = None, path = None):
        """stores the settings in an output file (HDF5)"""
        if path is None: path=f'{self.nxsEntryPoint}MCResult1/optimization/'
        assert filename is not None
        for key in self.storeKeys:
            value = getattr(self, key, None)
            self._HDFstoreKV(filename = filename, path = path, key = key, value = value)

    def load(self, filename = None, repetition = None, path = None):
        if path is None: path=f'{self.nxsEntryPoint}MCResult1/optimization/'
        if repetition is None: repetition = self.repetition

        assert filename is not None
        for key in self.loadKeys:
            with h5py.File(filename, 'r') as h5f:
                setattr(self, key, h5f[f"{path}repetition{repetition}/{key}"][()])
