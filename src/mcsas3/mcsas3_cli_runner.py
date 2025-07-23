#!/usr/bin/env python3

# requires at least attrs version == 21.4
import argparse
import logging
import multiprocessing
import sys  # , os
from pathlib import Path
from sys import platform

from mcsas3 import __version__ as version  # ignore unused import # noqa: F401
from mcsas3.cli_tools import McSAS3_cli_optimize

# from mcsas3.mcmodelhistogrammer import McModelHistogrammer
# from mcsas3.mcanalysis import McAnalysis
# import yaml


def isMac():
    return platform == "darwin"


def main():
    multiprocessing.freeze_support()
    # manager=pyplot.get_current_fig_manager()
    # print manager
    # process input arguments
    parser = argparse.ArgumentParser(
        description="""
            Runs a McSAS optimization from the command line.
            For this to work, you need to have YAML-formatted configuration files ready,
            both for the input file read parameters, as well as for the optimization set-up.

            After the McSAS run has completed, you can run the histogrammer (also from the command
            line) in the same way by feeding it the McSAS output file and a histogramming
            configuration file.

            Examples of these configuration files are provided in the *example_configurations*
            subdirectory.

            Released under a GPLv3+ license.
            """
    )
    # TODO: add info about output files to be created ...
    parser.add_argument(
        "-f",
        "--dataFile",
        type=lambda p: Path(p).absolute(),
        default=Path(__file__).absolute().parent / "testdata" / "quickstartdemo1.csv",
        help="Path to the filename with the SAXS data",
        # required=True,
    )
    parser.add_argument(
        "-F",
        "--readConfigFile",
        type=lambda p: Path(p).absolute(),
        default=Path(__file__).absolute().parent
        / "example_configurations"
        / "read_config_csv.yaml",
        help="Path to the config file how to read the input data",
        # required=True,
    )
    parser.add_argument(
        "-r",
        "--resultFile",
        type=lambda p: Path(p).absolute(),
        default=Path(__file__).absolute().parent / "test.nxs",
        help="Path to the file to create and store the McSAS3 result in",
        # required=True,
    )
    parser.add_argument(
        "-R",
        "--runConfigFile",
        type=lambda p: Path(p).absolute(),
        default=Path(__file__).absolute().parent
        / "example_configurations"
        / "run_config_spheres_auto.yaml",
        help="Path to the configuration file containing the model parameters",
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
    parser.add_argument(
        "-d",
        "--deleteIfExists",
        # type=bool,
        # default=False,
        action="store_true",
        help=(
            "Delete the output file if it exists. This will need to be activated if you are"
            " overwriting previous optimizations "
        ),
        # required=True,
    )
    parser.add_argument(
        "-t",
        "--nThreads",
        type=int,
        default=0,
        help=(
            "The number (n>0) of cores/threads used for optimization."
            " If omitted, the value from the config file is used (default)."
            " Never more threads are used as cores exist."
        ),
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
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    # replaceStdOutErr() # replace all text output with our sinks

    adict = vars(args)
    McSAS3_cli_optimize(**adict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
