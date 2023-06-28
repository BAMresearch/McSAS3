from pathlib import Path
from typing import Optional

import numpy as np
import pandas

from .McData import McData


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
        self.csvargs = {
            "sep": r"\s+",
            "header": None,
            "names": ["Q", "I", "ISigma"],
        }  # default for 1D, overwritten in subclass
        self.dataRange = [-np.inf, np.inf]  # min-max for data range to fit
        self.qNudge = 0  # nudge in case of misaligned centers. Applied to measData
        self.processKwargs(**kwargs)  # redo kwargs in case the reset values have been updated

        # load from dataframe if provided
        if df is not None:
            self.loader = "from_pandas"  # TODO: need to handle this on restore state
            self.from_pandas(df)
        elif loadFromFile is not None:
            pass  # do not try loading the file, the information is already there.
        elif self.filename is not None:  # filename has been set
            self.from_file(self.filename)
        # link measData to the requested value

    def linkMeasData(self, measDataLink: Optional[str] = None) -> None:  # measDataLink:str|None
        if measDataLink is None:
            measDataLink = self.measDataLink
        assert measDataLink in [
            "rawData",
            "clippedData",
            "binnedData",
        ], (
            f"measDataLink value: {measDataLink} not valid. Must be one of 'rawData', 'clippedData'"
            " or 'binnedData'"
        )
        measDataObj = getattr(self, measDataLink)
        self.measData = dict(
            Q=[measDataObj.Q.values + self.qNudge],
            I=measDataObj.I.values,
            ISigma=measDataObj.ISigma.values,
        )

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
        assert isinstance(
            df, pandas.DataFrame
        ), "from_pandas requires a pandas DataFrame with 'Q', 'I', and 'ISigma'"
        # maybe add a check for the keys:
        assert all(
            [key in df.keys() for key in ["Q", "I", "ISigma"]]
        ), "from_pandas requires the dataframe to contain 'Q', 'I', and 'ISigma'"
        assert all(
            [df[key].dtype.kind in "f" for key in ["Q", "I", "ISigma"]]
        ), "data could not be read correctly. If csv, did you supply the right csvargs?"
        self.rawData = df
        self.prepare()

    def from_csv(self, filename: Path, csvargs: dict = {}) -> None:
        """reads from a three-column csv file, takes pandas from_csv arguments"""
        assert filename is not None, "from_csv requires an input filename of a csv file"
        localCsvargs = self.csvargs.copy()
        localCsvargs.update(csvargs)
        self.from_pandas(pandas.read_csv(filename, **localCsvargs))

    def clip(self) -> None:
        self.clippedData = (
            self.rawData.query(f"{self.dataRange[0]} <= Q < {self.dataRange[1]}").dropna().copy()
        )
        assert len(self.clippedData) != 0, "Data clipping range too small, no datapoints found!"

    def omit(self) -> None:
        """This can skip/omit unwanted ranges of data (for example a data range with an unwanted
        XRD peak in it). Requires an "omitQRanges" list of [[qmin, qmax]]-data ranges to omit.
        """

        # nothng to do:
        if self.omitQRanges is None:
            return
        assert isinstance(self.omitQRanges, list), "omitQRanges must be a list"
        for omitQRange in self.omitQRanges:
            assert (
                len(omitQRange) == 2
            ), "each omitQRange must contain two elements: a minimum and maximum value"
            # we drop the matches:
            self.clippedData.drop(
                self.clippedData.query(f"{omitQRange[0]} <= Q < {omitQRange[1]}").index,
                inplace=True,
            )

    def reBin(
        self, nbins: Optional[int] = None, IEMin: float = 0.01, QEMin: float = 0.01
    ) -> None:  # nbins:int|None
        """Unweighted rebinning funcionality with extended uncertainty estimation,
        adapted from the datamerge methods, as implemented in Paulina's notebook of spring 2020
        """
        if nbins is None:
            nbins = self.nbins

        qMin = self.clippedData.Q.dropna().min()
        qMax = self.clippedData.Q.dropna().max()

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
            dfRange = self.clippedData.query(
                "{} <= Q < {}".format(binEdges[binN], binEdges[binN + 1])
            ).copy()
            if len(dfRange) == 0:
                # no datapoints in the range
                pass

            elif len(dfRange) == 1:
                # only one datapoint in the range
                # might not be necessary to do this..
                # can't do stats on this:
                binDat.I.loc[binN] = float(dfRange.I.iloc[0])
                binDat.IStd.loc[binN] = float(dfRange.ISigma.iloc[0])
                binDat.ISEM.loc[binN] = float(dfRange.ISigma.iloc[0])
                binDat.IError.loc[binN] = float(dfRange.ISigma.iloc[0])
                binDat.ISigma.loc[binN] = np.max([binDat.ISEM.loc[binN], float(dfRange.I.iloc[0]) * IEMin])

                binDat.Q.loc[binN] = float(dfRange.Q.iloc[0])
                binDat.QStd.loc[binN] = binDat.Q.loc[binN] * QEMin
                binDat.QSEM.loc[binN] = binDat.Q.loc[binN] * QEMin
                binDat.QError.loc[binN] = binDat.Q.loc[binN] * QEMin
                if "QSigma" in dfRange.keys():
                    binDat.QStd.loc[binN] = float(dfRange.QSigma.iloc[0])
                    binDat.QSEM.loc[binN] = float(dfRange.QSigma.iloc[0])
                    binDat.QError.loc[binN] = float(dfRange.QSigma.iloc[0])
                binDat.QSigma.loc[binN] = np.max(
                    [float(binDat.QSEM.loc[binN]), float(dfRange.Q.iloc[0]) * QEMin]
                )

            else:
                # multiple datapoints in the range
                binDat.I.loc[binN] = dfRange.I.mean(skipna=True)  # , numeric_only = True)
                binDat.IStd.loc[binN] = dfRange.I.std(ddof=1, skipna=True)
                binDat.ISEM.loc[binN] = dfRange.I.sem(ddof=1, skipna=True)
                binDat.IError.loc[binN] = np.sqrt(((dfRange.ISigma) ** 2).sum()) / len(dfRange)
                binDat.ISigma.loc[binN] = np.max(
                    [
                        binDat.ISEM.loc[binN],
                        binDat.IError.loc[binN],
                        binDat.I.loc[binN] * IEMin,
                    ]
                )

                binDat.Q.loc[binN] = dfRange.Q.mean(skipna=True)
                binDat.QStd.loc[binN] = dfRange.Q.std(ddof=1, skipna=True)
                binDat.QSEM.loc[binN] = dfRange.Q.sem(ddof=1, skipna=True)
                binDat.QError.loc[binN] = binDat.QSEM.loc[binN]
                if "QSigma" in dfRange.keys():
                    # overwrite with propagated uncertainties if available
                    binDat.QError.loc[binN] = np.sqrt(((dfRange.QSigma) ** 2).sum()) / len(dfRange)
                binDat.QSigma.loc[binN] = np.max(
                    [
                        binDat.QSEM.loc[binN],
                        binDat.QError.loc[binN],
                        binDat.Q.loc[binN] * QEMin,
                    ]
                )

        # remove empty bins
        binDat.dropna(thresh=4, inplace=True)
        self.binnedData = binDat
