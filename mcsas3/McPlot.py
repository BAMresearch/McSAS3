import pandas
import numpy as np
from .McHDF import McHDF
from .mcmodel import McModel
from .mccore import McCore
from .mcopt import McOpt
from .mcmodelhistogrammer import McModelHistogrammer
import os.path
import h5py
import matplotlib.pyplot as plt

class mcPlot(McHDF):
    """ 
    A class to help in plotting of input- and output data used in the MC optimization. 
    This is generally run after an analysis has occurred, but also has methods for 
    plotting the input dataset(s). 
    This is not a main component of the McSAS3 library, and is only provided for convenience.
    It is very much a work in progress and its structure or methods may vary in subsequent
    releases.
    """
    _analysis = None # instance of McAnalysis
    _inputData = None # instance of McData 
    _figureHandle = None # handle to figure
    _axesHandles = None # subplots-style array of axes handles.

    def __init__(self, **kwargs):
        pass
