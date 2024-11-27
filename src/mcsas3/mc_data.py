# src/mcsas3/mcdata.py

import logging
import attrs
from pathlib import Path, PurePosixPath
from typing import List, Optional

import h5py
import numpy as np
import pandas

from mcsas3.mc_hdf import loadKV, loadKVPairs, storeKV, storeKVPairs,  ResultIndex

# todo use attrs to @define a McData dataclass

@attrs.define
class McData:
    """
    A simple base class for a data carrier object that can load from a range of sources,
    and do rebinning for too large datasets.
    This is inherited by the McData1D and McData2D classes intended for actual use.
    """
    filename: Optional[Path] = attrs.field(default=None, validator=attrs.validators.optional(attrs.validators.instance_of(Path)))
    _outputFilename: Optional[Path] = attrs.field(default=None, validator=attrs.validators.optional(attrs.validators.instance_of(Path)))
    loader: Optional[str] = attrs.field(default=None, validator=attrs.validators.optional(attrs.validators.instance_of(str)))
    rawData: Optional[pandas.DataFrame] = attrs.field(default=None)
    rawData2D: Optional[pandas.DataFrame] = attrs.field(default=None)
    clippedData: Optional[pandas.DataFrame] = attrs.field(default=None)
    binnedData: Optional[pandas.DataFrame] = attrs.field(default=None)
    measData: Optional[dict] = attrs.field(default=None)
    measDataLink: str = attrs.field(default="binnedData", validator=attrs.validators.in_(["rawData", "clippedData", "binnedData"]))
    dataRange: Optional[list] = attrs.field(default=None)
    nbins: int = attrs.field(default=100, validator=attrs.validators.instance_of(int))
    IEmin: float = attrs.field(default=0.01, validator=attrs.validators.instance_of(float))
    pathDict: Optional[dict] = attrs.field(default=None)
    binning: str = attrs.field(default="logarithmic", validator=attrs.validators.in_(["logarithmic"]))
    csvargs: dict = attrs.field(factory=dict)
    qNudge: Optional[float|List] = attrs.field(default=None)#, validator=attrs.validators.optional(attrs.validators.instance_of(float)))
    omitQRanges: Optional[list] = attrs.field(default=None)
    resultIndex: ResultIndex = attrs.field(default=ResultIndex(1), validator=attrs.validators.instance_of(ResultIndex))

    # dataframe objects at least should contain entries for Q, I, ISigma (1D) or Qx, Qy, I, ISigma (2D)
    # filename = None  # input filename
    # _outputFilename = None  # output filename for storing
    # loader = None  # can be set to one of the available loaders
    # rawData = None  # as read from the file,
    # rawData2D = None  # only filled if a 2D NeXus file is loaded
    # clippedData = None  # clipped to range, dataframe object
    # binnedData = None  # clipped and rebinned
    # measData = binnedData  # measurement data dict, translated from binnedData dataframe
    # measDataLink = "binnedData"  # indicate what measData links to
    # dataRange = None  # min-max for data range to fit. overwritten in subclass
    # nbins = 100  # default, set to zero for no rebinning
    # IEmin = 0.01 # default minimum relative uncertainty on the intensity.
    # pathDict = None  # for loading HDF5 files without pointers to the data
    # binning = "logarithmic"  # the only option that makes sense
    # csvargs = {}  # overwritten in subclass
    # qNudge = None  # can adjust/offset the q values in case of misaligned q vector,
    # # in particular visible in 2D data...
    # omitQRanges = None  # to skip or omit unwanted data ranges, for example with sharp XRD peaks,
    # # must be a list of [[qmin, qmax], ...] pairs
    # resultIndex = None
    # maybe make this behave like a dict? or maybe that's a bad idea... possible method here:
    # https://stackoverflow.com/questions/4014621/a-python-class-that-acts-like-dict
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
        "IEmin",
        "binning",
        "dataRange",
        "pathDict",
        "csvargs",
        "loader",
        "qNudge",
        "omitQRanges",
    ]
    loadKeys = (
        {  # keys to store in an HDF5 output file, values are types to cast to using _HDFLoadKV.
            "filename": Path,
            "measDataLink": "str",
            "nbins": int,
            "IEmin": float,
            "binning": "str",
            "dataRange": None,  # not sure what this is.. array?
            "csvargs": "dict",
            "loader": "str",
            "omitQRanges": list,  # not sure if this works?
        }
    )

    def __init__(
        self,
        df: Optional[pandas.DataFrame] = None,
        loadFromFile: Optional[Path] = None,
        resultIndex: int = 1,
        **kwargs: dict,
    ) -> None:
        """loadFromFile must be a previous optimization.
        Else, use any of the other 'from_*' functions"""

        # reset everything so we're sure not to inherit anything from elsewhere:
        self.filename = None  # input filename
        self._outputFilename = None  # output filename for storing
        self.loader = None  # can be set to one of the available loaders
        self.rawData = None  # as read from the file,
        self.rawData2D = None  # only filled if a 2D NeXus file is loaded
        self.clippedData = None  # clipped to range, dataframe object
        self.binnedData = None  # clipped and rebinned
        self.measData = (
            self.binnedData
        )  # measurement data dict, translated from binnedData dataframe
        self.measDataLink = "binnedData"  # indicate what measData links to
        self.dataRange = None  # min-max for data range to fit. overwritten in subclass
        self.nbins = 100  # default, set to zero for no rebinning
        self.IEmin = 0.01 # default minimum relative uncertainty on the intensity.
        self.pathDict = None  # for loading HDF5 files without pointers to the data
        self.binning = "logarithmic"  # the only option that makes sense
        self.csvargs = {}  # overwritten in subclass
        self.qNudge = 0  # can adjust/offset the q values in case of misaligned q vector,
        # in particular visible in 2D data...
        self.omitQRanges = None  # to skip or omit unwanted data ranges, for example with sharp
        # XRD peaks, must be a list of [[qmin, qmax], ...] pairs

        # make sure we store and read from the right place.
        self.resultIndex = ResultIndex(resultIndex)  # defines the HDF5 root path

        if loadFromFile is not None:
            self.load(loadFromFile)

    def processKwargs(self, **kwargs: dict) -> None:
        for key, value in kwargs.items():
            assert key in self.storeKeys, "Key {} is not a valid option".format(key)
            setattr(self, key, value)

    def linkMeasData(self, measDataLink: str = None) -> None:
        assert False, "defined in 1D and 2D subclasses"
        pass

    def from_file(self, filename: Optional[Path] = None) -> None:
        if filename is None:
            assert (
                self.filename is not None
            ), "at least filename or self.filename must be set for loading from file"
        else:
            self.filename = Path(filename)
        self.filename = Path(self.filename)  # cast into pathlib if not already
        # make sure file exists
        assert self.filename.is_file(), f"input filename: {self.filename} must exist"

        if (self.filename.suffix == ".pdh") or (self.loader == "from_pdh"):
            self.loader = "from_pdh"  # ensure this is set
            self.from_pdh(self.filename)
        elif (self.filename.suffix in [".csv", ".dat", ".txt"]) or (self.loader == "from_csv"):
            self.loader = "from_csv"  # ensure this is set
            self.from_csv(self.filename)
        elif (self.filename.suffix in [".h5", ".hdf5", ".nx", ".nxs"]) or (
            self.loader == "from_nexus"
        ):
            self.loader = "from_nexus"
            self.from_nexus(self.filename)
            # load first, then find out if 1D or 2D
        else:
            assert False, (
                "Input file type could not be determined. Use from_pandas to load a dataframe or"
                " use df = [DataFrame] in input, or use 'loader' = 'from_pdh' or 'from_csv' in"
                " input"
            )

    def from_pandas(self, df: pandas.DataFrame = None) -> None:
        assert False, "defined in 1D and 2D subclasses"
        pass

    def from_csv(self, filename: Path = None, csvargs=None) -> None:
        assert False, "defined in 1D and 2D subclasses"
        pass

    def from_pdh(self, filename: Path = None) -> None:
        assert False, "defined in 1D subclass only"
        pass

    # universal reader for 1D and 2D!
    def from_nexus(self, filename: Optional[Path] = None) -> None:
        # optionally, path can be defined as a dict to point at Q, I and ISigma entries.
        def objBytesToStr(inObject):
            outObject = inObject
            if isinstance(inObject, bytes):
                outObject = inObject.decode("utf-8")
            if isinstance(inObject, np.ndarray):
                outObject = inObject.astype("str")
            return outObject

        if filename is None:
            assert (
                self.filename is not None
            ), "either filename or self.filename must be set to a data source"
            filename = self.filename
        else:
            self.filename = filename  # reset to new source if not already set
        self.rawData = {}

        if self.pathDict is not None:
            assert isinstance(
                self.pathDict, dict
            ), "provided path must be dict with keys 'Q', 'I', and 'ISigma'"
            assert all(
                [j in self.pathDict.keys() for j in ["Q", "I", "ISigma"]]
            ), "provided path must be dict with keys 'Q', 'I', and 'ISigma'"
            with h5py.File(filename, "r") as h5f:
                [
                    self.rawData.update({key: h5f[f"{val}"][()].squeeze()})
                    for key, val in self.pathDict.items()
                ]

        else:
            sigPath = "/"
            with h5py.File(filename, "r") as h5f:
                while "default" in h5f[sigPath].attrs:
                    # this is what we find as a new default to add to the path
                    sigPathAdd = h5f[sigPath].attrs["default"]
                    # make sure it's not a bytes string:
                    sigPathAdd = objBytesToStr(sigPathAdd)
                    # if isinstance(sigPathAdd, bytes): sigPathAdd = sigPathAdd.decode("utf-8")
                    # add to the path
                    sigPath += sigPathAdd + "/"
                # make sure we now have access to a signal:
                assert "signal" in h5f[sigPath].attrs, "no signal in default neXus path"
                signalLabel = objBytesToStr(h5f[sigPath].attrs["signal"])
                # if isinstance(signalLabel, bytes): signalLabel = signalLabel.decode("utf-8")
                sigPathI = sigPath + signalLabel
                # extract intensity along qDim... sorry, don't know how (qDim is found below):
                self.rawData.update({"I": h5f[sigPathI][()].squeeze()})
                # and ISigma:
                uncertaintiesAvailable = False
                maskAvailable = False
                if f"{signalLabel}_uncertainty" in h5f[sigPath].attrs:
                    uncLabel = objBytesToStr(h5f[sigPath].attrs[f"{signalLabel}_uncertainty"])
                    uncertaintiesAvailable = True
                elif "uncertainties" in h5f[sigPathI].attrs:
                    uncLabel = objBytesToStr(h5f[sigPathI].attrs["uncertainties"])
                    uncertaintiesAvailable = True
                else:
                    # some default:
                    self.rawData.update({"ISigma": self.rawData["I"] * 0.001})
                if "mask" in h5f[sigPath].attrs:
                    maskLabel = objBytesToStr(h5f[sigPath].attrs["mask"])
                    maskAvailable = True

                if uncertaintiesAvailable:  # load them
                    # if isinstance(uncLabel, bytes): uncLabel = uncLabel.decode("utf-8")
                    sigPathISigma = sigPath + uncLabel
                    self.rawData.update({"ISigma": h5f[sigPathISigma][()].squeeze()})
                if maskAvailable:  # load them
                    sigPathMask = sigPath + maskLabel
                    self.rawData.update({"mask": h5f[sigPathMask][()].squeeze()})

                # now we have I, we search for Q in the "axes" attribute:
                axesLabel = None
                if "axes" in h5f[sigPath].attrs:
                    axesLabel = "axes"
                elif "I_axes" in h5f[sigPath].attrs:
                    axesLabel = "I_axes"
                assert (
                    axesLabel is not None
                ), "could not find axes label associated with dataset signal in HDF5 file"
                axesObj = objBytesToStr(h5f[sigPath].attrs[axesLabel])
                # q can have many names in here:
                ques = ["q", "Q"]  # q options
                # ques = ['q', 'Q', b'q', b'Q'] # q options
                # check where we may have a match:
                quesTest = [i in axesObj for i in ques]
                # assert one of them is there
                assert any(quesTest), "q (or Q) not found in signal axes description"
                # this is what our q label is in the axes attribute:
                qLabel = ques[np.argwhere(np.array(quesTest)).squeeze()]
                # if isinstance(qLabel, bytes): qLabel = qLabel.decode("utf-8")
                self.rawData.update({"Q": h5f[sigPath + qLabel][()].squeeze()})
        if self.rawData["Q"].ndim > 1:
            # we have a three-dimensional Q array, in the order of [dim, y, x]
            # find out which dimensions are nonzero (the remainder is Qz):
            QxyIndices = np.argwhere(
                [self.rawData["Q"][i, :, :].any() for i in range(self.rawData["Q"].shape[0])]
            )
            self.rawData["Q"] = self.rawData["Q"][QxyIndices, :, :].squeeze()
            self.rawData["Qx"] = self.rawData["Q"][QxyIndices[1], :, :].squeeze()
            self.rawData["Qy"] = self.rawData["Q"][QxyIndices[0], :, :].squeeze()
            self.rawData2D = self.rawData.copy()  # intermediate storage of original data
            # but we also need to prepare a Pandas-compatible list-format data
            del self.rawData["Q"]
            for key in self.rawData.keys():
                self.rawData[key] = self.rawData[key].flatten()

        self.rawData = pandas.DataFrame(data=self.rawData)
        self.prepare()

    def is2D(self) -> bool:
        return self.rawData2D is not None

    def clip(self) -> None:
        assert False, "defined in 1D and 2D subclasses"
        pass

    def omit(self) -> None:
        assert False, "defined in the 1D and (maybe) 2D subclasses"
        pass

    def reBin(self) -> None:
        assert False, "defined in 1D and 2D subclasses"
        pass

    def prepare(self) -> None:
        """runs the clipping and binning (in that order), populates clippedData and binnedData"""
        self.clip()
        self.omit()
        if self.nbins != 0:
            self.reBin()
        else:
            self.binnedData = self.clippedData.copy()
        self.linkMeasData()

    def store(self, filename: Path, path: Optional[PurePosixPath] = None) -> None:
        """stores the settings in an output file (HDF5)"""
        if path is None:
            path = self.resultIndex.nxsEntryPoint / "mcdata"
        print(f"storing in {filename} at {path}")
        pairs = [(key, getattr(self, key, None)) for key in self.storeKeys]
        if pairs is None:
            print("I don't understand, there's supposed to be a list of pairs here.. ")
        if pairs is not None:
            storeKVPairs(
                filename=filename,
                path=path,
                pairs = pairs
            )

    def load(self, filename: Path, path: Optional[PurePosixPath] = None) -> None:
        # this loads the data from a prior McSAS run. 
        if path is None:
            path = self.resultIndex.nxsEntryPoint / "mcdata"
        for key, datatype in self.loadKeys.items():
            value = loadKV(filename, path / key, datatype=datatype, default=None, dbg=True)
            if key == "csvargs":
                self.csvargs.update(value)
            else:
                setattr(self, key, value)
        # load rawData if availalbe in the result file
        try: 
            self.rawData=pandas.DataFrame(data=loadKV(filename, path/'rawData', datatype='dict'))
        except AttributeError:
            logging.warning(f'could not load rawData from {filename=}. Are you sure this is a prior McSAS run? Attempting to load original data....')
            self.from_file()  # try loading the data from the original file
        self.prepare()

