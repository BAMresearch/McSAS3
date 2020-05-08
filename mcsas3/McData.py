import numpy as np
import pandas
import h5py
from mcsas3.McHDF import McHDF
from pathlib import Path


class McData(McHDF):
    """
    A simple base class for a data carrier object that can load from a range of sources, and do rebinning for too large datasets
    This is inherited by the McData1D and McData2D classes intended for actual use. 
    """

    # dataframe objects at least should contain entries for Q, I, ISigma (1D) or Qx, Qy, I, ISigma (2D)
    filename = None  # input filename
    _outputFilename = None # output filename for storing
    loader = None  # can be set to one of the available loaders
    rawData = None  # as read from the file,
    clippedData = None  # clipped to range, dataframe object
    binnedData = None  # clipped and rebinned
    measData = binnedData  # measurement data dict, translated from binnedData dataframe
    measDataLink = "binnedData"  # indicate what measData links to
    dataRange = None  # min-max for data range to fit. overwritten in subclass
    nbins = 100  # default, set to zero for no rebinning
    binning = "logarithmic"  # the only option that makes sense
    csvargs = {}  # overwritten in subclass
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
        "csvargs",
        "loader"
    ]
    loadKeys = [  # keys to store in an HDF5 output file
        "filename",
        "measDataLink",
        "nbins",
        "binning",
        "dataRange",
        "csvargs",
        "loader"
    ]

    def __init__(self, df=None, loadFromFile=None, **kwargs):
        """loadFromFile must be a previous optimization. Else, use any of the other 'from_*' functions """
        if loadFromFile is not None:
            self.load(loadFromFile)

        for key, value in kwargs.items():
            assert key in self.storeKeys, "Key {} is not a valid option".format(key)
            setattr(self, key, value)

        # load from dataframe if provided
        if df is not None:
            self.loader = "from_pandas" # TODO: need to handle this on restore state
            self.from_pandas(df)

        elif self.filename is not None:  # filename has been set
            self.from_file(self.filename)
        # link measData to the requested value

    def linkMeasData(self, measDataLink=None):
        assert False, "defined in 1D and 2D subclasses"
        pass

    def from_file(self, filename = None):
        if filename is None:
            assert self.filename is not None, "at least filename or self.filename must be set for loading from file"
        else:
            self.filename = Path(filename)
        self.filename = Path(self.filename)  # cast into pathlib if not already
        # make sure file exists
        assert (
            self.filename.is_file()
        ), f"input filename: {self.filename} must exist"

        if (self.filename.suffix == ".pdh") or (self.loader == "from_pdh"):
            self.loader="from_pdh" # ensure this is set
            self.from_pdh(self.filename)
        elif (self.filename.suffix in [".csv", ".dat", ".txt"]) or (
            self.loader == "from_csv"
        ):
            self.loader="from_csv" # ensure this is set
            self.from_csv(self.filename)
        elif (self.filename.suffix in ['.h5', '.hdf5', '.nx', '.nxs']) or (
            self.loader == "from_nexus"
        ):
            self.loader="from_nexus"
            self.from_nexus(self.filename)
            # load first, then find out if 1D or 2D
        else:
            assert (
                False
            ), "Input file type could not be determined. Use from_pandas to load a dataframe or use df = [DataFrame] in input, or use 'loader' = 'from_pdh' or 'from_csv' in input"

    def from_pandas(self, df=None):
        assert False, "defined in 1D and 2D subclasses"
        pass

    def from_csv(self, filename=None, csvargs=None):
        assert False, "defined in 1D and 2D subclasses"
        pass

    def from_pdh(self, filename=None):
        assert False, "defined in 1D subclass only"
        pass

    def from_nexus(self, filename=None):
        # find out if 1D or 2D, then use 1D or 2D loaders?
        assert False, "defined in 1D and 2D subclasses"
        pass

    def clip(self):
        assert False, "defined in 1D and 2D subclasses"
        pass

    def reBin(self):
        assert False, "defined in 1D and 2D subclasses"
        pass

    def prepare(self):
        """runs the clipping and binning (in that order), populates clippedData and binnedData"""
        self.clip()
        if self.nbins != 0:
            self.reBin()
        else:
            self.binnedData = self.clippedData.copy()
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
            if key == 'csvargs':
                # special loading, csvargs was stored as dict.
                with h5py.File(filename, "r") as h5f:
                    [self.csvargs.update({key: val[()]}) for key, val in h5f[f'{path}csvargs'].items()]
            else:
                with h5py.File(filename, "r") as h5f:
                    if key in h5f[f"{path}"]:
                        setattr(self, key, h5f[f"{path}{key}/"][()])
        if self.loader == 'from_pandas':
            buildDict = {}
            with h5py.File(filename, "r") as h5f:
                [buildDict.update({key: val[()]}) for key, val in h5f[f'{path}rawData'].items()]
            self.rawData = pandas.DataFrame(data = buildDict)
        else:
            self.from_file()
        self.prepare()