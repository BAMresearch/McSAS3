# import pandas
# import numpy as np

from pathlib import Path
from typing import Optional

# from .mcmodel import McModel
# from .mccore import McCore
# from .mcopt import McOpt
# from .mcmodelhistogrammer import McModelHistogrammer
# import os.path
# import h5py
import matplotlib.pyplot as plt


class McPlot:
    """
    A class to help in plotting of input- and output data used in the MC optimization.
    This is generally run after an analysis has occurred, but also has methods for
    plotting the input dataset(s).
    This is not a main component of the McSAS3 library, and is only provided for convenience.
    It is very much a work in progress and its structure or methods may vary in subsequent
    releases.
    """

    _analysis = None  # instance of McAnalysis
    _inputData = None  # instance of McData
    _figureHandle = None  # handle to figure
    _axesHandles = None  # subplots-style array of axes handles.

    def __init__(self, **kwargs):
        pass

    def getHistReport(self, histIndex: int = 0) -> str:
        # helper function that gets the histogram statistics report preformatted from the
        # analysis run. Can also do some post-processing here but that should be avoided.

        # get report, some string replacements to prevent errors of:
        # "missing Glyph (9), which is the tab"
        # .replace('      ', ' ').replace(' 	 ', ' ').replace('----------------','')
        return self._analysis.debugReport(histIndex).split("\n", 1)[1]  # first line discarded

    def getRunReport(self) -> str:
        # helper function that gets the run statistics report preformatted from the
        # analysis run. Can also do some post-processing here but that should be avoided.

        return self._analysis.debugRunReport().split("\n", 1)[1]  # first line is discarded

    def resultCard(self, mcres, saveHistFile: Optional[Path] = None) -> None:
        """
        Produces a standard "result card" as in the original McSAS, with the data and fit
        on the left-hand side, and the resulting histograms in the subsequent plots.
        Information on the optimization is shown above the data, and information on the
        population statistics are shown over their respective histograms.
        If I can get it working, I should show the partial intensities too for each
        histogram range.
        """
        nhistos = len(mcres._averagedHistograms.keys())
        fhs, ahs = plt.subplots(
            nrows=2,
            ncols=1 + nhistos,
            figsize=[6 + 6 * nhistos, 5],
            gridspec_kw={"height_ratios": [1, 2]},  # "width_ratios": [1, 1, 1],
        )
        csfont = {"fontname": "Courier New"}

        # histogram:
        for n, key in enumerate(mcres._averagedHistograms.keys()):
            histDataFrame = mcres._averagedHistograms[n]
            plt.sca(ahs[1, 1 + n])
            plt.bar(
                histDataFrame["xMean"],
                histDataFrame["yMean"],
                align="center",
                width=histDataFrame["xWidth"],
                yerr=histDataFrame["yStd"],
            )
            plt.xscale(mcres._histRanges.loc[n, "binScale"])
            plt.xlabel(mcres._histRanges.loc[n, "parameter"])
            # plt.xlim(30* FPFactor, 34* FPFactor)
            plt.ylabel("Vol. frac. \n (relative or absolute)")

            # get report, some string replacements to prevent errors of
            # "missing Glyph (9), which is the tab"
            histReport = mcres.debugReport(n).split("\n", 1)[
                1
            ]  # .replace('      ', ' ').replace(' 	 ', ' ').replace('----------------','')
            plt.sca(ahs[0, 1 + n])  # top right
            ahs[0, 1 + n].set_aspect(1)
            ahs[0, 1 + n].axis("off")
            ahs[0, 1 + n].text(
                0.2,
                0,
                histReport,
                **csfont,
                rotation=0,
                horizontalalignment="center",
                verticalalignment="bottom",
                multialignment="left",
                transform=ahs[0, 1 + n].transAxes,
                bbox=dict(facecolor="white", alpha=0),
            )

        # plot data and fit:
        plt.sca(ahs[1, 0])
        plt.errorbar(
            mcres._measData["Q"][0],
            mcres._measData["I"],
            yerr=mcres._measData["ISigma"],
            label="Measured data",
            zorder=1,
        )
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Q (1/nm)")
        plt.ylabel("I (1/cm)")
        plt.plot(
            mcres._measData["Q"][0],
            mcres.modelIAvg.modelIMean.values,
            zorder=2,
            label="McSAS3 fit",
        )
        plt.legend()

        # plot fitting statistics:
        runReport = mcres.debugRunReport().split("\n", 1)[1]
        plt.sca(ahs[0, 0])
        ahs[0, 0].set_aspect(1)
        ahs[0, 0].axis("off")
        ahs[0, 0].text(
            0.2,
            0,
            runReport,
            **csfont,
            rotation=0,
            horizontalalignment="center",
            verticalalignment="bottom",
            multialignment="left",
            transform=ahs[0, 0].transAxes,
            bbox=dict(facecolor="white", alpha=0),
        )
        plt.tight_layout()
        # TODO: change path

        if saveHistFile is not None:
            plt.savefig(saveHistFile)
