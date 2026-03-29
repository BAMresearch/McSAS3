# these need to be loaded at the beginning to avoid errors related to relative imports
# (ImportWarning in h5py), might be related to the change of import style for Python 3.5+.
# Tested on Python 3.7 at 20200417
import unittest
from pathlib import Path

# %matplotlib inline
# import matplotlib.pyplot as plt
from mcsas3 import mc_data_2d
from mcsas3.data_adapters import analysis_data_from_bundle

# import warnings
# warnings.filterwarnings('error')


class testMcData2D(unittest.TestCase):
    def test_mcdata2d_instantiated(self):
        md = mc_data_2d.McData2D()
        md.from_nexus(filename=Path(r"testdata/009766_forSasView.h5"))
        analysis_data = analysis_data_from_bundle(md.to_analysis_bundle(), q_nudge=md.qNudge)
        self.assertIsNotNone(analysis_data, "analysisData is not populated")
        self.assertTrue("Q" in analysis_data.keys())


if __name__ == "__main__":
    unittest.main()
