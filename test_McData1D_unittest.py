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
from mcsas3 import McData1D

# import warnings
# warnings.filterwarnings('error')


class testMcData1D(unittest.TestCase):
    def test_mcdata1d_instantiated(self):
        md = McData1D.McData1D()
        md.from_pdh(filename=r"testdata/S2870 BSA THF 1 1 d.pdh")
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys())

    def test_mcdata1d_singleLine(self):
        md = McData1D.McData1D(filename=r"testdata/S2870 BSA THF 1 1 d.pdh")
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys())

    def test_mcdata1d_singleLineWithOptions(self):
        md = McData1D.McData1D(
            filename=r"testdata/S2870 BSA THF 1 1 d.pdh", dataRange=[0.1, 0.6], nbins=50
        )
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys(), "measData does not contain Q")
        self.assertTrue(
            np.min(md.measData["Q"]) > 0.1, "clipper has not applied minimum"
        )
        self.assertTrue(
            np.max(md.measData["Q"]) < 0.6, "clipper has not applied maximum"
        )
        self.assertTrue(
            len(md.measData["Q"]) < 51, "rebinner has not rebinned to <51 bins"
        )

    def test_mcdata1d_csv(self):
        md = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys(), "measData does not contain Q")
        self.assertTrue(
            len(md.measData["Q"]) < 101, "rebinner has not rebinned to <51 bins"
        )

    def test_mcdata1d_csv_norebin(self):
        md = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=0,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys(), "measData does not contain Q")
        self.assertTrue(
            len(md.measData["I"]) == len(md.rawData), "rebinner has not been bypassed")
        
    def test_restore_state(self):
        # test state created in test_optimizer_1D_sphere_createState
        md = McData1D.McData1D(loadFromFile=Path("test_state.h5"))

if __name__ == "__main__":
    unittest.main()
