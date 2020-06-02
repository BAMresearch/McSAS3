import unittest

# these need to be loaded at the beginning to avoid errors related to relative imports (ImportWarning in h5py)
# might be related to the change of import style for Python 3.5+. Tested on Python 3.7 at 20200417
import sys, os, pandas, scipy
import numpy as np
from pathlib import Path

# these packages are failing to import in McHat if they are not loaded here:
import h5py
# %matplotlib inline
# import matplotlib.pyplot as plt
# see if imports work
from mcsas3 import McData1D
from mcsas3 import McHat
from mcsas3.mcmodelhistogrammer import McModelHistogrammer
from mcsas3.mcanalysis import McAnalysis

from pathlib import Path

class testtest(unittest.TestCase):

    def testTests(self):
        # tests whether I can read a file written by datamerge v2.5
        hpath = Path('testdata','datamerge.nxs')

if __name__ == "__main__":
    unittest.main()
