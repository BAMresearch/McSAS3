#!/usr/bin/env python3

import argparse
import logging
import multiprocessing
import sys
from pathlib import Path
from sys import platform

from mcsas3.cli_tools import McSAS3_cli_histogram


def isMac():
    return platform == "darwin"


def main():
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
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    # replaceStdOutErr() # replace all text output with our sinks
    # testing:
    adict = vars(args)
    McSAS3_cli_histogram(**adict)
    # m.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
