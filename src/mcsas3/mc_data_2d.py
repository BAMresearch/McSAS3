from pathlib import Path
from typing import Optional

import numpy as np
import pandas

from .data_adapters import (
    STAGE_BINNED,
    STAGE_CLIPPED,
    STAGE_RAW,
    bundle_from_2d_stage,
    canonical_stage_from_legacy_link,
    legacy_2d_stage_from_bundle,
    legacy_dataframe_from_bundle,
    legacy_measdata_from_bundle,
    legacy_rawdata2d_from_bundle,
    set_processing_analysis_stage,
)
from .data_model import ProcessingData
from .mc_data import McData
from .preprocessing import clip_2d_bundle, omit_2d_bundle, prepare_2d_bundle, rebin_2d_bundle

STAGE_BY_LINK = {
    "rawData": STAGE_RAW,
    "clippedData": STAGE_CLIPPED,
    "binnedData": STAGE_BINNED,
}


class McData2D(McData):
    """Subclass for managing 2D datasets.
    Copied from 1D dataset handler, not every functionality is enabled"""

    storeKeys = McData.storeKeys + ["orthoQ1Range", "orthoQ0Range"]
    loadKeys = dict(McData.loadKeys, orthoQ1Range=None, orthoQ0Range=None)

    csvargs: dict = {
        "sep": r"\s+",
        "header": None,
        "names": ["Q", "I", "ISigma"],
    }  # default for 1D, overwritten in subclass
    dataRange = [0, np.inf]  # min-max for data range to fit
    orthoQ1Range = [0, np.inf]  # min-max for abs(Qx) in case of square masking
    orthoQ0Range = [0, np.inf]  # min-max for abs(Qy) in case of square masking
    qNudge = [
        0,
        0,
    ]  # nudge in direction 0 and 1 in case of misaligned centers. Applied to measData

    def __init__(self, df=None, loadFromFile=None, resultIndex: int = 1, **kwargs: dict) -> None:
        super().__init__(loadFromFile=loadFromFile, resultIndex=resultIndex, **kwargs)
        self.csvargs = self.csvargs or {}
        if self.dataRange is None:
            self.dataRange = [0, np.inf]
        if getattr(self, "orthoQ1Range", None) is None:
            self.orthoQ1Range = [0, np.inf]
        if getattr(self, "orthoQ0Range", None) is None:
            self.orthoQ0Range = [0, np.inf]
        if self.qNudge is None or np.isscalar(self.qNudge):
            self.qNudge = [0, 0]
        self.processKwargs(**kwargs)

        # load from dataframe if provided
        if df is not None:
            self.loader = "from_pandas"  # TODO: need to handle this on restore state
            self.from_pandas(df)

        elif loadFromFile is not None:
            pass  # do not try loading the file, the information is already there.
        elif self.filename is not None:  # filename has been set
            self.from_file(self.filename)
        # link measData to the requested value

    def _ensure_processing_data(self) -> None:
        if self.processingData is None:
            self.processingData = ProcessingData()

    def _sync_raw_views(self) -> None:
        bundle = self.processingData[STAGE_RAW]
        self.rawData2D = legacy_rawdata2d_from_bundle(bundle)
        self.rawData = legacy_dataframe_from_bundle(bundle)

    def _sync_stage_view(self, stage_name: str) -> dict:
        stage_view = legacy_2d_stage_from_bundle(self.processingData[stage_name])
        setattr(self, "clippedData" if stage_name == STAGE_CLIPPED else "binnedData", stage_view)
        return stage_view

    def _sync_compatibility_views_from_processing_data(self) -> None:
        if self.processingData is not None and STAGE_RAW in self.processingData:
            self._sync_raw_views()
        else:
            self.rawData2D = None
            self.rawData = None

        if self.processingData is not None and STAGE_CLIPPED in self.processingData:
            self._sync_stage_view(STAGE_CLIPPED)
        else:
            self.clippedData = None

        if self.processingData is not None and STAGE_BINNED in self.processingData:
            self._sync_stage_view(STAGE_BINNED)
        else:
            self.binnedData = None

    def _set_stage_bundle(
        self,
        stage_name: str,
        bundle,
        *,
        source_q_units=None,
        source_intensity_units=None,
    ) -> None:
        self._ensure_processing_data()
        if stage_name == STAGE_RAW:
            bundle = bundle_from_2d_stage(
                legacy_rawdata2d_from_bundle(bundle) if "signal" in bundle else bundle,
                q_units=self._canonical_q_units(),
                intensity_units=self._canonical_intensity_units(),
                source_q_units=source_q_units,
                source_intensity_units=source_intensity_units,
            )
        self.processingData[stage_name] = bundle
        if stage_name == STAGE_RAW:
            self._sync_raw_views()
        else:
            self._sync_stage_view(stage_name)
        self._mark_legacy_data_canonical()

    def _seed_processing_from_raw_if_needed(self) -> None:
        if self.processingData is not None and STAGE_RAW in self.processingData:
            self._sync_raw_views()
            return

        assert self.rawData2D is not None, "rawData2D must exist before processing stages can be built"
        self.processingData = ProcessingData()
        self._set_stage_bundle(
            STAGE_RAW,
            self.rawData2D,
            source_q_units=self._source_q_units_for_ingest(),
            source_intensity_units=self._source_intensity_units_for_ingest(),
        )

    def _get_stage_bundle(self, stage_name: str):
        if self.processingData is not None and stage_name in self.processingData:
            if stage_name == STAGE_RAW:
                self._sync_raw_views()
            else:
                self._sync_stage_view(stage_name)
            return self.processingData[stage_name]

        if stage_name == STAGE_RAW:
            self._seed_processing_from_raw_if_needed()
            return self.processingData[STAGE_RAW]

        legacy_stage = self.clippedData if stage_name == STAGE_CLIPPED else self.binnedData
        assert legacy_stage is not None, f"No data available for stage '{stage_name}'"
        bundle = bundle_from_2d_stage(legacy_stage)
        self._set_stage_bundle(stage_name, bundle)
        return bundle

    def _get_stage_view(self, stage_name: str) -> dict:
        if stage_name == STAGE_RAW:
            self._get_stage_bundle(STAGE_RAW)
            return self.rawData2D

        self._get_stage_bundle(stage_name)
        return self.clippedData if stage_name == STAGE_CLIPPED else self.binnedData

    def prepare(self) -> None:
        self._seed_processing_from_raw_if_needed()
        prepared = prepare_2d_bundle(
            self.processingData[STAGE_RAW],
            data_range=self.dataRange,
            ortho_q0_range=self.orthoQ0Range,
            ortho_q1_range=self.orthoQ1Range,
            omit_q_ranges=self.omitQRanges,
            nbins=self.nbins,
            iemin=self.IEmin,
            source_stage=self.rawData2D,
        )
        self._set_stage_bundle(STAGE_CLIPPED, prepared.clipped)
        self._set_stage_bundle(STAGE_BINNED, prepared.binned)
        self.linkMeasData()

    def linkMeasData(self, measDataLink: Optional[str] = None) -> None:
        if measDataLink is None:
            stage_name = self.analysisStage
        else:
            stage_name = canonical_stage_from_legacy_link(measDataLink)
            self.analysisStage = stage_name
        self._seed_processing_from_raw_if_needed()
        assert stage_name in self.processingData, f"Requested measurement stage '{stage_name}' is not available"
        set_processing_analysis_stage(self.processingData, stage_name)
        self.measData = legacy_measdata_from_bundle(self.processingData[stage_name], q_nudge=self.qNudge)

    def from_pandas(self, df: pandas.DataFrame = None) -> None:
        assert False, "2D data from_pandas not implemented yet"
        pass

    def from_csv(self, filename: Path, csvargs: dict = {}) -> None:
        assert False, "2D data from_csv not implemented yet"
        pass

    def clip(self) -> None:
        self._seed_processing_from_raw_if_needed()
        clipped = clip_2d_bundle(
            self.processingData[STAGE_RAW],
            data_range=self.dataRange,
            ortho_q0_range=self.orthoQ0Range,
            ortho_q1_range=self.orthoQ1Range,
            source_stage=self.rawData2D,
        )
        self._set_stage_bundle(STAGE_CLIPPED, clipped)

    def omit(self) -> None:
        """This can skip/omit unwanted ranges of data (for example a data range with an unwanted
        XRD peak in it). Requires an "omitQRanges" list of [[qmin, qmax]]-data ranges to omit."""
        self._seed_processing_from_raw_if_needed()
        if STAGE_CLIPPED not in self.processingData:
            self.clip()
        clipped = omit_2d_bundle(self.processingData[STAGE_CLIPPED], omit_q_ranges=self.omitQRanges)
        self._set_stage_bundle(STAGE_CLIPPED, clipped)

    def reconstruct2D(self, modelI1D: np.ndarray) -> np.ndarray:
        """Reconstructs a masked 2D data array from the (1D) model intensity, skipping the masked
        and clipped pixels (left as NaN). This function can be used to plot the resulting model
        intensity and comparing it with self.clippedData["I2D"].
        """
        # RMI = reconstructedModelI
        clipped_data = self._get_stage_view(STAGE_CLIPPED)
        reconstructed = np.full(clipped_data["I2D"].shape, np.nan)
        reconstructed[np.where(clipped_data["invMask"])] = modelI1D
        return reconstructed

    def reBin(self, nbins: Optional[int] = None, IEmin: float = 0.01, QEMin: float = 0.01) -> None:
        if nbins is None:
            nbins = self.nbins
        self._seed_processing_from_raw_if_needed()
        if STAGE_CLIPPED not in self.processingData:
            self.clip()
        binned = rebin_2d_bundle(self.processingData[STAGE_CLIPPED], nbins=nbins, iemin=IEmin, qemin=QEMin)
        self._set_stage_bundle(STAGE_BINNED, binned)
