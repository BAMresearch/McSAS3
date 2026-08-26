from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd
import yaml
from attrs import define, field, validators

from . import workflows
from ._cli_common import validate_yaml_file
from .mc_analysis import McAnalysis
from .mc_plot import McPlot


def _histogram_config_rows(hist_config_file: Path) -> list[dict]:
    rows = []
    with open(hist_config_file, "r", encoding="utf-8") as f:
        documents = yaml.safe_load_all(f)
        for document_index, document in enumerate(documents, start=1):
            if document is None:
                continue
            if isinstance(document, Mapping):
                rows.append(dict(document))
            elif isinstance(document, list):
                for item_index, item in enumerate(document, start=1):
                    if item is None:
                        continue
                    if not isinstance(item, Mapping):
                        raise ValueError(
                            "Histogram configuration list item "
                            f"{item_index} in document {document_index} must be a mapping."
                        )
                    rows.append(dict(item))
            else:
                raise ValueError(f"Histogram configuration document {document_index} must be a mapping or list.")

    if not rows:
        raise ValueError("Histogram configuration must contain at least one histogram definition.")
    return rows


def load_histogram_ranges(hist_config_file: Path) -> pd.DataFrame:
    """Load histogram range definitions from mapping or list-style YAML documents."""

    return pd.DataFrame(_histogram_config_rows(hist_config_file))


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

        histRanges = load_histogram_ranges(self.histConfigFile)
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
