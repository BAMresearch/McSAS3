#!/usr/bin/env python3

# requires at least attrs version == 21.4
import argparse
import logging
import multiprocessing
import sys  # , os
from pathlib import Path
from sys import platform

from mcsas3.cli_tools import McSAS3_cli_histogram, McSAS3_cli_optimize


def isMac():
    return platform == "darwin"


if __name__ == "__main__":
    multiprocessing.freeze_support()
    # manager=pyplot.get_current_fig_manager()
    # print manager
    # process input arguments
    parser = argparse.ArgumentParser(
        description="""
            Runs a McSAS optimization from the command line. This main entry point for the McSAS3
            package executes both the optimization and the histogramming.

            For this to work, you need to have YAML-formatted configuration files ready,
            for the input file read parameters, for the optimization set-up, and for the
            histogramming. Separate optimization and histogramming runs can be run using the
            mcsas3_cli_runner.py and mcsas3_cli_histogrammer.py scripts.

            After the McSAS run has completed, this runs the histogrammer
            """,
        epilog="""
            Examples of these configuration files are provided in the *example_configurations*
            subdirectory.

            Released under a GPLv3+ license.
            """,
    )
    parser.add_argument(
        "-f",
        "--dataFile",
        type=lambda p: Path(p).absolute(),
        help="""Path to the filename with the SAXS data, an example file can be found at
                'testdata/quickstartdemo1.csv' of the source distribution.""",
    )
    parser.add_argument(
        "-F",
        "--readConfigFile",
        type=lambda p: Path(p).absolute(),
        help="""Path to the config file how to read the input data, an example file can be found
                at 'example_configurations/read_config_csv.yaml' of the source distribution.""",
    )
    outpathDefault = Path().absolute() / "output.nxs"
    parser.add_argument(
        "-r",
        "--resultFile",
        type=lambda p: Path(p).absolute(),
        default=outpathDefault,
        help=f"""Path to the file to create and store the McSAS3 result in,
                the default is '{outpathDefault}'.""",
    )
    parser.add_argument(
        "-R",
        "--runConfigFile",
        type=lambda p: Path(p).absolute(),
        help="""Path to the configuration file containing the model parameters, an example file can
                be found at 'example_configurations/run_config_spheres_auto.yaml' of the source
                distribution.""",
    )
    parser.add_argument(
        "-H",
        "--histConfigFile",
        type=lambda p: Path(p).absolute(),
        help="""Path to the filename with the histogramming configuration, an example file can be
                found at 'example_configurations/hist_config_dual.yaml' of the source distribution.
        """,
    )
    parser.add_argument(
        "-i",
        "--resultIndex",
        type=int,
        default=1,
        help="The result index to work on, in case you want multiple McSAS runs on the same data",
    )
    parser.add_argument(
        "-d",
        "--deleteIfExists",
        default=False,
        action="store_true",
        help="""Delete the output file if it exists. This will need to be activated if you are
                overwriting previous optimizations""",
    )
    parser.add_argument(
        "-t",
        "--nThreads",
        type=int,
        default=0,
        help="""The number (n>0) of cores/threads used for optimization. If omitted, the value from
                the config file is used (default). Never more threads are used as cores exist.""",
    )
    if isMac():
        # on OSX remove automatically provided PID,
        # otherwise argparse exits and the bundle start fails silently
        for i in range(len(sys.argv)):
            if sys.argv[i].startswith("-psn"):  # PID provided by osx
                del sys.argv[i]
    args = parser.parse_args()
    # initiate logging (to console stdout for now)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    # replaceStdOutErr() # replace all text output with our sinks

    adict = vars(args)
    # split arguments into two dictionaries, one for the optimizer and one for the histogrammer
    adict_optimize = [
        {k: v for k, v in adict.items() if k in
            ["dataFile", "resultFile", "readConfigFile", "runConfigFile", "resultIndex", "deleteIfExists", "nThreads"]}
    ]
    adict_histogram = [
        {k: v for k, v in adict.items() if k in
            ["resultFile", "histConfigFile", "resultIndex"]}
    ]
    try:
        m = McSAS3_cli_optimize(**adict_optimize)
        m = McSAS3_cli_histogram(**adict_histogram)
    except TypeError as e:  # for wrong cmdline arguments supplied
        print(f"{type(e).__name__}: {str(e)}\n", file=sys.stderr)
        parser.print_help()
