import numpy as np
import scipy

class optimizeScalingAndBackground(object):
    """small class derived from the McSAS mcsas/backgroundscalingfit.py class, 
    quickly provides an optimized scaling and background value for two datasets.
    
    TODO (maybe): include a $I \propto Q^{-4}$ background contribution? If so, Q should be
    available to this class.......
    
    inputs:
    *measDataI*: numpy array of measured intensities
    *measDataISigma*: associated uncertainties
    *modelDataI*: array of model intensities. 
    *x0* (optional): two-element tuple with initial guess for scaling and background
    *xBounds* (optional): constraints to the optimization, speeds up when appropriate constraints are given

    Returns:
    :x: length 2 ndarray with optimized scaling parameter and background parameter
    :cs: final reduced chi-squared 
    
    Usage example: 
    >>> o = optimizeScalingAndBackground(measDataI, measDataISigma)
    >>> xOpt, rcs = o.match(modelDataI) 
    """
    measDataI = None
    measDataISigma = None
    xBounds = None
    
    def __init__(self, measDataI = None, measDataISigma = None, xBounds = None):
        self.measDataI = measDataI
        self.measDataISigma = measDataISigma
        self.validate()
        if xBounds is None:
            self.xBounds = [[0, None], 
                            [-self.measDataI.mean(), self.measDataI.mean()]]

    def validate(self):
        # checks input
        assert(not any(np.isnan(self.measDataI)))
        assert(not any(np.isinf(self.measDataI)))
        assert(not any(np.isnan(self.measDataISigma)))
        assert(not any(np.isinf(self.measDataISigma)))
        assert(any(np.isfinite(self.measDataISigma)))
        assert(any(np.isfinite(self.measDataISigma)))
        assert(self.measDataI.size != 0)
        assert(self.measDataI.shape == self.measDataISigma.shape)
        assert(self.measDataI.ndim == 1)
        
    @staticmethod
    def optFunc(sc, measDataI, measDataISigma, modelDataI):
        # reduced chi-square; normalized by uncertainty. 
        cs = sum((
            (measDataI - (modelDataI * sc[0] + sc[1]))/measDataISigma)**2
        ) / measDataI.size
        return cs
    
    def match(self, modelDataI, x0 = None):
        if x0 is None: # optional argument with starting guess..
            # some initial guess
            x0 = np.array([self.measDataI.mean() / modelDataI.mean(), self.measDataI.min()])
        # adapt bounds to modelData:
        # self._xBounds[0][1] /= modelDataI.mean()
        opt = scipy.optimize.minimize(self.optFunc, 
                                x0, 
                                args = (self.measDataI, self.measDataISigma, modelDataI), 
                                # method = "TNC", 
                                bounds = self.xBounds)
        return opt["x"], opt["fun"]
    