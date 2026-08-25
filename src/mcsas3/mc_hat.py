# src/mcsas3/mc_hat.py

import logging
import sys
import threading
import time
from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Any, Optional

import numpy as np

from mcsas3.mc_hdf import ResultIndex, loadKVPairs, storeKVPairs

from .data_adapters import as_analysis_bundle, q_support_from_bundle
from .mc_core import McCore
from .mc_model import McModel
from .mc_opt import McOpt

STORE_LOCK = None
STOP_EVENT = None
logger = logging.getLogger(__name__)


def initWorkerState(lock, stop_event):
    """Initialize multiprocessing worker globals for synchronized store/stop handling."""

    global STORE_LOCK, STOP_EVENT
    STORE_LOCK = lock
    STOP_EVENT = stop_event


def worker_stop_requested() -> bool:
    """Return whether the process-shared stop event has been set for a worker."""

    return STOP_EVENT is not None and STOP_EVENT.is_set()


def _attach_buffer_log_handler(output_buffer: StringIO) -> tuple[logging.Logger, logging.Handler, int, bool]:
    """Attach a temporary log handler for buffered worker output capture."""

    logger_namespace = logging.getLogger("mcsas3")
    handler = logging.StreamHandler(output_buffer)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    previous_level = logger_namespace.level
    previous_propagate = logger_namespace.propagate
    logger_namespace.addHandler(handler)
    logger_namespace.setLevel(logging.INFO)
    logger_namespace.propagate = False
    return logger_namespace, handler, previous_level, previous_propagate


# TODO: use attrs to @define a mchatataclass
class McHat:
    """
    The hat sits on top of `McCore` and orchestrates repeated optimization runs.

    Preferred measurement input is the canonical selected-analysis `DataBundle`.
    `OptimizerInput` remains supported as an execution-format escape hatch.
    """

    _analysisBundle = None  # canonical bundle selected for fitting, when available
    _modelArgs = None  # dict with settings to be passed on to the model instance
    _optArgs = None  # dict with optimization settings to be passed on to the optimization instance
    _model = None  # McModel instance for multiple repetitions
    _opt = None  # McOpt instance for multiple repetitions
    nCores = 0  # number of cores to use for parallelization,
    # 0: autodetect, 1: without multiprocessing
    nRep = 10  # number of independent repetitions to opitimize
    _stopEvent = None  # thread-local stop signal for this McHat instance
    _processStopEvent = None  # process-shared stop signal for active worker pool
    _runActive = False  # whether run() is currently active
    lastRunStopped = False  # whether the last run ended due to a stop request

    storeKeys = [  # keys to store in an output file
        "nCores",
        "nRep",
    ]
    loadKeys = storeKeys

    def __init__(self, loadFromFile: Optional[Path] = None, resultIndex: int = 1, **kwargs: dict) -> None:
        # reset to make sure we're not inheriting any settings from another instance:
        self._analysisBundle = None  # canonical bundle selected for fitting, when available
        self._modelArgs = None  # dict with settings to be passed on to the model instance
        self._optArgs = None  # dict with optimization settings to be passed on to the optimization instance
        self._model = None  # McModel instance for multiple repetitions
        self._opt = None  # McOpt instance for multiple repetitions
        self.nCores = 0  # number of cores to use for parallelization,
        # 0: autodetect, 1: without multiprocessing
        self.nRep = 10  # number of independent repetitions to opitimize
        self._stopEvent = threading.Event()
        self._processStopEvent = None
        self._runActive = False
        self.lastRunStopped = False

        """kwargs accepts all parameters from McModel and McOpt."""
        # make sure we store and read from the right place.
        self.resultIndex = ResultIndex(resultIndex)  # defines the HDF5 root path

        if loadFromFile is not None:
            self.load(loadFromFile)

        self._optArgs = dict([(key, kwargs.pop(key)) for key in McOpt.storeKeys if key in kwargs])
        self._optArgs.update({"resultIndex": resultIndex})
        self._modelArgs = dict([(key, kwargs.pop(key)) for key in McModel.settables if key in kwargs])
        self._modelArgs.update({"resultIndex": resultIndex})

        for key, value in kwargs.items():
            if key not in self.storeKeys:
                raise ValueError(f"Key {key} is not a valid option")
            setattr(self, key, value)
        if self.nRep <= 0:
            raise ValueError("Must optimize for at least one repetition.")

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_stopEvent"] = None
        state["_processStopEvent"] = None
        state["_runActive"] = False
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        if self._stopEvent is None:
            self._stopEvent = threading.Event()
        self._processStopEvent = None

    @property
    def isRunning(self) -> bool:
        """Return whether `run()` is currently active on this instance."""

        return self._runActive

    def request_stop(self) -> None:
        """Request that the active run stop as soon as practical."""

        self._stopEvent.set()
        if self._processStopEvent is not None:
            self._processStopEvent.set()

    def clear_stop_request(self) -> None:
        """Clear any previously requested stop flags before a new run starts."""

        self._stopEvent.clear()
        if self._processStopEvent is not None:
            self._processStopEvent.clear()

    def stop_requested(self) -> bool:
        """Return whether a local or process-shared stop has been requested."""

        return self._stopEvent.is_set() or (self._processStopEvent is not None and self._processStopEvent.is_set())

    def fillFitParameterLimits(self, analysis_input: Any) -> None:
        """Resolve any `auto` fit parameter limits against the supplied measurement support."""

        try:
            q_support = q_support_from_bundle(as_analysis_bundle(analysis_input))
        except TypeError:
            from .optimizer_input import as_optimizer_input

            q_support = as_optimizer_input(analysis_input).q_support
        for key, val in self._modelArgs["fitParameterLimits"].items():
            if isinstance(val, str):
                if val != "auto":
                    raise ValueError('Fit parameter limits must be explicit [min, max] pairs or the string "auto".')
                # auto-fill values
                if np.min(q_support) <= 0:
                    raise ValueError("For auto-scaling of measurement limits, the smallest Q value must be > 0.")
                self._modelArgs["fitParameterLimits"][key] = [
                    np.pi / np.max(q_support),
                    2 * np.pi / np.min(q_support),
                ]

    def run(self, analysis_input: Any, filename: Path, resultIndex: int = 1) -> None:
        """Run all configured repetitions, optionally in parallel, and store completed results."""

        self.clear_stop_request()
        self.lastRunStopped = False
        self._runActive = True
        try:
            try:
                resolved_input = as_analysis_bundle(analysis_input)
                self._analysisBundle = resolved_input
            except TypeError:
                resolved_input = analysis_input
                self._analysisBundle = None
            # ensure the fit parameter limits are filled in based on the data limits if auto
            self.fillFitParameterLimits(resolved_input)
            if (self.nCores == 1) or (self.nRep == 1):
                for rep in range(self.nRep):
                    if self.stop_requested():
                        break
                    self.runOnce(resolved_input, filename, rep, resultIndex=resultIndex)
            # elif self.nCores == 2:
            #     print([(analysis_input, filename, r) for r in range(self.nRep)])
            else:
                import multiprocessing

                if self.nCores == 0:
                    # don't run more processes than we need...
                    self.nCores = np.minimum(multiprocessing.cpu_count(), self.nRep)
                start = time.time()
                lock = multiprocessing.Lock()
                self._processStopEvent = multiprocessing.Event()
                pool = multiprocessing.Pool(
                    self.nCores,
                    initializer=initWorkerState,
                    initargs=(lock, self._processStopEvent),
                )
                runArgs = [(resolved_input, filename, r, True, resultIndex) for r in range(self.nRep)]
                async_result = pool.starmap_async(self.runOnce, runArgs)
                outputs = None
                while outputs is None:
                    try:
                        outputs = async_result.get(timeout=0.2)
                    except multiprocessing.TimeoutError:
                        continue
                pool.close()
                pool.join()
                logger.info(
                    "McSAS analysis with %s repetitions took %.1fs with %s threads.",
                    self.nRep,
                    time.time() - start,
                    min(self.nCores, self.nRep),
                )
                for repetition, output, _completed in sorted(outputs, key=lambda value: value[0]):
                    if output:
                        logger.info("%s", output.rstrip())
        finally:
            self.lastRunStopped = self.stop_requested()
            self._runActive = False
            self._processStopEvent = None

    def runOnce(
        self,
        analysis_input: Any,
        filename: Path,
        repetition: int = 0,
        bufferStdIO: bool = False,
        resultIndex: int = 1,
    ) -> tuple[int, str, bool] | None:
        """Run a single optimization repetition and optionally return buffered worker output."""
        original_stdout = None
        original_stderr = None
        output_buffer = None
        buffer_logger = None
        buffer_handler = None
        buffer_logger_level = logging.NOTSET
        buffer_logger_propagate = True
        completed = False
        if bufferStdIO:
            # buffer stdout/err in an individual StringIO object for each repetition
            output_buffer = StringIO()
            buffer_logger, buffer_handler, buffer_logger_level, buffer_logger_propagate = _attach_buffer_log_handler(
                output_buffer
            )
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stderr = sys.stdout = output_buffer
        if self._opt is None:
            self._opt = McOpt(**self._optArgs)
        if self._model is None:
            self._model = McModel(**self._modelArgs)

        self._opt.repetition = repetition
        base_seed = self._modelArgs.get("seed")
        if base_seed is not None:
            try:
                effective_seed = int(base_seed) + int(repetition)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Configured seed must be an integer-compatible value, got {base_seed!r}.") from exc
            self._model.seed = effective_seed
            self._model.randomGenerators = None
            self._model._initialize_random_generators()
        self._model.resetParameterSet()
        try:
            stop_callback = worker_stop_requested if bufferStdIO else self.stop_requested
            mc = McCore(
                analysis_input,
                model=self._model,
                opt=self._opt,
                resultIndex=resultIndex,
                stop_requested=stop_callback,
            )
            completed = mc.optimize()
            try:
                self._model.kernel.release()
            except AttributeError:
                pass  # can happen with a simulation model
            except Exception as e:
                logger.warning("%s: %s", mc, e)
            if completed:
                logger.info("Final chiSqr: %s, N accepted: %s", self._opt.gof, self._opt.accepted)
                if STORE_LOCK is not None:
                    # prevent multiple threads writing HDF5 file simultaneously
                    STORE_LOCK.acquire()
                try:
                    mc.store(filename=filename)
                    self.store(filename=filename)
                except Exception as e:
                    logger.warning("%s: %s", mc, e)
                finally:
                    if STORE_LOCK is not None:
                        STORE_LOCK.release()
            else:
                logger.info("Optimization of repetition %s stopped before completion.", repetition)
        finally:
            if bufferStdIO and buffer_logger is not None and buffer_handler is not None:
                buffer_logger.removeHandler(buffer_handler)
                buffer_handler.close()
                buffer_logger.setLevel(buffer_logger_level)
                buffer_logger.propagate = buffer_logger_propagate
            if bufferStdIO and original_stdout is not None and original_stderr is not None:
                sys.stdout = original_stdout
                sys.stderr = original_stderr

        if bufferStdIO:  # return buffered output if desired
            if output_buffer is None:
                raise RuntimeError("Buffered output was requested but no output buffer was initialized.")
            return repetition, output_buffer.getvalue(), completed
        return

    # same as in McOpt
    def store(self, filename: Path, path: Optional[PurePosixPath] = None) -> None:
        """stores the settings in an output file (HDF5)"""
        if path is None:
            path = self.resultIndex.nxsEntryPoint / "optimization"
        storeKVPairs(filename, path, [(key, getattr(self, key, None)) for key in self.storeKeys])

    # same as in McOpt, except for the repetition (in McOpt)
    def load(self, filename: Path, path: Optional[PurePosixPath] = None) -> None:
        """Load orchestrator settings from the result HDF5 file."""

        if path is None:
            path = self.resultIndex.nxsEntryPoint / "optimization"
        for key, value in loadKVPairs(filename, path, self.loadKeys):
            setattr(self, key, value)
