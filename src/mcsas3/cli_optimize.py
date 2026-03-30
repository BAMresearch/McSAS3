from __future__ import annotations

from pathlib import Path

import yaml
from attrs import define, field, validators

from . import workflows
from ._cli_common import validate_existing_file, validate_yaml_file


@define
class McSAS3_cli_optimize(object):
    """Runs the McSAS optimizer (only) from the command line arguments."""

    dataFile: Path = field(kw_only=True, validator=validators.instance_of(Path))
    resultFile: Path = field(kw_only=True, validator=validators.instance_of(Path))
    readConfigFile: Path = field(kw_only=True, validator=[validators.instance_of(Path), validate_yaml_file])
    runConfigFile: Path = field(kw_only=True, validator=[validators.instance_of(Path), validate_yaml_file])
    resultIndex: int = field(kw_only=True, validator=[validators.instance_of(int)])
    deleteIfExists: bool = field(kw_only=True, validator=[validators.instance_of(bool)])
    nThreads: int = field(kw_only=True, validator=[validators.instance_of(int)])

    @dataFile.validator
    def fileExists(self, attribute, value):
        validate_existing_file(self, attribute, value)

    def __attrs_post_init__(self):
        self.run()

    def run(self):
        if self.resultFile.is_file():
            if (self.resultFile != self.dataFile) & (self.deleteIfExists):
                self.resultFile.unlink()
        with open(self.readConfigFile, "r") as f:
            readDict = yaml.safe_load(f) or {}
        processing = workflows.prepare_1d_processing_data_from_file(
            self.dataFile,
            result_index=self.resultIndex,
            **readDict,
        )
        with open(self.runConfigFile, "r") as f:
            optDict = yaml.safe_load(f) or {}
        if self.nThreads > 0:
            optDict["nCores"] = self.nThreads
        processing_metadata = dict(readDict)
        processing_metadata["filename"] = self.dataFile
        workflows.optimize_processing_data(
            processing,
            self.resultFile,
            result_index=self.resultIndex,
            processing_metadata=processing_metadata,
            seed=None,
            **optDict,
        )
