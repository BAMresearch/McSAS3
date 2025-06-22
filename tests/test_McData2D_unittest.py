# these need to be loaded at the beginning to avoid errors related to relative imports
# (ImportWarning in h5py), might be related to the change of import style for Python 3.5+.
# Tested on Python 3.7 at 20200417
from pathlib import Path
import unittest

# %matplotlib inline
# import matplotlib.pyplot as plt
from mcsas3 import mc_data_2d

# import warnings
# warnings.filterwarnings('error')


class testMcData2D(unittest.TestCase):
    def test_mcdata2d_instantiated(self):
        md = mc_data_2d.McData2D()
        md.from_nexus(filename=Path(r"testdata/009766_forSasView.h5"))
        self.assertIsNotNone(md.measData, "measData is not populated")
        self.assertTrue("Q" in md.measData.keys())


if __name__ == "__main__":
    unittest.main()
