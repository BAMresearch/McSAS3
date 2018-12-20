import numpy as np

class McOpt(object):
    """Class to store optimization settings and keep track of running variables"""

    accepted = None    # number of accepted picks
    convCrit = None    # reduced chi-square before valid return
    gof = None         # continually updated gof value
    maxIter = None     # maximum steps before fail
    maxAccept = None   # maximum accepted before valid return
    modelI = None      # internal, will be filled later
    nContrib = None    # also copied in McParams
    nRep = None        # number of repeated independent optimizations to calculate population statistics over
    repetition = None  # Optimization instance repetition number (defines storage location)
    step = None        # number of iteration steps
    testX0 = None      # X0 if test is accepted.
    testModelI = None  # internal, updated intensity after replacing with pick
    testModelV = None  # volume of test object, optionally used for weighted histogramming later on.
    weighting = 0.5    # NOT USED, set to default = volume-weighted.  volume-weighting / compensation factor for the contributions 
    x0 = None          # continually updated new guess for total scaling, background values.


    
    def __init__(self, nContrib = 300, maxIter = 100000, maxAccept = np.inf, convCrit = 1, nRep = 4):
        self.nContrib = int(nContrib)
        self.maxIter = maxIter
        self.maxAccept = maxAccept
        self.convCrit = convCrit
        self.x0 = None # np.array([1, 0])
        
    def contribIndex(self):
        """ returns current index of contribution being optimized """
        return self.step % self.nContrib
    
