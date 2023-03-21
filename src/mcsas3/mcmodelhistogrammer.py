from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas

import mcsas3.McHDF as McHDF

from .mccore import McCore
from .mcmodel import McModel
from .mcopt import McOpt


class McModelHistogrammer:
    """
    This class takes care of the analysis of an optimized model instance parameters.
    That means it histograms the result based on the histogram range settings, and
    calculates the five population modes. These are not weighted by the scaling factor,
    and exist therefore in non-absolute units. Contribution weighting is assumed to be 0.5,
    i.e. volume-weighted.

    McModelHistogrammer is calculated for every repetition individually.

    Besides this class, there will be an McAnalysis class that combines the results from
    McModelHistogrammer (and calculates the resulting mean and standard deviations),
    its optimization-instance parameters, and calculates the observability limits.

    McModelHistogrammer is expected to be called from other routines, and so only minimal
    input-checking is done.

    histRanges argument should contain the following keys:
        - parameter: name of the parameter to histogram - must be a fitparameter (is checked)
        - autoRange: Boolean which will use fitparameterlimits to define histogram width,
                     overrides presetRange
        - presetRangeMin: a min value that defines the histogram lower limit
        - presetRangeMax: a max value that defines the histogram upper limit
        - nBins: the number of bins to divide into
        - binScale: "linear" or "log"
        - binWeighting: "vol" implemented only. Future options: "num", "volsqr", "surf"

    The histogrammer and McAnalysis classes can be run independent from the optimization
    procedure, to allow re-histogramming using different settings without needing re-
    optimisation (like our original McSAS did).
    """

    _model = None  # instance of model to work with
    _opt = None  # instance of optimization parameters
    _histRanges = (
        pandas.DataFrame()
    )  # pandas dataframe with one row per range, and the parameters as developed in McSAS
    _binEdges = (
        dict()
    )  # dict of binEdge arrays: _binEdges[0] matches parameters in _histRanges.loc[0].
    _histDict = (
        dict()
    )  # histograms, one per range, i.e. _hist[0] matches parameters in _histRanges.loc[0]
    _modes = pandas.DataFrame(
        columns=["totalValue", "mean", "variance", "skew", "kurtosis"]
    )  # modes of the populations: total, mean, variance, skew, kurtosis
    _correctionFactor = 1e-5  # scaling factor to switch from SasModel units used in the model
    # instance (1/(cm sr) for dimensions in Angstrom) to absolute units
    # in 1/(m sr) for dimensions in nm

    def __init__(
        self, coreInstance: McCore, histRanges: pandas.DataFrame, resultIndex: int = 1
    ) -> None:
        # reset variables, make sure we don't inherit anything from another instance:
        self._model = None  # instance of model to work with
        self._histRanges = (
            pandas.DataFrame()
        )  # pandas dataframe with one row per range, and the parameters as developed in McSAS
        self._binEdges = (
            dict()
        )  # dict of binEdge arrays: _binEdges[0] matches parameters in _histRanges.loc[0].
        self._histDict = (
            dict()
        )  # histograms, one per range, i.e. _hist[0] matches parameters in _histRanges.loc[0]
        self._modes = pandas.DataFrame(
            columns=["totalValue", "mean", "variance", "skew", "kurtosis"]
        )  # modes of the populations: total, mean, variance, skew, kurtosis

        self.resultIndex = McHDF.ResultIndex(resultIndex)  # defines the HDF5 root path

        assert isinstance(
            coreInstance, McCore
        ), "A core instance (containing model + opt) must be provided!"
        assert isinstance(
            histRanges, pandas.DataFrame
        ), "A pandas dataframe with histogram ranges must be provided"
        assert isinstance(coreInstance._model, McModel), "the core does not have a valid model set"
        assert isinstance(
            coreInstance._opt, McOpt
        ), "the core does not have a valid optimization instance set"
        self._model = coreInstance._model
        self._opt = coreInstance._opt  # we need this for the scaling factor.
        self._histRanges = histRanges

        for histIndex, histRange in histRanges.iterrows():
            # does the model have that parameter?
            assert (
                histRange.parameter in self._model.parameterSet.keys()
            ), "histogram parameter must be present in model fitparameters"
            assert histRange.binScale in [
                "linear",
                "log",
                "auto",
            ], "binning scale must be either 'linear' or 'log'"  # , or 'auto' (Doana)"
            assert (
                histRange.binWeighting == "vol"
            ), "only volume-weighted binning implemented for now"
            assert isinstance(histRange.autoRange, bool), "autoRange must be a boolean"
            assert isinstance(histRange.nBin, int) and (
                histRange.nBin > 0
            ), "nBin must be an integer > 0"

            if histRange.autoRange:
                histRange["rangeMin"] = self._model.fitParameterLimits[histRange.parameter][0]
                histRange["rangeMax"] = self._model.fitParameterLimits[histRange.parameter][1]
            else:
                histRange["rangeMin"] = histRange.presetRangeMin
                histRange["rangeMax"] = histRange.presetRangeMax
            self._histRanges.loc[histIndex, "rangeMin"] = histRange["rangeMin"]
            self._histRanges.loc[histIndex, "rangeMax"] = histRange["rangeMax"]

            self._binEdges[histIndex] = self.genX(
                histRange, self._model.parameterSet, self._model.volumes
            )
            self.histogram(histRange, histIndex)
            self.modes(histRange, histIndex)

    def debugPlot(self, histIndex: int) -> None:
        """Plots a single histogram, for debugging purposes only,
        can only be done after histogramming is complete."""
        plt.bar(
            self._binEdges[histIndex][:-1],
            self._histDict[histIndex],
            align="edge",
            width=np.diff(self._binEdges[histIndex]),
        )
        if self._histRanges.loc[histIndex].binScale == "log":
            plt.xscale("log")

    def histogram(self, histRange: pandas.DataFrame, histIndex: int) -> None:
        """histograms the data into an individual range"""

        n, _ = np.histogram(
            self._model.parameterSet[histRange.parameter],
            bins=self._binEdges[histIndex],
            density=False,
            # already volume-weighted. If done so again, we get a vol-sqr-weighted plot
            # with the larger sizes overemphasized
            # weights = self._model.volumes # correctness needs to be checked !!!
        )
        # correct for SasView units - McSAS Units difference (correctionFactor),
        # and scale to absolute units by multiplying with the overall curve scaling factor..
        self._histDict[histIndex] = n.astype(np.float64) * self._opt.x0[0] * self._correctionFactor

    def modes(self, histRange: pandas.DataFrame, histIndex: int) -> None:
        def calcModes(rset, frac):
            # function taken from the old McSAS code:
            val = sum(frac)
            if val == 0:
                return val, np.nan, np.nan, np.nan, np.nan
            else:
                mu = sum(rset * frac) / sum(frac)
                var = sum((rset - mu) ** 2 * frac) / sum(frac)
                sigma = np.sqrt(abs(var))
                skw = sum((rset - mu) ** 3 * frac) / (sum(frac) * sigma**3)
                krt = sum((rset - mu) ** 4 * frac) / (sum(frac) * sigma**4)
                return val, mu, var, skw, krt

        # clip the data to the min/max specified in the range:
        workData = self._model.parameterSet[histRange.parameter]
        workVolumes = self._model.volumes
        clippedDataValues = workData[
            workData.between(histRange.rangeMin, histRange.rangeMax)
        ].values
        clippedDataVolumes = workVolumes[workData.between(histRange.rangeMin, histRange.rangeMax)]

        if clippedDataVolumes.size == 0:
            val, mu, var, skw, krt = np.nan, np.nan, np.nan, np.nan, np.nan
        else:
            # needs a rethink...
            val, mu, var, skw, krt = calcModes(
                clippedDataValues, np.ones(clippedDataVolumes.shape)
            )  # /workVolumes.sum()
        self._modes.loc[histIndex] = pandas.Series(
            {
                "totalValue": val * self._correctionFactor * self._opt.x0[0],
                "mean": mu,
                "variance": var,
                "skew": skw,
                "kurtosis": krt,
            }
        )

    def genX(
        self, histRange: pandas.DataFrame, parameterSet: pandas.DataFrame, volumes: np.ndarray
    ) -> np.ndarray:
        """Generates bin edges"""
        if histRange.binScale == "linear":
            binEdges = np.linspace(histRange.rangeMin, histRange.rangeMax, histRange.nBin + 1)
        elif histRange.binScale == "log":
            binEdges = np.logspace(
                np.log10(histRange.rangeMin),
                np.log10(histRange.rangeMax),
                histRange.nBin + 1,
            )
        elif histRange.binScale == "auto":
            assert isinstance(
                parameterSet, pandas.DataFrame
            ), "a parameterSet must be provided for automatic bin determination"
            binEdges = np.histogram_bin_edges(
                parameterSet[histRange.parameter],
                bins="auto",
                range=[histRange.rangeMin, histRange.rangeMax],
                # weights = volumes , # can't be used by "auto" yet,
                # but may be in the future according to the docs...
            )
        return binEdges

    def store(self, filename: Path, repetition: int) -> None:
        # TODO: CHECK USE OF KEYS IN STORE PATH:
        assert (
            repetition is not None
        ), "Repetition number must be given when storing histograms into a paramFile"

        path = self.resultIndex.nxsEntryPoint / "histograms"
        # store histogram ranges and settings, for archival purposes only,
        # these settings are not planned to be reused.:
        oDict = self._histRanges.copy().to_dict(orient="index")
        for key in oDict.keys():
            # print("histRanges: storing key: {}, value: {}".format(key, oDict[key]))
            pairs = [(dKey, dValue) for dKey, dValue in oDict[key].items()]
            # TODO: keys might be wrong here:
            McHDF.storeKVPairs(filename, path / f"histRange{key}", pairs)

        # store modes, for archival purposes only, these settings are not planned to be reused:
        oDict = self._modes.copy().to_dict(orient="index")
        for key in oDict.keys():
            # print("modes: storing key: {}, value: {}".format(key, oDict[key]))
            pairs = [(dKey, dValue) for dKey, dValue in oDict[key].items()]
            # TODO: keys might be wrong here:
            McHDF.storeKVPairs(
                filename, path / f"histRange{key}" / f"repetition{repetition}", pairs
            )

        for histIndex, histRange in self._histRanges.iterrows():
            McHDF.storeKVPairs(
                filename,
                path / f"histRange{histIndex}" / f"repetition{repetition}",
                (("binEdges", self._binEdges[histIndex]), ("hist", self._histDict[histIndex])),
            )
