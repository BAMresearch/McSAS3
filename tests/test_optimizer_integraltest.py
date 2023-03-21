import os
import shutil  # for file copy

# these need to be loaded at the beginning to avoid errors related to relative imports
# (ImportWarning in h5py), might be related to the change of import style for Python 3.5+.
# Tested on Python 3.7 at 20200417
import sys
import unittest
import warnings

# from scipy.special import j0 # this one works in a notebook, but not here?
# import scipy.optimize
from pathlib import Path

# import matplotlib.pyplot as plt
import numpy
import numpy as np
import pandas

# # load required modules
# homedir = os.path.expanduser("~")
# # disable OpenCL for multiprocessing on CPU
# os.environ["SAS_OPENCL"] = "none"
# # set location where the SasView/sasmodels are installed
# # sasviewPath = os.path.join(homedir, "AppData", "Local", "SasView")
# sasviewPath = os.path.join(homedir, "Code", "sasmodels")  # BRP-specific
# if sasviewPath not in sys.path:
#     sys.path.append(sasviewPath)
from mcsas3 import McData1D, McData2D, McHat, McPlot

# from mcsas3.mcmodelhistogrammer import McModelHistogrammer
from mcsas3.mcanalysis import McAnalysis

# import scipy

# these packages are failing to import in McHat if they are not loaded here:
# import h5py


warnings.filterwarnings("error")


class testOptimizer(unittest.TestCase):
    def test_optimizer_2D_cylinder(self):
        resPath = Path("test_result2DCylinder.h5")
        if resPath.is_file():
            resPath.unlink()

        # md = McData2D.McData2D()
        # md.from_nexus(filename=r"testdata/009766_forSasView.h5")
        mds = McData2D.McData2D(
            filename=Path("testdata", "009766_forSasView.h5"),
        )

        mh = McHat.McHat(
            modelName="cylinder",
            nContrib=600,
            modelDType="default",
            fitParameterLimits={
                "radius": (5, 500),
                "length": (600, 1200),
                "phi": (90 - 90, 90 + 90),
            },
            staticParameters={
                "background": 0,
                "scale": 1,
                "sld": 6.3,  # e-6,
                "sld_solvent": 1,  # e-6, # D2O
                "theta": 90,
            },
            maxIter=1e5,
            convCrit=1e5,
            nRep=4,
            nCores=0,
            seed=None,
        )
        md = mds.measData.copy()
        mh.run(md, resPath)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="length",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="phi",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=True,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)

    def test_optimizer_1D_mcsas_sphere_and_rehistogrammer(self):
        # uses an internal sphere function for the case the sasmodels don't want to work.
        # remove any prior results file:
        resPath = Path("test_resultssphere.h5")
        if resPath.is_file():
            resPath.unlink()

        mds = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
            resultIndex=2,
        )
        mds.store(resPath)

        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="mcsas_sphere",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"radius": (3.14, 314)},
            staticParameters={
                "background": 0,
                "scale": 1,
                "sld": 3.35e-5,
                "sld_solvent": 0,
            },
            maxIter=1e5,
            convCrit=1,
            nRep=4,
            nCores=1,
            seed=None,
            resultIndex=2,
        )
        md = mds.measData.copy()
        mh.run(md, resPath, resultIndex=2)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True, resultIndex=2)

        # -- -- --
        # def test_reHistogrammer(self):
        # immediately test the rehistogrammer as it requires the output of the steps until here..
        # read the configuration file
        # resPath = Path("test_resultssphere.h5")

        # clear prior results:
        del mds, mh, histRanges

        # load the data

        mds = McData1D.McData1D(loadFromFile=resPath, resultIndex=2)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="log",
                    presetRangeMin=5,
                    presetRangeMax=25,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=True,
                ),
            ]
        )
        # run the Monte Carlo method
        md = mds.measData.copy()
        mcres = McAnalysis(resPath, md, histRanges, store=True, resultIndex=2)

        # plotting:
        # plot the histogram result
        mp = McPlot.McPlot()
        # output file for plot:
        saveHistFile = resPath.with_suffix(".png")
        if saveHistFile.is_file():
            saveHistFile.unlink()
        mp.resultCard(mcres, saveHistFile=saveHistFile)

    def test_optimizer_1D_sphere(self):
        # remove any prior results file:
        resPath = Path("test_resultssphere_1D.h5")
        if resPath.is_file():
            resPath.unlink()

        mds = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )

        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="sphere",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"radius": (3.14, 314)},
            staticParameters={"background": 0, "scaling": 0.1e6},
            maxIter=1e5,
            convCrit=1,
            nRep=4,
            nCores=0,
            seed=None,
        )
        md = mds.measData.copy()
        mh.run(md, resPath)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)

    def test_optimizer_1D_sphere_with_hardspherestructure(self):
        # remove any prior results file:
        resPath = Path("test_resultshardsphere.h5")
        if resPath.is_file():
            resPath.unlink()

        mds = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )

        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="sphere@hardsphere",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"radius": (3.14, 314)},
            staticParameters={
                "background": 0,
                "scaling": 1,
                "radius_effective_mode": 1,  # effective radius follows radius
                "structure_factor_mode": 1,  # with beta approximation
                "volfraction": 0.01,
            },
            maxIter=1e5,
            convCrit=1,
            nRep=4,
            nCores=0,
            seed=None,
        )
        md = mds.measData.copy()
        mh.run(md, resPath)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)

    def test_optimizer_1D_sim0_singlecore(self):
        # use a simulation for fitting.
        # remove any prior results file:
        resPath = Path("test_resultssim_1D_singlecore.h5")
        if resPath.is_file():
            resPath.unlink()

        # measurement data:
        mds = McData1D.McData1D(
            filename=Path("testdata", "nPSize4.dat"),
            nbins=0,  # no rebinning
            csvargs={
                "sep": ";",
                "header": None,
                "names": ["Q", "I", "ISigma"],
                "usecols": [0, 3, 4],
            },
            dataRange=[0.04, 1],
        )
        # simulation data:
        simd = McData1D.McData1D(
            filename=Path("testdata", "fancyCubePD0p01.nxs"),
            pathDict={
                "Q": "/sasentry1/sasdata1/Q",
                "I": "/sasentry1/sasdata1/I",
                "ISigma": "/sasentry1/sasdata1/Idev",
            },
            dataRange=[0, 38],  # clip last datapoint for neatness
        )

        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="sim",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"factor": (20, 40)},
            staticParameters={
                "extrapY0": 2.21e-09,
                "extrapScaling": 9.61e01,
                "simDataQ0": simd.measData["Q"][0],
                "simDataQ1": None,
                "simDataI": simd.measData["I"],
                "simDataISigma": simd.measData["ISigma"],
            },
            # staticParameters={"extrapY0": 2.21e-09, "extrapScaling": 9.61e+01,
            #                   "simDataDict": simd.measData},
            maxIter=1e5,
            convCrit=14,
            nRep=4,
            nCores=1,
            seed=None,
        )
        mds.store(resPath)
        md = mds.measData.copy()
        mh.run(md, resPath)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="factor",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=0.1,
                    presetRangeMax=3,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="factor",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=0.1,
                    presetRangeMax=3,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)

    def test_optimizer_1D_sim1_multicore(self):
        # use a simulation for fitting.
        # remove any prior results file:
        resPath = Path("test_resultssim_1D_multicore.h5")
        if resPath.is_file():
            resPath.unlink()

        # measurement data:
        mds = McData1D.McData1D(
            filename=Path("testdata", "nPSize4.dat"),
            nbins=0,  # no rebinning
            csvargs={
                "sep": ";",
                "header": None,
                "names": ["Q", "I", "ISigma"],
                "usecols": [0, 3, 4],
            },
            dataRange=[0.04, 1],
        )
        # simulation data:
        simd = McData1D.McData1D(
            filename=Path("testdata", "fancyCubePD0p01.nxs"),
            pathDict={
                "Q": "/sasentry1/sasdata1/Q",
                "I": "/sasentry1/sasdata1/I",
                "ISigma": "/sasentry1/sasdata1/Idev",
            },
            dataRange=[0, 38],  # clip last datapoint for neatness
        )

        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="sim",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"factor": (20, 40)},
            staticParameters={
                "extrapY0": 2.21e-09,
                "extrapScaling": 9.61e01,
                "simDataQ0": simd.measData["Q"][0],
                "simDataQ1": None,
                "simDataI": simd.measData["I"],
                "simDataISigma": simd.measData["ISigma"],
            },
            maxIter=1e5,
            convCrit=14,
            nRep=4,
            nCores=2,
            seed=None,
        )
        mds.store(resPath)
        md = mds.measData.copy()
        mh.run(md, resPath)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="factor",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=0.1,
                    presetRangeMax=3,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="factor",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=0.1,
                    presetRangeMax=3,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)

    def test_optimizer_1D_sim2_histogram(self):
        # can only be run after the test_optimizer_1D_sim has been run
        resPath = Path("test_resultssim_1D_multicore.h5")
        assert resPath.exists(), "MC optimization not done yet, run the sim test first"

        # measurement data:
        mds = McData1D.McData1D(
            filename=Path("testdata", "nPSize4.dat"),
            nbins=0,  # no rebinning
            csvargs={
                "sep": ";",
                "header": None,
                "names": ["Q", "I", "ISigma"],
                "usecols": [0, 3, 4],
            },
            dataRange=[0.04, 1],
        )
        md = mds.measData.copy()

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="factor",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=0.1,
                    presetRangeMax=3,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="factor",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=0.1,
                    presetRangeMax=3,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)

    def test_optimizer_1D_sphere_rehistogram(self):
        # same as above, but include a test of the re-histogramming functionality:
        # remove any prior results file:
        resPath = Path("test_resultssphere_rehist.h5")
        if resPath.is_file():
            resPath.unlink()

        mds = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )
        # load required modules
        homedir = os.path.expanduser("~")
        # disable OpenCL for multiprocessing on CPU
        os.environ["SAS_OPENCL"] = "none"
        # set location where the SasView/sasmodels are installed
        # sasviewPath = os.path.join(homedir, "AppData", "Local", "SasView")
        sasviewPath = os.path.join(homedir, "Code", "sasmodels")  # BRP-specific
        if sasviewPath not in sys.path:
            sys.path.append(sasviewPath)

        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="sphere",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"radius": (1, 314)},
            staticParameters={"background": 0, "scaling": 0.1e6},
            maxIter=1e5,
            convCrit=1,
            nRep=4,
            nCores=0,
            seed=None,
        )
        md = mds.measData.copy()
        mh.run(md, resPath)
        # histogram the determined size contributions
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)

        # now change the histograms and re-run:
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=34,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=60,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=200,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)

    def test_optimizer_1D_sphere_state(self):
        # (re-)creates a state for the restore-state test.
        resPath = Path("test_state.h5")
        if resPath.is_file():
            resPath.unlink()

        mds = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )
        mds.store(filename=resPath)

        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="sphere",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"radius": (1, 314)},
            staticParameters={"background": 0, "scaling": 0.1e6},
            maxIter=1e5,
            convCrit=1,
            nRep=4,
            nCores=0,
            seed=None,
        )
        md = mds.measData.copy()
        mh.run(md, resPath)
        # histogram the determined size contributions
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)
        # state created

        # def test_optimizer_1D_sphere_restorestate(self):
        # can we recover a state as stored in the HDF5 file?:
        del mds, mh, md, histRanges

        mds = McData1D.McData1D(loadFromFile=resPath)
        # load required modules
        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="sphere",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"radius": (1, 314)},
            staticParameters={"background": 0, "scaling": 0.1e6},
            maxIter=1e5,
            convCrit=1,
            nRep=4,
            nCores=0,
            seed=None,
        )
        md = mds.measData.copy()
        mh.run(md, resPath)
        # histogram the determined size contributions
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)

        # now change the histograms and re-run:
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=34,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=60,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=200,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)

    def test_optimizer_1D_sphere_accuratestate(self):
        # (re-)creates an accurate state for histogramming tests.
        resPath = Path("test_accuratestate.h5")
        if resPath.is_file():
            resPath.unlink()

        mds = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )
        mds.store(filename=resPath)

        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="sphere",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"radius": (3.14, 314)},
            staticParameters={
                "background": 0,
                "scaling": 1,
                "sld": 77.93,
                "sld_solvent": 9.45,
            },
            maxIter=1e5,
            convCrit=1,
            nRep=50,
            nCores=2,
            seed=None,
        )
        md = mds.measData.copy()
        mh.run(md, resPath)
        # histogram the determined size contributions
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=3.14,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=3.142,
                    presetRangeMax=25,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=25,
                    presetRangeMax=75,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=75,
                    presetRangeMax=150,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md, histRanges, store=True)
        # state created

        # def test_optimizer_1D_sphere_rehistogram_accuratestate(self):
        # for troubleshooting the histogramming function :
        del mds, md, histRanges, mh

        mds = McData1D.McData1D(loadFromFile=resPath)
        md = mds.measData.copy()
        # histogram the determined size contributions
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=3.14,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=3.142,
                    presetRangeMax=25,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=25,
                    presetRangeMax=75,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=75,
                    presetRangeMax=150,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        mcres = McAnalysis(resPath, md, histRanges, store=True)
        # test whether the volume fraction of the first population is within expectation:
        np.testing.assert_allclose(
            mcres._averagedModes.loc[1, "totalValue"]["valMean"], 0.027, atol=0.001
        )
        # test whether the volume fraction of the second population is within expectation:
        np.testing.assert_allclose(
            mcres._averagedModes.loc[2, "totalValue"]["valMean"], 9.01e-02, atol=0.001
        )
        # test whether the volume fraction of the third population is within expectation:
        np.testing.assert_allclose(
            mcres._averagedModes.loc[3, "totalValue"]["valMean"], 9.57e-02, atol=0.001
        )
        # test whether the mean dimension of the first population is within expectation:
        np.testing.assert_allclose(mcres._averagedModes.loc[1, "mean"]["valMean"], 1.11e01, atol=1)
        # test whether the mean dimension of the first population is within expectation:
        np.testing.assert_allclose(mcres._averagedModes.loc[2, "mean"]["valMean"], 4.71e01, atol=5)
        # test whether the mean dimension of the first population is within expectation:
        np.testing.assert_allclose(mcres._averagedModes.loc[3, "mean"]["valMean"], 1.03e02, atol=5)

    def test_optimizer_1D_gaussianchain(self):
        # remove any prior results file:
        resPath = Path("test_resultsgaussianchain.h5")
        if resPath.is_file():
            resPath.unlink()

        md = McData1D.McData1D(
            filename=r"testdata/S2870 BSA THF 1 1 d.pdh", dataRange=[0.1, 4], nbins=50
        )
        md.store(resPath)
        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="mono_gauss_coil",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"rg": (1, 20)},
            staticParameters={"background": 0, "i_zero": 0.00319},
            maxIter=1e5,
            convCrit=2,
            nRep=5,
            nCores=0,
            seed=None,
        )
        # test step seems to be broken? Maybe same issue with multicore processing with sasview
        mh.run(md.measData, resPath)
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="rg",
                    nBin=25,
                    binScale="linear",
                    presetRangeMin=0.1,
                    presetRangeMax=30,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, md.measData, histRanges, store=True)

    def test_optimizer_nxsas_io(self):
        tpath = Path("testdata", "test_nexus_io.nxs")
        # tests whether I can read and write in the same nexus file
        if tpath.is_file():
            tpath.unlink()
        hpath = Path("testdata", "20190725_11_expanded_stacked_processed_190807_161306.nxs")

        shutil.copy(hpath, tpath)

        od = McData1D.McData1D(filename=tpath)
        od.store(filename=tpath)

        mh = McHat.McHat(
            modelName="sphere",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"radius": (0.2, 160)},
            staticParameters={"background": 0, "scaling": 1e3},
            maxIter=1e5,
            convCrit=4000,
            nRep=4,
            nCores=0,
            seed=None,
        )

        mh.run(od.measData.copy(), tpath)
        # histogram the determined size contributions
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=1,
                    presetRangeMax=10,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(tpath, od.measData.copy(), histRanges, store=True)


if __name__ == "__main__":
    unittest.main()
