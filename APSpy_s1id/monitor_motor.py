import sys
import os
import numpy
import scipy
import math
import logging
import time

import datetime as dt
import epics as PyEpics
import matplotlib.pyplot as plt
import APSpy.spec as spec
import APSpy.macros as mac
import APSpy.rst_table as rst_table
import APSpy.AD as AD

# import APSpy.macros_1id as mac1id
# import APSpy.fpga_1id as fpga1id                # qdo ./macros_PK/FPGA_2013Aug11/FPGA_signals.mac 
# import APSpy.AD_1id as AD1id                    # qdo ./macros_PK/hydra_2013Aug11/use_hydra.mac

# import APSpy.hookup_1id as hookup1id            # qdo ./macros_PK/fastsweep_BCEhutch_preci_prrot_aero_GE_Retiga_2013Aug11/hookup_macros.mac
# import APSpy.sweep_core_1id as sweepcore1id
# import APSpy.gate_1id as gate1id
# import APSpy.counters_1id as counters1id
# import APSpy.motor_1id as motor1id
# import APSpy.scanrecord_1id as scanrecord1id

# import APSpy.dic_1id as dic1id                  # qdo ./macros_PK/DIC_macros.mac

#################################################
### THIS IS THE INSTALL FOR NOW
### POINTS AT THE FOLDER WHERE THE PYTHON SOURCE FILES ARE
### THIS WILL BE IMPROVED
#################################################
sys.path.insert(0, '/home/beams/S1IDUSER/new_data/1id_python/APSpy_1id/src')

alldoneC = PyEpics.PV('1idc:alldone')
alldoneE = PyEpics.PV('1ide:alldone')

spec.EnableEPICS()

def ImportMotorSymbols():
    exec( spec.DefineMotorSymbols( spec.mtrDB, make_global=True ) )

###################################################
### USER INPUT
###################################################
pname = "/home/1-id/s1iduser/1id_python/APSpy_1id/src/testing/motor_monitor"

###################################################    
### DEF MOTORS
###################################################
# C MOTORS
nmtrC = 96
for i in range(1, nmtrC+1):
    symstr = 'm' + str(i) + 'c'
    prefixstr = '1idc:m' + str(i)
    spec.DefineMtr(symstr, prefixstr, '')
    
# E MOTORS
spec.DefineMtr('m1e', '1ide:m1', '')
spec.DefineMtr('m2e', '1ide:m2', '')
spec.DefineMtr('m3e', '1ide:m3', '')
spec.DefineMtr('m4e', '1ide:m4', '')
spec.DefineMtr('m6e', '1ide:m6', '')
spec.DefineMtr('m7e', '1ide:m7', '')
spec.DefineMtr('m8e', '1ide:m8', '')
spec.DefineMtr('m9e', '1ide:m9', '')

# E1 MOTORS
nmtrE1 = 104
for i in range(1, nmtrE1+1):
    symstr = 'm' + str(i) + 'e1'
    prefixstr = '1ide1:m' + str(i)
    spec.DefineMtr(symstr, prefixstr, '')

###################################################    
### START MONITORING
###################################################
nmtr = len(spec.mtrDB)

#################################################
# PV RECORD
#################################################       
while True:
    for i in range(0, nmtr+1):
        print time.ctime()
        print 'monitoring in progress'
        print 'do not shut off unless authorized by ali'
        idx = 1000 + i
        idxstr = 'mtr' + str(idx)

        mtr = spec.mtrDB[idxstr]
        t = time.localtime()
        
        fname = mtr.symbol + "_" + str(t[0]) + "_" + str(t[1]) + "_" + str(t[2]) + "_" + str(t[3]) + "_" + str(t[4]) + ".data"
        pfname = os.path.join(pname, fname)

        ## hdf5_db = h5py.File('myfile.hdf5','r')
        mtr.mtr_pv.show_all()
        mtr.mtr_pv.write_state(pfname)
        
    spec.sleep(30*60)
