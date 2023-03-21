import shutil  # for copy

# these need to be loaded at the beginning to avoid errors related to relative imports
# (ImportWarning in h5py), might be related to the change of import style for Python 3.5+.
# Tested on Python 3.7 at 20200417
import unittest
from pathlib import Path

# these packages are failing to import in McHat if they are not loaded here:
import numpy as np
import pandas

# for reading configuration files
import yaml

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
        self.assertTrue(np.min(md.measData["Q"]) > 0.1, "clipper has not applied minimum")
        self.assertTrue(np.max(md.measData["Q"]) < 0.6, "clipper has not applied maximum")
        self.assertTrue(len(md.measData["Q"]) < 51, "rebinner has not rebinned to <51 bins")

    def test_mcdata1d_csv(self):
        md = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys(), "measData does not contain Q")
        self.assertTrue(len(md.measData["Q"]) < 101, "rebinner has not rebinned to <51 bins")

    def test_mcdata1d_nxs_with_omit_from_yaml(self):
        readConfigFile = Path("example_configurations", "read_config_nxs_with_omit.yaml")
        filename = Path("testdata", "datamerge.nxs")
        with open(readConfigFile, "r") as f:
            readDict = yaml.safe_load(f)
        # try loading the data
        _ = McData1D.McData1D(filename=filename, resultIndex=0, **readDict)

    def test_mcdata1d_csv_norebin(self):
        md = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=0,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys(), "measData does not contain Q")
        self.assertTrue(len(md.measData["I"]) == len(md.rawData), "rebinner has not been bypassed")

    def test_restore_state(self):
        if Path("test_state.h5").is_file():
            Path("test_state.h5").unlink()

        mds = McData1D.McData1D(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )
        mds.store(filename="test_state.h5")
        del mds
        _ = McData1D.McData1D(loadFromFile=Path("test_state.h5"))

    # def test_restore_state_withIndex(self):
    #     md = McData1D.McData1D(
    #         loadFromFile=Path("testdata", "merged_096.nxs"), resultIndex=2
    #     )

    def test_restore_state_fromDataframe(self):
        # create state:
        if Path("test_state_df.h5").is_file():
            Path("test_state_df.h5").unlink()

        # test dataframe:
        Q = np.linspace(0.01, 0.99, 100, dtype=float)
        Int = Q**-4
        ISigma = Int * 0.01
        testdf = pandas.DataFrame(data={"Q": Q, "I": Int, "ISigma": ISigma})
        od = McData1D.McData1D(df=testdf)
        od.store(filename="test_state_df.h5")
        del od
        _ = McData1D.McData1D(loadFromFile=Path("test_state_df.h5"))

    def test_from_nxsas(self):
        # tests whether McData can load from NXsas
        hpath = Path("testdata", "20190725_11_expanded_stacked_processed_190807_161306.nxs")
        _ = McData1D.McData1D(filename=hpath)

    def test_restore_state_from_nxsas(self):
        # tests whether I can restore state from a nexus file-derived McSAS state file
        hpath = Path("testdata", "20190725_11_expanded_stacked_processed_190807_161306.nxs")
        od = McData1D.McData1D(filename=hpath)
        od.store(filename="test_state_nxsas.h5")
        del od
        _ = McData1D.McData1D(loadFromFile=Path("test_state_nxsas.h5"))

    def test_nxsas_io(self):
        # tests whether I can read and write in the same nexus file
        if Path("testdata", "test_nexus_io.nxs").is_file():
            Path("testdata", "test_nexus_io.nxs").unlink()
        hpath = Path("testdata", "20190725_11_expanded_stacked_processed_190807_161306.nxs")
        tpath = Path("testdata", "test_nexus_io.nxs")
        shutil.copy(hpath, tpath)

        od = McData1D.McData1D(filename=tpath)
        od.store(filename=tpath)
        del od
        _ = McData1D.McData1D(loadFromFile=tpath)

    def test_read_datamerge(self):
        # tests whether I can read a file written by datamerge v2.5
        hpath = Path("testdata", "datamerge.nxs")
        _ = McData1D.McData1D(filename=hpath)


if __name__ == "__main__":
    unittest.main()
