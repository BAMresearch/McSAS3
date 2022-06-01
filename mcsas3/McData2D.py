import numpy as np
import pandas
from .McData import McData
import h5py


class McData2D(McData):
    """subclass for managing 2D datasets. Copied from 1D dataset handler, not every functionality is enabled"""

    csvargs = {
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

    def __init__(self, df=None, loadFromFile=None, resultIndex=1, **kwargs):
        super().__init__(resultIndex=resultIndex, **kwargs)
        self.csvargs = {
            "sep": r"\s+",
            "header": None,
            "names": ["Q", "I", "ISigma"],
        }  # default for 1D, overwritten in subclass
        self.dataRange = [0, np.inf]  # min-max for data range to fit
        self.orthoQ1Range = [0, np.inf]
        self.orthoQ0Range = [0, np.inf]
        self.qNudge = [0, 0]  # nudge in case of misaligned centers. Applied to measData
        self.processKwargs(**kwargs)

        # load from dataframe if provided
        if df is not None:
            self.loader = "from_pandas"  # TODO: need to handle this on restore state
            self.from_pandas(df)

        elif self.filename is not None:  # filename has been set
            self.from_file(self.filename)
        # link measData to the requested value

    def linkMeasData(self, measDataLink=None):
        if measDataLink is None:
            measDataLink = self.measDataLink
        assert measDataLink in [
            "rawData",
            "clippedData",
            "binnedData",
        ], f"measDataLink value: {measDataLink} not valid. Must be one of 'rawData', 'clippedData' or 'binnedData'"
        measDataObj = getattr(self, measDataLink)
        self.measData = dict(
            Q=[
                measDataObj["Q"][0] + self.qNudge[0],
                measDataObj["Q"][1] + self.qNudge[1],
            ],
            I=measDataObj["I"],
            ISigma=measDataObj["ISigma"],
        )

    def from_pandas(self, df=None):
        assert False, "2D data from_pandas not implemented yet"
        pass

    #     """uses a dataframe as input, should contain 'Q', 'I', and 'ISigma'"""
    #     assert isinstance(
    #         df, pandas.DataFrame
    #     ), "from_pandas requires a pandas DataFrame with 'Q', 'I', and 'ISigma'"
    #     # maybe add a check for the keys:
    #     assert all(
    #         [key in df.keys() for key in ["Q", "I", "ISigma"]]
    #     ), "from_pandas requires the dataframe to contain 'Q', 'I', and 'ISigma'"
    #     assert all(
    #         [df[key].dtype.kind in 'f' for key in ["Q", "I", "ISigma"]]
    #     ), "data could not be read correctly. If csv, did you supply the right csvargs?"
    #     self.rawData = df
    #     self.prepare()

    def from_csv(self, filename, csvargs={}):
        assert False, "2D data from_csv not implemented yet"
        pass

    #     """reads from a three-column csv file, takes pandas from_csv arguments"""
    #     assert filename is not None, "from_csv requires an input filename of a csv file"
    #     localCsvargs = self.csvargs.copy()
    #     localCsvargs.update(csvargs)
    #     self.from_pandas(pandas.read_csv(filename, **localCsvargs))

    def clip(self):

        # copied from a jupyter notebook:
        # test with directly imported data
        I = self.rawData2D["I"]
        ISigma = self.rawData2D["ISigma"]
        Q1 = self.rawData2D["Qx"]
        Q0 = self.rawData2D["Qy"]
        if "mask" in self.rawData2D.keys():
            mask = self.rawData2D["mask"]
        else:
            mask = np.zeros(I.shape)
        newMask = mask.astype(bool)

        withinLimits = (
            (np.abs(Q1) > self.orthoQ1Range[0])
            & (np.abs(Q1) < self.orthoQ1Range[1])
            & (np.abs(Q0) > self.orthoQ0Range[0])
            & (np.abs(Q0) < self.orthoQ0Range[1])
            & (np.sqrt(Q1 ** 2 + Q0 ** 2) > self.dataRange[0])
            & (np.sqrt(Q1 ** 2 + Q0 ** 2) < self.dataRange[1])
        ).astype(bool) * np.invert(newMask)

        # find crop envelope:
        Q0Lim = (
            np.argwhere(withinLimits.sum(axis=1) > 0).min(),
            np.argwhere(withinLimits.sum(axis=1) > 0).max(),
        )
        Q1Lim = (
            np.argwhere(withinLimits.sum(axis=0) > 0).min(),
            np.argwhere(withinLimits.sum(axis=0) > 0).max(),
        )
        assert (
            Q0Lim[0] < Q0Lim[1]
        ), "Could not determine valid crop limits for axis 0 (y)"
        assert (
            Q1Lim[0] < Q1Lim[1]
        ), "Could not determine valid crop limits for axis 1 (x)"

        # a0l, a0h, a1l, a1h = 200, 600, 300, 700
        self.clippedData = dict()
        self.clippedData["I2D"] = I[Q0Lim[0] : Q0Lim[1], Q1Lim[0] : Q1Lim[1]]
        self.clippedData["mask2D"] = newMask[Q0Lim[0] : Q0Lim[1], Q1Lim[0] : Q1Lim[1]]
        self.clippedData["ISigma2D"] = ISigma[Q0Lim[0] : Q0Lim[1], Q1Lim[0] : Q1Lim[1]]
        self.clippedData["Q0Crop2D"] = Q0[Q0Lim[0] : Q0Lim[1], Q1Lim[0] : Q1Lim[1]]
        self.clippedData["Q1Crop2D"] = Q1[Q0Lim[0] : Q0Lim[1], Q1Lim[0] : Q1Lim[1]]

        self.clippedData["kansas"] = self.clippedData["I2D"].shape
        # remove infinite intensities and zero-uncertainty datapoints as well (add to mask):
        bArr = np.invert(
            (np.isinf(self.clippedData["I2D"]) | (self.clippedData["ISigma2D"] == 0))
        )
        self.clippedData["invMask"] = bArr * np.invert(
            self.clippedData["mask2D"]
        ).astype(bool)

        self.clippedData["I"] = (
            self.clippedData["I2D"][self.clippedData["invMask"]]
        ).flatten()
        self.clippedData["ISigma"] = (
            self.clippedData["ISigma2D"][self.clippedData["invMask"]]
        ).flatten()
        self.clippedData["Q"] = [
            self.clippedData["Q0Crop2D"][self.clippedData["invMask"]].flatten(),
            self.clippedData["Q1Crop2D"][self.clippedData["invMask"]].flatten(),
        ]

        self.clippedData["Qextent"] = [
            (self.clippedData["Q"][0]).min(),
            (self.clippedData["Q"][0]).max(),
            (self.clippedData["Q"][1]).min(),
            (self.clippedData["Q"][1]).max(),
        ]

    def reconstruct2D(self, modelI1D):
        """
        Reconstructs a masked 2D data array from the (1D) model intensity, skipping the masked and clipped pixels (left as NaN)
        This function can be used to plot the resulting model intensity and comparing it with self.clippedData["I2D"]
        """
        # RMI = reconstructedModelI
        RMI = np.full(self.clippedData["I2D"].shape, np.nan)
        RMI[np.where(self.clippedData["invMask"])] = modelI1D
        return RMI

    def reBin(self, nbins=None, IEMin=0.01, QEMin=0.01):
        print("2D data rebinning not implemented, binnedData = clippedData for now")
        self.binnedData = self.clippedData

