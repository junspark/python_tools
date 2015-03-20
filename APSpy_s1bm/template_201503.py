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
sys.path.insert(0, '/home/beams/S1IDUSER/APSpy/src')

alldone = PyEpics.PV('1edd:alldone')

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

def pkGaussian(x, *p):
    # c0    : constant 4*log(2)
    # A     : intensity
    # x     : (tth-tth_peak)/Gamma
    # Gamma : FWHM
    c0 = 4*numpy.log(2)
    A, Gamma, xPeak, n0, n1 = p
    
    delx = (x - xPeak)/Gamma
    
    ybkg = numpy.polyval([n0, n1], x)
    yG = A*(c0**0.5/Gamma/numpy.pi**0.5)*numpy.exp(-c0*delx**2)
    ypk = ybkg + yG
    
    return ypk

spec.EnableEPICS()

###################################################
### USER INPUT
###################################################

###################################################
### SCRIPT TESTING MODE FLAG
###################################################
testing_flag = True

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
# dv_crd_file = True
# dv_crd_pname = '/home/beams/S1BMUSER/Desktop/Data/parkjs/parkjs_dec14_edd'
# dv_crd_fname = 'dv_crd_cat.dvcrd.csv'
# dv_crd_pfname = os.path.join(dv_crd_pname, dv_crd_fname)

### REFERENCE POSITION
### x0, y0, z0 DEFINE THE CENTER OF THE SCAN
### dx, dy, dz DEFINE THE RANGE OF THE SCAN
dv_crd_file = False
x0 = -19.764
y0 = -66.313
z0 = 6.775

dx = 77.064
x_steps = 385

dy = 0.0
y_steps = 1

dz = 7.2
z_steps = 5

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
    spec.DefineMtr('VPtop', '1edd:m3', 'VPtop (mm)')    ## COLOR CODED
    spec.DefineMtr('VPbot', '1edd:m4', 'VPbot (mm)')    ## COLOR CODED
    spec.DefineMtr('VPob',  '1edd:m5', 'VPob (mm)')    ## COLOR CODED
    spec.DefineMtr('VPib',  '1edd:m6', 'VPib (mm)')    ## COLOR CODED
    spec.DefineMtr('VPth',  '1edd:m16', 'VPtheta (deg)')        ## ELCO CABLE 1
    spec.DefineMtr('HPtop', '1edd:m8', 'HPtop (mm)')        ## PRINTER CABLE 14
    spec.DefineMtr('HPbot', '1edd:m7', 'HPbot (mm)')        ## PRINTER CABLE 17
    spec.DefineMtr('HPob',  '1edd:m2', 'HPob (mm)')        ## PRINTER CABLE 15
    spec.DefineMtr('HPib',  '1edd:m1', 'HPib (mm)')        ## PRINTER CABLE 16
    spec.DefineMtr('HPth',  '1edd:m9', 'HPtheta (deg)')     ## ELCO CABLE 7
    spec.DefineMtr('samX',  '1edd:m11', 'samX (mm)')        ## ELCO CABLE 3
    spec.DefineMtr('samY',  '1idc:m72', 'samY (mm)')        ## MOVOACT FROM C HUTCH ==> CHECK WHICH MOTOR IS ACTUALLY MOVING
    spec.DefineMtr('samY2',  '1edd:m14', 'samY2 (mm)')        ## ELCO CABLE 6
    spec.DefineMtr('samZ',  '1edd:m10', 'samZ (mm)')        ## ELCO CABLE 2

ImportMotorSymbols()
spec.ListMtrs()
# sys.exit()
### SCALARS
spec.DefineScaler('1edd:3820:scaler1',3)

### INTERSTING PVs
shutter_state = PyEpics.PV('PA:01BM:STA_A_FES_OPEN_PL.VAL')
shutter_control = PyEpics.PV('1bma:rShtrA:Open.PROC')
ring_current = PyEpics.PV('S:SRcurrentAI')

###################################################    
### END OF DEFINE MOTORS & SCALARS
###################################################

###################################################    
### MCA DETECTOR SETUP
###################################################
horz_prefix = 'dp_vortex_xrd76:mca1'
horz_EraseStart = PyEpics.PV(horz_prefix+'EraseStart')
horz_status = PyEpics.PV(horz_prefix+'.ACQG')
horz_val = PyEpics.PV(horz_prefix+'.VAL')
horz_bg = PyEpics.PV(horz_prefix+'.BG')

vert_prefix = 'dp_vortex_xrd73:mca1'
vert_EraseStart = PyEpics.PV(vert_prefix+'EraseStart')
vert_status = PyEpics.PV(vert_prefix+'.ACQG')
vert_val = PyEpics.PV(vert_prefix+'.VAL')
vert_bg = PyEpics.PV(vert_prefix+'.BG')

###################################################    
### END OF MCA DETECTOR SETUP
###################################################
dummy_num_pv = '1edd:userStringCalc10.L';
dummy_str_pv = '1edd:userStringCalc10.LL';
PyEpics.caput(dummy_num_pv, -999.0, 3.0, 'wait=True')
PyEpics.caput(dummy_str_pv, 'nan', 3.0, 'wait=True')

h_det_fname_pv = '1edd:userStringCalc10.AA';
h_det_fnum_pv = '1edd:userStringCalc10.AA';
h_det_prtm = horz_prefix+'.PRTM'


###################################################    
### INITATE LOGGING
###################################################
if testing_flag is True:
    mac.init_logging()
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
    
    
    mac.add_logging_PV('H det time per frame', '1bmb:userCalc10.A')     ### NEED A PV
    
    
    mac.add_logging_PV('V det fname', '1edd:userStringSeq10.STR2')  ### NEED A PV
    mac.add_logging_PV('V det fnumber', '1bmb:userCalc10.A')        ### NEED A PV
    mac.add_logging_PV('V det frames per file', '1bmb:userCalc10.A')    ### NEED A PV
    mac.add_logging_PV('V det time per frame', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('det3 fname', '1edd:userStringSeq10.STR2') ### NEED A PV
    mac.add_logging_PV('det3 fnumber', '1bmb:userCalc10.A')        ### NEED A PV
    mac.add_logging_PV('det3 frames per file', '1bmb:userCalc10.A')    ### NEED A PV
    mac.add_logging_PV('det3 time per frame', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('det4 fname', '1edd:userStringSeq10.STR2') ### NEED A PV
    mac.add_logging_PV('det4 fnumber', '1bmb:userCalc10.A')        ### NEED A PV
    mac.add_logging_PV('det4 frames per file', '1bmb:userCalc10.A')    ### NEED A PV
    mac.add_logging_PV('det4 time per frame', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('det5 fname', '1edd:userStringSeq10.STR2') ### NEED A PV
    mac.add_logging_PV('det5 fnumber', '1bmb:userCalc10.A')        ### NEED A PV
    mac.add_logging_PV('det5 frames per file', '1bmb:userCalc10.A')    ### NEED A PV
    mac.add_logging_PV('det5 time per frame', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('det6 fname', '1edd:userStringSeq10.STR2') ### NEED A PV
    mac.add_logging_PV('det6 fnumber', '1bmb:userCalc10.A')        ### NEED A PV
    mac.add_logging_PV('det6 frames per file', '1bmb:userCalc10.A')    ### NEED A PV
    mac.add_logging_PV('det6 time per frame', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('det7 fname', '1edd:userStringSeq10.STR2') ### NEED A PV
    mac.add_logging_PV('det7 fnumber', '1bmb:userCalc10.A')        ### NEED A PV
    mac.add_logging_PV('det7 frames per file', '1bmb:userCalc10.A')    ### NEED A PV
    mac.add_logging_PV('det7 time per frame', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('det8 fname', '1edd:userStringSeq10.STR2') ### NEED A PV
    mac.add_logging_PV('det8 fnumber', '1bmb:userCalc10.A')        ### NEED A PV
    mac.add_logging_PV('det8 frames per file', '1bmb:userCalc10.A')    ### NEED A PV
    mac.add_logging_PV('det8 time per frame', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('det9 fname', '1edd:userStringSeq10.STR2') ### NEED A PV
    mac.add_logging_PV('det9 fnumber', '1bmb:userCalc10.A')        ### NEED A PV
    mac.add_logging_PV('det9 frames per file', '1bmb:userCalc10.A')    ### NEED A PV
    mac.add_logging_PV('det9 time per frame', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('det10 fname', '1edd:userStringSeq10.STR2') ### NEED A PV
    mac.add_logging_PV('det10 fnumber', '1bmb:userCalc10.A')        ### NEED A PV
    mac.add_logging_PV('det10 frames per file', '1bmb:userCalc10.A')    ### NEED A PV
    mac.add_logging_PV('det10 time per frame', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('IC0-front','1edd:3820:scaler1_cts1.B')
    mac.add_logging_PV('IC0-setting', '1bmb:userCalc10.A')     ### NEEDS TO BE COMPUTED IN USER CALC THEN PUT IN
    
    mac.add_logging_PV('IC1-back','1edd:3820:scaler1_cts1.C')
    mac.add_logging_PV('IC1-setting', '1bmb:userCalc10.A')     ### NEEDS TO BE COMPUTED IN USER CALC THEN PUT IN
    
    mac.add_logging_PV('dummy IC1','1edd:3820:scaler1_cts1.C') ### NEED A PV
    mac.add_logging_PV('dummy IC1-setting', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy IC2','1edd:3820:scaler1_cts1.C') ### NEED A PV
    mac.add_logging_PV('dummy IC2-setting', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy IC3','1edd:3820:scaler1_cts1.C') ### NEED A PV
    mac.add_logging_PV('dummy IC3-setting', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy IC4','1edd:3820:scaler1_cts1.C') ### NEED A PV
    mac.add_logging_PV('dummy IC4-setting', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy IC5','1edd:3820:scaler1_cts1.C') ### NEED A PV
    mac.add_logging_PV('dummy IC5-setting', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy IC6','1edd:3820:scaler1_cts1.C') ### NEED A PV
    mac.add_logging_PV('dummy IC6-setting', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy IC7','1edd:3820:scaler1_cts1.C') ### NEED A PV
    mac.add_logging_PV('dummy IC7-setting', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy IC8','1edd:3820:scaler1_cts1.C') ### NEED A PV
    mac.add_logging_PV('dummy IC8-setting', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_motor(samX) ### NEED A PV OR MOTOR
    mac.add_logging_motor(samY) ### NEED A PV OR MOTOR
    mac.add_logging_motor(samZ) ### NEED A PV OR MOTOR
    
    mac.add_logging_motor(RX)   ### NEED A PV OR MOTOR
    mac.add_logging_motor(RY)   ### NEED A PV OR MOTOR
    mac.add_logging_motor(RZ)   ### NEED A PV OR MOTOR
    
    mac.add_logging_motor(samX2)    ### NEED A PV OR MOTOR
    mac.add_logging_motor(samY2)    ### NEED A PV OR MOTOR
    mac.add_logging_motor(samZ2)    ### NEED A PV OR MOTOR
    
    mac.add_logging_motor(samZ3)    ### NEED A PV OR MOTOR
    
    mac.add_logging_motor(Hx)       ### NEED A PV OR MOTOR
    mac.add_logging_motor(ThH)      ### NEED A PV OR MOTOR
    mac.add_logging_PV('H det pos3', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_motor(Vy)       ### NEED A PV OR MOTOR
    mac.add_logging_motor(ThV)      ### NEED A PV OR MOTOR
    mac.add_logging_PV('V det pos3', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy det1 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det1 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det1 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy det2 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det2 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det2 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy det3 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det3 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det3 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy det4 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det4 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det4 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy det5 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det5 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det5 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy det6 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det6 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det6 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy det7 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det7 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det7 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy det8 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det8 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy det8 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy hex pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy hex pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy hex pos3', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy hex pos4', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy hex pos5', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy hex pos6', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy hex pos7', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_motor(HPbot)    ### NEED A PV OR MOTOR
    mac.add_logging_motor(HPtop)    ### NEED A PV OR MOTOR
    mac.add_logging_motor(HPib)     ### NEED A PV OR MOTOR
    mac.add_logging_motor(HPob)     ### NEED A PV OR MOTOR
    
    mac.add_logging_motor(VPbot)    ### NEED A PV OR MOTOR
    mac.add_logging_motor(VPtop)    ### NEED A PV OR MOTOR
    mac.add_logging_motor(VPib)     ### NEED A PV OR MOTOR
    mac.add_logging_motor(VPob)     ### NEED A PV OR MOTOR
    
    mac.add_logging_PV('dummy slit1 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit1 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit1 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit1 pos4', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy slit2 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit2 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit2 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit2 pos4', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy slit3 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit3 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit3 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit3 pos4', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy slit4 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit4 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit4 pos3', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy slit4 pos4', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy lens1 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy lens1 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy lens2 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy lens2 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy lens3 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy lens3 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy lens4 pos1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy lens4 pos2', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('dummy encoder1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy encoder2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy encoder3', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy encoder4', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy encoder5', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy encoder6', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy encoder7', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy encoder8', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy encoder9', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('dummy encoder10', '1bmb:userCalc10.A')     ### NEED A PV
    
    mac.add_logging_PV('ev1', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('ev2', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('ev3', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('ev4', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('ev5', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('ev6', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('ev7', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('ev8', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('ev9', '1bmb:userCalc10.A')     ### NEED A PV
    mac.add_logging_PV('ev10', '1bmb:userCalc10.A')     ### NEED A PV
elif testing_flag is False:
    mac.init_logging()
    mac.add_logging_PV('Epoch Time', '1bmb:GTIM_TIME')
    mac.add_logging_PV('Elapsed Time','1edd:3820:scaler1.T')
    mac.add_logging_PV('Iring','S:SRcurrentAI')
    mac.add_logging_PV('SR Lifetime', 'BL01:srLifetime')
    
    
    mac.add_logging_PV('IC0-front','1edd:3820:scaler1_cts1.B')  
    mac.add_logging_PV('IC1-back','1edd:3820:scaler1_cts1.C')
    mac.add_logging_PV('NULL','1edd:3820:scaler1_cts1.D')
    mac.add_logging_PV('HP inst dead time','dp_vortex_xrd76:mca1.IDTIM')
    mac.add_logging_PV('HP ave dead time','dp_vortex_xrd76:mca1.DTIM')
    mac.add_logging_PV('HP real elap time','dp_vortex_xrd76:mca1.ERTM')
    mac.add_logging_PV('HP live elap time','dp_vortex_xrd76:mca1.ELTM')
    
    mac.add_logging_PV('VP inst dead time','dp_vortex_xrd73:mca1.IDTIM')
    mac.add_logging_PV('VP ave dead time','dp_vortex_xrd73:mca1.DTIM')
    mac.add_logging_PV('VP real elap time','dp_vortex_xrd73:mca1.ERTM')
    mac.add_logging_PV('VP live elap time','dp_vortex_xrd73:mca1.ELTM')
    
    mac.add_logging_PV('iteration number', '1edd:userCalc10.A')
    mac.add_logging_PV('position number', '1edd:userCalc10.B')
    mac.add_logging_PV('file id number', '1edd:userCalc10.C')
    mac.add_logging_PV('horz val file name', '1edd:userStringSeq10.STR1')
    mac.add_logging_PV('vert val file name', '1edd:userStringSeq10.STR2')
    mac.add_logging_motor(samX)
    mac.add_logging_motor(samY)
    mac.add_logging_motor(samY2)
    mac.add_logging_motor(samZ)
    mac.add_logging_motor(HPbot)
    mac.add_logging_motor(HPtop)
    mac.add_logging_motor(HPib)
    mac.add_logging_motor(HPob)
    mac.add_logging_motor(HPth)
    mac.add_logging_motor(VPbot)
    mac.add_logging_motor(VPtop)
    mac.add_logging_motor(VPib)
    mac.add_logging_motor(VPob)
    mac.add_logging_motor(VPth)

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
        PyEpics.caput('1edd:userCalc10.A', t, 3.0, 'wait=True')
        PyEpics.caput('1edd:userCalc10.B', i, 3.0, 'wait=True')
        PyEpics.caput('1edd:userCalc10.C', FileIDNumber, 3.0, 'wait=True')
        
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
        
        PyEpics.caput('1edd:userStringSeq10.STR1', horz_val_fname, 3.0, 'wait=True')
        PyEpics.caput('1edd:userStringSeq10.STR2', vert_val_fname, 3.0, 'wait=True')
        
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
