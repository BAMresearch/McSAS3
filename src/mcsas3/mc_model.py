import logging
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional, Tuple

import numpy as np
import pandas
import sasmodels
import sasmodels.core
import sasmodels.direct_model
from scipy import interpolate

from mcsas3.mc_hdf import ResultIndex, loadKV, storeKV, storeKVPairs

from .parameter_units import (
    LEGACY_CUSTOM_MODEL_SCALE_TO_VOLUME_FRACTION,
    SASMODELS_SCALE_TO_VOLUME_FRACTION,
    sasmodels_length_parameter_ids,
    sasmodels_parameter_values,
    sasmodels_q_arrays,
)

logger = logging.getLogger(__name__)

SPHERE_MODEL_DEFAULTS = {
    "scale": 1.0,
    "background": 0.0,
    "sld": 1.0e-6,
    "sld_solvent": 0,
    "radius": 1,
}
AUTO_EXTRAPOLATION = "auto"
SIM_MODEL_DEFAULTS = {
    "extrapY0": AUTO_EXTRAPOLATION,
    "extrapScaling": AUTO_EXTRAPOLATION,
    "simDataQ0": np.array([0, 0]),
    "simDataQ1": None,
    "simDataI": np.array([1, 1]),
    "simDataISigma": np.array([0.01, 0.01]),
}
SIM_MODEL_EXTRAPOLATION_TAIL_FRACTION = 0.1
SIM_MODEL_EXTRAPOLATION_MIN_POINTS = 5
CUSTOM_MODEL_LOADERS = {
    "sim": "_load_sim_model",
    "mcsas_sphere": "_load_mcsas_sphere_model",
}


def _copy_default_value(value):
    if isinstance(value, np.ndarray):
        return np.array(value, copy=True)
    return value


def _pseudo_model_info(defaults: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        parameters=SimpleNamespace(defaults={key: _copy_default_value(value) for key, value in defaults.items()})
    )


def _require_valid_settable_keys(kwargs: dict, allowed_keys: list[str]) -> None:
    for key in kwargs:
        if key not in allowed_keys:
            raise ValueError(
                "Key '{}' is not a valid settable option. Valid options are: \n {}".format(key, allowed_keys)
            )


class mcsasSphereModel:
    """pretends to be a sasmodel, but just for a sphere - in case sasmodels give gcc errors"""

    settables = ("sld", "sld_solvent", "radius", "scale", "background")

    def __init__(self, **kwargs: dict) -> None:
        # reset values to make sure we're not inheriting anything from another instance:
        self.sld = SPHERE_MODEL_DEFAULTS["sld"]  # input SLD in units of 1e-6 1/A^2.
        self.sld_solvent = SPHERE_MODEL_DEFAULTS["sld_solvent"]
        self.radius = SPHERE_MODEL_DEFAULTS["radius"]
        # self.scale = None  # second element of two-element Q list
        # self.background = []  # intensity of simulated data
        self.measQ = None  # needs to be set later when initializing
        self.info = _pseudo_model_info(SPHERE_MODEL_DEFAULTS)

        # overwrites settings loaded from file if specified.
        _require_valid_settable_keys(kwargs, self.settables)
        for key, value in kwargs.items():
            setattr(self, key, value)

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


class McSimPseudoModel:
    """
    Pretends to be a sasmodel for direct simulated model curves.

    Values below the simulated Q range use the first simulated intensity. Values above
    the simulated Q range use ``extrapY0 + extrapScaling * Q**-4``. If omitted or set
    to ``"auto"``, ``extrapY0`` resolves to zero and ``extrapScaling`` is estimated
    from finite high-Q data points with positive Q values.
    """

    settables = (
        "extrapY0",
        "extrapScaling",
        "simDataQ0",
        "simDataQ1",
        "simDataI",
        "simDataISigma",
    )

    def __init__(self, **kwargs: dict) -> None:
        # reset values to make sure we're not inheriting anything from another instance:
        self.extrapY0 = SIM_MODEL_DEFAULTS["extrapY0"]
        self.extrapScaling = SIM_MODEL_DEFAULTS["extrapScaling"]
        # simDataDict = {} # this can't be passed on in multiprocessing arguments,
        # so need to pass on individual bits:
        self.simDataQ0 = np.array([], dtype=float)  # first element of two-eleemnt Q list
        self.simDataQ1 = SIM_MODEL_DEFAULTS["simDataQ1"]  # second element of two-element Q list
        self.simDataI = np.array([], dtype=float)  # intensity of simulated data
        self.simDataISigma = np.array([], dtype=float)  # uncertainty on intensity of simulated data
        self.Ipolator = None  # interp1D instance for interpolating intensity
        self.ISpolator = None  # interp1D instance for interpolating uncertainty on intensity
        self.measQ = None  # needs to be set later when initializing
        self.info = _pseudo_model_info(SIM_MODEL_DEFAULTS)

        # overwrites settings loaded from file if specified.
        _require_valid_settable_keys(kwargs, self.settables)
        for key, value in kwargs.items():
            setattr(self, key, value)
        required_sim_keys = ["simDataQ0", "simDataQ1", "simDataI", "simDataISigma"]
        missing_sim_keys = [key for key in required_sim_keys if key not in kwargs]
        if missing_sim_keys:
            raise ValueError(
                "The following input arguments must be provided to describe the simulation data: "
                "simDataQ0, simDataQ1, simDataI, simDataISigma. Missing: " + ", ".join(missing_sim_keys)
            )
        self.simDataQ0 = np.asarray(self.simDataQ0, dtype=float)
        self.simDataI = np.asarray(self.simDataI, dtype=float)
        self.simDataISigma = np.asarray(self.simDataISigma, dtype=float)
        self._resolve_high_q_extrapolation()
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

    @staticmethod
    def _is_auto_extrapolation_value(value: object) -> bool:
        return value is None or (isinstance(value, str) and value.lower() == AUTO_EXTRAPOLATION)

    def _resolve_high_q_extrapolation(self) -> None:
        if self._is_auto_extrapolation_value(self.extrapY0):
            self.extrapY0 = 0.0
        else:
            self.extrapY0 = float(self.extrapY0)

        if self._is_auto_extrapolation_value(self.extrapScaling):
            self.extrapScaling = self._estimate_porod_extrapolation_scaling(self.extrapY0)
        else:
            self.extrapScaling = float(self.extrapScaling)

        if not np.isfinite(self.extrapY0) or not np.isfinite(self.extrapScaling):
            raise ValueError("extrapY0 and extrapScaling must resolve to finite numeric values.")
        self.info.parameters.defaults["extrapY0"] = self.extrapY0
        self.info.parameters.defaults["extrapScaling"] = self.extrapScaling

    def _estimate_porod_extrapolation_scaling(self, extrap_y0: float) -> float:
        q = np.asarray(self.simDataQ0, dtype=float)
        intensity = np.asarray(self.simDataI, dtype=float)
        sigma = np.asarray(self.simDataISigma, dtype=float)
        valid = np.isfinite(q) & np.isfinite(intensity) & (q > 0)
        use_sigma = sigma.shape == q.shape
        q = q[valid]
        intensity = intensity[valid]
        if use_sigma:
            sigma = sigma[valid]
        if q.size < 2:
            raise ValueError("At least two finite positive Q values are needed for automatic Porod extrapolation.")

        sort_index = np.argsort(q)
        q = q[sort_index]
        intensity = intensity[sort_index]
        if use_sigma:
            sigma = sigma[sort_index]
        tail_size = min(
            q.size,
            max(
                SIM_MODEL_EXTRAPOLATION_MIN_POINTS,
                int(np.ceil(q.size * SIM_MODEL_EXTRAPOLATION_TAIL_FRACTION)),
            ),
        )
        tail_q = q[-tail_size:]
        tail_intensity = intensity[-tail_size:] - extrap_y0
        predictor = tail_q**-4
        weights = np.ones_like(predictor)
        if use_sigma:
            tail_sigma = sigma[-tail_size:]
            if np.all(np.isfinite(tail_sigma) & (tail_sigma > 0)):
                weights = 1.0 / tail_sigma**2

        denominator = np.sum(weights * predictor**2)
        if not np.isfinite(denominator) or denominator <= 0:
            raise ValueError("Automatic Porod extrapolation could not fit a finite high-Q coefficient.")
        return float(np.sum(weights * predictor * tail_intensity) / denominator)

    def extrapolatorHighQ(self, Q: np.ndarray) -> np.ndarray:
        y0 = self.extrapY0
        scaling = self.extrapScaling
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

    settables = (
        "nContrib",  # these are the allowed input arguments, can also be used later for storage
        "fitParameterLimits",
        "staticParameters",
        "modelName",
        "modelDType",
        "seed",
        "logRandom",
    )

    def fit_keys(self) -> List[str]:
        return [key for key in self.fitParameterLimits.keys()]

    def _log_uniform(self, rng: np.random.Generator, low: float, high: float, size: int | None = None) -> np.ndarray:
        if low <= 0 or high <= 0:
            raise ValueError("low and high must be positive, nonzero values.")
        if low > high:
            low, high = high, low
        return 10 ** (rng(low=np.log10(low), high=np.log10(high), size=size))

    def __init__(
        self,
        loadFromFile: Optional[Path] = None,
        loadFromRepetition: Optional[int] = None,
        resultIndex: int = 1,
        **kwargs: dict,
    ) -> None:
        self._reset_state()

        # make sure we store and read from the right place.
        self.resultIndex = ResultIndex(resultIndex)  # defines the HDF5 root path

        if loadFromFile is not None:
            # nContrib is reset with the length of the tables:
            self.load(loadFromFile, loadFromRepetition)

        self._apply_configuration(kwargs)
        self._initialize_random_generators()
        self._initialize_parameter_set()
        self._load_model_function()
        self.checkSettings()

    def _reset_state(self) -> None:
        """Reset instance state so a fresh model never inherits previous run state."""
        self.func = None  # SasModels model instance
        self.modelName = "sphere"  # SasModels model name
        self.modelDType = "fast"  # model data type, choose 'fast' for single precision
        self.kernel = object  # SasModels kernel pointer
        self.parameterSet = None  # pandas dataFrame of length nContrib, with column names of parameters
        self.staticParameters = None  # dictionary of static parameter-value pairs during MC optimization
        self.pickParameters = None  # dict of values with new random picks,
        # named by parameter names
        self.pickIndex = None  # int showing the running number of the current contribution being tested
        self.fitParameterLimits = None  # dict of value pairs (tuples) *for fit parameters only*
        # with lower, upper limits for the random function
        # generator, named by parameter names
        self.randomGenerators = None  # dict with random value generators
        self.volumes = None  # array of volumes for each model contribution, calculated during execution
        self._sasmodels_length_parameters = None
        self.seed = 12345  # random generator seed, should vary for parallel execution
        self.nContrib = 300  # number of contributions that make up the entire model
        self.logRandoms = None
        self.logRandom = False

    def _apply_configuration(self, kwargs: dict) -> None:
        # overwrites settings loaded from file if specified.
        _require_valid_settable_keys(kwargs, self.settables)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _initialize_random_generators(self) -> None:
        if self.randomGenerators is None:
            uniform = np.random.default_rng(self.seed).uniform
            self.randomGenerators = {key: uniform for key in self.fit_keys()}
        if self.logRandoms is None:
            self.logRandoms = {key: self.logRandom for key in self.fit_keys()}

    def _initialize_parameter_set(self) -> None:
        if self.parameterSet is None:
            self.parameterSet = pandas.DataFrame(index=range(self.nContrib), columns=self.fit_keys())
            self.resetParameterSet()

    def _load_model_function(self) -> None:
        custom_loader_name = CUSTOM_MODEL_LOADERS.get(self.modelName.lower())
        if custom_loader_name is None:
            self._load_sasmodels_model()
            return
        getattr(self, custom_loader_name)()

    def checkSettings(self) -> None:
        for key in self.settables:
            if key in ("seed",):
                continue
            val = getattr(self, key, None)
            if val is None:
                raise ValueError("Required McModel setting {} has not been defined.".format(key))

        if self.func is None:
            raise RuntimeError("SasModels function has not been loaded.")
        if self.parameterSet is None:
            raise RuntimeError("parameterSet has not been initialized.")

    def _uses_sasmodels_unit_conventions(self) -> bool:
        return self.modelName.lower() not in CUSTOM_MODEL_LOADERS

    def volume_fraction_correction_factor(self) -> float:
        if self._uses_sasmodels_unit_conventions():
            return SASMODELS_SCALE_TO_VOLUME_FRACTION
        return LEGACY_CUSTOM_MODEL_SCALE_TO_VOLUME_FRACTION

    def make_kernel(self, model_q: list[np.ndarray]):
        """Create a model kernel, converting canonical McSAS3 Q units for SasModels."""
        kernel_q = sasmodels_q_arrays(model_q) if self._uses_sasmodels_unit_conventions() else model_q
        self.kernel = self.func.make_kernel(kernel_q)
        return self.kernel

    def _kernel_parameters(self, parameters: dict) -> dict:
        kernel_params = dict(self.staticParameters, **parameters)
        if self._uses_sasmodels_unit_conventions():
            return sasmodels_parameter_values(
                kernel_params,
                length_parameters=self._sasmodels_length_parameters,
            )
        return kernel_params

    def kernel_static_parameters(self) -> dict:
        """Return static parameters in the unit convention expected by the loaded model."""
        return self._kernel_parameters({})

    def calcModelIV(self, parameters: dict) -> Tuple[np.ndarray, np.ndarray]:
        # moved from McCore
        kernelParams = self._kernel_parameters(parameters)
        if (self.modelName.lower() != "sim") and (self.modelName.lower() != "mcsas_sphere"):
            # Fsq has been checked with Paul Kienzle, is the part in the square brackets squared
            # as in this equation (http://www.sasview.org/docs/user/models/sphere.html).
            # So needs to be divided by the volume.
            if isinstance(self.kernel, sasmodels.mixture.MixtureKernel):
                logger.warning(
                    "for Mixture kernels (e.g. a+b+...), element a must be a volumetric object "
                    "for McSAS optimizations, the rest must be static!"
                )

            if isinstance(self.kernel, (sasmodels.product.ProductKernel, sasmodels.mixture.MixtureKernel)):
                # call_Fq not available
                Fsq = sasmodels.direct_model.call_kernel(self.kernel, kernelParams)
                try:
                    V_shell = self.kernel.results()["volume"]
                except KeyError:
                    raise NotImplementedError("This model does not have a volume and cannot be used in McSAS3.")
                # this needs to be done for productKernel:
                Fsq = Fsq * V_shell
            else:
                F, Fsq, R_eff, V_shell, V_ratio = sasmodels.direct_model.call_Fq(self.kernel, kernelParams)
        else:
            Fsq, V_shell = self.kernel(**kernelParams)
        # modelIntensity = Fsq/V_shell
        # modelVolume = V_shell

        # TODO: check if this is correct also for the simulated data...
        #       Volume-weighting seems correct for the SasView models at least
        # division by 4/3 np.pi seems to be necessary to bring the absolute intensity in line
        # return Fsq / V_shell / (4 / 3 * np.pi), V_shell
        return Fsq / V_shell, V_shell

    def pick(self) -> None:
        """pick new random model parameter"""
        self.pickParameters = self.generate_random_parameter_values()

    def generate_random_parameter_values(self) -> dict[str, float]:
        """Generate one new random parameter set within the configured fit limits."""
        return_dict = dict.fromkeys(self.fitParameterLimits)
        for parName, (lower, upper) in self.fitParameterLimits.items():
            if self.logRandoms[parName]:
                return_dict[parName] = self._log_uniform(self.randomGenerators[parName], lower, upper)
            else:
                return_dict[parName] = self.randomGenerators[parName](low=lower, high=upper)
        return return_dict

    def resetParameterSet(self) -> None:
        """fills the model parameter values with random values"""
        for contribi in range(self.nContrib):
            self.parameterSet.loc[contribi] = self.generate_random_parameter_values()

    # Loading and Storing functions:

    def load(self, loadFromFile: Path, loadFromRepetition: int) -> None:
        """
        loads a preset set of contributions from a previous optimization, stored in HDF5
        nContrib is reset to the length of the previous optimization.
        """
        if loadFromFile is None:
            raise ValueError("Input filename cannot be empty. Also specify a repetition number to load.")
        if loadFromRepetition is None:
            raise ValueError("Repetition number must be given when loading model parameters from a file")

        path = self.resultIndex.nxsEntryPoint / "model"

        self.fitParameterLimits = loadKV(loadFromFile, path / "fitParameterLimits", datatype="dict")
        self.staticParameters = loadKV(loadFromFile, path / "staticParameters", datatype="dict")
        self.modelName = loadKV(loadFromFile, path / "modelName", datatype="str")  # .decode('utf8')
        path /= f"repetition{loadFromRepetition}"
        self.parameterSet = loadKV(loadFromFile, path / "parameterSet", datatype="dictToPandas")
        self.volumes = loadKV(loadFromFile, path / "volumes")
        self.seed = loadKV(loadFromFile, path / "seed")
        self.modelDType = loadKV(loadFromFile, path / "modelDType", datatype="str")
        self.nContrib = self.parameterSet.shape[0]

    def store(self, filename: Path, repetition: int) -> None:
        if repetition is None:
            raise ValueError("Repetition number must be given when storing model parameters into a paramFile")
        if filename is None:
            raise ValueError("filename cannot be empty")

        path = self.resultIndex.nxsEntryPoint / "model"
        storeKVPairs(filename, path / "fitParameterLimits", self.fitParameterLimits.items())
        storeKVPairs(filename, path / "staticParameters", self.staticParameters.items())
        storeKV(filename, path=path / "modelName", value=str(self.modelName))  # store modelName

        psDict = self.parameterSet.copy().to_dict(orient="split")
        storeKVPairs(filename, path / f"repetition{repetition}" / "parameterSet", psDict.items())
        storeKVPairs(
            filename,
            path / f"repetition{repetition}",
            [("seed", self.seed), ("volumes", self.volumes), ("modelDType", self.modelDType)],
        )

    def available_models(self) -> dict[str, list[str]]:
        """Return available SasModels grouped by dimensionality support."""
        available = {"one_dimensional": [], "one_and_two_dimensional": []}
        for model in sasmodels.core.list_models():
            model_info = sasmodels.core.load_model_info(model)
            if model_info.parameters.has_2d:
                available["one_and_two_dimensional"].append(model_info.id)
            else:
                available["one_dimensional"].append(model_info.id)
        return available

    def _load_sasmodels_model(self) -> None:
        self.func = sasmodels.core.load_model(self.modelName, dtype=self.modelDType)
        self._sasmodels_length_parameters = sasmodels_length_parameter_ids(self.func.info)

    def _load_mcsas_sphere_model(self) -> None:
        self.func = mcsasSphereModel(**self.staticParameters)

    def _load_sim_model(self) -> None:
        static_parameters = dict(self.staticParameters)
        static_parameters.setdefault("simDataQ1", None)
        model_parameters = {
            key: static_parameters[key] for key in McSimPseudoModel.settables if key in static_parameters
        }
        self.func = McSimPseudoModel(**model_parameters)
        static_parameters["extrapY0"] = self.func.extrapY0
        static_parameters["extrapScaling"] = self.func.extrapScaling
        self.staticParameters = static_parameters

    def model_parameters(self) -> dict:
        """Return the default parameter set for the currently loaded model."""
        if self.func is None:
            raise RuntimeError("Model must be loaded before model parameters can be queried.")
        return self.func.info.parameters.defaults
