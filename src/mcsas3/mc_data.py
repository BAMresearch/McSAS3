# src/mcsas3/mcdata.py

from pathlib import Path, PurePosixPath
from typing import List, Optional

import attrs
import pandas

from mcsas3.mc_hdf import (
    PROCESSING_DATA_GROUP,
    ResultIndex,
    loadKV,
    loadProcessingData,
    storeKVPairs,
    storeProcessingData,
)

from .data_adapters import (
    CANONICAL_STAGE_NAMES,
    DEFAULT_ANALYSIS_STAGE,
    DEFAULT_INTENSITY_UNITS,
    DEFAULT_Q_UNITS,
    get_processing_analysis_stage,
    normalize_analysis_stage,
    selected_bundle_from_processing,
    set_processing_analysis_stage,
)

# todo use attrs to @define a McData dataclass


@attrs.define
class McData:
    """
    A simple base class for a data carrier object that can load from a range of sources,
    and do rebinning for too large datasets.
    This is inherited by the McData1D and McData2D classes intended for actual use.
    """

    filename: Optional[Path] = attrs.field(
        default=None, validator=attrs.validators.optional(attrs.validators.instance_of(Path))
    )
    _outputFilename: Optional[Path] = attrs.field(
        default=None, validator=attrs.validators.optional(attrs.validators.instance_of(Path))
    )
    loader: Optional[str] = attrs.field(
        default=None, validator=attrs.validators.optional(attrs.validators.instance_of(str))
    )
    processingData: Optional[object] = attrs.field(default=None)
    _analysisStage: str = attrs.field(
        default=DEFAULT_ANALYSIS_STAGE,
        validator=attrs.validators.in_(CANONICAL_STAGE_NAMES),
    )
    dataRange: Optional[list] = attrs.field(default=None)
    nbins: int = attrs.field(default=100, validator=attrs.validators.instance_of(int))
    IEmin: float = attrs.field(default=0.01, validator=attrs.validators.instance_of(float))
    pathDict: Optional[dict] = attrs.field(default=None)
    binning: str = attrs.field(default="logarithmic", validator=attrs.validators.in_(["logarithmic"]))
    csvargs: dict = attrs.field(factory=dict)
    sourceQUnits: Optional[object] = attrs.field(default=None)
    sourceIntensityUnits: Optional[object] = attrs.field(default=None)
    qNudge: Optional[float | List] = attrs.field(
        default=None
    )  # , validator=attrs.validators.optional(attrs.validators.instance_of(float)))
    omitQRanges: Optional[list] = attrs.field(default=None)
    resultIndex: ResultIndex = attrs.field(default=ResultIndex(1), validator=attrs.validators.instance_of(ResultIndex))

    storeKeys = [  # keys to store in an HDF5 output file
        "filename",
        "analysisStage",
        "nbins",
        "IEmin",
        "binning",
        "dataRange",
        "pathDict",
        "csvargs",
        "loader",
        "sourceQUnits",
        "sourceIntensityUnits",
        "qNudge",
        "omitQRanges",
    ]
    loadKeys = {  # keys to store in an HDF5 output file, values are types to cast to using _HDFLoadKV.
        "filename": Path,
        "analysisStage": "str",
        "nbins": int,
        "IEmin": float,
        "binning": "str",
        "dataRange": None,  # not sure what this is.. array?
        "csvargs": "dict",
        "loader": "str",
        "sourceQUnits": "str",
        "sourceIntensityUnits": "str",
        "qNudge": None,
        "omitQRanges": list,  # not sure if this works?
    }
    kwargAliases = {
        "QUnits": "sourceQUnits",
        "IUnits": "sourceIntensityUnits",
        "Q_units": "sourceQUnits",
        "I_units": "sourceIntensityUnits",
    }

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
        self.processingData = None  # canonical data stages, introduced during the MoDaCor migration
        self._analysisStage = DEFAULT_ANALYSIS_STAGE
        self.dataRange = None  # min-max for data range to fit. overwritten in subclass
        self.nbins = 100  # default, set to zero for no rebinning
        self.IEmin = 0.01  # default minimum relative uncertainty on the intensity.
        self.pathDict = None  # for loading HDF5 files without pointers to the data
        self.binning = "logarithmic"  # the only option that makes sense
        self.csvargs = {}  # overwritten in subclass
        self.sourceQUnits = None  # source units declared or detected at ingestion time
        self.sourceIntensityUnits = None  # source units declared or detected at ingestion time
        self.qNudge = 0  # can adjust/offset the q values in case of misaligned q vector,
        # in particular visible in 2D data...
        self.omitQRanges = None  # to skip or omit unwanted data ranges, for example with sharp
        # XRD peaks, must be a list of [[qmin, qmax], ...] pairs
        self._legacyDataInCanonicalUnits = False

        # make sure we store and read from the right place.
        self.resultIndex = ResultIndex(resultIndex)  # defines the HDF5 root path

        if loadFromFile is not None:
            self.load(loadFromFile)

    def processKwargs(self, **kwargs: dict) -> None:
        normalized_kwargs = {}
        for key, value in kwargs.items():
            if key == "analysisStage":
                self.analysisStage = value
                continue
            normalized_key = self.kwargAliases.get(key, key)
            if normalized_key in normalized_kwargs:
                previous_value = normalized_kwargs[normalized_key]
                if str(previous_value) != str(value):
                    raise ValueError(
                        f"Conflicting configuration values provided for '{normalized_key}': "
                        f"{previous_value!r} and {value!r}."
                    )
                continue
            normalized_kwargs[normalized_key] = value

        for key, value in normalized_kwargs.items():
            assert key in self.storeKeys, "Key {} is not a valid option".format(key)
            setattr(self, key, value)

    @property
    def analysisStage(self) -> str:
        return self._analysisStage

    @analysisStage.setter
    def analysisStage(self, stage_name: str) -> None:
        normalized_stage = normalize_analysis_stage(stage_name)
        self._analysisStage = normalized_stage
        if self.processingData is not None:
            set_processing_analysis_stage(self.processingData, normalized_stage)

    def _mark_legacy_data_canonical(self) -> None:
        self._legacyDataInCanonicalUnits = True

    def _source_q_units_for_ingest(self):
        if self._legacyDataInCanonicalUnits:
            return None
        return self.sourceQUnits

    def _source_intensity_units_for_ingest(self):
        if self._legacyDataInCanonicalUnits:
            return None
        return self.sourceIntensityUnits

    def _canonical_q_units(self):
        return DEFAULT_Q_UNITS

    def _canonical_intensity_units(self):
        return DEFAULT_INTENSITY_UNITS

    def _sync_compatibility_views_from_processing_data(self) -> None:
        """Populate legacy compatibility views from canonical processing data."""
        return None

    def from_file(self, filename: Optional[Path] = None) -> None:
        raise NotImplementedError("McData subclasses must implement from_file().")

    def from_pandas(self, df: pandas.DataFrame = None) -> None:
        raise NotImplementedError("McData subclasses must implement from_pandas().")

    def from_csv(self, filename: Path = None, csvargs=None) -> None:
        raise NotImplementedError("McData subclasses must implement from_csv().")

    def from_pdh(self, filename: Path = None) -> None:
        raise NotImplementedError("McData1D implements from_pdh(); the base McData carrier does not.")

    def from_nexus(self, filename: Optional[Path] = None) -> None:
        raise NotImplementedError("McData subclasses must implement from_nexus().")

    def is2D(self) -> bool:
        return self.rawData2D is not None

    def clip(self) -> None:
        raise NotImplementedError("McData subclasses must implement clip().")

    def omit(self) -> None:
        raise NotImplementedError("McData subclasses must implement omit().")

    def reBin(self) -> None:
        raise NotImplementedError("McData subclasses must implement reBin().")

    def prepare(self) -> None:
        raise NotImplementedError("McData subclasses must implement prepare().")

    def to_processing_data(self):
        if self.processingData is None or len(self.processingData) == 0:
            raise ValueError("McData requires canonical processingData before it can expose ProcessingData views.")

        set_processing_analysis_stage(self.processingData, self.analysisStage)
        return self.processingData

    def to_analysis_bundle(self):
        processing = self.to_processing_data()
        return selected_bundle_from_processing(processing, stage_name=self.analysisStage)

    def store(self, filename: Path, path: Optional[PurePosixPath] = None) -> None:
        """stores the settings in an output file (HDF5)"""
        if path is None:
            path = self.resultIndex.nxsEntryPoint / "mcdata"
        processing = self.to_processing_data()
        storeProcessingData(filename=filename, path=path / PROCESSING_DATA_GROUP, processing=processing)
        pairs = [(key, getattr(self, key, None)) for key in self.storeKeys]
        storeKVPairs(filename=filename, path=path, pairs=pairs)

    def load(self, filename: Path, path: Optional[PurePosixPath] = None) -> None:
        # this loads the data from a prior McSAS run.
        self.processingData = None
        if path is None:
            path = self.resultIndex.nxsEntryPoint / "mcdata"
        for key, datatype in self.loadKeys.items():
            value = loadKV(filename, path / key, datatype=datatype, default=None, dbg=True)
            if key == "csvargs":
                if value is not None:
                    self.csvargs.update(value)
            else:
                if value is not None:
                    setattr(self, key, value)
        loaded_processing = loadProcessingData(filename, path / PROCESSING_DATA_GROUP, default=None)
        if loaded_processing is None:
            raise ValueError(
                f"Result file {filename} does not contain canonical processing data at {path / PROCESSING_DATA_GROUP}."
            )

        self.processingData = loaded_processing
        self._legacyDataInCanonicalUnits = True
        self.analysisStage = get_processing_analysis_stage(loaded_processing)
        self._sync_compatibility_views_from_processing_data()
