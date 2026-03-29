import numpy as np
import scipy
import scipy.optimize

from .data_adapters import as_analysis_bundle, fit_arrays_from_bundle
from .optimizer_input import as_optimizer_input


class optimizeScalingAndBackground(object):
    """small class derived from the McSAS mcsas/backgroundscalingfit.py class,
    quickly provides an optimized scaling and background value for two datasets.

    **TODO (maybe)**: include a porod background contribution? If so, Q should be
    available to this class.

    Parameters
    ----------
    measDataI:
        numpy array of measured intensities
    measDataISigma:
        associated uncertainties
    modelDataI:
        array of model intensities.
    x0:
        optional, two-element tuple with initial guess for scaling and background
    xBounds:
        optional, constraints to the optimization,
        speeds up when appropriate constraints are given

    Returns
    -------
    x:
        length 2 ndarray with optimized scaling parameter and background parameter
    cs:
        final reduced chi-squared


    Usage example:

        o = optimizeScalingAndBackground(measDataI, measDataISigma)
        xOpt, rcs = o.match(modelDataI)
    """

    measDataI = None
    measDataISigma = None
    xBounds = None

    def __init__(self, measDataI=None, measDataISigma=None, xBounds=None):
        if measDataISigma is None and not isinstance(measDataI, (np.ndarray, list, tuple)):
            try:
                analysis_bundle = as_analysis_bundle(measDataI)
            except TypeError:
                optimizer_input = as_optimizer_input(measDataI)
                measDataI = optimizer_input.i
                measDataISigma = optimizer_input.isigma
            else:
                _q_arrays, measDataI, measDataISigma = fit_arrays_from_bundle(analysis_bundle)
        self.measDataI = measDataI
        self.measDataISigma = measDataISigma
        self.validate()
        if xBounds is None:
            self.xBounds = [
                [0, None],
                [
                    -self.measDataI[np.isfinite(self.measDataI)].mean(),
                    self.measDataI[np.isfinite(self.measDataI)].mean(),
                ],
            ]
            # [self.measDataI[np.isfinite(self.measDataI)].min(),
            # self.measDataI[np.isfinite(self.measDataI)].max()]]

    def initialGuess(self, optI):
        # new guess:
        sc = np.median(self.measDataI / optI)
        bgnd = self.measDataI[-int(np.floor(4 * len(self.measDataI) / 5)) :].mean()

        # bgnd = self.measDataI[np.isfinite(self.measDataI)].min()
        # sc = ((self.measDataI - bgnd) / optI).mean()
        if sc <= 0:
            sc = 1.0  # auto-determination failed, but we need to stay within bounds
        # x0 = np.array([self.measDataI.mean() / optI.mean(), self.measDataI.min()])
        # sc = ((self.measDataI) / optI).mean()
        bgnd = np.clip(bgnd, self.xBounds[1][0], self.xBounds[1][1])
        return np.array([sc, bgnd])

    def validate(self):
        # checks input
        if np.any(np.isnan(self.measDataI)):
            raise ValueError("Measured intensities cannot contain NaN values.")
        if np.any(np.isinf(self.measDataI)):
            raise ValueError("Measured intensities cannot contain infinite values.")
        if np.any(np.isnan(self.measDataISigma)):
            raise ValueError("Intensity uncertainties cannot contain NaN values.")
        if np.any(np.isinf(self.measDataISigma)):
            raise ValueError("Intensity uncertainties cannot contain infinite values.")
        if not np.any(np.isfinite(self.measDataISigma)):
            raise ValueError("At least one finite intensity uncertainty is required.")
        if self.measDataI.size == 0:
            raise ValueError("Measured intensities cannot be empty.")
        if self.measDataI.shape != self.measDataISigma.shape:
            raise ValueError("Measured intensities and uncertainties must have matching shapes.")
        if self.measDataI.ndim != 1:
            raise ValueError("Measured intensities must be one-dimensional.")

    @staticmethod
    def optFunc(sc, measDataI, measDataISigma, modelDataI):
        # reduced chi-square; normalized by uncertainty.
        cs = sum(((measDataI - (modelDataI * sc[0] + sc[1])) / measDataISigma) ** 2) / measDataI.size
        return cs

    def match(self, modelDataI, x0=None):
        if x0 is None:  # optional argument with starting guess..
            # some initial guess
            x0 = self.initialGuess(modelDataI)
        # adapt bounds to modelData:
        # self._xBounds[0][1] /= modelDataI.mean()
        opt = scipy.optimize.minimize(
            self.optFunc,
            x0,
            args=(self.measDataI, self.measDataISigma, modelDataI),
            method="TNC",
            bounds=self.xBounds,
        )
        return opt["x"], opt["fun"]
