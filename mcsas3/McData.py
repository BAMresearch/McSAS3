import numpy as np
from .McHDF import McHDF

class McData(McHDF):
    """
    A simple data carrier object that can load from a range of sources, and do rebinning for too large datasets
    """
    rawData = None # as read from the file, dict object at least with entries for Q, I, ISigma
    clippedData = None # clipped to range, dict object at least with entries for Q, I, ISigma
    binnedData = None  # clipped and rebinned
    measData = binnedData  # measurement data dict at least with entries for Q, I, ISigma, == binnedData by default
    measDataLink = 'binnedData' # indicate what measData links to
    dataRange = [-np.inf, np.inf] # min-max for data range to fit
    nbins = 100 # default
    binning = 'logarithmic' # the only option that makes sense
    storeKeys = [ # keys to store in an output file
        "rawData",
        "clippedData",
        "binnedData",
        "measData",
        "measDataLink",
        "nbins",
        "binning",
        "dataRange",
    ]
    loadKeys = storeKeys
    loadKeys.pop("measData") # generated from measDataLink

    def __init__(self, loadFromFile=None, **kwargs):
        """kwargs accepts all parameters from McModel and McOpt."""

        if loadFromFile is not None:
            self.load(loadFromFile)

        for key, value in kwargs.items():
            assert (key in self.storeKeys), "Key {} is not a valid option".format(key)
            setattr(self, key, value)

        # link measData to the requested value

    def linkMeasData(self, measDataLink = None):
        if measDataLink is None:
            measDataLink = self.measDataLink
        assert (measDataLink in ["rawData", "clippedData", "binnedData"]), f"measDataLink value: {measDataLink} not valid. Must be one of 'rawData', 'clippedData' or 'binnedData'"
        self.measData = getattr(self, measDataLink)

    def from_pandas(self, dataframe):
        """uses a dataframe as input, should contain 'Q', 'I', and 'ISigma'"""
        pass

    def from_csv(self, filename, csvargs = None):
        """reads from a three-column csv file, takes pandas from_csv arguments"""
        pass

    def from_pdh(self, filename=None):
        """reads from a PDH file"""
        pass

    def prepare(self):
        """runs the clipping and binning (in that order), populates clippedData and binnedData"""
        pass

    def store(self, filename = None, path = '/entry1/analysis/MCResult1/mcdata/'):
        """stores the settings in an output file (HDF5)"""
        assert filename is not None
        for key in self.storeKeys:
            value = getattr(self, key, None)
            self._HDFstoreKV(filename = filename, path = path, key = key, value = value)

    def load(self, filename = None, path = '/entry1/analysis/MCResult1/mcdata/'):
        assert filename is not None
        for key in self.loadKeys:
            with h5py.File(filename, 'r') as h5f:
                setattr(self, key, h5f["{}/{}".format(path, key)][()])
