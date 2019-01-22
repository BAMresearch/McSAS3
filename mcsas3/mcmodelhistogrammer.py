import numpy as np
import pandas
from .mcmodel import McModel
import matplotlib.pyplot as plt
from .McHDF import McHDF

class McModelHistogrammer(McHDF):
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
        - autoRange: Boolean which will use fitparameterlimits to define histogram width, overrides presetRange
        - presetRangeMin: a min value that defines the histogram lower limit
        - presetRangeMax: a max value that defines the histogram upper limit
        - nBins: the number of bins to divide into
        - binScale: "linear" or "log"
        - binWeighting: "vol" implemented only. Future options: "num", "volsqr", "surf" 

    The histogrammer and McAnalysis classes can be run independent from the optimization 
    procedure, to allow re-histogramming using different settings without needing re-
    optimisation (like our original McSAS did). 
    """

    _model = None # instance of model to work with
    _histRanges = pandas.DataFrame() # pandas dataframe with one row per range, and the parameters as developed in McSAS
    _binEdges = dict() # dict of binEdge arrays: _binEdges[0] matches parameters in _histRanges.loc[0]. 
    _histList = dict() # histograms, one per range, i.e. _hist[0] matches parameters in _histRanges.loc[0]
    _modes = pandas.DataFrame(columns = ['totalValue', 'mean', 'variance', 'skew', 'kurtosis']) # modes of the populations: total, mean, variance, skew, kurtosis

    def __init__(self, modelInstance = None, histRanges = None):
        assert isinstance(modelInstance, McModel), "A model instance must be provided!"
        assert isinstance(histRanges, pandas.DataFrame), "A pandas dataframe with histogram ranges must be provided"

        self._model = modelInstance
        self._histRanges = histRanges 

        for histIndex, histRange in histRanges.iterrows():
            # does the model have that parameter?
            assert histRange.parameter in self._model.parameterSet.keys(), "histogram parameter must be present in model fitparameters"
            assert histRange.binScale in ['linear', 'log', 'auto'], "binning scale must be either 'linear', 'log', or 'auto' (Doana)"
            assert histRange.binWeighting is 'vol', "only volume-weighted binning implemented for now"
            assert isinstance(histRange.autoRange, bool), "autoRange must be a boolean"

            if histRange.autoRange:
                histRange['rangeMin'] = self._model.fitParameterLimits[histRange.parameter][0]
                histRange['rangeMax'] = self._model.fitParameterLimits[histRange.parameter][1]
            else:
                histRange['rangeMin'] = histRange.presetRangeMin
                histRange['rangeMax'] = histRange.presetRangeMax

            self._binEdges[histIndex] = self.genX(histRange, self._model.parameterSet, self._model.volumes)
            self.histogram(histRange, histIndex)
            self.modes(histRange, histIndex)

    def debugPlot(self, histIndex):
        """ plots a single histogram, for debugging purposes only, can only be done after histogramming is complete"""
        plt.bar(self._binEdges[histIndex][:-1], 
            self._histList[histIndex], 
            align = 'edge', 
            width = np.diff(self._binEdges[histIndex]))
        if self._histRanges.loc[histIndex].binScale is 'log':
            plt.xscale('log')

    def histogram(self, histRange, histIndex):
        """ histograms the data into an individual range """
        
        self._histList[histIndex], _ = np.histogram(
            self._model.parameterSet[histRange.parameter], 
            bins = self._binEdges[histIndex], 
            density = True, 
            weights = self._model.volumes # correctness needs to be checked !!!
        )

    def modes(self, histRange, histIndex):
        def calcModes(rset, frac):
        	# function taken from the old McSAS code:
            val = sum(frac)
            mu  = sum(rset * frac)
            if 0 != sum(frac):
                mu /= sum(frac)
            var = sum( (rset-mu)**2 * frac )/sum(frac)
            sigma   = np.sqrt(abs(var))
            skw = ( sum( (rset-mu)**3 * frac )
                     / (sum(frac) * sigma**3))
            krt = ( sum( (rset-mu)**4 * frac )
                     / (sum(frac) * sigma**4))
            return val, mu, var, skw, krt

        # clip the data to the min/max specified in the range:
        workData = self._model.parameterSet[histRange.parameter]
        workVolumes = self._model.volumes
        clippedDataValues = workData[workData.between(histRange.rangeMin, histRange.rangeMax)].values
        clippedDataVolumes = workVolumes[workData.between(histRange.rangeMin, histRange.rangeMax).values]

        val, mu, var, skw, krt = calcModes(clippedDataValues, clippedDataVolumes)
        self._modes.loc[histIndex] = pandas.Series({
        	'totalValue': val,
        	'mean': mu,
        	'variance': var,
        	'skew': skw,
        	'kurtosis': krt
        	})

    def genX(self, histRange, parameterSet, volumes):
        """Generates bin edges"""
        if histRange.binScale is 'lin':
            binEdges = np.linspace(
            histRange.rangeMin, histRange.rangeMax, histRange.nBin + 1)
        elif histRange.binScale is 'log':
            binEdges = np.logspace(
            np.log10(histRange.rangeMin), np.log10(histRange.rangeMax), histRange.nBin + 1)
        elif histRange.binScale is 'auto':
            assert isinstance(parameterSet, pandas.DataFrame), "a parameterSet must be provided for automatic bin determination"
            binEdges = np.histogram_bin_edges(
                parameterSet[histRange.parameter],
                bins = 'auto',
                range = [histRange.rangeMin, histRange.rangeMax], 
                # weights = volumes , # can't be used by "auto" yet, but may be in the future according to the docs...
            )
        return binEdges

    def store(self, filename = None, repetition = None):
        assert(repetition is not None),"Repetition number must be given when storing histograms into a paramFile"

        # store histogram ranges and settings, for arhcival purposes only, these settings are not planned to be reused.:
        oDict = self._histRanges.copy().to_dict(orient = 'index')
        for key in oDict.keys():
            print("histRanges: storing key: {}, value: {}".format(key, oDict[key]))
            for dKey, dValue in oDict[key].items():
	            self._HDFstoreKV(filename = filename, 
	                path = "/entry1/MCResult1/histograms/repetition{}/histRange{}/".format(repetition, key), 
	                key = dKey, 
	                value = dValue)  

	    # store modes, for arhcival purposes only, these settings are not planned to be reused:
        oDict = self._modes.copy().to_dict(orient = 'index')
        for key in oDict.keys():
            print("modes: storing key: {}, value: {}".format(key, oDict[key]))
            for dKey, dValue in oDict[key].items():
	            self._HDFstoreKV(filename = filename, 
	                path = "/entry1/MCResult1/histograms/repetition{}/histRange{}/".format(repetition, key), 
	                key = dKey, 
	                value = dValue)              

        for histIndex, histRange in self._histRanges.iterrows():
            self._HDFstoreKV(filename = filename, 
                path = "/entry1/MCResult1/histograms/repetition{}/histRange{}/".format(repetition, histIndex), 
                key = "binEdges", 
                value = self._binEdges[histIndex])
            self._HDFstoreKV(filename = filename, 
                path = "/entry1/MCResult1/histograms/repetition{}/histRange{}/".format(repetition, histIndex), 
                key = "hist", 
                value = self._histList[histIndex])
    