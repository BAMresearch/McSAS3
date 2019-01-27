import pandas
import numpy as np
from .McHDF import McHDF
from .mcmodel import McModel
from .mcopt import McOpt
from .mcmodelhistogrammer import McModelHistogrammer
import os.path
import h5py
import matplotlib.pyplot as plt


class McAnalysis(McHDF):
    """
    This class is the analyzer / histogramming code for the entire set of repetitions. 
    It can only been run after each individual repetition has been histogrammed using
    the McModelHistogrammer class. 

    McAnalysis uses the individual repetition histograms to calculate the mean and spread 
    of each histogram bin, and the mean and spread of each population mode. It also uses
    the scaling parameters to scale all values to absolute volume fractions. 

    Due to the complexity of setting up, McAnalysis *must* be provided an output HDF5
    file, where all the results and set-up are stored. It then reads the individual
    optimization results and performs its statistical calculations. 
    """
    #base:
    _measData = None    # measurement data dict with entries for Q, I, ISigma, will be replaced by sasview data model
    _OSB = None         # optimizeScalingAndBackground instance for this data
    _model = None       # just a continuously changing variable
    _opt = None         # instance of McOpt

    # specifics for analysis
    _histRanges = pandas.DataFrame() # pandas dataframe with one row per range, and the parameters as developed in McSAS, this gets passed on to McModelHistogrammer as well
    _concatOpts = pandas.DataFrame() # dictionary of pandas Dataframes, each dataframe containing a list (with length of nRep) of scaling factors, backgrounds, goodness-of-fit, and eventual other optimization details
    _concatModes = dict() # not sure how to combine yet. 
    _concatHistograms = dict() # ibid. 
    _concatBinEdges = dict() # ibid..
    _averagedModes = None # will be multi-column-name pandas DataFrame, with one row per histogram range. It's pretty cool.
    _averagedModelData = pandas.DataFrame()
    _averagedHistograms = dict() # dict of dataFrames, one per histogram range, each containing pandas.DataFrame(columns = ['xMean', 'xWidth', 'yMean', 'yStd', 'Obs', 'cdfMean', 'cdfStd'])
    _averagedOpts = pandas.DataFrame() # a dataFrame containing mean and std of optimization parameters. Some will be useful, some will be pointless.
    _repetitionList = [] # list of values after "repetition", just in case an optimization didn't make it
    _resultNumber = 1 # in case there are multiple McSAS optimization series stored in a single file... not sure if this will be used
    _modeKeys = ['totalValue', 'mean', 'variance', 'skew', 'kurtosis']
    _optKeys = ['scaling', 'background', 'gof', 'accepted', 'step']

    def __init__(self, inputFile = None, histRanges = None, store = False):
        # 1. open the input file, and for every repetition:
        # 2. set up the model again, and
        # 3. set up the optimization instance again, and
        # 4. run the McModelHistogrammer, and 
        # 5. put the histogrammer results in the right place, and 
        # 6. concatenate the results in a big table for statistical analysis, and
        # 7. calculate the mean model intensity, and 
        # 8. find the overall scaling parameter for the model intensity, and 
        # 9. scale the volumes with this scaling parameter, and
        # 9. calculate the observability for the bins

        assert os.path.isfile(inputFile), "A valid McSAS3 project filename must be provided. " 
        assert isinstance(histRanges, pandas.DataFrame), "A pandas dataframe with histogram ranges must be provided"

        # ok, we need to start with the full suite:
        self._concatOpts = pandas.DataFrame(columns = self._optKeys)

        self._histRanges = histRanges
        self.getNRep(inputFile)
        self.histAndLoadReps(inputFile, store)
        self.averageModes()
        self.averageHistograms()
        self.averageOpts()

    def histAndLoadReps(self, inputFile, store):
        """ 
        for every repetition, runs its mcModelHistogrammer, and loads the results into the local namespace 
        for further processing
        """
        # not the best approach, best do this per histogram to avoid losing track of what goes where. 
        for repi, repetition in enumerate(self._repetitionList):
            # for every repetition, load the model
            self._model = McModel(loadFromFile = inputFile, loadFromRepetition = repetition)
            mh = McModelHistogrammer(self._model, self._histRanges)
            if store:
                mh.store(inputFile, repetition)

            # tabulate the necessary optimization parameters:
            self._opt = McOpt(loadFromFile = inputFile, loadFromRepetition = repetition)
            self._concatOpts.loc[repetition] = pandas.Series(data = {
                'scaling': self._opt.x0[0], 'background': self._opt.x0[1],
                'gof': self._opt.gof, 'accepted': self._opt.accepted, 'step': self._opt.step
                }) # this would not be necessary if McOpt was pandas.Series or DataFrame already... Possible avenue for improvement...

            """ 
            this is going to need some reindexing: 
            mh contains info on the histogram of one repetition for multiple ranges, but we want
            a dictionary of dicts, one per range, containing all histograms of the repetitions
            """
            for histIndex, _ in self._histRanges.iterrows():   
                # make sure we can append to a dataframe..
                self.ensureConcatEssentials(histIndex)         
                self._concatModes[histIndex].loc[repetition] = mh._modes.loc[histIndex]
                self._concatHistograms[histIndex][repetition] = mh._histDict[histIndex]
                self._concatBinEdges[histIndex][repetition] = mh._binEdges[histIndex]

                # self._concatModes[repetition] = mh._modes # note that modes is a pandas DataFrame with a list of modes, one row per histogram range
                # self._concatHistograms[repetition] = mh._histDict # histList is a dict of hist values, one row per histogram range
                # self._concatBinEdges[repetition] = mh._binEdges # _binEdges is a dict of bin edges, one row per histogram range

    def ensureConcatEssentials(self, histIndex):
        """ small function that makes sure at least an empty dataframe exists for appending the concatenated data to"""
        if not histIndex in self._concatModes:
            self._concatModes[histIndex] = pandas.DataFrame(columns = self._modeKeys)
        if not histIndex in self._concatHistograms:
            self._concatHistograms[histIndex] = dict()
        if not histIndex in self._concatBinEdges:
            self._concatBinEdges[histIndex] = dict()

    def averageOpts(self):
        """ combines the multiindex dataframes into a single table with one row per histogram range """
        self._averagedOpts = pandas.DataFrame(data = {
            "mean": self._concatOpts.mean(), 
            "Std": self._concatOpts.std(ddof = 1)
            })

    def averageModes(self):
        """ combines the multiindex dataframes into a single table with one row per histogram range """
        dfs = dict()
        for histIndex, histRange in self._histRanges.iterrows():
            dfs[histIndex] = self.averageMode(histIndex)
        self._averagedModes = pandas.DataFrame(data = dfs).T

    def averageMode(self, histIndex):
        """ 
        Calculates the mean and standard deviation for each mode, for a particular repetition index, 
        and returns a multiindex DataFrame
        """
        df = pandas.DataFrame(data = {
            "mean": self._concatModes[histIndex].mean(), 
            "Std": self._concatModes[histIndex].std(ddof = 1)
            })
        return df.stack()

    def averageHistograms(self):
        """ 
        averages all the histogram ranges sequentially and stores the averaged histograms in a dict with {histIndex: histogram DataFrame}
        """
        for histIndex, histRange in self._histRanges.iterrows():
            self._averagedHistograms[histIndex] = self.averageHistogram(histIndex)

    def averageHistogram(self, histIndex):
        """ produces a single averaged histogram for a given histogram range index. returns a dataframe """
        averagedHistogram = pandas.DataFrame(columns = ['xMean', 'xWidth', 'yMean', 'yStd', 'Obs', 'cdfMean', 'cdfStd'])

        # histogram bar height:
        hists = [self._concatHistograms[histIndex][repetition] for repetition in self._repetitionList]
        averagedHistogram['yMean'] = np.array(hists).mean(axis = 0)
        averagedHistogram['yStd'] = np.array(hists).std(axis = 0, ddof = 1)

        # histogram bar center and width:
        if len(self._repetitionList) > 1:
            # assuming (!) that the binEdges for all are the same, so no 'auto' bin edge selection possible
            assert all(self._concatBinEdges[histIndex][self._repetitionList[0]] == self._concatBinEdges[histIndex][self._repetitionList[1]]) 

        binEdges = self._concatBinEdges[histIndex][self._repetitionList[0]] # these are the left edges
        averagedHistogram['xWidth'] = np.diff(binEdges)
        averagedHistogram['xMean'] = binEdges[:-1] + 0.5 * averagedHistogram['xWidth']

        return averagedHistogram

    def debugPlot(self, histIndex):
        """ plots a single histogram, for debugging purposes only, can only be done after histogramming is complete"""
        histDataFrame = self._averagedHistograms[histIndex]
        plt.bar(
            histDataFrame['xMean'], 
            histDataFrame['yMean'], 
            align = 'center', 
            width = histDataFrame['xWidth'],
            yerr = histDataFrame['yStd']
            )

        if self._histRanges.loc[histIndex].binScale is 'log':
            plt.xscale('log')

    def getNRep(self, inputFile):
        """ Finds out which repetition indices are available in the results file, skipping potential missing indices 
        note : repetition must be int"""
        self._repetitionList = [] # reinitialize to zero
        with h5py.File(inputFile) as h5f:
            for key in h5f['/entry1/MCResult{}/model/'.format(self._resultNumber)].keys():
                if 'repetition' in key:
                    self._repetitionList.append(int(key.strip('repetition')))
        print('{} repetitions found in McSAS file {}'.format(len(self._repetitionList), inputFile))            

