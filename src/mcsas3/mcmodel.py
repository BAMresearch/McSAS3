from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas
import sasmodels
import sasmodels.core
import sasmodels.direct_model
from scipy import interpolate

import mcsas3.McHDF as McHDF


# TODO: perhaps better defined as a dataclass with attrs
class sphereParameters(object):
    # micro-class to mimick the nested structure of SasModels in simulation model:
    defaults = {
        "scale": 1.0,
        "background": 0.0,
        "sld": 1.0e-6,
        "sld_solvent": 0,
        "radius": 1,
    }

    def __init__(self) -> None:
        pass


# ibid.
class sphereInfo(object):
    # micro-class to mimick the nested structure of SasModels in simulation model:
    parameters = sphereParameters()

    def __init__(self) -> None:
        pass


class mcsasSphereModel(object):
    """pretends to be a sasmodel, but just for a sphere - in case sasmodels give gcc errors"""

    sld = None
    sld_solvent = None
    radius = None
    # scale = None
    # background = None
    settables = ["sld", "sld_solvent", "radius", "scale", "background"]
    measQ = None  # needs to be set later when initializing
    info = sphereInfo()

    def __init__(self, **kwargs: dict) -> None:
        # reset values to make sure we're not inheriting anything from another instance:
        self.sld = 1  # input SLD in units of 1e-6 1/A^2.
        self.sld_solvent = 0
        self.radius = []  # first element of two-eleemnt Q list
        # self.scale = None  # second element of two-element Q list
        # self.background = []  # intensity of simulated data
        self.measQ = None  # needs to be set later when initializing
        self.info = sphereInfo()

        # overwrites settings loaded from file if specified.
        for key, value in kwargs.items():
            assert (
                key in self.settables
            ), "Key '{}' is not a valid settable option. Valid options are: \n {}".format(
                key, self.settables
            )
            setattr(self, key, value)
        # assert all([key in kwargs.keys()
        #             for key in ['simDataQ0', 'simDataQ1', 'simDataI', 'simDataISigma']]),
        #        'The following input arguments must be provided to describe the simulation data:'
        #        'simDataQ0, simDataQ1, simDataI, simDataISigma'

    def make_kernel(self, measQ: np.ndarray = None):  # not sure of the output type... sasmodel?
        self.measQ = measQ
        return self.kernelfunc

    def kernelfunc(self, **parDict: dict) -> Tuple[np.ndarray, np.ndarray]:
        # print('stop here. see what we have. return I, V')
        qr = self.measQ[0] * parDict["radius"]
        F = 3.0 * (np.sin(qr) - qr * np.cos(qr)) / (qr**3.0)
        V = (np.pi * 4.0 / 3.0) * parDict["radius"] ** 3
        Int = (
            V**2
            # * self.scale
            * ((self.sld - self.sld_solvent) / 1e2)
            ** 2  # WARNING: CONVERSION FACTOR PRESENT (1e2) to convert from 1/A^2 to 1/nm^2!!!
            * F**2
        )
        return Int, V


# ibid.
class simParameters(object):
    # micro-class to mimick the nested structure of SasModels in simulation model:
    defaults = {
        "extrapY0": 0,
        "extrapScaling": 1,
        "simDataQ0": np.array([0, 0]),
        "simDataQ1": None,
        "simDataI": np.array([1, 1]),
        "simDataISigma": np.array([0.01, 0.01]),
    }

    def __init__(self):
        pass


# ibid.
class simInfo(object):
    # micro-class to mimick the nested structure of SasModels in simulation model:
    parameters = simParameters()

    def __init__(self):
        pass


# ibid.
class McSimPseudoModel(object):
    """pretends to be a sasmodel"""

    extrapY0 = None
    extrapScaling = None
    # simDataDict = {} # this can't be passed on in multiprocessing arguments,
    # so need to pass on individual bits:
    simDataQ0 = []  # first element of two-eleemnt Q list
    simDataQ1 = None  # second element of two-element Q list
    simDataI = []  # intensity of simulated data
    simDataISigma = []  # uncertainty on intensity of simulated data
    settables = [
        "extrapY0",
        "extrapScaling",
        "simDataQ0",
        "simDataQ1",
        "simDataI",
        "simDataISigma",
    ]
    Ipolator = None  # interp1D instance for interpolating intensity
    ISpolator = None  # interp1D instance for interpolating uncertainty on intensity
    measQ = None  # needs to be set later when initializing
    info = simInfo()

    def __init__(self, **kwargs: dict) -> None:
        # reset values to make sure we're not inheriting anything from another instance:
        self.extrapY0 = None
        self.extrapScaling = None
        # simDataDict = {} # this can't be passed on in multiprocessing arguments,
        # so need to pass on individual bits:
        self.simDataQ0 = []  # first element of two-eleemnt Q list
        self.simDataQ1 = None  # second element of two-element Q list
        self.simDataI = []  # intensity of simulated data
        self.simDataISigma = []  # uncertainty on intensity of simulated data
        self.Ipolator = None  # interp1D instance for interpolating intensity
        self.ISpolator = None  # interp1D instance for interpolating uncertainty on intensity
        self.measQ = None  # needs to be set later when initializing
        self.info = simInfo()

        # overwrites settings loaded from file if specified.
        for key, value in kwargs.items():
            assert (
                key in self.settables
            ), "Key '{}' is not a valid settable option. Valid options are: \n {}".format(
                key, self.settables
            )
            setattr(self, key, value)
        # if not 'simDataDict' in kwargs.keys():
        assert all(
            [
                key in kwargs.keys()
                for key in ["simDataQ0", "simDataQ1", "simDataI", "simDataISigma"]
            ]
        ), (
            "The following input arguments must be provided to describe the simulation data:"
            " simDataQ0, simDataQ1, simDataI, simDataISigma"
        )
        # self.simDataDict = {
        #     'Q': (self.simDataQ0, self.simDataQ1),
        #     'I': self.simDataI,
        #     'ISigma': self.simDataISigma
        # }
        # initialize interpolators and extrapolators:

        self.Ipolator = interpolate.interp1d(
            self.simDataQ0,
            self.simDataI,
            kind="linear",
            bounds_error=False,
            fill_value=(self.simDataI[0], np.nan),
        )
        self.ISpolator = interpolate.interp1d(
            self.simDataQ0,
            self.simDataISigma,
            kind="linear",
            bounds_error=False,
            fill_value=(self.simDataISigma[0], np.nan),
        )

    def make_kernel(self, measQ: np.ndarray):  # return type?
        self.measQ = measQ
        return self.kernelfunc

    # create extrapolator, based on the previously determined fit values:
    def extrapolatorHighQ(self, Q: np.ndarray) -> np.ndarray:
        y0 = self.extrapY0  # 2.21e-09
        scaling = self.extrapScaling  # 9.61e+01
        return y0 + Q ** (-4) * scaling

    def kernelfunc(self, **parDict: dict) -> Tuple[np.ndarray, np.ndarray]:
        # print('stop here. see what we have. return I, V')
        return self.interpscale(Rscale=parDict["factor"])

    def interpscale(
        self,
        Rscale: float = 1.0,  # scaling factor for the data. fitting parameter.
    ) -> Tuple[np.ndarray, np.ndarray]:
        # calculate scaled intensity:
        qScaled = self.measQ[0] * Rscale
        scaledSim = {
            "Q": [self.measQ[0]],
            "I": self.Ipolator(qScaled),
            "ISigma": self.ISpolator(qScaled),
        }
        # fill in intensity and (large) uncertainty in the extrapolated region:
        # for now we assume the uncertainty on the extrapolated region to be
        # the same as the magnitude of the extrapolated region:
        extrapArray = np.isnan(scaledSim["I"])
        scaledSim["I"][extrapArray] = self.extrapolatorHighQ(qScaled[extrapArray])
        scaledSim["ISigma"][extrapArray] = self.extrapolatorHighQ(qScaled[extrapArray])

        # Return Fsq-analog, i.e. a volume-squared intensity, will be volume-weighted later
        return scaledSim["I"] * Rscale**6, Rscale**3


# TODO: replace with attrs @define'd dataclass:
class McModel:
    """
    Specifies the fit parameter details and contains random pickers.
    Configuration can be alternatively loaded from an existing result file.

    Parameters
    ----------
    fitParameterLimits: dict of value pairs {"param1": (lower, upper), ... }
        for fit parameters
    staticParameters: dict of parameter-value pairs {"param2": value, ...}
        to keep static during the fit
    seed:
        random number generator seed, should vary for parallel execution
    nContrib:
        number of individual SasModel contributions
        from which the total model intensity is calculated
    modelName:
        SasModels model name to load, default 'sphere'
    OR: alternatively:
    loadFromFile: str
        A filename from a previous optimization that contains the required settings
    loadFromRepetition: int
        If the filename is specified, load the parameters from this particular repetition

    """

    func = None  # SasModels model instance
    modelName = "sphere"  # SasModels model name
    modelDType = "fast"  # model data type, choose 'fast' for single precision
    kernel = object  # SasModels kernel pointer
    parameterSet = None  # pandas dataFrame of length nContrib, with column names of parameters
    staticParameters = None  # dictionary of static parameter-value pairs during MC optimization
    pickParameters = None  # dict of values with new random picks, named by parameter names
    pickIndex = None  # int showing the running number of the current contribution being tested
    fitParameterLimits = None  # dict of value pairs (tuples) *for fit parameters only* with lower,
    # upper limits for the random function generator,
    # named by parameter names
    randomGenerators = None  # dict with random value generators
    volumes = None  # array of volumes for each model contribution, calculated during execution
    seed = 12345  # random generator seed, should vary for parallel execution
    nContrib = 300  # number of contributions that make up the entire model

    settables = [
        "nContrib",  # these are the allowed input arguments, can also be used later for storage
        "fitParameterLimits",
        "staticParameters",
        "modelName",
        "modelDType",
        "seed",
    ]

    def fitKeys(self) -> List[str]:
        return [key for key in self.fitParameterLimits.keys()]

    def __init__(
        self,
        loadFromFile: Optional[Path] = None,
        loadFromRepetition: Optional[int] = None,
        resultIndex: int = 1,
        **kwargs: dict,
    ) -> None:
        # reset everything so we're sure not to inherit anything from another instance:
        self.func = None  # SasModels model instance
        self.modelName = "sphere"  # SasModels model name
        self.modelDType = "fast"  # model data type, choose 'fast' for single precision
        self.kernel = object  # SasModels kernel pointer
        self.parameterSet = (
            None  # pandas dataFrame of length nContrib, with column names of parameters
        )
        self.staticParameters = (
            None  # dictionary of static parameter-value pairs during MC optimization
        )
        self.pickParameters = None  # dict of values with new random picks,
        # named by parameter names
        self.pickIndex = (
            None  # int showing the running number of the current contribution being tested
        )
        self.fitParameterLimits = None  # dict of value pairs (tuples) *for fit parameters only*
        # with lower, upper limits for the random function
        # generator, named by parameter names
        self.randomGenerators = None  # dict with random value generators
        self.volumes = (
            None  # array of volumes for each model contribution, calculated during execution
        )
        self.seed = 12345  # random generator seed, should vary for parallel execution
        self.nContrib = 300  # number of contributions that make up the entire model

        # make sure we store and read from the right place.
        self.resultIndex = McHDF.ResultIndex(resultIndex)  # defines the HDF5 root path

        if loadFromFile is not None:
            # nContrib is reset with the length of the tables:
            self.load(loadFromFile, loadFromRepetition)

        # overwrites settings loaded from file if specified.
        for key, value in kwargs.items():
            assert (
                key in self.settables
            ), "Key '{}' is not a valid settable option. Valid options are: \n {}".format(
                key, self.settables
            )
            setattr(self, key, value)

        if self.randomGenerators is None:
            self.randomGenerators = dict.fromkeys(
                [key for key in self.fitKeys()],
                np.random.RandomState(self.seed).uniform,
            )
        if self.parameterSet is None:
            self.parameterSet = pandas.DataFrame(index=range(self.nContrib), columns=self.fitKeys())
            self.resetParameterSet()

        if self.modelName.lower() == "sim":
            self.loadSimModel()
        elif self.modelName.lower() == "mcsas_sphere":
            self.loadMcsasSphereModel()
        else:
            self.loadModel()

        self.checkSettings()

    def checkSettings(self) -> None:
        for key in self.settables:
            if key in ("seed",):
                continue
            val = getattr(self, key, None)
            assert val is not None, "required McModel setting {} has not been defined..".format(key)

        assert self.func is not None, "SasModels function has not been loaded"
        assert self.parameterSet is not None, "parameterSet has not been initialized"

    def calcModelIV(self, parameters: dict) -> Tuple[np.ndarray, np.ndarray]:
        # moved from McCore
        if (self.modelName.lower() != "sim") and (self.modelName.lower() != "mcsas_sphere"):
            # Fsq has been checked with Paul Kienzle, is the part in the square brackets squared
            # as in this equation (http://www.sasview.org/docs/user/models/sphere.html).
            # So needs to be divided by the volume.
            if isinstance(self.kernel, sasmodels.product.ProductKernel):
                # call_Fq not available
                Fsq = sasmodels.direct_model.call_kernel(
                    self.kernel, dict(self.staticParameters, **parameters)
                )
                # might slow it down considerably, but it appears this is the way
                # to get the volume for productkernels
                V_shell = self.kernel.results()["volume"]
                # this needs to be done for productKernel:
                Fsq = Fsq * V_shell
            else:
                F, Fsq, R_eff, V_shell, V_ratio = sasmodels.direct_model.call_Fq(
                    self.kernel, dict(self.staticParameters, **parameters)
                )
        else:
            Fsq, V_shell = self.kernel(**dict(self.staticParameters, **parameters))
        # modelIntensity = Fsq/V_shell
        # modelVolume = V_shell

        # TODO: check if this is correct also for the simulated data...
        #       Volume-weighting seems correct for the SasView models at least
        # division by 4/3 np.pi seems to be necessary to bring the absolute intensity in line
        # return Fsq / V_shell / (4 / 3 * np.pi), V_shell
        return Fsq / V_shell, V_shell

    def pick(self) -> None:
        """pick new random model parameter"""
        self.pickParameters = self.generateRandomParameterValues()

    def generateRandomParameterValues(self) -> None:
        """to be depreciated as soon as models can generate their own..."""
        # initialize dict with parameter-value pairs defaulting to None
        returnDict = dict.fromkeys([key for key in self.fitParameterLimits])
        # fill:
        for parName in self.fitParameterLimits.keys():
            # can be replaced by a loop over iteritems:
            (upper, lower) = self.fitParameterLimits[parName]
            returnDict[parName] = self.randomGenerators[parName](upper, lower)
        return returnDict

    def resetParameterSet(self) -> None:
        """fills the model parameter values with random values"""
        for contribi in range(self.nContrib):
            # can be improved with a list comprehension, but this only executes once..
            self.parameterSet.loc[contribi] = self.generateRandomParameterValues()

    # Loading and Storing functions:

    def load(self, loadFromFile: Path, loadFromRepetition: int) -> None:
        """
        loads a preset set of contributions from a previous optimization, stored in HDF5
        nContrib is reset to the length of the previous optimization.
        """
        assert (
            loadFromFile is not None
        ), "Input filename cannot be empty. Also specify a repetition number to load."
        assert (
            loadFromRepetition is not None
        ), "Repetition number must be given when loading model parameters from a file"

        path = self.resultIndex.nxsEntryPoint / "model"

        self.fitParameterLimits = McHDF.loadKV(
            loadFromFile, path / "fitParameterLimits", datatype="dict"
        )
        self.staticParameters = McHDF.loadKV(
            loadFromFile, path / "staticParameters", datatype="dict"
        )
        self.modelName = McHDF.loadKV(
            loadFromFile, path / "modelName", datatype="str"
        )  # .decode('utf8')
        path /= f"repetition{loadFromRepetition}"
        self.parameterSet = McHDF.loadKV(
            loadFromFile, path / "parameterSet", datatype="dictToPandas"
        )
        self.parameterSet.columns = [
            colname for colname in self.parameterSet.columns
        ]  # what does this do, a no-op?
        self.volumes = McHDF.loadKV(loadFromFile, path / "volumes")
        self.seed = McHDF.loadKV(loadFromFile, path / "seed")
        self.modelDType = McHDF.loadKV(loadFromFile, path / "modelDType", datatype="str")
        self.nContrib = self.parameterSet.shape[0]

    def store(self, filename: Path, repetition: int) -> None:
        assert (
            repetition is not None
        ), "Repetition number must be given when storing model parameters into a paramFile"
        assert filename is not None

        path = self.resultIndex.nxsEntryPoint / "model"
        McHDF.storeKVPairs(filename, path / "fitParameterLimits", self.fitParameterLimits.items())
        McHDF.storeKVPairs(filename, path / "staticParameters", self.staticParameters.items())
        McHDF.storeKV(
            filename, path=path / "modelName", value=str(self.modelName)
        )  # store modelName

        psDict = self.parameterSet.copy().to_dict(orient="split")
        McHDF.storeKVPairs(
            filename, path / f"repetition{repetition}" / "parameterSet", psDict.items()
        )
        McHDF.storeKVPairs(
            filename,
            path / f"repetition{repetition}",
            [("seed", self.seed), ("volumes", self.volumes), ("modelDType", self.modelDType)],
        )

    # SasView SasModel helper functions:

    def availableModels(self) -> None:
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

    def modelExists(self) -> bool:
        return True
        # todo: this doesn't work anymore when combining models, e.g. sphere@hardsphere
        # # checks whether the given model name exists, throw exception if not
        # assert (
        #     self.modelName in sasmodels.core.list_models()
        # ), "Model with name: {} does not exist in the list of available models: \n {}".format(
        #     self.modelName, sasmodels.core.list_models()
        # )
        # return True

    def loadModel(self) -> None:
        # loads sasView model and puts the handle in the right place:
        self.modelExists()  # check if model exists
        self.func = sasmodels.core.load_model(self.modelName, dtype=self.modelDType)

    def loadMcsasSphereModel(self) -> None:
        self.func = mcsasSphereModel(
            **self.staticParameters
            # no arguments here... probably
        )

    def loadSimModel(self) -> None:
        if "simDataQ1" not in self.staticParameters.keys():
            # if it was None when written, it might not exist when loading
            self.staticParameters.update({"simDataQ1": None})

        self.func = McSimPseudoModel(
            extrapY0=self.staticParameters["extrapY0"],
            extrapScaling=self.staticParameters["extrapScaling"],
            simDataQ0=self.staticParameters["simDataQ0"],
            simDataQ1=self.staticParameters["simDataQ1"],
            simDataI=self.staticParameters["simDataI"],
            simDataISigma=self.staticParameters["simDataISigma"],
        )
        # simDataDict= self.staticParameters['simDataDict'])

    def showModelParameters(self) -> dict:
        # find out what the parameters are for the set model, e.g.:
        # mc.showModelParameters()
        assert (
            self.func is not None
        ), "Model must be loaded already before this function can be used, using self.loadModel()"
        return self.func.info.parameters.defaults
