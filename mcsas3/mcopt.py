import numpy as np
import h5py

class McOpt(object):
    """Class to store optimization settings and keep track of running variables"""

    accepted = None    # number of accepted picks
    convCrit = 1       # reduced chi-square before valid return
    gof = None         # continually updated gof value
    maxIter = 100000   # maximum steps before fail
    maxAccept = np.inf # maximum accepted before valid return
    modelI = None      # internal, will be filled later
    # nContrib = None  # moved to model McParams
    nRep = 4           # number of repeated independent optimizations to calculate population statistics over
    repetition = None  # Optimization instance repetition number (defines storage location)
    step = None        # number of iteration steps
    testX0 = None      # X0 if test is accepted.
    testModelI = None  # internal, updated intensity after replacing with pick
    testModelV = None  # volume of test object, optionally used for weighted histogramming later on.
    weighting = 0.5    # NOT USED, set to default = volume-weighted.  volume-weighting / compensation factor for the contributions 
    x0 = None          # continually updated new guess for total scaling, background values.

    storeKeys = [ # keys to store in an output file 
        "accepted",
        "convCrit",
        "gof",
        "maxIter",
        "maxAccept",
        "modelI",
        "nRep",
        "repetition",
        "step",
        "weighting",
        "x0"
        ]
    loadKeys = [ # load (and replace) these settings from a previous run into the current settings
        "convCrit",
        "maxIter",
        "nRep", 
        "maxAccept"        
        ]

    def __init__(self, loadFromFile = None, **kwargs):
        """initializes the options to the MC algorithm, *or* loads them from a previous run. 
        Note: If the parameters are loaded from a previous file, any additional key-value pairs are updated. """
        if loadFromFile is not None:
            self.load(loadFromFile)

        for key, value in kwargs.items(): 
            assert (key in self.storeKeys), "Key {} is not a valid option".format(key)
            setattr(self, key, value)

    def store(self, ofname):
        """stores the settings in an output file (HDF5)"""
        for key in self.storeKeys:
            with h5py.File(ofname) as h5f:
                h5g = h5f.require_group('/entry1/MCResult1/options/')
                data = getattr(self, key, None)
                # convert all compatible data types to arrays:
                if type(data) is tuple or type(data) is list:
                    value = np.array(value)
                # store arrays:
                if data is not None and type(data) is np.ndarray:
                    h5g.require_dataset(key, data = data, shape = data.shape, dtype = data.dtype)
                elif data is not None:
                    dset = h5g.get(key, None)
                    if dset is None:
                        h5g.create_dataset(key, data = data)
                    else:
                        dset[()] = data


    def load(self, ifname):
        for key in self.loadKeys:
            with h5py.File(ifname) as h5f:
                setattr(self, key, h5f['/entry1/MCResult1/options/{}'.format(key)].value)
