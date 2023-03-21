#!/usr/bin/env python3

import argparse
import logging
import multiprocessing
import sys
from pathlib import Path
from sys import platform

import pandas as pd
import yaml
from attrs import define, field, validators

from mcsas3 import McData1D, McPlot
from mcsas3.mcanalysis import McAnalysis


@define
class McSAS3_cli_hist:
    """Runs the McSAS histogrammer from the command line arguments"""

    def checkConfig(self, attribute, value):
        assert value.exists(), f"configuration file {value} must exist"
        assert value.suffix == ".yaml", "configuration file must be a yaml file (and end in .yaml)"

    resultFile: Path = field(kw_only=True, validator=validators.instance_of(Path))
    histConfigFile: Path = field(
        kw_only=True, validator=[validators.instance_of(Path), checkConfig]
    )
    resultIndex: int = field(kw_only=True, validator=[validators.instance_of(int)])

    def run(self):
        # read the configuration file

        # load the data
        mds = McData1D.McData1D(loadFromFile=self.resultFile, resultIndex=self.resultIndex)

        # read the configuration file
        with open(self.histConfigFile, "r") as f:
            histRanges = pd.DataFrame(list(yaml.safe_load_all(f)))
        # run the Monte Carlo method
        md = mds.measData.copy()
        mcres = McAnalysis(
            self.resultFile, md, histRanges, store=True, resultIndex=self.resultIndex
        )

        # plotting:
        # plot the histogram result
        mp = McPlot.McPlot()
        # output file for plot:
        saveHistFile = self.resultFile.with_suffix(".pdf")
        if saveHistFile.is_file():
            saveHistFile.unlink()
        mp.resultCard(mcres, saveHistFile=saveHistFile)


def isMac():
    return platform == "darwin"


if __name__ == "__main__":
    multiprocessing.freeze_support()
    # manager=pyplot.get_current_fig_manager()
    # print manager
    # process input arguments
    parser = argparse.ArgumentParser(
        description="""
            Runs a McSAS histogramming from the command line.
            For this to work, you need to have YAML-formatted configuration files ready,
            both for the input file read parameters, as well as for the optimization set-up.

            The histogrammer furthermore needs a result file from the McSAS optimization.
            If you do not have that result file, please run the McSAS optimization first before
            attempting to histogram the results.

            Examples of these configuration files are provided in the *example_configurations*
            subdirectory.

            Released under a GPLv3+ license.
            """
    )

    parser.add_argument(
        "-r",
        "--resultFile",
        type=lambda p: Path(p).absolute(),
        default=Path(__file__).absolute().parent / "test.nxs",
        help="Path to the file with the McSAS3 optimization result",
        required=True,
    )
    parser.add_argument(
        "-H",
        "--histConfigFile",
        type=lambda p: Path(p).absolute(),
        default=Path("./example_configurations/hist_config_dual.yaml"),
        help="Path to the filename with the histogramming configuration",
        # required=True,
    )
    parser.add_argument(
        "-i",
        "--resultIndex",
        type=int,
        default=1,
        help="The result index to work on, in case you want multiple McSAS runs on the same data",
        # required=True,
    )

    if isMac():
        # on OSX remove automatically provided PID,
        # otherwise argparse exits and the bundle start fails silently
        for i in range(len(sys.argv)):
            if sys.argv[i].startswith("-psn"):  # PID provided by osx
                del sys.argv[i]
    try:
        args = parser.parse_args()
    except SystemExit:
        raise
    # initiate logging (to console stdout for now)
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    # replaceStdOutErr() # replace all text output with our sinks
    # testing:
    adict = vars(args)
    m = McSAS3_cli_hist(**adict)
    m.run()
