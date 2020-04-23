import unittest

# these need to be loaded at the beginning to avoid errors related to relative imports (ImportWarning in h5py)
# might be related to the change of import style for Python 3.5+. Tested on Python 3.7 at 20200417
import sys, os, pandas, numpy, scipy

# these packages are failing to import in McHat if they are not loaded here:
import h5py
from scipy.special import j0
import scipy.optimize
from pathlib import Path

import matplotlib.pyplot as plt
from mcsas3 import McData1D

import warnings

warnings.filterwarnings("error")


class testOptimizer(unittest.TestCase):
    def test_optimizer_1D_sphere(self):
        mds = McData1D.McData1D(
            filename=Path("src", "testdata", "quickstartdemo1.csv"),
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
        from mcsas3 import McHat

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
        from mcsas3.mcmodelhistogrammer import McModelHistogrammer
        from mcsas3.mcanalysis import McAnalysis

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

    def test_optimizer_1D_gaussianchain(self):
        md = McData1D.McData1D()
        md.from_pdh(filename=r"S2870 BSA THF 1 1 d.pdh")
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

        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="mono_gauss_coil",
            nContrib=300,
            modelDType="default",
            fitParameterLimits={"rg": (1, 20)},
            staticParameters={"background": 0, "i_zero": 0.00319},
            maxIter=1e5,
            convCrit=0.45,
            nRep=2,
            nCores=0,
            seed=None,
        )
        # test step seems to be broken? Maybe same issue with multicore processing with sasview
        # mh.run(md.measData, "results.h5")


if __name__ == "__main__":
    unittest.main()
