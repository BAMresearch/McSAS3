import pandas
import sasmodels
import numpy as np
from .osb import optimizeScalingAndBackground
import scipy.optimize 

class McCore(object): 
    """
    The core of the MC procedure. Strict requirements on input include:
    modelFunc: SasModels function
    measData: measurement data dictionary with Q, I, ISigma containing arrays
    pickParameters: dict of values with new random picks, named by parameter names
    modelParameterLimits: dict of value pairs (tuples) with random pick bounds, named by parameter names 
    x0: continually updated new guess for total scaling, background values. 
    weighting: volume-weighting / compensation factor for the contributions
    nContrib: number of contributions
    """
    
    _measData = None   # measurement data dict with entries for Q, I, ISigma
    _model = None      # instance of McModel
    _opt = None        # instance of McOpt
    _OSB = None        # optimizeScalingAndBackground instance for this data
    _ofname = None     # store output data in here (HDF5)

    def __init__(self, 
                 measData = None, 
                 model = None, 
                 opt = None,
                ):
        
        self._model = model 
        self._measData = measData 
        self._opt = opt    # McOpt instance
        self._opt.nContrib # pass on this important parameter
        self._opt.step = 0 # number of iteration steps
        self._opt.accepted = 0 # number of accepted iterations
        self._OSB = optimizeScalingAndBackground(measData["I"], measData["ISigma"])

        self.initModel()   # initialize SasView model
        self._opt.gof = self.evaluate() # calculate initial GOF measure
        # store the initial background and scaling optimization as new initial guess:
        self._opt.x0 = self._opt.testX0

    def initModel(self):
        # sets up parameters set with nContrib contributions:
        self._model.initialize(self._opt.nContrib) 
        # set default parameters:
        self._model.func.info.parameters.defaults.update(self._model.staticParameters)
        # generate kernel
        self._model.kernel = self._model.func.make_kernel(self._measData["Q"])
        # calculate scattering intensity by combining intensities from all contributions
        self.initModelI()
    
    def load(self):
        """loads the configuration and set-up from the extended NXcanSAS file"""
        # not implemented yet
        pass

    def calcModelI(self, parameters):
        """calculates the intensity and volume of a particular set of parameters"""
        return sasmodels.direct_model.call_kernel(
                self._model.kernel, 
                dict(self._model.staticParameters, **parameters)
            )
    
    def returnModelV(self):
        """
        Returns the volume of the last kernel calculation. 
        Has to be run directly after calculation. May be replaced by more appropriate 
        SasModels function calls once available. 
        """
        return self._model.kernel.result[self._model.kernel.q_input.nq]
    
    def initModelI(self):
        """calculate the total intensity from all contributions"""
        # set initial shape:
        I = self.calcModelI( 
            self._model.parameterSet.loc[0].to_dict()
        ) 
        # zero-out all previously stored values for intensity and volume
        self._opt.modelI = np.zeros(I.shape)
        self._model.volumes = np.zeros(self._opt.nContrib)
        # add the intensity of every contribution
        for contribi in range(self._opt.nContrib):
            I = self.calcModelI( 
                self._model.parameterSet.loc[contribi].to_dict()
            ) 
            V = self.returnModelV()
            # intensity is added, normalized by number of contributions. 
            # volume normalization is already done in SasModels (!), so we have volume-weighted intensities from there...
            self._opt.modelI += I / self._opt.nContrib # / (self._opt.nContrib * V)
            # we store the volumes anyway since we may want to use them later for showing alternatives of number-weighted, or volume-squared weighted histograms
            self._model.volumes[contribi] = V
    
    def evaluate(self, testData = None): # takes 20 ms! 
        """scale and calculate goodness-of-fit (GOF) from all contributions"""

        if testData is None:
            testData = self._opt.modelI
            
        # this function takes quite a while:
        self._opt.testX0, gof = self._OSB.match(testData, self._opt.x0)
        return gof
    
    def reEvaluate(self):
        """replace single contribution with new contribution, recalculate intensity and GOF"""

        # calculate old intensity to subtract:
        Iold = self.calcModelI( 
            self._model.parameterSet.loc[self._opt.contribIndex()].to_dict()
        ) 
        # not needed:
        # Vold = self.returnModelV() # = self._model.volumes[self._opt.contribIndex()]
        
        # calculate new intensity to add:
        Ipick = self.calcModelI( self._model.pickParameters ) 
        Vpick = self.returnModelV()
        
        # remove intensity from contribi from modelI
        # add intensity from Pick
        self._opt.testModelI = self._opt.modelI + (Ipick - 
                                Iold )/ self._opt.nContrib
        
        # store pick volume in temporary location
        self._opt.testModelV = Vpick
        # recalculate reduced chi-squared for this option
        return self.evaluate(self._opt.testModelI)
    
    def reject(self):
        """reject pick"""
        # nothing to do. Can be used to fish out a running rejection/acceptance ratio later
        pass
    
    def accept(self):
        """accept pick"""
        # store parameters of accepted pick:
        self._model.parameterSet.loc[self._opt.contribIndex()] = self._model.pickParameters
        # store calculated intensity as new total intensity:
        self._opt.modelI = self._opt.testModelI
        # store new pick volume to the set of volumes:
        self._model.volumes[self._opt.contribIndex()] = self._opt.testModelV
        # store latest scaling and background values as new initial guess:
        self._opt.x0 = self._opt.testX0
        # add one to the accepted moves counter:
        self._opt.accepted += 1
    
    def iterate(self):
        """pick, re-evaluate and accept/reject"""
        # pick new model parameters:
        self._model.pick() # 3 µs
        # calculate GOF for the new total set:
        newGof = self.reEvaluate() # 2 ms
        # if this is an improvement:
        if (newGof < self._opt.gof):
            # accept the move:
            self.accept() # 500 µs
            # and store the new GOF as current:
            self._opt.gof = newGof           
        # increment step counter in either case: 
        self._opt.step += 1
    
    def optimize(self):
        """iterate until target GOF or maxiter reached"""
        print("Optimization started")
        print("chiSqr: {}, N accepted: {} / {}"
              .format(self._opt.gof, self._opt.accepted, self._opt.step))       

        # continue optimizing until we reach any of these targets:
        while ((self._opt.accepted < self._opt.maxAccept) & # max accepted moves
               (self._opt.step < self._opt.maxIter) &       # max number of tries
               (self._opt.gof > self._opt.convCrit)):       # convergence criterion reached
            self.iterate()
            # show me every 1000 steps where you are in the optimization:
            if (self._opt.step % 1000 == 1):
                print("chiSqr: {}, N accepted: {} / {}"
                      .format(self._opt.gof, self._opt.accepted, self._opt.step))
                
    def run(self):
        """runs the full sequence: multiple repetitions of optimizations, to be parallelized"""
        # NOT FINISHED YET, individual optimizations are not yet stored(!)
        for rep in range(self._opt.nRep):
            self._opt.repetition = rep # set running variable (important for storage)
            self.optimize()
            
    def store(self):
        """stores the resulting model parameter-set of a single repetition in the NXcanSAS object, ready for histogramming"""
        # not finished
        
        with pandas.HDFStore(self._ofname) as h5f:

            h5f.put('/mcsas/opt1/contributions/rep{}'.format(self._opt.repetition), 
                    self._model.parameterSet, 
                    #format = 'table', 
                    data_columns=True)
            # self._model.parameterSet.to_hdf(
            #     self._ofname, 
            #     key = '/mcsas/opt1/contributions/rep{}'.format(self._opt.repetition), 
            #     mode = 'a', 
            #     format = "table",
            #     # data_columns = True,
            #     # complevel = 5,
            #     # complib = 'zlib'
            # )

        #     # multiple optimizations with different settings could be stored, using [opt1, opt2, etc]
        #     # I guess we have to set an attribute to the currently active optimization...
        #     og = h5f.require_group('/mcsas/opt1/contributions') # contrbutions stored in this group
        #     dset = og.create_dataset('{}'.format(self._opt.repetition), data = self._model.parameterSet)

