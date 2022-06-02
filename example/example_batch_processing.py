#!/usr/bin/env python3 
import os
import sys

THREADS = 8
SIMULATE = " mcsas3_cli_runner.py "
HISTOGRAM  = " mcsas3_cli_histogrammer.py "

for idx, fileName in enumerate(sys.argv[1:]):
    os.system( SIMULATE + " -f " + fileName  + " -F read_config_nxs.yaml -R ./run_config_spheres_auto.yaml -r " + fileName + ".nxs -n " + str(THREADS) )
    os.system( HISTOGRAM + " -r " + fileName + ".nxs -H hist_config_dual.yaml &") 
