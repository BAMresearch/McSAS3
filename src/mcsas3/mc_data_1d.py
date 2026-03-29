# src/mcsas3/mcdata_1d.py

from pathlib import Path
from typing import Optional

import numpy as np
import pandas

from .data_adapters import (
    STAGE_BINNED,
    STAGE_CLIPPED,
    STAGE_RAW,
    bundle_from_1d_dataframe,
    legacy_dataframe_from_bundle,
)
from .data_model import ProcessingData
from .ingestion import DEFAULT_1D_CSVARGS, Loaded1DData, load_1d_dataframe_from_file
from .mc_data import McData
from .preprocessing import (
    Prepared1DStage,
    clip_1d_bundle,
    omit_1d_bundle,
    prepare_1d_bundle,
    rebin_1d_bundle,
)

STAGE_BY_LINK = {
    "rawData": STAGE_RAW,
    "clippedData": STAGE_CLIPPED,
    "binnedData": STAGE_BINNED,
}
ATTR_BY_STAGE = {stage: attr for attr, stage in STAGE_BY_LINK.items()}


class McData1D(McData):
    """subclass for managing 1D datasets."""

    csvargs = None  # default for 1D, overwritten in subclass
    dataRange = None  # min-max for data range to fit
    qNudge = None  # nudge used when deriving flattened analysis-data compatibility views
    omitQRanges = None  # to skip or omit unwanted data ranges, for example with sharp XRD peaks

    def __init__(
        self,
        df: Optional[pandas.DataFrame] = None,
        loadFromFile: Optional[Path] = None,
        resultIndex: int = 1,
        **kwargs: dict,
    ) -> None:
        super().__init__(loadFromFile=loadFromFile, resultIndex=resultIndex, **kwargs)
        self.csvargs = self.csvargs or dict(DEFAULT_1D_CSVARGS)
        if self.dataRange is None:
            self.dataRange = [-np.inf, np.inf]
        if self.qNudge is None:
            self.qNudge = 0
        self.processKwargs(**kwargs)

        # load from dataframe if provided
        if df is not None:
            self.loader = "from_pandas"  # TODO: need to handle this on restore state
            self.from_pandas(df)
        elif loadFromFile is not None:
            pass  # do not try loading the file, the information is already there.
        elif self.filename is not None:  # filename has been set
            self.from_file(self.filename)

    def _ensure_processing_data(self) -> None:
        if self.processingData is None:
            self.processingData = ProcessingData()

    def _ingest_loaded_data(self, loaded: Loaded1DData) -> None:
        self.loader = loaded.loader
        if self.sourceQUnits is None and loaded.source_q_units is not None:
            self.sourceQUnits = loaded.source_q_units
        if self.sourceIntensityUnits is None and loaded.source_intensity_units is not None:
            self.sourceIntensityUnits = loaded.source_intensity_units
        self.from_pandas(loaded.frame)

    def _legacy_stage_view(self, stage_name: str) -> pandas.DataFrame:
        return legacy_dataframe_from_bundle(self.processingData[stage_name])

    def _set_stage_dataframe(
        self,
        stage_name: str,
        frame: pandas.DataFrame,
        *,
        source_q_units=None,
        source_intensity_units=None,
    ) -> pandas.DataFrame:
        local_frame = frame.copy()
        self._ensure_processing_data()
        self.processingData[stage_name] = bundle_from_1d_dataframe(
            local_frame,
            q_units=self._canonical_q_units(),
            intensity_units=self._canonical_intensity_units(),
            source_q_units=source_q_units,
            source_intensity_units=source_intensity_units,
        )
        compatibility_view = self._legacy_stage_view(stage_name)
        setattr(self, ATTR_BY_STAGE[stage_name], compatibility_view)
        self._mark_legacy_data_canonical()
        return compatibility_view

    def _sync_compatibility_views_from_processing_data(self) -> None:
        for stage_name, attr_name in ATTR_BY_STAGE.items():
            if self.processingData is not None and stage_name in self.processingData:
                setattr(self, attr_name, self._legacy_stage_view(stage_name))
            else:
                setattr(self, attr_name, None)

    def _apply_prepared_stage(self, stage_name: str, prepared_stage: Prepared1DStage) -> pandas.DataFrame:
        self._ensure_processing_data()
        self.processingData[stage_name] = prepared_stage.bundle
        setattr(self, ATTR_BY_STAGE[stage_name], self._legacy_stage_view(stage_name))
        self._mark_legacy_data_canonical()
        return getattr(self, ATTR_BY_STAGE[stage_name])

    def _seed_processing_from_raw_if_needed(self) -> None:
        if self.processingData is not None and STAGE_RAW in self.processingData:
            return
        assert self.rawData is not None, "rawData must exist before processing stages can be built"
        self.processingData = ProcessingData()
        self._set_stage_dataframe(
            STAGE_RAW,
            self.rawData,
            source_q_units=self._source_q_units_for_ingest(),
            source_intensity_units=self._source_intensity_units_for_ingest(),
        )

    def prepare(self) -> None:
        self._seed_processing_from_raw_if_needed()
        prepared = prepare_1d_bundle(
            self.processingData[STAGE_RAW],
            data_range=self.dataRange,
            omit_q_ranges=self.omitQRanges,
            nbins=self.nbins,
            iemin=self.IEmin,
        )
        self._apply_prepared_stage(STAGE_CLIPPED, prepared.clipped)
        self._apply_prepared_stage(STAGE_BINNED, prepared.binned)

    def from_pdh(self, filename: Path) -> None:
        """reads from a PDH file, re-uses Ingo Bressler's code from the notebook example"""
        assert filename is not None, "from_pdh requires an input filename of a PDH file"
        loaded = load_1d_dataframe_from_file(filename, loader="from_pdh", csvargs=self.csvargs)
        self._ingest_loaded_data(loaded)

    def from_pandas(self, df: pandas.DataFrame) -> None:
        """uses a dataframe as input, should contain 'Q', 'I', and 'ISigma'"""
        assert isinstance(df, pandas.DataFrame), "from_pandas requires a pandas DataFrame with 'Q', 'I', and 'ISigma'"
        # maybe add a check for the keys:
        assert all([key in df.keys() for key in ["Q", "I", "ISigma"]]), (
            "from_pandas requires the dataframe to contain 'Q', 'I', and 'ISigma'"
        )
        assert all([df[key].dtype.kind in "f" for key in ["Q", "I", "ISigma"]]), (
            "data could not be read correctly. If csv, did you supply the right csvargs?"
        )
        self._legacyDataInCanonicalUnits = False
        self.processingData = ProcessingData()
        self._set_stage_dataframe(
            STAGE_RAW,
            df,
            source_q_units=self._source_q_units_for_ingest(),
            source_intensity_units=self._source_intensity_units_for_ingest(),
        )
        self.prepare()

    def from_csv(self, filename: Path, csvargs: dict = {}) -> None:
        """reads from a three-column csv file, takes pandas from_csv arguments"""
        assert filename is not None, "from_csv requires an input filename of a csv file"
        localCsvargs = self.csvargs.copy()
        localCsvargs.update(csvargs)
        loaded = load_1d_dataframe_from_file(filename, loader="from_csv", csvargs=localCsvargs)
        self._ingest_loaded_data(loaded)

    def from_nexus(self, filename: Path) -> None:
        """reads a 1D NeXus/NXsas dataset into the canonical preprocessing path"""
        assert filename is not None, "from_nexus requires an input filename of a NeXus file"
        loaded = load_1d_dataframe_from_file(filename, loader="from_nexus", path_dict=self.pathDict)
        self._ingest_loaded_data(loaded)

    def from_file(self, filename: Optional[Path] = None) -> None:
        self.processingData = None
        self._legacyDataInCanonicalUnits = False
        if filename is None:
            assert self.filename is not None, "at least filename or self.filename must be set for loading from file"
        else:
            self.filename = Path(filename)
        self.filename = Path(self.filename)

        loaded = load_1d_dataframe_from_file(
            self.filename,
            loader=self.loader,
            csvargs=self.csvargs,
            path_dict=self.pathDict,
        )
        self._ingest_loaded_data(loaded)

    def clip(self) -> None:
        self._seed_processing_from_raw_if_needed()
        prepared = clip_1d_bundle(self.processingData[STAGE_RAW], data_range=self.dataRange)
        self._apply_prepared_stage(STAGE_CLIPPED, prepared)

    def omit(self) -> None:
        """This can skip/omit unwanted ranges of data (for example a data range with an unwanted
        XRD peak in it). Requires an "omitQRanges" list of [[qmin, qmax]]-data ranges to omit.
        """
        self._seed_processing_from_raw_if_needed()
        if STAGE_CLIPPED not in self.processingData:
            self.clip()
        prepared = omit_1d_bundle(
            self.processingData[STAGE_CLIPPED],
            omit_q_ranges=self.omitQRanges,
        )
        self._apply_prepared_stage(STAGE_CLIPPED, prepared)

    def reBin(self, nbins: Optional[int] = None, IEmin: Optional[float] = None, QEMin: float = 0.01) -> None:
        if nbins is None:
            nbins = self.nbins

        if IEmin is None:
            IEmin = self.IEmin
        self._seed_processing_from_raw_if_needed()
        if STAGE_CLIPPED not in self.processingData:
            self.clip()
        prepared = rebin_1d_bundle(
            self.processingData[STAGE_CLIPPED],
            nbins=nbins,
            iemin=IEmin,
            qemin=QEMin,
        )
        self._apply_prepared_stage(STAGE_BINNED, prepared)
