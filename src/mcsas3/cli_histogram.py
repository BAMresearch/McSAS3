from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml
from attrs import define, field, validators

from . import workflows
from ._cli_common import validate_yaml_file
from .mc_analysis import McAnalysis
from .mc_plot import McPlot


@define
class McSAS3_cli_histogram(object):
    """Runs the McSAS histogrammer (only) from the command line arguments."""

    resultFile: Path = field(kw_only=True, validator=validators.instance_of(Path))
    histConfigFile: Path = field(kw_only=True, validator=[validators.instance_of(Path), validate_yaml_file])
    resultIndex: int = field(kw_only=True, validator=[validators.instance_of(int)])

    def __attrs_post_init__(self):
        self.run()

    def run(self):
        processing = workflows.load_result_processing_data(self.resultFile, result_index=self.resultIndex)

        with open(self.histConfigFile, "r") as f:
            histRanges = pd.DataFrame(list(yaml.safe_load_all(f)))
        mcres = McAnalysis(
            self.resultFile,
            processing,
            histRanges,
            store=True,
            resultIndex=self.resultIndex,
        )

        mp = McPlot()
        saveHistFile = self.resultFile.with_suffix(".pdf")
        if saveHistFile.is_file():
            saveHistFile.unlink()
        mp.resultCard(mcres, saveHistFile=saveHistFile)
