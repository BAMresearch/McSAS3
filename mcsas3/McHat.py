import sys, time
import numpy as np
import h5py
from .McHDF import McHDF
from .mcopt import McOpt
from .mcmodel import McModel
from .mccore import McCore
from io import StringIO

STORE_LOCK = None


def initStoreLock(lock):
    global STORE_LOCK
    STORE_LOCK = lock


class McHat(McHDF):
    """
    The hat sits on top of the McCore. It takes care of parallel processing of each repetition. 
    """

    _measData = None  # measurement data dict with entries for Q, I, ISigma
    _modelArgs = None  # dict with settings to be passed on to the model instance
    _optArgs = None  # dict with optimization settings to be passed on to the optimization instance
    _model = None  # McModel instance for multiple repetitions
    _opt = None  # McOpt instance for multiple repetitions
    nCores = 0  # number of cores to use for parallelization,
    nUserThreads = None # number of cores/threads to use for parallelization when given as command line argument. when given it overwrites values from config files. useful flor batch processing

    # 0: autodetect, 1: without multiprocessing
    nRep = 10  # number of independent repetitions to opitimize

    storeKeys = [  # keys to store in an output file
        "nCores",
        "nRep",
    ]
    loadKeys = storeKeys

    def __init__(self, loadFromFile=None, nThreads=None, resultIndex=1, **kwargs):

        # reset to make sure we're not inheriting any settings from another instance:
        self._measData = None  # measurement data dict with entries for Q, I, ISigma
        self._modelArgs = (
            None  # dict with settings to be passed on to the model instance
        )
        self._optArgs = None  # dict with optimization settings to be passed on to the optimization instance
        self._model = None  # McModel instance for multiple repetitions
        self._opt = None  # McOpt instance for multiple repetitions
        self.nCores = 0  # number of cores to use for parallelization from config file
        self.nUserThreads = None # number of cores/threads to use for parallelization when given as command line argument. when given it overwrites values from config files. useful flor batch processing
        # 0: autodetect, 1: without multiprocessing
        self.nRep = 10  # number of independent repetitions to opitimize

        """kwargs accepts all parameters from McModel and McOpt."""
        # make sure we store and read from the right place. 
        self._HDFSetResultIndex(resultIndex)

        if loadFromFile is not None:
            self.load(loadFromFile)
        
        self.nUserThreads = nThreads              

        self._optArgs = dict(
            [(key, kwargs.pop(key)) for key in McOpt.storeKeys if key in kwargs]
        )
        self._optArgs.update({'resultIndex':resultIndex})
        self._modelArgs = dict(
            [(key, kwargs.pop(key)) for key in McModel.settables if key in kwargs]
        )
        self._modelArgs.update({'resultIndex':resultIndex})
        for key, value in kwargs.items():
            assert key in self.storeKeys, "Key {} is not a valid option".format(key)
            setattr(self, key, value)
        assert self.nRep > 0, "Must optimize for at least one repetition"

        

    def fillFitParameterLimits(self, measData):
        for key, val in self._modelArgs["fitParameterLimits"].items():
            if isinstance(val, str):
                assert (
                    val == "auto"
                ), 'Only fit parameter options are either providing [min, max] limits or setting to "auto"'
                # auto-fill values
                assert (
                    np.min(measData["Q"]) > 0
                ), "for auto-scaling of measurement limits, the smallest Q value cannot be zero"
                self._modelArgs["fitParameterLimits"][key] = [
                    np.pi / np.max(measData["Q"]),
                    np.pi / np.min(measData["Q"]),
                ]

    def run(self, measData=None, filename=None, resultIndex=1):
        """runs the full sequence: multiple repetitions of optimizations, to be parallelized. 
        This probably needs to be taken out of core, and into a new parent"""

        # ensure the fit parameter limits are filled in based on the data limits if auto
        self.fillFitParameterLimits(measData)

        if self.nCores == 1:
            for rep in range(self.nRep):
                self.runOnce(measData, filename, rep, resultIndex=resultIndex)
        # elif self.nCores == 2:
        #     print([(measData, filename, r) for r in range(self.nRep)])
        else:
            import multiprocessing

            # don't run more processes than we need...
            if self.nUserThreads is not None:
                self.nCores = self.nUserThreads
            self.nCores = np.minimum(multiprocessing.cpu_count(), self.nCores)

            start = time.time()
            lock = multiprocessing.Lock()
            pool = multiprocessing.Pool(
                self.nCores, initializer=initStoreLock, initargs=(lock,)
            )
            runArgs = [(measData, filename, r, True, resultIndex) for r in range(self.nRep)]
            outputs = pool.starmap(self.runOnce, runArgs)
            pool.close()
            pool.join()
            print(
                "McSAS analysis with {} repetitions took {:.1f}s with {} threads.".format(
                    self.nRep, time.time() - start, min(self.nCores, self.nRep)
                )
            )
            # for args in runArgs:
            #    buf = args[-1]
            #    print(buf, buf.getvalue()) # last argument is stdio buffer
            for output in sorted(outputs, key=lambda x: x[0]):
                print(output)

    def runOnce(self, measData=None, filename=None, repetition=0, bufferStdIO=False, resultIndex=1):
        """runs the full sequence: multiple repetitions of optimizations, to be parallelized. 
        This probably needs to be taken out of core, and into a new parent"""
        if bufferStdIO:
            # buffer stdout/err in an individual StringIO object for each repetition
            sys.stderr = sys.stdout = StringIO()
        if self._opt is None:
            self._opt = McOpt(**self._optArgs)
        if self._model is None:
            self._model = McModel(**self._modelArgs)

        self._opt.repetition = repetition
        self._model.resetParameterSet()
        mc = McCore(measData, model=self._model, opt=self._opt, resultIndex=resultIndex)
        mc.optimize()
        try:
            self._model.kernel.release()
        except AttributeError:
            pass  # can happen with a simulation model
        except:
            raise
        print(
            "Final chiSqr: {}, N accepted: {}".format(self._opt.gof, self._opt.accepted)
        )

        # storing the results
        if STORE_LOCK is not None:
            # prevent multiple threads writing HDF5 file simultaneously
            STORE_LOCK.acquire()
        mc.store(filename=filename)
        self.store(filename=filename)
        if STORE_LOCK is not None:
            STORE_LOCK.release()

        if bufferStdIO:  # return buffered output if desired
            return sys.stdout.getvalue()
        return

    def store(self, filename=None, path=None):
        if path is None:
            path = f"{self.nxsEntryPoint}optimization/"
        """stores the settings in an output file (HDF5)"""
        assert filename is not None
        for key in self.storeKeys:
            value = getattr(self, key, None)
            self._HDFstoreKV(filename=filename, path=path, key=key, value=value)

    def load(self, filename=None, path=None):
        if path is None:
            path = f"{self.nxsEntryPoint}optimization/"
        assert filename is not None
        for key in self.loadKeys:
            with h5py.File(filename, "r") as h5f:
                setattr(self, key, h5f["{}/{}".format(path, key)][()])
