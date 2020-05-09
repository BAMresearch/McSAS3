import unittest

# these need to be loaded at the beginning to avoid errors related to relative imports (ImportWarning in h5py)
# might be related to the change of import style for Python 3.5+. Tested on Python 3.7 at 20200417
import sys, os, pandas, numpy, scipy

# these packages are failing to import in McHat if they are not loaded here:
import h5py
# from scipy.special import j0 # this one works in a notebook, but not here?
import scipy.optimize
from pathlib import Path
import shutil # for file copy
import matplotlib.pyplot as plt

# load required modules
homedir = os.path.expanduser("~")
# disable OpenCL for multiprocessing on CPU
os.environ["SAS_OPENCL"] = "none"
# set location where the SasView/sasmodels are installed
# sasviewPath = os.path.join(homedir, "AppData", "Local", "SasView")
sasviewPath = os.path.join(homedir, "Code", "sasmodels")  # BRP-specific
if sasviewPath not in sys.path:
    sys.path.append(sasviewPath)
from mcsas3 import McHat
from mcsas3 import McData1D
from mcsas3.mcmodelhistogrammer import McModelHistogrammer
from mcsas3.mcanalysis import McAnalysis
import warnings

warnings.filterwarnings("error")


class testOptimizer(unittest.TestCase):
    def test_optimizer_1D_sphere(self):
        # remove any prior results file:
        resPath = Path("test_resultssphere.h5")
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
            fitParameterLimits={"radius": (1, 314)},
            staticParameters={"background": 0, "scaling": 0.1e6},
            maxIter=1e5,
            convCrit=1,
            nRep=4,
            nCores=0,
            seed=None,
        )
        md = mds.measData.copy()
        mh.run(md, "test_resultssphere.h5")


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
        mcres = McAnalysis("test_resultssphere.h5", md, histRanges, store=True)

    def test_optimizer_1D_sphere_rehistogram(self):
        # same as above, but include a test of the re-histogramming functionality:
        # remove any prior results file:
        resPath = Path("test_resultssphere.h5")
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
        mh.run(md, "test_resultssphere.h5")
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
        mcres = McAnalysis("test_resultssphere.h5", md, histRanges, store=True)

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
        mcres = McAnalysis("test_resultssphere.h5", md, histRanges, store=True)

    def test_optimizer_1D_sphere_createstate(self):
        # (re-)creates a state for the restore-state test. 
        resPath = Path("test_state.h5")
        if resPath.is_file():
            resPath.unlink()

        mds = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )
        mds.store(filename = "test_state.h5")

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
        mh.run(md, "test_state.h5")
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
        mcres = McAnalysis("test_state.h5", md, histRanges, store=True)
        # state created

    def test_optimizer_1D_sphere_restorestate(self):
        # can we recover a state as stored in the HDF5 file?:

        mds = McData1D.McData1D(loadFromFile=Path("test_state.h5"))
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
        mh.run(md, "test_resultssphere.h5")
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
        mcres = McAnalysis("test_resultssphere.h5", md, histRanges, store=True)

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
        mcres = McAnalysis("test_resultssphere.h5", md, histRanges, store=True)


    def test_optimizer_1D_gaussianchain(self):
        # remove any prior results file:
        resPath = Path("test_resultsgaussianchain.h5")
        if resPath.is_file():
            resPath.unlink()

        md = McData1D.McData1D(filename=r"testdata/S2870 BSA THF 1 1 d.pdh", dataRange = [0.1, 4], nbins = 50)
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
        mh.run(md.measData, "test_resultsgaussianchain.h5")
        histRanges = pandas.DataFrame([dict(
                        parameter="rg", nBin=25, binScale="linear",
                        presetRangeMin=0.1, presetRangeMax=30,
                        binWeighting="vol", autoRange=False),])
        mcres = McAnalysis("test_resultsgaussianchain.h5", md.measData, histRanges, store=True)

    def test_optimizer_nxsas_io(self):
        # tests whether I can read and write in the same nexus file
        if Path('testdata', "test_nexus_io.nxs").is_file():
            Path('testdata', "test_nexus_io.nxs").unlink()
        hpath = Path('testdata', '20190725_11_expanded_stacked_processed_190807_161306.nxs')
        tpath = Path('testdata', "test_nexus_io.nxs")
        shutil.copy(hpath, tpath)

        od = McData1D.McData1D(filename = tpath)
        od.store(filename = tpath)

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
        mcres = McAnalysis(tpath, od.measData.copy(), histRanges, store=True)


if __name__ == "__main__":
    unittest.main()
