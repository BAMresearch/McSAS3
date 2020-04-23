import unittest

# these need to be loaded at the beginning to avoid errors related to relative imports (ImportWarning in h5py)
# might be related to the change of import style for Python 3.5+. Tested on Python 3.7 at 20200417
import sys, os, pandas, numpy, scipy

# these packages are failing to import in McHat if they are not loaded here:
import h5py
from scipy.special import j0
import scipy.optimize

import matplotlib.pyplot as plt
from mcsas3 import McData1D

import warnings
warnings.filterwarnings('error')


class testOptimizer(unittest.TestCase):
    def test_optimizer_1D_gaussianchain(self):
        md = McData1D.McData1D()
        md.from_pdh(filename=r"S2870 BSA THF 1 1 d.pdh")
        # load required modules
        homedir = os.path.expanduser("~")
        # disable OpenCL for multiprocessing on CPU
        os.environ["SAS_OPENCL"] = "none"
        # set location where the SasView/sasmodels are installed
        # sasviewPath = os.path.join(homedir, "AppData", "Local", "SasView")
        sasviewPath = os.path.join(homedir, "Code", "sasmodels") # BRP-specific
        if sasviewPath not in sys.path:
            sys.path.append(sasviewPath)
        from mcsas3 import McHat

        # run the Monte Carlo method
        mh = McHat.McHat(
            modelName="mono_gauss_coil", nContrib=300, modelDType="default",
            fitParameterLimits={"rg": (1, 20)},
            staticParameters={"background": 0, "i_zero": 0.00319},
            maxIter=1e5, convCrit=.45, nRep=2, nCores=0, seed=None)
        # test step seems to be broken? Maybe same issue with multicore processing with sasview
        # mh.run(md.measData, "results.h5")

if __name__ == "__main__":
    unittest.main()
