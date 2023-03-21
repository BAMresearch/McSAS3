import os.path
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas

import mcsas3.McHDF as McHDF

from .mccore import McCore
from .mcmodelhistogrammer import McModelHistogrammer


class McAnalysis:
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

    # base:
    _core = None  # instance of core through which _model, _measData, _opt should be accessed
    _measData = None  # measurement data dict with entries for Q, I, ISigma,
    # will be replaced by sasview data model

    # specifics for analysis
    _histRanges = (
        pandas.DataFrame()
    )  # pandas dataframe with one row per range, and the parameters as developed in McSAS,
    # this gets passed on to McModelHistogrammer as well
    _concatI = (
        dict()
    )  # for now, just a simple concatenation of the entire set, one row per repetition,
    # not separated to indivudual histogram ranges..
    _concatOpts = (
        pandas.DataFrame()
    )  # dictionary of pandas Dataframes, each dataframe containing a list (with length of nRep)
    # of scaling factors, backgrounds, goodness-of-fit, and eventual other optimization details
    _concatModes = dict()  # dictionary of pandas DataFrames, one per histogram range.
    _concatHistograms = dict()  # ibid.
    _concatBinEdges = dict()  # ibid..
    _averagedModes = None  # will be multi-column-name pandas DataFrame,
    # with one row per histogram range. It's pretty cool.
    _averagedI = None  # averaged model intensity
    # _averagedModelData = pandas.DataFrame()
    _averagedHistograms = dict()  # dict of dataFrames, one per histogram range, each containing
    # pandas.DataFrame(columns = ['xMean','xWidth','yMean','yStd','Obs','cdfMean','cdfStd'])
    _averagedOpts = (
        pandas.DataFrame()
    )  # a dataFrame containing mean and std of optimization parameters.
    # Some will be useful, some will be pointless.
    _repetitionList = (
        []
    )  # list of values after "repetition", just in case an optimization didn't make it
    _modeKeys = ["totalValue", "mean", "variance", "skew", "kurtosis"]
    _optKeys = ["scaling", "background", "gof", "accepted", "step"]

    def __init__(
        self,
        inputFile: Path,
        measData: dict,
        histRanges: pandas.DataFrame,
        store: bool = False,
        resultIndex: int = 1,
    ) -> None:
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

        # reset everything to make sure we're not inheriting anything:
        # base:
        self._core = (
            None  # instance of core through which _model, _measData, _opt should be accessed
        )
        self._measData = None  # measurement data dict with entries for Q, I, ISigma,

        # specifics for analysis
        self._histRanges = (
            pandas.DataFrame()
        )  # pandas dataframe with one row per range, and the parameters as developed in McSAS,
        # this gets passed on to McModelHistogrammer as well
        self._concatI = (
            dict()
        )  # for now, just a simple concatenation of the entire set, one row per repetition,
        # not separated to indivudual histogram ranges..
        self._concatOpts = (
            pandas.DataFrame()
        )  # dictionary of pandas Dataframes, each dataframe containing a list (with length of
        # nRep) of scaling factors, backgrounds, goodness-of-fit,
        # and eventual other optimization details
        self._concatModes = dict()  # dictionary of pandas DataFrames, one per histogram range.
        self._concatHistograms = dict()  # ibid.
        self._concatBinEdges = dict()  # ibid..
        self._averagedModes = None  # will be multi-column-name pandas DataFrame,
        # with one row per histogram range. It's pretty cool.
        self._averagedI = None  # averaged model intensity
        # _averagedModelData = pandas.DataFrame()
        self._averagedHistograms = (
            dict()
        )  # dict of dataFrames, one per histogram range, each containing
        # pandas.DataFrame(columns = ['xMean','xWidth','yMean','yStd','Obs','cdfMean','cdfStd'])
        self._averagedOpts = (
            pandas.DataFrame()
        )  # a dataFrame containing mean and std of optimization parameters.
        # Some will be useful, some will be pointless.
        self._averagedAcceptedSteps = []  # averaged steps at which the optimization was accepted
        self._averagedAcceptedGofs = (
            []
        )  # not sure how to average these two... not same size, not same location...
        self._repetitionList = (
            []
        )  # list of values after "repetition", just in case an optimization didn't make it
        self._modeKeys = ["totalValue", "mean", "variance", "skew", "kurtosis"]
        self._optKeys = ["scaling", "background", "gof", "accepted", "step"]

        assert os.path.isfile(inputFile), "A valid McSAS3 project filename must be provided. "
        assert isinstance(
            histRanges, pandas.DataFrame
        ), "A pandas dataframe with histogram ranges must be provided"
        assert measData is not None, "measurement data must be provided for analysis"

        self._concatOpts = pandas.DataFrame(columns=self._optKeys)
        self._histRanges = histRanges
        self._measData = measData
        # make sure we store and read from the right place.
        self.resultIndex = McHDF.ResultIndex(resultIndex)  # defines the HDF5 root path

        print("Getting List of repetitions...")
        self.getNRep(inputFile)
        print("Histogramming every repetition and extracting elements to average...")
        self.histAndLoadReps(inputFile, store, resultIndex)
        print("Averaging population modes...")
        self.averageModes()
        print("Averaging histograms...")
        self.averageHistograms()
        print("Averaging optimization parameters...")
        self.averageOpts()
        print("Averaging model intensity...")
        self.averageI()
        if store:
            print("Storing averages...")
            self.store(inputFile)

    @property
    def modelIAvg(self) -> pandas.DataFrame:
        return self._averagedI

    @property
    def optParAvg(self) -> pandas.DataFrame:
        return self._averagedOpts

    def histAndLoadReps(self, inputFile: Path, store: bool, resultIndex: int = 1) -> None:
        """For every repetition, runs its mcModelHistogrammer, and loads the results
        into the local namespace for further processing."""
        # not the best approach, best do this per histogram
        # to avoid losing track of what goes where.
        for repi, repetition in enumerate(self._repetitionList):
            # for every repetition, load a core:
            self._core = McCore(
                measData=self._measData,
                loadFromFile=inputFile,
                loadFromRepetition=repetition,
                resultIndex=resultIndex,
            )

            # for every repetition, load the model
            # self._model = McModel(loadFromFile = inputFile, loadFromRepetition = repetition)
            mh = McModelHistogrammer(
                self._core, self._histRanges, resultIndex=resultIndex
            )  # switched from supplying model instance, to supplying complete core instance.
            if store:
                mh.store(inputFile, repetition)

            # tabulate the necessary optimization parameters:
            # self._opt = McOpt(loadFromFile = inputFile, loadFromRepetition = repetition)
            self._concatOpts.loc[repetition] = pandas.Series(
                data={
                    "scaling": self._core._opt.x0[0],
                    "background": self._core._opt.x0[1],
                    "gof": self._core._opt.gof,
                    "accepted": self._core._opt.accepted,
                    "step": self._core._opt.step,
                }
            )  # this would not be necessary if McOpt was pandas.Series or DataFrame already...
            # Possible avenue for improvement...

            # tabulate the intensity and scale them with x0
            self._concatI[repetition] = (
                self._core._opt.modelI * self._core._opt.x0[0] + self._core._opt.x0[1]
            )

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

    def ensureConcatEssentials(self, histIndex: int) -> None:
        """Small function that makes sure at least an empty DataFrame exists for
        appending the concatenated data to"""
        if histIndex not in self._concatModes:
            self._concatModes[histIndex] = pandas.DataFrame(columns=self._modeKeys)
        if histIndex not in self._concatHistograms:
            self._concatHistograms[histIndex] = dict()
        if histIndex not in self._concatBinEdges:
            self._concatBinEdges[histIndex] = dict()

    def averageI(self) -> None:
        self._averagedI = pandas.DataFrame(
            data={
                "modelIMean": np.array([i for k, i in self._concatI.items()]).mean(axis=0),
                "modelIStd": np.array([i for k, i in self._concatI.items()]).std(axis=0),
            }
        )

    def averageOpts(self) -> None:
        """Combines the multiindex dataframes into a single table with one row
        per histogram range."""
        self._averagedOpts = pandas.DataFrame(
            data={
                "valMean": self._concatOpts.mean(),
                "valStd": self._concatOpts.std(ddof=1),
            }
        )

    def averageModes(self) -> None:
        """Combines the multiindex dataframes into a single table with one row
        per histogram range."""
        dfs = dict()
        for histIndex, histRange in self._histRanges.iterrows():
            dfs[histIndex] = self.averageMode(histIndex)
        self._averagedModes = pandas.DataFrame(data=dfs).T

    def averageMode(self, histIndex: int) -> pandas.DataFrame:
        """Calculates the mean and standard deviation for each mode, for a particular repetition
        index, and returns a multiindex DataFrame."""
        df = pandas.DataFrame(
            data={
                "valMean": self._concatModes[histIndex].mean(),
                "valStd": self._concatModes[histIndex].std(ddof=1),
            }
        )
        return df.stack()

    def averageHistograms(self) -> None:
        """Averages all the histogram ranges sequentially and stores the averaged histograms
        in a dict with {histIndex: histogram DataFrame}."""
        for histIndex, histRange in self._histRanges.iterrows():
            aH = self.averageHistogram(histIndex)
            self._averagedHistograms[histIndex] = aH
            for key in aH.keys():
                self._averagedHistograms[histIndex][key].astype(aH[key].dtype)

    def averageHistogram(self, histIndex: int) -> None:
        """Produces a single averaged histogram for a given histogram range index.
        Returns a DataFrame."""
        # these are the columns and datatypes I want in my histograms.
        # forced datatypes to prevent issues later on when storing
        cols = {
            "xMean": float,
            "xWidth": float,
            "yMean": float,
            "yStd": float,
            "Obs": float,
            "cdfMean": float,
            "cdfStd": float,
        }
        # averagedHistogram = pandas.DataFrame(
        #       columns = ['xMean', 'xWidth', 'yMean', 'yStd', 'Obs', 'cdfMean', 'cdfStd'])
        averagedHistogram = pandas.DataFrame(columns=cols.keys())
        # ensure correct column type so we don't get issues later on when storing the dataFrame
        for key, keyType in cols.items():
            averagedHistogram[key].astype(keyType)

        # histogram bar height:
        hists = np.array(
            [self._concatHistograms[histIndex][repetition] for repetition in self._repetitionList]
        )
        averagedHistogram["yMean"] = hists.mean(axis=0)
        averagedHistogram["yStd"] = hists.std(axis=0, ddof=1 if hists.shape[0] > 1 else 0)

        # histogram bar center and width:
        if len(self._repetitionList) > 1:
            # assuming (!) that the binEdges for all are the same,
            # so no 'auto' bin edge selection possible
            assert all(
                self._concatBinEdges[histIndex][self._repetitionList[0]]
                == self._concatBinEdges[histIndex][self._repetitionList[1]]
            )

        binEdges = self._concatBinEdges[histIndex][
            self._repetitionList[0]
        ]  # these are the left edges
        averagedHistogram["xWidth"] = np.diff(binEdges)
        averagedHistogram["xMean"] = binEdges[:-1] + 0.5 * averagedHistogram["xWidth"]

        return averagedHistogram

    def debugPlot(self, histIndex: int, **kwargs: dict) -> None:
        """Plots a single histogram, for debugging purposes only,
        can only be done after histogramming is complete."""
        histDataFrame = self._averagedHistograms[histIndex]
        plt.bar(
            histDataFrame["xMean"],
            histDataFrame["yMean"],
            align="center",
            width=histDataFrame["xWidth"],
            yerr=histDataFrame["yStd"],
            **kwargs,
        )

        if self._histRanges.loc[histIndex].binScale == "log":
            plt.xscale("log")

    def debugReport(self, histIndex: int) -> str:
        """Preformats the rangeInfo results ready for printing (mostly translated from
        the original McSAS). Should be plotted with a fixed-width font because nothing says
        2020 like misaligned text."""
        statFieldNames = self._modeKeys
        histRange = self._histRanges.loc[histIndex]
        # for histIndex, histRange in self._histRanges.iterrows():
        oString = f"*** Population statistics for Histogram number {histIndex} ***\n"
        oString += (
            f"For {histRange.rangeMin: 0.02e} ≤ {histRange.parameter} ≤"
            f" {histRange.rangeMax: 0.02e}, vol-weighted \n"
        )
        oString += "\n".rjust(48, "-")
        for fieldName in statFieldNames:
            valMean = self._averagedModes[fieldName]["valMean"][histIndex]
            valStd = self._averagedModes[fieldName]["valStd"][histIndex]
            oString += self.debugAddString(fieldName, valMean, valStd)
        return oString

    def debugAddString(
        self, fieldName: str, valMean: float, valStd: float
    ) -> str:  # not sure if val* needs to be float or more generic numeric types
        # does a bit of error checking to avoid division by zero for debug*Report methods
        if valMean != 0:
            oString = (
                f"{fieldName.ljust(10)}: {valMean: 0.02e} ± {valStd: 0.02e} (±"
                f" {valStd/valMean * 100: 0.02f} %) \n"
            )
        else:
            oString = f"{fieldName.ljust(10)}: {valMean: 0.02e} ± {valStd: 0.02e} \n"
        return oString

    def debugRunReport(self) -> str:
        """Preformats the run statistics results ready for printing (mostly translated from
        the original McSAS). Should be plotted with a fixed-width font because nothing
        says 2020 like misaligned text."""
        statFieldNames = self._optKeys
        oString = (
            f"*** Optimization statistics average over {len(self._repetitionList)} repetitions"
            " ***\n"
        )
        oString += (
            f"For {np.min(self._measData['Q']): 0.02e} ≤ Q (1/nm) ≤"
            f" {np.max(self._measData['Q']): 0.02e}\n"
        )
        oString += "\n".rjust(50, "-")
        for fieldName in statFieldNames:
            valMean = self.optParAvg["valMean"][fieldName]
            valStd = self.optParAvg["valStd"][fieldName]
            oString += self.debugAddString(fieldName, valMean, valStd)

        return oString

    def getNRep(self, inputFile: Path) -> None:
        """Finds out which repetition indices are available in the results file,
        skipping potential missing indices. Note: repetition must be int."""
        self._repetitionList = []  # reinitialize to zero
        with h5py.File(inputFile, "r") as h5f:
            for key in h5f[str(self.resultIndex.nxsEntryPoint / "model")].keys():
                if "repetition" in key:
                    self._repetitionList.append(int(key.strip("repetition")))
        print(f"{len(self._repetitionList)} repetitions found in McSAS file {inputFile}")

    def store(self, filename: Path) -> None:
        # store averaged histograms, for arhcival purposes only,
        # these settings are not planned to be reused.:
        path = self.resultIndex.nxsEntryPoint / "histograms"
        oDict = self._averagedHistograms.copy()  # .to_dict(orient="index")
        for key in oDict.keys():
            keypath = path / f"histRange{key}" / "average"
            # print("histRanges: storing key: {}, value: {}".format(key, oDict[key]))
            pairs = [(dKey, dValue.values.astype(float)) for dKey, dValue in oDict[key].items()]
            McHDF.storeKVPairs(filename, keypath, pairs)

        # store modes, for arhcival purposes only, these settings are not planned to be reused:
        oDict = self._averagedModes.copy().to_dict(orient="index")
        # careful, multiindex...
        for key in oDict.keys():  # xs('valMean',axis=1,level=1).keys():
            # print("modes: storing key: {}, value: {}".format(key, oDict[key]))
            keypath = path / f"histRange{key}" / "average"
            for col in ("totalValue", "mean", "variance", "skew", "kurtosis"):
                colpath = keypath / f"{col}"
                pairs = [(subcol, oDict[key][(col, subcol)]) for subcol in ("valMean", "valStd")]
                McHDF.storeKVPairs(filename, colpath, pairs)

        for valName, row in self.optParAvg.iterrows():
            keypath = self.resultIndex.nxsEntryPoint / "optimization" / "average" / f"{valName}"
            pairs = [(key, getattr(row, key)) for key in ("valMean", "valStd")]
            McHDF.storeKVPairs(filename, keypath, pairs)

        pairs = [(dKey, dValue.values) for dKey, dValue in self.modelIAvg.copy().items()]
        McHDF.storeKVPairs(
            filename, self.resultIndex.nxsEntryPoint / "optimization" / "average", pairs
        )
