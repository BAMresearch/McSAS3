from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, ClassVar

import attrs
import numpy as np
from attrs import validators

from mcsas3.mc_hdf import ResultIndex, loadKV, loadKVPairs, storeKVPairs

from .osb import LEGACY_FIT_PARAMETER_NAMES, fit_parameter_names


def _coerce_result_index(value: ResultIndex | int) -> ResultIndex:
    if isinstance(value, ResultIndex):
        return value
    return ResultIndex(value)


@attrs.define(slots=False)
class McOpt:
    """Optimization settings and per-repetition optimizer state."""

    storeKeys: ClassVar[list[str]] = [
        "accepted",
        "convCrit",
        "gof",
        "maxIter",
        "maxAccept",
        "modelI",
        "repetition",
        "step",
        "weighting",
        "x0",
        "acceptedSteps",
        "acceptedGofs",
        "fitPorodBackground",
        "x0ParameterNames",
    ]
    loadKeys: ClassVar[list[str]] = [
        "accepted",
        "convCrit",
        "gof",
        "maxIter",
        "maxAccept",
        "modelI",
        "step",
        "x0",
        "acceptedSteps",
        "acceptedGofs",
    ]

    accepted: int | None = None
    convCrit: float = 1.0
    gof: float | None = None
    maxIter: int = 100000
    maxAccept: float = np.inf
    modelI: np.ndarray | None = None
    repetition: int | None = None
    step: int | None = None
    testX0: np.ndarray | None = None
    testModelI: np.ndarray | None = None
    testModelV: Any = None
    weighting: float = 0.5
    x0: np.ndarray | None = None
    acceptedSteps: list[int] = attrs.field(factory=list)
    acceptedGofs: list[float] = attrs.field(factory=list)
    fitPorodBackground: bool = attrs.field(default=False, validator=validators.instance_of(bool))
    x0ParameterNames: list[str] = attrs.field(factory=lambda: list(LEGACY_FIT_PARAMETER_NAMES))
    resultIndex: ResultIndex = attrs.field(default=1, converter=_coerce_result_index, kw_only=True)
    loadFromFile: Path | None = attrs.field(default=None, kw_only=True)
    loadFromRepetition: int = attrs.field(default=0, kw_only=True)

    def __attrs_post_init__(self) -> None:
        if self.repetition is None:
            self.repetition = self.loadFromRepetition
        if self.loadFromFile is not None:
            self.load(self.loadFromFile, repetition=self.loadFromRepetition)

    def store(self, filename: Path, path: PurePosixPath | None = None) -> None:
        """Store the optimizer settings in the result HDF5 file."""
        if path is None:
            path = self.resultIndex.nxsEntryPoint / "optimization"
        storeKVPairs(filename, path, [(key, getattr(self, key, None)) for key in self.storeKeys])

    def load(self, filename: Path, path: PurePosixPath | None = None, repetition: int | None = None) -> None:
        """Load optimizer settings from the result HDF5 file."""
        if repetition is None:
            repetition = self.repetition
        if path is None:
            path = self.resultIndex.nxsEntryPoint / "optimization" / f"repetition{repetition}"
        for key, value in loadKVPairs(filename, path, self.loadKeys):
            setattr(self, key, value)
        stored_fit_porod = loadKV(filename, path / "fitPorodBackground", default=None)
        self.fitPorodBackground = (
            bool(stored_fit_porod) if stored_fit_porod is not None else np.asarray(self.x0).size == 3
        )
        stored_parameter_names = loadKV(filename, path / "x0ParameterNames", default=None)
        if stored_parameter_names is None:
            self.x0ParameterNames = list(fit_parameter_names(self.x0))
        else:
            self.x0ParameterNames = [
                value.decode() if isinstance(value, (bytes, bytearray, np.bytes_)) else str(value)
                for value in np.asarray(stored_parameter_names).reshape(-1)
            ]
