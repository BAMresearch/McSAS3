import pandas
import numpy as np


class McModel(object):
    """
    Specifies the fit parameter details and contains random pickers. 
    requires:
    fitParameterLimits: dict of value pairs {"param1": (lower, upper), ... } for fit parameters
    staticParameters: dict of parameter-value pairs to keep static during the fit. 
    """
    # import np.random.uniform 
    
    func = None # SasModels model instance
    kernel = None # SasModels kernel pointer
    parameterSet = None # pandas dataFrame of length nContrib, with column names of parameters
    staticParameters = None # dictionary of static parameter-value pairs during MC optimization
    pickParameters = None  # dict of values with new random picks, named by parameter names
    pickIndex = None # int showing the running number of the current contribution being tested
    fitParameterLimits = None # dict of value pairs (tuples) *for fit parameters only* with lower, upper limits for the random function generator, named by parameter names 
    randomGenerators = None # dict with random value generators 
    volumes = None # array of volumes for each model contribution, calculated during execution
    seed = None # random generator seed, should vary for parallel execution
    
    def fitKeys(self):
        return [key for key in self.fitParameterLimits]
    
    def __init__(self, fitParameterLimits = None, staticParameters = None, func = None, seed = 12345):
        self.func = func
        self.fitParameterLimits = fitParameterLimits
        self.staticParameters = staticParameters
        self.seed = seed

    def initialize(self, nContrib):
        # after nContrib is known, this can be exectued.
        self.randomGenerators = dict.fromkeys(
            [key for key in self.fitParameterLimits], np.random.RandomState(self.seed).uniform)
        self.parameterSet = pandas.DataFrame(
            index = range(nContrib), columns = self.fitKeys())
        self.fillParameterSet()
       
    def pick(self):
        """pick new random model parameter"""
        self.pickParameters = self.generateRandomParameterValues()

    def generateRandomParameterValues(self):
        """to be depreciated as soon as models can generate their own..."""
        # initialize dict with parameter-value pairs defaulting to None
        returnDict = dict.fromkeys([key for key in self.fitParameterLimits])
        # fill:
        for parName in self.fitParameterLimits.keys():
            # can be replaced by a loop over iteritems:
            (upper, lower) = self.fitParameterLimits[parName]            
            returnDict[parName] = self.randomGenerators[parName](upper, lower)
        return returnDict
    
    def fillParameterSet(self):
        """fills the model parameter values with random values"""
        for contribi in range(self.parameterSet.shape[0]):
            # can be improved with a list comprehension, but this only executes once..
            self.parameterSet.loc[contribi] = self.generateRandomParameterValues()
    