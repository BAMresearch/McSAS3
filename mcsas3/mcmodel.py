import pandas
import numpy as np
from .McHDF import McHDF
import sasmodels
import sasmodels.core, sasmodels.direct_model

class McModel(McHDF):
    """
    Specifies the fit parameter details and contains random pickers. Configuration can be alternatively loaded from an existing result file. 

    parameters:
    ===
    * fitParameterLimits *: dict of value pairs {"param1": (lower, upper), ... } for fit parameters
    * staticParameters *: dict of parameter-value pairs to keep static during the fit {"param2": value, ...}. 
    * seed *: random number generator seed, should vary for parallel execution
    * nContrib *: number of individual SasModel contributions from which the total model intensity is calculated
    * modelName *: SasModels model name to load, default 'sphere'

    or:
    ===
    * loadFromFile *: A filename from a previous optimization that contains the required settings
    * loadFromRepetition *: if the filename is specified, load the parameters from this particular repetition

    """

    func = None               # SasModels model instance
    modelName = "sphere"      # SasModels model name
    modelDType = "fast"       # model data type, choose 'fast' for single precision
    kernel = None             # SasModels kernel pointer
    parameterSet = None       # pandas dataFrame of length nContrib, with column names of parameters
    staticParameters = None   # dictionary of static parameter-value pairs during MC optimization
    pickParameters = None     # dict of values with new random picks, named by parameter names
    pickIndex = None          # int showing the running number of the current contribution being tested
    fitParameterLimits = None # dict of value pairs (tuples) *for fit parameters only* with lower, upper limits for the random function generator, named by parameter names 
    randomGenerators = None   # dict with random value generators 
    volumes = None            # array of volumes for each model contribution, calculated during execution
    seed = 12345              # random generator seed, should vary for parallel execution
    nContrib = 300            # number of contributions that make up the entire model

    settables = ["nContrib", # these are the allowed input arguments, can also be used later for storage
                "fitParameterLimits", 
                "staticParameters", 
                "modelName", 
                "modelDType",
                "seed"]

    def fitKeys(self):
        return [key for key in self.fitParameterLimits]
    
    def __init__(self, 
                loadFromFile = None,
                loadFromRepetition = None,
                **kwargs
                ):

        if loadFromFile is not None:
            # nContrib is reset with the length of the tables:
            self.load(loadFromFile, loadFromRepetition)

        # overwrites settings loaded from file if specified.
        for key, value in kwargs.items(): 
            assert (key in self.settables), "Key '{}' is not a valid settable option. "\
                    "Valid options are: \n {}".format(key, self.settables)
            setattr(self, key, value)

        if self.randomGenerators is None:
            self.randomGenerators = dict.fromkeys(
                [key for key in self.fitKeys()], np.random.RandomState(self.seed).uniform)

        if self.parameterSet is None:
            self.parameterSet = pandas.DataFrame(
                index = range(self.nContrib), columns = self.fitKeys())
            self.resetParameterSet()

        self.loadModel()
        self.checkSettings()

    def checkSettings(self):
        for key in self.settables:
            val = getattr(self, key, None)
            assert val is not None, "required McModel setting {} has not been defined..".format(key)

        assert self.func is not None, "SasModels function has not been loaded"
        assert self.parameterSet is not None, "parameterSet has not been initialized"

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
    
    def resetParameterSet(self):
        """fills the model parameter values with random values"""
        for contribi in range(self.nContrib):
            # can be improved with a list comprehension, but this only executes once..
            self.parameterSet.loc[contribi] = self.generateRandomParameterValues()

    ####### Loading and Storing functions: ########

    def load(self, loadFromFile = None, loadFromRepetition = None):
        """
        loads a preset set of contributions from a previous optimization, stored in HDF5 
        nContrib is reset to the length of the previous optimization. 
        """
        assert(loadFromFile is not None), "Input filename cannot be empty. Also specify a repetition number to load."
        assert(loadFromRepetition is not None), "Repetition number must be given when loading model parameters from a file"
        
        self.fitParameterLimits = self._HDFloadKV(
            filename = loadFromFile, 
            path = "/entry1/analysis/MCResult1/model/fitParameterLimits/", 
            datatype = "dict")
        self.staticParameters = self._HDFloadKV(
            filename = loadFromFile, 
            path = "/entry1/analysis/MCResult1/model/staticParameters/", 
            datatype = "dict")
        self.modelName = self._HDFloadKV(
            filename = loadFromFile, 
            path = "/entry1/analysis/MCResult1/model/modelName")
        self.parameterSet = self._HDFloadKV(
            filename = loadFromFile,
            path = "/entry1/analysis/MCResult1/model/repetition{}/parameterSet/".format(loadFromRepetition),
            datatype = "dictToPandas")
        self.volumes = self._HDFloadKV(
            filename = loadFromFile, 
            path = "/entry1/analysis/MCResult1/model/repetition{}/volumes".format(loadFromRepetition))
        self.seed = self._HDFloadKV(filename = loadFromFile, 
            path = "/entry1/analysis/MCResult1/model/repetition{}/seed".format(loadFromRepetition))
        self.modelDType = self._HDFloadKV(filename = loadFromFile,
            path = "/entry1/analysis/MCResult1/model/repetition{}/modelDType".format(loadFromRepetition))

        self.nContrib = self.parameterSet.shape[0]

    def store(self, filename = None, repetition = None):
        assert(repetition is not None),"Repetition number must be given when storing model parameters into a paramFile"

        for parName in self.fitParameterLimits.keys():
            self._HDFstoreKV(filename = filename, 
                path = "/entry1/analysis/MCResult1/model/fitParameterLimits/", 
                key = parName, 
                value = self.fitParameterLimits[parName])
        for parName in self.staticParameters.keys():
            self._HDFstoreKV(filename = filename, 
                path = "/entry1/analysis/MCResult1/model/staticParameters/", 
                key = parName, 
                value = self.staticParameters[parName])
        # store modelName
        self._HDFstoreKV(filename = filename, 
            path = "/entry1/analysis/MCResult1/model/", 
            key = "modelName", 
            value = self.modelName)  

        psDict = self.parameterSet.copy().to_dict(orient = 'split')
        for parName in psDict.keys():
            # print("storing key: {}, value: {}".format(parName, psDict[parName]))
            self._HDFstoreKV(filename = filename, 
                path = "/entry1/analysis/MCResult1/model/repetition{}/parameterSet".format(repetition), 
                key = parName, 
                value = psDict[parName])
        # Store seed:
        self._HDFstoreKV(filename = filename, 
            path = "/entry1/analysis/MCResult1/model/repetition{}/".format(repetition), 
            key = "seed", 
            value = self.seed)
        # store volumes:
        self._HDFstoreKV(filename = filename, 
            path = "/entry1/analysis/MCResult1/model/repetition{}/".format(repetition), 
            key = "volumes",
            value = self.volumes)
        # store modelDType
        self._HDFstoreKV(filename = filename,
            path = "/entry1/analysis/MCResult1/model/repetition{}/".format(repetition),
            key = "modelDType",
            value = self.modelDType)

    ####### SasView SasModel helper functions: ########

    def availableModels(self):
        # show me all the available models, 1D and 1D+2D
        print("\n \n   1D-only SasModel Models:\n")

        for model in sasmodels.core.list_models():
            modelInfo = sasmodels.core.load_model_info(model)
            if not modelInfo.parameters.has_2d:
                print("{} is available only in 1D".format(modelInfo.id))

        print("\n \n   2D- and 1D- SasModel Models:\n")
        for model in sasmodels.core.list_models():
            modelInfo = sasmodels.core.load_model_info(model)
            if modelInfo.parameters.has_2d:
                print("{} is available in 1D and 2D".format(modelInfo.id))

    def modelExists(self):
        # checks whether the given model name exists, throw exception if not
        assert self.modelName in sasmodels.core.list_models(), "Model with name: {} does not exist in the list of available models: \n {}".format(self.modelName, sasmodels.core.list_models())
        return True

    def loadModel(self):
        # loads sasView model and puts the handle in the right place:
        self.modelExists() # check if model exists
        self.func = sasmodels.core.load_model(self.modelName, dtype=self.modelDType)

    def showModelParameters(self):
        # find out what the parameters are for the set model, e.g.:
        # mc.showModelParameters()
        assert self.func is not None, "Model must be loaded already before this function can be used, using self.loadModel()"
        return self.func.info.parameters.defaults


