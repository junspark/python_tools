### TODO ###
### RUN /APSshare/anaconda/x86_64/bin/ipython --pylab='auto'
### FOR EPICS SCREEN epics_1edd
### DEPRECATED: NEED TO RUN /APSshare/epd/rh6-x86_64/bin/ipython --pylab='auto'
### DEFINE SCALARS
### SHUTTER CONTROL IN 1BMB
### PAR FILE LOGS
### REAL TIME FITTING
import os
import sys
import numpy
import scipy
import math
import logging
import time
import rlcompleter
import readline

import datetime as dt
import epics as PyEpics
import matplotlib.pyplot as plt
import APSpy.spec as spec
import APSpy.macros as mac
import APSpy.rst_table as rst_table
import utilities as utils

from scipy.special import erf
from scipy.optimize import curve_fit
from pprint import pprint
from mpl_toolkits.mplot3d import axes3d

#### ENABLE TAB COMPLETION
readline.parse_and_bind('tab: complete')

#################################################
### THIS IS THE INSTALL FOR NOW
### POINTS AT THE FOLDER WHERE THE PYTHON SOURCE FILES ARE
### THIS WILL BE IMPROVED
#################################################
# sys.path.insert(0, '/home/beams/S1IDUSER/APSpy/src')

#################################################
### OTHER FUNCTIONS
#################################################
### SHOULDNT THIS BE PART OF THE STANDARD LIB?
def ImportMotorSymbols():
    exec( spec.DefineMotorSymbols( spec.mtrDB, make_global=True ) )

def waitmove():
    while not alldone.get():
        spec.sleep(1)
    logging.info("keep waiting for motor(s) to stop? " + str(alldone.get() != 1) )

spec.EnableEPICS()

###################################################
### USER INPUT
###################################################

###################################################
### SCRIPT TESTING MODE FLAG
###################################################
testing_flag = False

###################################################
### PATH NAME OF THE DATA FILES
datafile_pname = '/home/beams/S1IDUSER/mnt/s1b/__eval/APSpy_s1bm/data-template'

###################################################
### PATH AND FILE NAME OF THE PAR FILE
logfile_pname = '/home/beams/S1IDUSER/mnt/s1b/__eval/APSpy_s1bm'
logfile_fname = 'template_TOA_XX_samplename.pypar'
logfile_pfname = os.path.join(logfile_pname, logfile_fname);

###################################################
### DIFFRACTION VOLUME COORDINATES
dv_crd_file = True
dv_crd_pname = '/home/beams/S1BMUSER/Desktop/Data/parkjs/parkjs_dec14_edd'
dv_crd_fname = 'dv_crd_cat.dvcrd.csv'
dv_crd_pfname = os.path.join(dv_crd_pname, dv_crd_fname)

### REFERENCE POSITION
### x0, y0, z0 DEFINE THE CENTER OF THE SCAN
### dx, dy, dz DEFINE THE RANGE OF THE SCAN
# dv_crd_file = False
# x0 = -19.764
# y0 = -66.313
# z0 = 6.775

# dx = 77.064
# x_steps = 385

# dy = 0.0
# y_steps = 1

# dz = 7.2
# z_steps = 5

###################################################
## EXPOSURE TIME
tframe = 3.0

###################################################
## Number of iterations over the DVs
NumIterations = 1

###################################################
### END OF USER INPUT
###################################################

###################################################
### CREATE DATA FOLDER IF IT DOES NOT EXIST
###################################################
if os.path.exists(datafile_pname):
    print '###################################################'
    print 'Path for data files exists'
    print '###################################################'
else:
    print '###################################################'
    print 'Creating path for data files'
    print '###################################################'
    os.makedirs(datafile_pname)
    
###################################################
### DEFINE DV COORDINATES
###################################################
if dv_crd_file is True:
    print '###################################################'
    print 'Using predefined diffraction volume coordinates file'
    print dv_crd_pfname
    print '###################################################'
    xyz = numpy.loadtxt(dv_crd_pfname, comments = '#', skiprows = 0, dtype = float, delimiter=',')
    
    xx = xyz[:,0];
    yy = xyz[:,1];
    zz = xyz[:,2];
    ct = len(xx)
elif dv_crd_file is False:
    print '###################################################'
    print 'Generating diffraction volume grid'
    print 'Using reference position and step size information'
    print '###################################################'
    
    ### GENERATE DV GRID 
    x_ini = x0 - dx/2
    x_fin = x0 + dx/2
    x_grid = numpy.linspace(x_ini, x_fin, x_steps)
    
    y_ini = y0 - dy/2
    y_fin = y0 + dy/2
    y_grid = numpy.linspace(y_ini, y_fin, y_steps)
    
    z_ini = z0 - dz/2
    z_fin = z0 + dz/2
    z_grid = numpy.linspace(z_ini, z_fin, z_steps)
    
    xx = numpy.zeros(x_steps*y_steps*z_steps)
    yy = numpy.zeros(x_steps*y_steps*z_steps)
    zz = numpy.zeros(x_steps*y_steps*z_steps)
    
    ct = 0
    for i in range(x_steps):
        for j in range(y_steps):
            for k in range(z_steps):
                xx[ct] = x_grid[i]
                yy[ct] = y_grid[j]
                zz[ct] = z_grid[k]
                ct = ct + 1

print '###################################################'
print 'total number of grid points : ' + str(ct)
print 'total scan time (s)       : ' + str(ct*tframe)
print 'total scan time (m)       : ' + str(ct*tframe/60)
print 'total scan time (h)       : ' + str(ct*tframe/60/60)
print '###################################################'

plt.close('all')
fig1 = plt.figure()
ax1 = fig1.add_subplot(111, projection='3d')
ax1.plot(xx, yy, zz, 'o', zdir='z')
ax1.set_xlabel('sam X (mm)')
ax1.set_ylabel('sam Y (mm)')
ax1.set_zlabel('sam Z (mm)')
ax1.view_init(45, 45)
plt.show(block=True)
plt.show()
# sys.exit()

###################################################
### END OF DEFINE DV COORDINATES
###################################################

###################################################    
### DEFINE MOTORS & SCALARS & SPECIAL PVs
###################################################
if testing_flag is True:
    spec.DefineMtr('samX',  '1ide1:m93', 'samX (mm)')
    spec.DefineMtr('samY',  '1ide1:m94', 'samY (mm)')
    spec.DefineMtr('samZ',  '1ide1:m95', 'samZ (mm)')
elif testing_flag is False:
    # execfile('configs/1bmb_config.py')
	execfile('configs/6bma_config.py')

ImportMotorSymbols()
spec.ListMtrs()

### INTERSTING PVs
ring_current = PyEpics.PV('S:SRcurrentAI')

# sys.exit()

###################################################    
### END OF DEFINE MOTORS & SCALARS
###################################################

###################################################    
### MCA DETECTOR SETUP
###################################################
if testing_flag is True:
    PyEpics.caput(h_det_fname_pv, 'dummy_h_det', 3.0, 'wait=True')
    PyEpics.caput(h_det_fnum_pv, 1.0, 3.0, 'wait=True')
    
    PyEpics.caput(v_det_fname_pv, 'dummy_v_det', 3.0, 'wait=True')
    PyEpics.caput(v_det_fnum_pv, 1.0, 3.0, 'wait=True')
elif testing_flag is False:
    horz_EraseStart = PyEpics.PV(horz_prefix+'EraseStart')
    horz_status = PyEpics.PV(horz_prefix+'.ACQG')
    horz_val = PyEpics.PV(horz_prefix+'.VAL')
    horz_exptime = PyEpics.PV(horz_prefix+'.PRTM')
    
    vert_EraseStart = PyEpics.PV(vert_prefix+'EraseStart')
    vert_status = PyEpics.PV(vert_prefix+'.ACQG')
    vert_val = PyEpics.PV(vert_prefix+'.VAL')
    vert_exptime = PyEpics.PV(vert_prefix+'.PRTM')

###################################################    
### END OF MCA DETECTOR SETUP
###################################################

###################################################
### SET DUMMY PVS FOR METADATA PADDING
###################################################
PyEpics.caput(dummy_num_pv, -999.0, 3.0, 'wait=True')
PyEpics.caput(dummy_str_pv, 'nan', 3.0, 'wait=True')
PyEpics.caput(dummy_h1_num_pv, -999.0, 3.0, 'wait=True')
PyEpics.caput(dummy_h1_str_pv, 'nan', 3.0, 'wait=True')
PyEpics.caput(dummy_v1_num_pv, -999.0, 3.0, 'wait=True')
PyEpics.caput(dummy_v1_str_pv, 'nan', 3.0, 'wait=True')
PyEpics.caput(dummy_h2_num_pv, tframe, 3.0, 'wait=True')
PyEpics.caput(dummy_h2_str_pv, 'nan', 3.0, 'wait=True')
PyEpics.caput(dummy_v2_num_pv, tframe, 3.0, 'wait=True')
PyEpics.caput(dummy_v2_str_pv, 'nan', 3.0, 'wait=True')
###################################################

# sys.exit()

###################################################    
### INITATE LOGGING
###################################################
mac.init_logging()
if testing_flag is True:
    mac.add_logging_PV('Epoch Time', '1bmb:GTIM_TIME')
    mac.add_logging_PV('Elapsed Time','1edd:3820:scaler1.T')
    mac.add_logging_PV('Iring','S:SRcurrentAI')
    mac.add_logging_PV('Undulator value', dummy_num_pv)
    mac.add_logging_PV('Energy Nominal', dummy_num_pv)
    mac.add_logging_PV('Energy Calibrated', dummy_num_pv)
    mac.add_logging_PV('Foil Position', dummy_num_pv)
    mac.add_logging_PV('Attenuator Position', dummy_num_pv)
    
    mac.add_logging_PV('H det fname', h_det_fname_pv)
    mac.add_logging_PV('H det fnumber', h_det_fnum_pv)
    mac.add_logging_PV('H det frames per file', dummy_num_pv)
    mac.add_logging_PV('H det time per frame', dummy_h2_num_pv)
    
    mac.add_logging_PV('V det fname', v_det_fname_pv)
    mac.add_logging_PV('V det fnumber', v_det_fnum_pv)
    mac.add_logging_PV('V det frames per file', dummy_num_pv)
    mac.add_logging_PV('V det time per frame', dummy_v2_num_pv)
    
    mac.add_logging_PV('det3 fname', dummy_str_pv)
    mac.add_logging_PV('det3 fnumber', dummy_num_pv)
    mac.add_logging_PV('det3 frames per file', dummy_num_pv)
    mac.add_logging_PV('det3 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det4 fname', dummy_str_pv)
    mac.add_logging_PV('det4 fnumber', dummy_num_pv)
    mac.add_logging_PV('det4 frames per file', dummy_num_pv)
    mac.add_logging_PV('det4 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det5 fname', dummy_str_pv)
    mac.add_logging_PV('det5 fnumber', dummy_num_pv)
    mac.add_logging_PV('det5 frames per file', dummy_num_pv)
    mac.add_logging_PV('det5 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det6 fname', dummy_str_pv)
    mac.add_logging_PV('det6 fnumber', dummy_num_pv)
    mac.add_logging_PV('det6 frames per file', dummy_num_pv)
    mac.add_logging_PV('det6 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det7 fname', dummy_str_pv)
    mac.add_logging_PV('det7 fnumber', dummy_num_pv)
    mac.add_logging_PV('det7 frames per file', dummy_num_pv)
    mac.add_logging_PV('det7 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det8 fname', dummy_str_pv)
    mac.add_logging_PV('det8 fnumber', dummy_num_pv)
    mac.add_logging_PV('det8 frames per file', dummy_num_pv)
    mac.add_logging_PV('det8 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det9 fname', dummy_str_pv)
    mac.add_logging_PV('det9 fnumber', dummy_num_pv)
    mac.add_logging_PV('det9 frames per file', dummy_num_pv)
    mac.add_logging_PV('det9 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det10 fname', dummy_str_pv)
    mac.add_logging_PV('det10 fnumber', dummy_num_pv)
    mac.add_logging_PV('det10 frames per file', dummy_num_pv)
    mac.add_logging_PV('det10 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('IC0-front', dummy_num_pv)
    mac.add_logging_PV('IC0-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC1-back', dummy_num_pv)
    mac.add_logging_PV('IC1-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC2', dummy_num_pv)
    mac.add_logging_PV('IC2-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC3', dummy_num_pv)
    mac.add_logging_PV('IC3-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC4', dummy_num_pv)
    mac.add_logging_PV('IC4-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC5', dummy_num_pv)
    mac.add_logging_PV('IC5-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC6', dummy_num_pv)
    mac.add_logging_PV('IC6-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC7', dummy_num_pv)
    mac.add_logging_PV('IC7-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC8', dummy_num_pv)
    mac.add_logging_PV('IC8-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC9', dummy_num_pv)
    mac.add_logging_PV('IC9-setting', dummy_num_pv)
    
    mac.add_logging_PV('samX', dummy_num_pv)  # MOTORS mac.add_logging_motor(samX) ### NEED A PV OR MOTOR
    mac.add_logging_PV('samY', dummy_num_pv)  # MOTORS mac.add_logging_motor(samX) ### NEED A PV OR MOTOR
    mac.add_logging_PV('samZ', dummy_num_pv)  # MOTORS mac.add_logging_motor(samX) ### NEED A PV OR MOTOR
    
    mac.add_logging_PV('RX', dummy_num_pv)
    mac.add_logging_PV('RY', dummy_num_pv)
    mac.add_logging_PV('RZ', dummy_num_pv)
    
    mac.add_logging_PV('samX2', dummy_num_pv)
    mac.add_logging_PV('samY2', dummy_num_pv)
    mac.add_logging_PV('samZ2', dummy_num_pv)
    
    mac.add_logging_PV('samZ3', dummy_num_pv)
    
    mac.add_logging_PV('HPx', dummy_num_pv)         ### MOTORS mac.add_logging_motor(samX) ### NEED A MOTOR
    mac.add_logging_PV('HPth', dummy_num_pv)        ### MOTORS mac.add_logging_motor(samX) ### NEED A MOTOR
    mac.add_logging_PV('H det pos3', dummy_num_pv)
    
    mac.add_logging_PV('VPx', dummy_num_pv)         ### MOTORS mac.add_logging_motor(samX) ### NEED A MOTOR
    mac.add_logging_PV('VPth', dummy_num_pv)        ### MOTORS mac.add_logging_motor(samX) ### NEED A MOTOR
    mac.add_logging_PV('V det pos3', dummy_num_pv)
    
    mac.add_logging_PV('det3 pos1', dummy_num_pv)
    mac.add_logging_PV('det3 pos2', dummy_num_pv)
    mac.add_logging_PV('det3 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det4 pos1', dummy_num_pv)
    mac.add_logging_PV('det4 pos2', dummy_num_pv)
    mac.add_logging_PV('det4 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det5 pos1', dummy_num_pv)
    mac.add_logging_PV('det5 pos2', dummy_num_pv)
    mac.add_logging_PV('det5 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det6 pos1', dummy_num_pv)
    mac.add_logging_PV('det6 pos2', dummy_num_pv)
    mac.add_logging_PV('det6 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det7 pos1', dummy_num_pv)
    mac.add_logging_PV('det7 pos2', dummy_num_pv)
    mac.add_logging_PV('det7 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det8 pos1', dummy_num_pv)
    mac.add_logging_PV('det8 pos2', dummy_num_pv)
    mac.add_logging_PV('det8 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det9 pos1', dummy_num_pv)
    mac.add_logging_PV('det9 pos2', dummy_num_pv)
    mac.add_logging_PV('det9 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det10 pos1', dummy_num_pv)
    mac.add_logging_PV('det10 pos2', dummy_num_pv)
    mac.add_logging_PV('det10 pos3', dummy_num_pv)
    
    mac.add_logging_PV('hex pos1', dummy_num_pv)
    mac.add_logging_PV('hex pos2', dummy_num_pv)
    mac.add_logging_PV('hex pos3', dummy_num_pv)
    mac.add_logging_PV('hex pos4', dummy_num_pv)
    mac.add_logging_PV('hex pos5', dummy_num_pv)
    mac.add_logging_PV('hex pos6', dummy_num_pv)
    mac.add_logging_PV('hex pos7', dummy_num_pv)
    
    mac.add_logging_PV('HPbot', dummy_num_pv) # mac.add_logging_motor(HPbot)
    mac.add_logging_PV('HPtop', dummy_num_pv) # mac.add_logging_motor(HPtop)
    mac.add_logging_PV('HPib', dummy_num_pv) # mac.add_logging_motor(HPib)
    mac.add_logging_PV('HPob', dummy_num_pv) # mac.add_logging_motor(HPob)
    
    mac.add_logging_PV('VPbot', dummy_num_pv) # mac.add_logging_motor(VPbot)
    mac.add_logging_PV('VPtop', dummy_num_pv) # mac.add_logging_motor(VPtop)
    mac.add_logging_PV('VPib', dummy_num_pv) # mac.add_logging_motor(VPib)
    mac.add_logging_PV('VPob', dummy_num_pv) # mac.add_logging_motor(VPob)
    
    mac.add_logging_PV('slit3 pos1', dummy_num_pv)
    mac.add_logging_PV('slit3 pos2', dummy_num_pv)
    mac.add_logging_PV('slit3 pos3', dummy_num_pv)
    mac.add_logging_PV('slit3 pos4', dummy_num_pv)
    
    mac.add_logging_PV('slit4 pos1', dummy_num_pv)
    mac.add_logging_PV('slit4 pos2', dummy_num_pv)
    mac.add_logging_PV('slit4 pos3', dummy_num_pv)
    mac.add_logging_PV('slit4 pos4', dummy_num_pv)
    
    mac.add_logging_PV('slit5 pos1', dummy_num_pv)
    mac.add_logging_PV('slit5 pos2', dummy_num_pv)
    mac.add_logging_PV('slit5 pos3', dummy_num_pv)
    mac.add_logging_PV('slit5 pos4', dummy_num_pv)
    
    mac.add_logging_PV('slit6 pos1', dummy_num_pv)
    mac.add_logging_PV('slit6 pos2', dummy_num_pv)
    mac.add_logging_PV('slit6 pos3', dummy_num_pv)
    mac.add_logging_PV('slit6 pos4', dummy_num_pv)
    
    mac.add_logging_PV('lens1 pos1', dummy_num_pv)
    mac.add_logging_PV('lens1 pos2', dummy_num_pv)
    
    mac.add_logging_PV('lens2 pos1', dummy_num_pv)
    mac.add_logging_PV('lens2 pos2', dummy_num_pv)
    
    mac.add_logging_PV('lens3 pos1', dummy_num_pv)
    mac.add_logging_PV('lens3 pos2', dummy_num_pv)
    
    mac.add_logging_PV('lens4 pos1', dummy_num_pv)
    mac.add_logging_PV('lens4 pos2', dummy_num_pv)
    
    mac.add_logging_PV('enc1', dummy_num_pv)
    mac.add_logging_PV('enc2', dummy_num_pv)
    mac.add_logging_PV('enc3', dummy_num_pv)
    mac.add_logging_PV('enc4', dummy_num_pv)
    mac.add_logging_PV('enc5', dummy_num_pv)
    mac.add_logging_PV('enc6', dummy_num_pv)
    mac.add_logging_PV('enc7', dummy_num_pv)
    mac.add_logging_PV('enc8', dummy_num_pv)
    mac.add_logging_PV('enc9', dummy_num_pv)
    mac.add_logging_PV('enc10', dummy_num_pv)
    
    mac.add_logging_PV('enc1', dummy_num_pv)
    mac.add_logging_PV('enc2', dummy_num_pv)
    mac.add_logging_PV('enc3', dummy_num_pv)
    mac.add_logging_PV('enc4', dummy_num_pv)
    mac.add_logging_PV('enc5', dummy_num_pv)
    mac.add_logging_PV('enc6', dummy_num_pv)
    mac.add_logging_PV('enc7', dummy_num_pv)
    mac.add_logging_PV('enc8', dummy_num_pv)
    mac.add_logging_PV('enc9', dummy_num_pv)
    mac.add_logging_PV('enc10', dummy_num_pv)
    
    mac.add_logging_PV('ev1', dummy_num_pv)
    mac.add_logging_PV('ev2', dummy_num_pv)
    mac.add_logging_PV('ev3', dummy_num_pv)
    mac.add_logging_PV('ev4', dummy_num_pv)
    mac.add_logging_PV('ev5', dummy_num_pv)
    mac.add_logging_PV('ev6', dummy_num_pv)
    mac.add_logging_PV('ev7', dummy_num_pv)
    mac.add_logging_PV('ev8', dummy_num_pv)
    mac.add_logging_PV('ev9', dummy_num_pv)
    mac.add_logging_PV('ev10', dummy_num_pv)
elif testing_flag is False:
    mac.init_logging()
    mac.add_logging_PV('Epoch Time', epoch_time_pv)
    mac.add_logging_PV('Elapsed Time', '%s.T' % scaler_name)
    mac.add_logging_PVobj('Iring', ring_current)
    mac.add_logging_PV('Undulator value', dummy_num_pv)
    mac.add_logging_PV('Energy Nominal', dummy_num_pv)
    mac.add_logging_PV('Energy Calibrated', dummy_num_pv)
    mac.add_logging_PV('Foil Position', dummy_num_pv)
    mac.add_logging_PV('Attenuator Position', dummy_num_pv)
    
    mac.add_logging_PV('H det fname', h_det_fname_pv)
    mac.add_logging_PV('H det fnumber', h_det_fnum_pv)
    mac.add_logging_PV('H det frames per file', dummy_num_pv)
    mac.add_logging_PV('H live elap time', '%s.ELTM' % horz_prefix)
    
    mac.add_logging_PV('V det fname', v_det_fname_pv)
    mac.add_logging_PV('V det fnumber', v_det_fnum_pv)
    mac.add_logging_PV('V det frames per file', dummy_num_pv)
    mac.add_logging_PV('V live elap time', '%s.ELTM' % vert_prefix)
    
    mac.add_logging_PV('det3 fname', dummy_str_pv)
    mac.add_logging_PV('det3 fnumber', dummy_num_pv)
    mac.add_logging_PV('det3 frames per file', dummy_num_pv)
    mac.add_logging_PV('det3 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det4 fname', dummy_str_pv)
    mac.add_logging_PV('det4 fnumber', dummy_num_pv)
    mac.add_logging_PV('det4 frames per file', dummy_num_pv)
    mac.add_logging_PV('det4 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det5 fname', dummy_str_pv)
    mac.add_logging_PV('det5 fnumber', dummy_num_pv)
    mac.add_logging_PV('det5 frames per file', dummy_num_pv)
    mac.add_logging_PV('det5 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det6 fname', dummy_str_pv)
    mac.add_logging_PV('det6 fnumber', dummy_num_pv)
    mac.add_logging_PV('det6 frames per file', dummy_num_pv)
    mac.add_logging_PV('det6 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det7 fname', dummy_str_pv)
    mac.add_logging_PV('det7 fnumber', dummy_num_pv)
    mac.add_logging_PV('det7 frames per file', dummy_num_pv)
    mac.add_logging_PV('det7 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det8 fname', dummy_str_pv)
    mac.add_logging_PV('det8 fnumber', dummy_num_pv)
    mac.add_logging_PV('det8 frames per file', dummy_num_pv)
    mac.add_logging_PV('det8 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det9 fname', dummy_str_pv)
    mac.add_logging_PV('det9 fnumber', dummy_num_pv)
    mac.add_logging_PV('det9 frames per file', dummy_num_pv)
    mac.add_logging_PV('det9 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('det10 fname', dummy_str_pv)
    mac.add_logging_PV('det10 fnumber', dummy_num_pv)
    mac.add_logging_PV('det10 frames per file', dummy_num_pv)
    mac.add_logging_PV('det10 time per frame', dummy_num_pv)
    
    mac.add_logging_PV('IC0-front', '%s_cts1.B' % scaler_name)
    mac.add_logging_PV('IC0-setting', ic0_preamp_sens_nA_pv)
    
    mac.add_logging_PV('IC1-back', '%s_cts1.C' % scaler_name)
    mac.add_logging_PV('IC1-setting', ic1_preamp_sens_nA_pv)
    
    mac.add_logging_PV('NULL', '%s_cts1.D' % scaler_name)
    mac.add_logging_PV('NULL-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC3', dummy_num_pv)
    mac.add_logging_PV('IC3-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC4', dummy_num_pv)
    mac.add_logging_PV('IC4-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC5', dummy_num_pv)
    mac.add_logging_PV('IC5-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC6', dummy_num_pv)
    mac.add_logging_PV('IC6-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC7', dummy_num_pv)
    mac.add_logging_PV('IC7-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC8', dummy_num_pv)
    mac.add_logging_PV('IC8-setting', dummy_num_pv)
    
    mac.add_logging_PV('IC9', dummy_num_pv)
    mac.add_logging_PV('IC9-setting', dummy_num_pv)
    
    mac.add_logging_motor(xr)
    mac.add_logging_motor(yr)
    mac.add_logging_motor(zr)
    
    mac.add_logging_motor(rotx)
    mac.add_logging_PV('RY', dummy_num_pv)
    mac.add_logging_motor(rotz)
    
    mac.add_logging_PV('samX2', dummy_num_pv)
    mac.add_logging_PV('samY2', dummy_num_pv)
    mac.add_logging_PV('samZ2', dummy_num_pv)
    
    mac.add_logging_PV('samZ3', dummy_num_pv)
    
    mac.add_logging_PV('HPx', dummy_num_pv)
    mac.add_logging_PV('HPth', dummy_num_pv)
    mac.add_logging_PV('H det pos3', dummy_num_pv)
    
    mac.add_logging_PV('VPx', dummy_num_pv)
    mac.add_logging_motor(ytth)
    mac.add_logging_PV('V det pos3', dummy_num_pv)
    
    mac.add_logging_PV('det3 pos1', dummy_num_pv)
    mac.add_logging_PV('det3 pos2', dummy_num_pv)
    mac.add_logging_PV('det3 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det4 pos1', dummy_num_pv)
    mac.add_logging_PV('det4 pos2', dummy_num_pv)
    mac.add_logging_PV('det4 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det5 pos1', dummy_num_pv)
    mac.add_logging_PV('det5 pos2', dummy_num_pv)
    mac.add_logging_PV('det5 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det6 pos1', dummy_num_pv)
    mac.add_logging_PV('det6 pos2', dummy_num_pv)
    mac.add_logging_PV('det6 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det7 pos1', dummy_num_pv)
    mac.add_logging_PV('det7 pos2', dummy_num_pv)
    mac.add_logging_PV('det7 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det8 pos1', dummy_num_pv)
    mac.add_logging_PV('det8 pos2', dummy_num_pv)
    mac.add_logging_PV('det8 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det9 pos1', dummy_num_pv)
    mac.add_logging_PV('det9 pos2', dummy_num_pv)
    mac.add_logging_PV('det9 pos3', dummy_num_pv)
    
    mac.add_logging_PV('det10 pos1', dummy_num_pv)
    mac.add_logging_PV('det10 pos2', dummy_num_pv)
    mac.add_logging_PV('det10 pos3', dummy_num_pv)
    
    mac.add_logging_PV('hex pos1', dummy_num_pv)
    mac.add_logging_PV('hex pos2', dummy_num_pv)
    mac.add_logging_PV('hex pos3', dummy_num_pv)
    mac.add_logging_PV('hex pos4', dummy_num_pv)
    mac.add_logging_PV('hex pos5', dummy_num_pv)
    mac.add_logging_PV('hex pos6', dummy_num_pv)
    mac.add_logging_PV('hex pos7', dummy_num_pv)
    
    mac.add_logging_motor(sl1r)
    mac.add_logging_motor(sl1l)
    mac.add_logging_motor(sl1t)
    mac.add_logging_motor(sl1b)
    
    mac.add_logging_motor(sl2r)
    mac.add_logging_motor(sl2l)
    mac.add_logging_motor(sl2t)
    mac.add_logging_motor(sl2b)
    
    mac.add_logging_motor(sl3r)
    mac.add_logging_motor(sl3l)
    mac.add_logging_motor(sl3t)
    mac.add_logging_motor(sl3b)
    
    mac.add_logging_motor(sl4r)
    mac.add_logging_motor(sl4l)
    mac.add_logging_motor(sl4t)
    mac.add_logging_motor(sl4b)
    
    mac.add_logging_PV('slit5 pos1', dummy_num_pv)
    mac.add_logging_PV('slit5 pos2', dummy_num_pv)
    mac.add_logging_PV('slit5 pos3', dummy_num_pv)
    mac.add_logging_PV('slit5 pos4', dummy_num_pv)
    
    mac.add_logging_PV('slit6 pos1', dummy_num_pv)
    mac.add_logging_PV('slit6 pos2', dummy_num_pv)
    mac.add_logging_PV('slit6 pos3', dummy_num_pv)
    mac.add_logging_PV('slit6 pos4', dummy_num_pv)
    
    mac.add_logging_PV('lens1 pos1', dummy_num_pv)
    mac.add_logging_PV('lens1 pos2', dummy_num_pv)
    
    mac.add_logging_PV('lens2 pos1', dummy_num_pv)
    mac.add_logging_PV('lens2 pos2', dummy_num_pv)
    
    mac.add_logging_PV('lens3 pos1', dummy_num_pv)
    mac.add_logging_PV('lens3 pos2', dummy_num_pv)
    
    mac.add_logging_PV('lens4 pos1', dummy_num_pv)
    mac.add_logging_PV('lens4 pos2', dummy_num_pv)
    
    mac.add_logging_PV('enc1', dummy_num_pv)
    mac.add_logging_PV('enc2', dummy_num_pv)
    mac.add_logging_PV('enc3', dummy_num_pv)
    mac.add_logging_PV('enc4', dummy_num_pv)
    mac.add_logging_PV('enc5', dummy_num_pv)
    mac.add_logging_PV('enc6', dummy_num_pv)
    mac.add_logging_PV('enc7', dummy_num_pv)
    mac.add_logging_PV('enc8', dummy_num_pv)
    mac.add_logging_PV('enc9', dummy_num_pv)
    mac.add_logging_PV('enc10', dummy_num_pv)
    
    mac.add_logging_PV('HP inst dead time', '%s.IDTIM' % horz_prefix)
    mac.add_logging_PV('HP ave dead time', '%s.DTIM' % horz_prefix)
    mac.add_logging_PV('HP real elap time', '%s.ERTM' % horz_prefix)
    mac.add_logging_PV('VP inst dead time', '%s.IDTIM' % vert_prefix)
    mac.add_logging_PV('VP ave dead time', '%s.DTIM' % vert_prefix)
    mac.add_logging_PV('VP real elap time', '%s.ERTM' % vert_prefix)
    mac.add_logging_PV('iteration number', iter_number_pv)
    mac.add_logging_PV('position number', pos_number_pv)
    mac.add_logging_PV('file id number', fid_number_pv)
    mac.add_logging_PV('ev10', dummy_num_pv)
    
    sys.exit()
    
###################################################    
### END OF INITATE LOGGING
###################################################

###################################################    
### PERFORM SCANS
###################################################
mac.write_logging_header(logfile_pfname)

if testing_flag is True:
    print '###################################################'
    print 'In simulation exposure mode'
    print 'Detector exposure time will not be set'
    print '###################################################'
elif testing_flag is False:
    print '###################################################'
    print 'Setting detector exposure time'
    PyEpics.caput(horz_prefix + '.PRTM', tframe, 3.0, 'wait=True')
    PyEpics.caput(vert_prefix + '.PRTM', tframe, 3.0, 'wait=True')
    print '###################################################'

for t in range(NumIterations):
    ### PREP STATUS PLOT
    plt.ion()
    plt.close('all')
    fig1 = plt.figure(figsize=plt.figaspect(1))
    ax = fig1.add_subplot(1, 1, 1, projection='3d')
    ax.view_init(45, 45)
    plt.show(block=False)
    
    for i in range(ct):
        FileIDNumber = ct * t + i
        
        ### INPUT INFORMATION INTO PVS
        PyEpics.caput(iter_number_pv, t, 3.0, 'wait=True')
        PyEpics.caput(pos_number_pv, i, 3.0, 'wait=True')
        PyEpics.caput(fid_number_pv, FileIDNumber, 3.0, 'wait=True')
        
        ### COMPUTE PREAMP SETTINGS AND INPUT INTO PV
        s = PyEpics.caget(ic0_preamp_sens_pv)
        u = PyEpics.caget(ic0_preamp_unit_pv)
        s_nA = utils.PreampUnitConversion(str(s), str(u))
        PyEpics.caput(ic0_preamp_sens_nA_pv, s_nA, 3.0, 'wait=True')
        
        s = PyEpics.caget(ic1_preamp_sens_pv)
        u = PyEpics.caget(ic1_preamp_unit_pv)
        s_nA = utils.PreampUnitConversion(str(s), str(u))
        PyEpics.caput(ic1_preamp_sens_nA_pv, s_nA, 3.0, 'wait=True')
        
        tic = time.time()
        print '###################################################'
        print 'loop %d of %d' % (t, NumIterations)
        print 'scanning at %d of %d' % (i, ct)
        print 'file id number %d' % FileIDNumber
        print time.ctime()
        print '###################################################'
        print 'samX = %.3f' % xx[i]
        print 'samY = %.3f' % yy[i]
        print 'samZ = %.3f' % zz[i]
        targets = [(samX, xx[i]), (samY, yy[i]), (samZ, zz[i])]
        
        suptitle_txt = fig1.suptitle('diffraction volume grid # ' + str(i) + '/' + str(ct))
        suptitle_txt.set_text('diffraction volume grid # ' + str(i) + '/' + str(ct))
        ax.set_xlabel('samX (mm)')
        ax.set_ylabel('samY (mm)')
        ax.set_zlabel('samZ (mm)')
        ax.plot(xx, yy, zz, 'bo', zdir='z')
        ax.hold(True)
        if i == 0:
            ax.plot([xx[0]], [yy[0]], [zz[0]], 'yo')
        else:
            ax.plot([xx[i]], [yy[i]], [zz[i]], 'yo')
            ax.plot(xx[0:i], yy[0:i], zz[0:i], 'ro')
        ax.hold(False)
        plt.draw()

        # DEFINE DATA FILE NAMES
        horz_val_fname = 'horz_det_iter_%d_ptnum_%d_fid_%d_val.data' % (t, i, FileIDNumber)
        vert_val_fname = 'vert_det_iter_%d_ptnum_%d_fid_%d_val.data' % (t, i, FileIDNumber)
        
        PyEpics.caput(h_det_fname_pv, horz_val_fname, 3.0, 'wait=True')
        PyEpics.caput(v_det_fname_pv, vert_val_fname, 3.0, 'wait=True')
        
        horz_val_pfname = os.path.join(datafile_pname, horz_val_fname);
        vert_val_pfname = os.path.join(datafile_pname, vert_val_fname);
        
        ## MOVE AND EXPOSE
        if testing_flag is True:
            print '###################################################'
            print 'In simulation exposure mode'
            print 'Motors WILL NOT be moved'
            print 'Synthetic data will be generated'
            print '###################################################'
            
            ### GENERATE SYNTHETIC DATA
            spectrum_x = numpy.linspace(1, 500, 500)
            p0 = [100, 0.10, 1.1, 0.1, 1]
            p1 = [200, 0.12, 2.3, 0.1, 2]
            p2 = [175, 0.15, 4.1, 0.3, 4]
            
            spectrum_y0 = pkGaussian(spectrum_x, *p0)
            spectrum_y1 = pkGaussian(spectrum_x, *p1)
            spectrum_y2 = pkGaussian(spectrum_x, *p2)
            
            spectrum_y = spectrum_y0 + spectrum_y1 + spectrum_y2
            
            hval = spectrum_y + numpy.random.normal(size=len(spectrum_x))*25
            hbg = spectrum_y + numpy.random.normal(size=len(spectrum_x))*25
            
            vval = spectrum_y + numpy.random.normal(size=len(spectrum_x))*25
            vbg = spectrum_y + numpy.random.normal(size=len(spectrum_x))*25
            
            time.sleep(tframe)
            
        elif testing_flag is False:
            print '###################################################'
            print 'In experiment mode - Motors WILL be moved'
            print '###################################################'
            
            ## check motors have gotten to positions & wait until motion finished
            spec.mmv(targets,wait=False)
            spec.ummv(targets)
            
            ## Safety
            spec.sleep(0.2)
            
            ### CHECK FOR RING STATUS
            while ring_current.get() < 10:
                print 'waiting for ring to come back'
                spec.sleep(10)
                
            ### WAIT FOR SHUTTER IF CLOSED OR TRY TO OPEN
            while (shutter_state.get() is 0) and (ring_current.get() > 10):
                print 'waiting for shutter to open'
                shutter_control.put(1)
                spec.sleep(20)
                
            ### TAKE DATA
            horz_EraseStart.put(1)
            vert_EraseStart.put(1)
            
            ### SAFETY
            spec.sleep(0.5)
            
            ### WAIT TILL FINISHED
            scan_done = 0
            while scan_done == 0:
                ### 1 = RUNNING, 0 = DONE
                if (horz_status.get() == 0) and (vert_status.get() == 0):
                # if (horz_status.get() == 0):
                    scan_done = 1
                spec.sleep(0.5)
            
            ### GET SPECTRA DATA FROM DETECTOR
            hval = horz_val.get()
            vval = vert_val.get()
            
            spectrum_x = numpy.linspace(1, len(hval), len(hval))
        
        ### WRITE LOG FILE
        mac.write_logging_parameters(logfile_pfname)
        
        ### WRITE DATA FILE
        numpy.savetxt(horz_val_pfname, hval, fmt="%d")
        numpy.savetxt(vert_val_pfname, vval, fmt="%d")
        
        ### SAFETY 
        spec.sleep(1)
        toc = time.time() - tic
        print '###################################################'
        print 'Actual time for this scan (s) : %.3f' %(toc)
        print 'Time overhead (s)             : %.3f' %(toc - tframe)
        print '###################################################'
    spec.sleep(10)

print 'END OF SCAN - HOPE THE SCAN WORKED!!'
plt.ioff()    
sys.exit()
