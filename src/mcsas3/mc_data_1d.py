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

    @property
    def rawData(self) -> Optional[pandas.DataFrame]:
        if self.processingData is not None and STAGE_RAW in self.processingData:
            return legacy_dataframe_from_bundle(self.processingData[STAGE_RAW])
        return None

    @property
    def clippedData(self) -> Optional[pandas.DataFrame]:
        if self.processingData is not None and STAGE_CLIPPED in self.processingData:
            return legacy_dataframe_from_bundle(self.processingData[STAGE_CLIPPED])
        return None

    @property
    def binnedData(self) -> Optional[pandas.DataFrame]:
        if self.processingData is not None and STAGE_BINNED in self.processingData:
            return legacy_dataframe_from_bundle(self.processingData[STAGE_BINNED])
        return None

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
        self._mark_legacy_data_canonical()
        return self._legacy_stage_view(stage_name)

    def _apply_prepared_stage(self, stage_name: str, prepared_stage: Prepared1DStage) -> pandas.DataFrame:
        self._ensure_processing_data()
        self.processingData[stage_name] = prepared_stage.bundle
        self._mark_legacy_data_canonical()
        return self._legacy_stage_view(stage_name)

    def _require_raw_stage(self) -> None:
        if self.processingData is None or STAGE_RAW not in self.processingData:
            raise ValueError("McData1D requires a canonical raw stage. Use from_pandas(), from_file(), or load().")

    def prepare(self) -> None:
        self._require_raw_stage()
        prepared = prepare_1d_bundle(
            self.processingData[STAGE_RAW],
            data_range=self.dataRange,
            omit_q_ranges=self.omitQRanges,
            nbins=self.nbins,
            iemin=self.IEmin,
        )
        self._apply_prepared_stage(STAGE_CLIPPED, prepared.clipped)
        self._apply_prepared_stage(STAGE_BINNED, prepared.binned)

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
        self._require_raw_stage()
        prepared = clip_1d_bundle(self.processingData[STAGE_RAW], data_range=self.dataRange)
        self._apply_prepared_stage(STAGE_CLIPPED, prepared)

    def omit(self) -> None:
        """This can skip/omit unwanted ranges of data (for example a data range with an unwanted
        XRD peak in it). Requires an "omitQRanges" list of [[qmin, qmax]]-data ranges to omit.
        """
        self._require_raw_stage()
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
        self._require_raw_stage()
        if STAGE_CLIPPED not in self.processingData:
            self.clip()
        prepared = rebin_1d_bundle(
            self.processingData[STAGE_CLIPPED],
            nbins=nbins,
            iemin=IEmin,
            qemin=QEMin,
        )
        self._apply_prepared_stage(STAGE_BINNED, prepared)
