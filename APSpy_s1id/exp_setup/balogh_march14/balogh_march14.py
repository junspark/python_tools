import sys
import numpy
import scipy
import math
import logging
import time

import datetime as dt
import epics as PyEpics  ## import epics as ep  #from epics import PV
import matplotlib.pyplot as plt
import APSpy.spec as spec
import APSpy.macros as mac
import APSpy.rst_table as rst_table
import APSpy.AD as AD

from scipy.special import erf
from scipy.optimize import curve_fit
from pprint import pprint

#################################################
### THIS IS THE INSTALL FOR NOW
### POINTS AT THE FOLDER WHERE THE PYTHON SOURCE FILES ARE
### THIS WILL BE IMPROVED
#################################################
sys.path.insert(0, '/home/beams/S1IDUSER/APSpy/src')

alldone = PyEpics.PV('1idc:alldone')

### SHOULDNT THIS BE PART OF THE STANDARD LIB?
def ImportMotorSymbols():
    exec( spec.DefineMotorSymbols( spec.mtrDB, make_global=True ) )
        
#################################################
# USER MODULES
#################################################
def attnSX ():
    attn1.put(0)
    attn2.put(0)
    attn3.put(0)
    attn4.put(0)

def attnPowder ():
    attn1.put(1)
    attn2.put(1)
    attn3.put(1)
    attn4.put(0)
    
###################################################    
### ENABLE EPICS
### WILL BE IN SIM MODE IF EPICS PACKAGE DOES NOT EXIST
###################################################    
spec.EnableEPICS()

###################################################    
### DEF MOTORS & SCALERS
###################################################
# spec.DefineMtr('samX', '1idc:m77', 'samXC (mm)')
# spec.DefineMtr('samY', '1idc:m69', 'samYC (mm)')
# spec.DefineMtr('samZ', '1idc:m78', 'samZC (mm)')
# spec.DefineMtr('aero', '1ide:m9', 'omega (deg)')
spec.DefineScaler('1id:scaler1',16)

ImportMotorSymbols()
spec.ListMtrs()

###################################################    
### DEF PVs OF INTEREST
###################################################
attn1 = PyEpics.PV("1id:9440:1:bo_0.VAL")
attn2 = PyEpics.PV("1id:9440:1:bo_1.VAL")
attn3 = PyEpics.PV("1id:9440:1:bo_2.VAL")
attn4 = PyEpics.PV("1id:9440:1:bo_3.VAL")

###################################################    
### INITIATE LOGGING
###################################################
# mac.init_logging()
# mac.add_logging_PV('GE_fname',GE_prefix+"FileName",as_string=True)
# mac.add_logging_PV('GE_fnum',GE_prefix+"FileNumber")
# mac.add_logging_motor(samY)
# mac.add_logging_Global('S0','spec.S[0]')

###################################################
### BASIC USER INPUT
###################################################
# logname = '/home/beams/S1IDUSER/new_data/balogh_march14/balogh_march14.pypar' ## PATH WHERE PAR FILE LIVES
