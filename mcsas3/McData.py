import numpy as np
import pandas
import h5py
from .McHDF import McHDF
from pathlib import Path


class McData(McHDF):
    """
    A simple base class for a data carrier object that can load from a range of sources, and do rebinning for too large datasets
    This is inherited by the McData1D and McData2D classes intended for actual use. 
    """

    # dataframe objects at least should contain entries for Q, I, ISigma (1D) or Qx, Qy, I, ISigma (2D)
    filename = None  # input filename
    loader = None  # can be set to one of the available loaders
    rawData = None  # as read from the file,
    clippedData = None  # clipped to range, dataframe object
    binnedData = None  # clipped and rebinned
    measData = binnedData  # measurement data dict, translated from binnedData dataframe
    measDataLink = "binnedData"  # indicate what measData links to
    dataRange = None  # min-max for data range to fit. overwritten in subclass
    nbins = 100  # default
    binning = "logarithmic"  # the only option that makes sense
    # maybe make this behave like a dict? or maybe that's a bad idea... possible method here: https://stackoverflow.com/questions/4014621/a-python-class-that-acts-like-dict
    # Q = None # links to measData
    # I = None # links to measData
    # ISigma = None # links to measData
    storeKeys = [  # keys to store in an HDF5 output file
        "filename",
        "rawData",
        "clippedData",
        "binnedData",
        "measData",
        "measDataLink",
        "nbins",
        "binning",
        "dataRange",
    ]
    loadKeys = storeKeys.copy()  # to load from an HDF5 file to restore its state
    loadKeys.remove("measData")  # generated from measDataLink

    csvargs = None  # overwritten in subclass

    def __init__(self, df=None, loadFromFile=None, **kwargs):
        """loadFromFile must be a previous optimization. Else, use any of the other 'from_*' functions """
        if loadFromFile is not None:
            self.load(loadFromFile)

        for key, value in kwargs.items():
            assert key in self.storeKeys, "Key {} is not a valid option".format(key)
            setattr(self, key, value)

        # load from dataframe if provided
        if df is not None:
            self.from_pandas(df)

        elif self.filename is not None:  # filename has been set
            self.filename = Path(self.filename)  # cast into pathlib if not already
            # make sure file exists
            assert (
                self.filename.is_file()
            ), f"input filename: {self.filename} must exist"

            if (self.filename.suffix == ".pdh") or (self.loader == "load_pdh"):
                self.from_pdh(self.filename)
            elif (self.filename.suffix in [".csv", ".dat", ".txt"]) or (
                self.loader == "load_csv"
            ):
                self.from_csv(self.filename)
            else:
                assert (
                    False
                ), "Input file type could not be determined. Use from_pandas to load a dataframe or use df = [DataFrame] in input, or use 'loader' = 'from_pdh' or 'from_csv' in input"

        # link measData to the requested value

    def linkMeasData(self, measDataLink=None):
        assert False, "defined in 1D and 2D subclasses"
        pass

    def from_pandas(self, df=None):
        assert False, "defined in 1D and 2D subclasses"
        pass

    def from_csv(self, filename=None, csvargs=None):
        assert False, "defined in 1D and 2D subclasses"
        pass

    def from_pdh(self, filename=None):
        assert False, "defined in 1D subclass only"
        pass

    def clip(self):
        assert False, "defined in 1D and 2D subclasses"
        pass

    def reBin(self):
        assert False, "defined in 1D and 2D subclasses"
        pass

    def prepare(self):
        """runs the clipping and binning (in that order), populates clippedData and binnedData"""
        for idx in range(len(self.rawData.Q)):
            self.rawData["Q"][idx] = np.array(self.rawData["Q"][idx])
        for key in ["I", "ISigma"]:
            self.rawData[key] = np.array(self.rawData[key])
        self.clip()
        self.reBin()
        self.linkMeasData()

    def store(self, filename=None, path="/entry1/analysis/MCResult1/mcdata/"):
        """stores the settings in an output file (HDF5)"""
        assert filename is not None
        for key in self.storeKeys:
            value = getattr(self, key, None)
            self._HDFstoreKV(filename=filename, path=path, key=key, value=value)

    def load(self, filename=None, path="/entry1/analysis/MCResult1/mcdata/"):
        assert filename is not None
        for key in self.loadKeys:
            with h5py.File(filename, "r") as h5f:
                setattr(self, key, h5f["{}/{}".format(path, key)][()])
