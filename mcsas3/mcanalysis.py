import pandas
import numpy as np
from .McHDF import McHDF

class McAnalysis(McHDF):
	"""
	This class is the analyzer / histogramming code for the entire set of repetitions. 
	It can only been run after each individual repetition has been histogrammed using
	the McModelHistogrammer class. 

	McAnalysis uses the individual repetition histograms to calculate the mean and spread 
	of each histogram bin, and the mean and spread of each population mode. It also uses
	the scaling parameters to scale all values to absolute volume fractions. 

	Due to the complexity of setting up, McAnalysis *must* be provided an output HDF5
	file, where all the results and set-up are stored. It then reads the individual
	optimization results and performs its statistical calculations. 
	"""
    _histRanges = pandas.DataFrame() # pandas dataframe with one row per range, and the parameters as developed in McSAS, this gets passed on to McModelHistogrammer as well
    _model = None # just a continuously changing variable
    _concatModes = None # not sure how to combine yet. 
    _concatHistograms = None # ibid. 
    _averagedModes = pandas.dataFrame(columns = [
    	'totalValue', 'mean', 'variance', 'skew', 'kurtosis',
    	'totalValueStd', 'meanStd', 'varianceStd', 'skewStd', 'kurtosisStd']) # like McSAS output
    _averagedModelData = pandas.dataFrame()


	def __init__(self, inputFile):
		# 1. open the input file, and for every repetition:
		# 2. set up the model again, and
		# 3. set up the optimization instance again, and
		# 4. run the McModelHistogrammer, and 
		# 5. put the histogrammer results in the right place, and 
		# 6. concatenate the results in a big table for statistical analysis, and
		# 7. calculate the mean model intensity, and 
		# 8. find the overall scaling parameter for the model intensity, and 
		# 9. scale the volumes with this scaling parameter, and
		# 9. calculate the observability for the bins


