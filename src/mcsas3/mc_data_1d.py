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
    canonical_stage_from_legacy_link,
    legacy_dataframe_from_bundle,
    legacy_measdata_from_bundle,
    set_processing_analysis_stage,
)
from .data_model import ProcessingData
from .mc_data import McData

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
    qNudge = None  # nudge in case of misaligned centers. Applied to measData
    omitQRanges = None  # to skip or omit unwanted data ranges, for example with sharp XRD peaks

    def __init__(
        self,
        df: Optional[pandas.DataFrame] = None,
        loadFromFile: Optional[Path] = None,
        resultIndex: int = 1,
        **kwargs: dict,
    ) -> None:
        super().__init__(loadFromFile=loadFromFile, resultIndex=resultIndex, **kwargs)
        self.csvargs = self.csvargs or {
            "sep": r"\s+",
            "header": None,
            "names": ["Q", "I", "ISigma"],
        }
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
        # link measData to the requested value

    def _ensure_processing_data(self) -> None:
        if self.processingData is None:
            self.processingData = ProcessingData()

    def _legacy_stage_view(self, stage_name: str, source_frame: Optional[pandas.DataFrame] = None) -> pandas.DataFrame:
        stage_frame = legacy_dataframe_from_bundle(self.processingData[stage_name])
        if source_frame is None:
            source_frame = getattr(self, ATTR_BY_STAGE[stage_name], None)
        if source_frame is None:
            return stage_frame

        extra_columns = [column for column in source_frame.columns if column not in stage_frame.columns]
        for column in extra_columns:
            stage_frame[column] = source_frame[column].to_numpy(copy=True)

        ordered_columns = list(source_frame.columns) + [
            column for column in stage_frame.columns if column not in source_frame.columns
        ]
        return stage_frame.loc[:, ordered_columns]

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
        compatibility_view = self._legacy_stage_view(stage_name, source_frame=local_frame)
        setattr(self, ATTR_BY_STAGE[stage_name], compatibility_view)
        self._mark_legacy_data_canonical()
        return compatibility_view

    def _sync_compatibility_views_from_processing_data(self) -> None:
        for stage_name, attr_name in ATTR_BY_STAGE.items():
            if self.processingData is not None and stage_name in self.processingData:
                setattr(self, attr_name, self._legacy_stage_view(stage_name))
            else:
                setattr(self, attr_name, None)

    def _get_stage_dataframe(self, stage_name: str) -> pandas.DataFrame:
        if self.processingData is not None and stage_name in self.processingData:
            compatibility_view = self._legacy_stage_view(stage_name)
            setattr(self, ATTR_BY_STAGE[stage_name], compatibility_view)
            return compatibility_view

        compatibility_view = getattr(self, ATTR_BY_STAGE[stage_name], None)
        assert compatibility_view is not None, f"No data available for stage '{stage_name}'"
        return compatibility_view

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
        self.clip()
        self.omit()
        if self.nbins != 0:
            self.reBin()
        else:
            self._set_stage_dataframe(STAGE_BINNED, self._get_stage_dataframe(STAGE_CLIPPED))
        self.linkMeasData()

    def linkMeasData(self, measDataLink: Optional[str] = None) -> None:  # measDataLink:str|None
        if measDataLink is None:
            stage_name = self.analysisStage
        else:
            stage_name = canonical_stage_from_legacy_link(measDataLink)
            self.analysisStage = stage_name
        self._seed_processing_from_raw_if_needed()
        assert stage_name in self.processingData, f"Requested measurement stage '{stage_name}' is not available"
        set_processing_analysis_stage(self.processingData, stage_name)
        self.measData = legacy_measdata_from_bundle(self.processingData[stage_name], q_nudge=self.qNudge)

    def from_pdh(self, filename: Path) -> None:
        """reads from a PDH file, re-uses Ingo Bressler's code from the notebook example"""
        assert filename is not None, "from_pdh requires an input filename of a PDH file"
        skiprows, nrows = 5, -1
        with open(filename) as fd:
            nrows = [ln for ln, line in enumerate(fd.readlines()) if line.startswith("<?xml")]
        csvargs = self.csvargs.copy()
        csvargs.update({"skiprows": skiprows, "nrows": nrows[0] - skiprows})
        self.from_pandas(pandas.read_csv(filename, **csvargs))

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
        self.from_pandas(pandas.read_csv(filename, **localCsvargs))

    def clip(self) -> None:
        raw_data = self._get_stage_dataframe(STAGE_RAW)
        clipped_data = raw_data.query(f"{self.dataRange[0]} <= Q < {self.dataRange[1]}").dropna().copy()
        assert len(clipped_data) != 0, "Data clipping range too small, no datapoints found!"
        self._set_stage_dataframe(STAGE_CLIPPED, clipped_data)

    def omit(self) -> None:
        """This can skip/omit unwanted ranges of data (for example a data range with an unwanted
        XRD peak in it). Requires an "omitQRanges" list of [[qmin, qmax]]-data ranges to omit.
        """

        # nothng to do:
        if self.omitQRanges is None:
            return
        assert isinstance(self.omitQRanges, list), "omitQRanges must be a list"
        clipped_data = self._get_stage_dataframe(STAGE_CLIPPED).copy()
        for omitQRange in self.omitQRanges:
            assert len(omitQRange) == 2, "each omitQRange must contain two elements: a minimum and maximum value"
            # we drop the matches:
            clipped_data.drop(
                clipped_data.query(f"{omitQRange[0]} <= Q < {omitQRange[1]}").index,
                inplace=True,
            )
        self._set_stage_dataframe(STAGE_CLIPPED, clipped_data)

    def reBin(self, nbins: Optional[int] = None, IEmin: Optional[float] = None, QEMin: float = 0.01) -> None:
        """Unweighted rebinning funcionality with extended uncertainty estimation,
        adapted from the datamerge methods, as implemented in Paulina's notebook of spring 2020
        """
        if nbins is None:
            nbins = self.nbins

        if IEmin is None:
            IEmin = self.IEmin

        clipped_data = self._get_stage_dataframe(STAGE_CLIPPED)

        qMin = clipped_data.Q.dropna().min()
        qMax = clipped_data.Q.dropna().max()

        # prepare bin edges:
        binEdges = np.logspace(np.log10(qMin), np.log10(qMax), num=nbins + 1)
        binDat = pandas.DataFrame(
            data={
                "Q": np.full(nbins, np.nan),  # mean Q
                "I": np.full(nbins, np.nan),  # mean intensity
                "IStd": np.full(nbins, np.nan),  # standard deviation of the mean intensity
                "ISEM": np.full(
                    nbins, np.nan
                ),  # standard error on mean of the mean intensity (maybe, but weighted is hard.)
                "IError": np.full(nbins, np.nan),  # Propagated errors of the intensity
                "ISigma": np.full(nbins, np.nan),  # Combined error estimate of the intensity
                "QStd": np.full(nbins, np.nan),  # standard deviation of the mean Q
                "QSEM": np.full(nbins, np.nan),  # standard error on the mean Q
                "QError": np.full(nbins, np.nan),  # Propagated errors on the mean Q
                "QSigma": np.full(nbins, np.nan),  # Combined error estimate on the mean Q
            }
        )

        # add a little to the end to ensure the last datapoint is captured:
        binEdges[-1] = binEdges[-1] + 1e-3 * (binEdges[-1] - binEdges[-2])

        # now do the binning per bin.
        for binN in range(len(binEdges) - 1):
            dfRange = clipped_data.query("{} <= Q < {}".format(binEdges[binN], binEdges[binN + 1])).copy()
            if len(dfRange) == 0:
                # no datapoints in the range
                pass

            elif len(dfRange) == 1:
                # only one datapoint in the range
                # might not be necessary to do this..
                # can't do stats on this:
                # FutureWarning fix:
                binDat.loc[binN, "Q"] = float(dfRange.Q.iloc[0])
                binDat.loc[binN, "QStd"] = binDat.loc[binN, "Q"] * QEMin
                binDat.loc[binN, "QSEM"] = binDat.loc[binN, "Q"] * QEMin
                binDat.loc[binN, "QError"] = binDat.loc[binN, "Q"] * QEMin

                binDat.loc[binN, "I"] = float(dfRange.I.iloc[0])
                binDat.loc[binN, "IStd"] = float(dfRange.ISigma.iloc[0])
                binDat.loc[binN, "ISEM"] = float(dfRange.ISigma.iloc[0])
                binDat.loc[binN, "IError"] = float(dfRange.ISigma.iloc[0])
                binDat.loc[binN, "ISigma"] = np.max([binDat.loc[binN, "ISEM"], float(dfRange.I.iloc[0]) * IEmin])

                if "QSigma" in dfRange.keys():
                    binDat.loc[binN, "QError"] = float(dfRange.QSigma.iloc[0])
                    binDat.loc[binN, "QStd"] = float(dfRange.QSigma.iloc[0])
                    binDat.loc[binN, "QSEM"] = float(dfRange.QSigma.iloc[0])

                binDat.loc[binN, "QSigma"] = np.max(
                    [
                        binDat.loc[binN, "QSEM"],
                        binDat.loc[binN, "QError"],
                        binDat.loc[binN, "Q"] * QEMin,
                    ]
                )

                # binDat.QSigma.loc[binN] = np.max(
                #     [float(binDat.QSEM.loc[binN]), float(dfRange.Q.iloc[0]) * QEMin]
                # )

            else:
                # multiple datapoints in the range
                # fixing FutureWarning
                binDat.loc[binN, "I"] = dfRange.I.mean(skipna=True)
                binDat.loc[binN, "IStd"] = dfRange.I.std(ddof=1, skipna=True)
                binDat.loc[binN, "ISEM"] = dfRange.I.sem(ddof=1, skipna=True)
                binDat.loc[binN, "IError"] = np.sqrt(((dfRange.ISigma) ** 2).sum()) / len(dfRange)
                binDat.loc[binN, "ISigma"] = np.max(
                    [
                        binDat.loc[binN, "ISEM"],
                        binDat.loc[binN, "IError"],
                        binDat.loc[binN, "I"] * IEmin,
                    ]
                )

                binDat.loc[binN, "Q"] = dfRange.Q.mean(skipna=True)
                binDat.loc[binN, "QStd"] = dfRange.Q.std(ddof=1, skipna=True)
                binDat.loc[binN, "QSEM"] = dfRange.Q.sem(ddof=1, skipna=True)
                binDat.loc[binN, "QError"] = binDat.loc[binN, "Q"] * QEMin

                if "QSigma" in dfRange.keys():
                    binDat.loc[binN, "QError"] = np.sqrt(((dfRange.QSigma) ** 2).sum()) / len(dfRange)

                binDat.loc[binN, "QSigma"] = np.max(
                    [
                        binDat.loc[binN, "QSEM"],
                        binDat.loc[binN, "QError"],
                        binDat.loc[binN, "Q"] * QEMin,
                    ]
                )

        # remove empty bins
        binDat.dropna(thresh=4, inplace=True)
        self._set_stage_dataframe(STAGE_BINNED, binDat)
