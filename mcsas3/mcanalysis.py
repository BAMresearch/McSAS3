import pandas
import numpy as np
from .McHDF import McHDF
from .mcmodel import McModel
from .mcopt import McOpt
from .mcmodelhistogrammer import McModelHistogrammer
import os.path
import h5py

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
    _concatModes = None # not sure how to combine yet. 
    _concatHistograms = None # ibid. 
    _averagedModes = pandas.DataFrame(columns = [
        'totalValue', 'mean', 'variance', 'skew', 'kurtosis',
        'totalValueStd', 'meanStd', 'varianceStd', 'skewStd', 'kurtosisStd']) # like McSAS output
    _averagedModelData = pandas.DataFrame()
    _repetitionList = [] # list of values after "repetition", just in case an optimization didn't make it
    _resultNumber = 1 # in case there are multiple McSAS optimization series stored in a single file... not sure if this will be used


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
        self._opt = McOpt(loadFromFile = inputFile)
        self._histRanges = histRanges
        self.getNRep(inputFile)

        for repi, repetition in enumerate(self._repetitionList):
            # for every repetition, load the model
            self._model = McModel(loadFromFile = inputFile, loadFromRepetition = repetition)
            mh = McModelHistogrammer(self._model, self._histRanges)
            if store:
                mh.store(inputFile, repetition)

    def getNRep(self, inputFile):
        self._repetitionList = [] # reinitialize to zero
        with h5py.File(inputFile) as h5f:
            for key in h5f['/entry1/MCResult{}/model/'.format(self._resultNumber)].keys():
                if 'repetition' in key:
                    self._repetitionList.append(key.strip('repetition'))
        print('{} repetitions found in McSAS file {}'.format(len(self._repetitionList), inputFile))            

