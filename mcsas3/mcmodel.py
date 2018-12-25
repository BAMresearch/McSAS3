import pandas
import numpy as np
from .McHDF import McHDF


class McModel(McHDF):
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
    nContrib = None # number of contributions that make up the entire model, migrated from mcOpt

    def fitKeys(self):
        return [key for key in self.fitParameterLimits]
    
    def __init__(self, 
                nContrib = 300, 
                fitParameterLimits = None, 
                staticParameters = None, 
                func = None, 
                seed = 12345,
                presetFile = None,
                repetition = None,
                ):
        self.func = func
        self.fitParameterLimits = fitParameterLimits
        self.staticParameters = staticParameters
        self.seed = seed
        self.nContrib = nContrib

        if presetFile is not None:
            # nContrib is reset with the length of the tables:
            self.load(presetFile, repetition)

        self.randomGenerators = dict.fromkeys(
            [key for key in self.fitParameterLimits], np.random.RandomState(self.seed).uniform)
        self.parameterSet = pandas.DataFrame(
            index = range(self.nContrib), columns = self.fitKeys())
        self.fillParameterSet()


    def load(self, presetFile = None, repetition = None):
        """
        loads a preset set of contributions from a previous optimization, stored in HDF5 
        nContrib is reset to the length of the previous optimization. 
        """
        assert(presetFile is not None), "Input filename cannot be empty. Also specify a repetition number to load."
        assert(repetition is not None), "Repetition number must be given when loading model parameters from a paramFile"
        self.parameterSet = pandas.read_hdf(presetFile, 
                      "/entry1/MCResult1/model/parameterSet/repetition{}/".format(repetition))    
        self.nContrib = self.parameterSet.shape[0]

    def store(self, filename = None, repetition = None):
        assert(repetition is not None),"Repetition number must be given when storing model parameters into a paramFile"
        # prepare data types for HDF5-compatibility:
        # for key in self.parameterSet.keys():
        #     if self.parameterSet[key].dtype is "float64":
        #         self.parameterSet[key].astype("float") # HDF5 supported dtype
        #     else:
        #         # not sure this line is necessary...
        #         self.parameterSet[key].astype(self.parameterSet[key].dtype)
            
        # store result in an output file: #0 should be repetition later on
        # self.parameterSet.to_hdf(paramFile, 
        #                               "/entry1/MCResult1/model/parameterSet/repetition{}".format(repetition), 
        #                               format = "fixed", data_columns = True)
        for parName in self.fitParameterLimits.keys():
            self._HDFstoreKV(filename = filename, 
                path = "/entry1/MCResult1/model/fitParameterLimits/", 
                key = parName, 
                value = self.fitParameterLimits[parName])
        for parName in self.staticParameters.keys():
            self._HDFstoreKV(filename = filename, 
                path = "/entry1/MCResult1/model/staticParameters/", 
                key = parName, 
                value = self.staticParameters[parName])
        psDict = self.parameterSet.copy().to_dict(orient = 'split')
        for parName in psDict.keys():
            # print("storing key: {}, value: {}".format(parName, psDict[parName]))
            self._HDFstoreKV(filename = filename, 
                path = "/entry1/MCResult1/model/parameterSet/repetition{}/".format(repetition), 
                key = parName, 
                value = psDict[parName])  
        # Store seed:
        self._HDFstoreKV(filename = filename, 
            path = "/entry1/MCResult1/model/parameterSet/repetition{}/".format(repetition), 
            key = "seed", 
            value = self.seed)  
        self._HDFstoreKV(filename = filename, 
            path = "/entry1/MCResult1/model/parameterSet/repetition{}/".format(repetition), 
            key = "volumes", 
            value = self.volumes)  
       
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
    