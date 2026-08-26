from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas

from mcsas3.mc_hdf import ResultIndex, storeKVPairs

from .mc_core import McCore
from .mc_model import McModel
from .mc_opt import McOpt
from .parameter_units import LEGACY_CUSTOM_MODEL_SCALE_TO_VOLUME_FRACTION
from .plot_labels import fit_parameter_axis_label

MODE_COLUMNS = ("totalValue", "mean", "variance", "skew", "kurtosis")


def _empty_modes_frame() -> pandas.DataFrame:
    return pandas.DataFrame(columns=MODE_COLUMNS)


class McModelHistogrammer:
    """
    Histogram and summarize a single optimized model repetition.

    The histograms are scaled to absolute volume fractions using the repetition scaling
    factor and the model-specific scale-to-volume-fraction correction factor.
    """

    _correctionFactor = LEGACY_CUSTOM_MODEL_SCALE_TO_VOLUME_FRACTION

    def __init__(self, coreInstance: McCore, histRanges: pandas.DataFrame, resultIndex: int = 1) -> None:
        self._model: McModel | None = None
        self._opt: McOpt | None = None
        self._histRanges = pandas.DataFrame()
        self._binEdges: dict[int, np.ndarray] = {}
        self._histDict: dict[int, np.ndarray] = {}
        self._modes = _empty_modes_frame()

        self.resultIndex = ResultIndex(resultIndex)

        self._validate_inputs(coreInstance, histRanges)
        self._model = coreInstance._model
        self._opt = coreInstance._opt
        self._histRanges = histRanges.copy(deep=True)

        for histIndex in self._histRanges.index:
            histRange = self._resolved_hist_range(histIndex)
            self._binEdges[histIndex] = self.genX(histRange, self._model.parameterSet)
            self.histogram(histRange, histIndex)
            self.modes(histRange, histIndex)

    def _validate_inputs(self, coreInstance: McCore, histRanges: pandas.DataFrame) -> None:
        if not isinstance(coreInstance, McCore):
            raise TypeError("A core instance (containing model + opt) must be provided.")
        if not isinstance(histRanges, pandas.DataFrame):
            raise TypeError("A pandas dataframe with histogram ranges must be provided.")
        if not isinstance(coreInstance._model, McModel):
            raise TypeError("The provided McCore instance does not have a valid model set.")
        if not isinstance(coreInstance._opt, McOpt):
            raise TypeError("The provided McCore instance does not have a valid optimization instance set.")

    def _resolved_hist_range(self, histIndex: int) -> pandas.Series:
        histRange = self._histRanges.loc[histIndex].copy()
        if histRange.parameter not in self._model.parameterSet.keys():
            raise ValueError("Histogram parameter must be present in model fit parameters.")
        if histRange.binScale not in ["linear", "log", "auto"]:
            raise ValueError("Binning scale must be one of 'linear', 'log', or 'auto'.")
        if histRange.binWeighting != "vol":
            raise ValueError("Only volume-weighted histogramming is implemented.")
        if not isinstance(histRange.autoRange, (bool, np.bool_)):
            raise TypeError("autoRange must be a boolean.")
        if not isinstance(histRange.nBin, (int, np.integer)) or histRange.nBin <= 0:
            raise ValueError("nBin must be an integer > 0.")

        if histRange.autoRange:
            range_min, range_max = self._model.fitParameterLimits[histRange.parameter]
        else:
            range_min, range_max = histRange.presetRangeMin, histRange.presetRangeMax

        self._histRanges.loc[histIndex, "rangeMin"] = range_min
        self._histRanges.loc[histIndex, "rangeMax"] = range_max
        histRange["rangeMin"] = range_min
        histRange["rangeMax"] = range_max
        return histRange

    @staticmethod
    def _calc_modes(values: np.ndarray, weights: np.ndarray) -> tuple[float, float, float, float, float]:
        total = np.sum(weights)
        if total == 0:
            return total, np.nan, np.nan, np.nan, np.nan
        mean = np.sum(values * weights) / total
        variance = np.sum((values - mean) ** 2 * weights) / total
        sigma = np.sqrt(abs(variance))
        skew = np.sum((values - mean) ** 3 * weights) / (total * sigma**3)
        kurtosis = np.sum((values - mean) ** 4 * weights) / (total * sigma**4)
        return total, mean, variance, skew, kurtosis

    def debugPlot(self, histIndex: int) -> None:
        """Plot a single histogram for debugging."""
        plt.bar(
            self._binEdges[histIndex][:-1],
            self._histDict[histIndex],
            align="edge",
            width=np.diff(self._binEdges[histIndex]),
        )
        if self._histRanges.loc[histIndex].binScale == "log":
            plt.xscale("log")
        plt.xlabel(fit_parameter_axis_label(self._histRanges.loc[histIndex].parameter))

    def _volume_fraction_correction_factor(self) -> float:
        return self._model.volume_fraction_correction_factor()

    def histogram(self, histRange: pandas.Series, histIndex: int) -> None:
        """Histogram the data into an individual range."""
        counts, _ = np.histogram(
            self._model.parameterSet[histRange.parameter],
            bins=self._binEdges[histIndex],
            density=False,
        )
        self._histDict[histIndex] = (
            counts.astype(np.float64) * self._opt.x0[0] * self._volume_fraction_correction_factor()
        )

    def modes(self, histRange: pandas.Series, histIndex: int) -> None:
        parameter_values = self._model.parameterSet[histRange.parameter]
        in_range = parameter_values.between(histRange.rangeMin, histRange.rangeMax)
        clipped_values = parameter_values[in_range].values
        clipped_volumes = self._model.volumes[in_range]

        if clipped_volumes.size == 0:
            total, mean, variance, skew, kurtosis = np.nan, np.nan, np.nan, np.nan, np.nan
        else:
            total, mean, variance, skew, kurtosis = self._calc_modes(
                clipped_values,
                np.ones(clipped_volumes.shape),
            )
        self._modes.loc[histIndex] = pandas.Series(
            {
                "totalValue": total * self._volume_fraction_correction_factor() * self._opt.x0[0],
                "mean": mean,
                "variance": variance,
                "skew": skew,
                "kurtosis": kurtosis,
            }
        )

    def genX(self, histRange: pandas.Series, parameterSet: pandas.DataFrame) -> np.ndarray:
        """Generate histogram bin edges."""
        if histRange.binScale == "linear":
            return np.linspace(histRange.rangeMin, histRange.rangeMax, histRange.nBin + 1)
        if histRange.binScale == "log":
            return np.logspace(
                np.log10(histRange.rangeMin),
                np.log10(histRange.rangeMax),
                histRange.nBin + 1,
            )
        if not isinstance(parameterSet, pandas.DataFrame):
            raise TypeError("A parameterSet must be provided for automatic bin determination.")
        return np.histogram_bin_edges(
            parameterSet[histRange.parameter],
            bins="auto",
            range=[histRange.rangeMin, histRange.rangeMax],
        )

    def store(self, filename: Path, repetition: int) -> None:
        if repetition is None:
            raise ValueError("Repetition number must be given when storing histograms into a paramFile")

        path = self.resultIndex.nxsEntryPoint / "histograms"
        hist_range_dict = self._histRanges.copy().to_dict(orient="index")
        for key, values in hist_range_dict.items():
            pairs = list(values.items())
            storeKVPairs(filename, path / f"histRange{key}", pairs)

        mode_dict = self._modes.copy().to_dict(orient="index")
        for key, values in mode_dict.items():
            pairs = list(values.items())
            storeKVPairs(filename, path / f"histRange{key}" / f"repetition{repetition}", pairs)

        for histIndex in self._histRanges.index:
            storeKVPairs(
                filename,
                path / f"histRange{histIndex}" / f"repetition{repetition}",
                (("binEdges", self._binEdges[histIndex]), ("hist", self._histDict[histIndex])),
            )
