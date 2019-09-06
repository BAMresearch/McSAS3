import sys, time
import numpy as np
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
    _modelArgs = None # dict with settings to be passed on to the model instance
    _optArgs = None   # dict with optimization settings to be passed on to the optimization instance
    _model = None     # McModel instance for multiple repetitions
    _opt = None       # McOpt instance for multiple repetitions
    nCores = 0        # number of cores to use for parallelization,
                      # 0: autodetect, 1: without multiprocessing
    nRep = 10         # number of independent repetitions to opitimize

    storeKeys = [ # keys to store in an output file
        "nCores",
        "nRep",
    ]
    loadKeys = storeKeys

    def __init__(self, loadFromFile=None, **kwargs):
        """kwargs accepts all parameters from McModel and McOpt."""

        if loadFromFile is not None:
            self.load(loadFromFile)

        self._optArgs = dict([(key, kwargs.pop(key))
                                for key in McOpt.storeKeys if key in kwargs])
        self._modelArgs = dict([(key, kwargs.pop(key))
                                for key in McModel.settables if key in kwargs])

        for key, value in kwargs.items():
            assert (key in self.storeKeys), "Key {} is not a valid option".format(key)
            setattr(self, key, value)

    def run(self, measData=None, filename=None):
        """runs the full sequence: multiple repetitions of optimizations, to be parallelized. 
        This probably needs to be taken out of core, and into a new parent"""

        if self.nCores == 1:
            for rep in range(self.nRep):
                self.runOnce(measData, filename, rep)
        elif self.nCores == 2:
            print([(measData, filename, r) for r in range(self.nRep)])
        else:
            import multiprocessing
            if self.nCores == 0:
                self.nCores = multiprocessing.cpu_count()
            start = time.time()
            lock = multiprocessing.Lock()
            pool = multiprocessing.Pool(self.nCores, initializer=initStoreLock, initargs=(lock,))
            runArgs = [(measData, filename, r, True) for r in range(self.nRep)]
            outputs = pool.starmap(self.runOnce, runArgs)
            pool.close()
            pool.join()
            print("McSAS analysis took {:.1f}s.".format(time.time()-start))
            #for args in runArgs:
            #    buf = args[-1]
            #    print(buf, buf.getvalue()) # last argument is stdio buffer
            for output in sorted(outputs, key=lambda x: x[0]):
                print(output)

    def runOnce(self, measData=None, filename=None, repetition=0, bufferStdIO=False):
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
        mc = McCore(measData, model = self._model, opt = self._opt)
        mc.optimize()
        self._model.kernel.release()
        print("Final chiSqr: {}, N accepted: {}"
              .format(self._opt.gof, self._opt.accepted))

        # storing the results
        if STORE_LOCK is not None:
            # prevent multiple threads writing HDF5 file simultaneously
            STORE_LOCK.acquire()
        mc.store(filename = filename)
        self.store(filename = filename)
        if STORE_LOCK is not None:
            STORE_LOCK.release()

        if bufferStdIO: # return buffered output if desired
            return sys.stdout.getvalue()
        return

    def store(self, filename = None, path = '/entry1/analysis/MCResult1/optimization/'):
        """stores the settings in an output file (HDF5)"""
        assert filename is not None
        for key in self.storeKeys:
            value = getattr(self, key, None)
            self._HDFstoreKV(filename = filename, path = path, key = key, value = value)

    def load(self, filename = None, path = '/entry1/analysis/MCResult1/optimization/'):
        assert filename is not None
        for key in self.loadKeys:
            with h5py.File(filename) as h5f:
                setattr(self, key, h5f["{}/{}".format(path, key)][()])