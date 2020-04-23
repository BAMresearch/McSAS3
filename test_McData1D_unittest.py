import unittest

# these need to be loaded at the beginning to avoid errors related to relative imports (ImportWarning in h5py)
# might be related to the change of import style for Python 3.5+. Tested on Python 3.7 at 20200417
import sys, os, pandas, numpy, scipy

# these packages are failing to import in McHat if they are not loaded here:
import h5py

# %matplotlib inline
# import matplotlib.pyplot as plt
from mcsas3 import McData1D

# import warnings
# warnings.filterwarnings('error')


class testMcData1D(unittest.TestCase):
    def test_mcdata1d_instantiated(self):
        md = McData1D.McData1D()
        md.from_pdh(filename=r"S2870 BSA THF 1 1 d.pdh")
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys())

    def test_mcdata1d_singleLine(self):
        md = McData1D.McData1D(filename=r"S2870 BSA THF 1 1 d.pdh")
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys())

    def test_mcdata1d_singleLineWithOptions(self):
        md = McData1D.McData1D(filename=r"S2870 BSA THF 1 1 d.pdh", dataRange=[0.1, 0.6], nbins=50)
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys())


if __name__ == "__main__":
    unittest.main()
