import pandas
import numpy as np
from .McHDF import McHDF
from .mcmodel import McModel
from .mccore import McCore
from .mcopt import McOpt
from .mcmodelhistogrammer import McModelHistogrammer
import os.path
import h5py
import matplotlib.pyplot as plt

class mcPlot(McHDF):
    """ 
    A class to help in plotting of input- and output data used in the MC optimization. 
    This is generally run after an analysis has occurred, but also has methods for 
    plotting the input dataset(s). 
    This is not a main component of the McSAS3 library, and is only provided for convenience.
    It is very much a work in progress and its structure or methods may vary in subsequent
    releases.
    """
    _analysis = None # instance of McAnalysis
    _inputData = None # instance of McData 
    _figureHandle = None # handle to figure
    _axesHandles = None # subplots-style array of axes handles.

    def __init__(self, **kwargs):
        pass

    def getHistReport(self, histIndex = 0):
        # helper function that gets the histogram statistics report preformatted from the 
        # analysis run. Can also do some post-processing here but that should be avoided.

        # get report, some string replacements to prevent errors of "missing Glyph (9), which is the tab"
        #.replace('      ', ' ').replace(' 	 ', ' ').replace('----------------','')
        return self._analysis.debugReport(histIndex).split('\n', 1)[1] # first line discarded

    def getRunReport(self):
        # helper function that gets the run statistics report preformatted from the 
        # analysis run. Can also do some post-processing here but that should be avoided.

        return self._analysis.debugRunReport().split('\n', 1)[1] # first line is discarded

    def resultCard(self, saveFilePath=None):
        """
        Produces a standard "result card" as in the original McSAS, with the data and fit
        on the left-hand side, and the resulting histograms in the subsequent plots. 
        Information on the optimization is shown above the data, and information on the
        population statistics are shown over their respective histograms.
        If I can get it working, I should show the partial intensities too for each
        histogram range. 
        """
        # code dump from Jupyter: 
        fhs, ahs = plt.subplots(nrows = 2, ncols = 2, figsize = [12, 5], gridspec_kw={'width_ratios':[1,1], 'height_ratios':[1,2]})
        histDataFrame = mcres._averagedHistograms[0]
        csfont = {'fontname':'Courier New'}

        # histogram:
        plt.sca(ahs[1, 1])
        plt.bar(
            histDataFrame['xMean'], 
            histDataFrame['yMean'], 
            align = 'center', 
            width = histDataFrame['xWidth'],
            yerr = histDataFrame['yStd'],
            )
        plt.xscale('linear')
        plt.xlabel('Size factor from STL')
        plt.xlim(20, 40)
        plt.ylabel('Volume fraction (arb. units)')

        # get report, some string replacements to prevent errors of "missing Glyph (9), which is the tab"
        histReport = self.getHistReport(histIndex = 0)
        plt.sca(ahs[0, 1]) # top right
        ahs[0,1].set_aspect(1)
        ahs[0,1].axis('off')
        ahs[0,1].text(.2, 0, histReport, **csfont, 
            rotation=0,
            horizontalalignment='center',
            verticalalignment='bottom',
            multialignment='left',
            transform=ahs[0,1].transAxes,
            bbox=dict(facecolor='white', alpha=0)
        )

        # plot data and fit:
        plt.sca(ahs[1, 0])
        mds.rawData.plot('Q', 'I', yerr= 'ISigma', ax = ahs[1,0], label = 'As provided data', zorder = 1)
        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel('Q (1/nm)')
        plt.ylabel('I (1/cm)')
        plt.xlim(1e-2, 1.5)
        plt.plot(mcres._measData['Q'][0], mcres.modelIAvg.modelIMean.values, zorder = 2, label = 'McSAS3 result from sim. data')
        plt.legend()

        # plot fitting statistics:
        runReport = self.getRunReport()
        plt.sca(ahs[0, 0])
        ahs[0,0].set_aspect(1)
        ahs[0,0].axis('off')
        ahs[0,0].text(.2, 0, runReport, **csfont, 
            rotation=0,
            horizontalalignment='center',
            verticalalignment='bottom',
            multialignment='left',
            transform=ahs[0,0].transAxes,
            bbox=dict(facecolor='white', alpha=0)
        )
        plt.tight_layout()

        if saveFilePath is not None:
            assert isinstance(saveFilePath, Path), 'save filename must be a Path instance'
            plt.savefig(saveFilePath)