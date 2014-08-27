### TODO ###
### NEED TO RUN /APSshare/epd/rh6-x86_64/bin/ipython --pylab='auto'
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
testing_flag = False

###################################################
### PATH NAME OF THE DATA FILES
datafile_pname = '/home/beams/S1BMUSER/Desktop/Data/parkjs/APSpy_1bm_dev/data/'

###################################################
### PATH AND FILE NAME OF THE PAR FILE
logfile_pname = '/home/beams/S1BMUSER/Desktop/Data/parkjs/APSpy_1bm_dev'
logfile_fname = 'template_log.pypar'
logfile_pfname = os.path.join(logfile_pname, logfile_fname);

###################################################
### DIFFRACTION VOLUME COORDINATES
dv_crd_file = True
dv_crd_pname = '/home/beams/S1BMUSER/Desktop/Data/parkjs/APSpy_1bm_dev'
dv_crd_fname = 'dv_crd_example.dvcrd'
dv_crd_pfname = os.path.join(dv_crd_pname, dv_crd_fname)

### REFERENCE POSITION
# dv_crd_file = False
# x0 = -19.535
# y0 = -56.412
# z0 = -4.095
# dx = 2.7
# x_steps = 2

# dy = 45
# y_steps = 3

# dz = 0
# z_steps = 1

###################################################
## EXPOSURE TIME
tframe = 10

###################################################
### END OF USER INPUT
###################################################

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
    print 'Generating diffraction volume grid using reference position and step size information'
    print '###################################################'
    
    ### GENERATE DV GRID 
    x_ini = x0 - dx/2
    x_fin = x0 + dx/2
    x_grid = numpy.linspace(x_ini, x_fin, x_steps)
    
    y_ini = y0
    y_fin = y0 + dy
    y_grid = numpy.linspace(y_ini, y_fin, y_steps)
    
    z_ini = z0
    z_fin = z0 + dz
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

###################################################
### END OF DEFINE DV COORDINATES
###################################################

###################################################    
### DEFINE MOTORS & SCALARS & SPECIAL PVs
###################################################
if testing_flag is True:
    spec.DefineMtr('samX',  '1ide1:m97', 'samX (mm)')
    spec.DefineMtr('samY',  '1ide1:m98', 'samX (mm)')
    spec.DefineMtr('samZ',  '1ide1:m99', 'samX (mm)')
elif testing_flag is False:
    spec.DefineMtr('VPtop', '1edd:m3', 'VPtop (mm)')
    spec.DefineMtr('VPbot', '1edd:m4', 'VPbot (mm)')
    spec.DefineMtr('VPob',  '1edd:m5', 'VPob (mm)')
    spec.DefineMtr('VPib',  '1edd:m6', 'VPib (mm)')
    spec.DefineMtr('samX',  '1edd:m11', 'samX (mm)')
    spec.DefineMtr('samY',  '1edd:m14', 'samY (mm)')
    spec.DefineMtr('samZ',  '1edd:m10', 'samZ (mm)')

ImportMotorSymbols()
spec.ListMtrs()

### SCALARS
# spec.DefineScaler('1id:scaler1',16)

### INTERSTING PVs
shutter_state = PyEpics.PV('PA:01BM:A_SHTRS_CLOSED')
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

vert_prefix = 'dp_vortex_xrd75:mca1'
vert_EraseStart = PyEpics.PV(vert_prefix+'EraseStart')
vert_status = PyEpics.PV(vert_prefix+'.ACQG')
vert_val = PyEpics.PV(vert_prefix+'.VAL')
vert_bg = PyEpics.PV(vert_prefix+'.BG')

###################################################    
### END OF MCA DETECTOR SETUP
###################################################

###################################################    
### INITATE LOGGING
###################################################
mac.init_logging()
mac.add_logging_PV('Iring','S:SRcurrentAI')
mac.add_logging_PV('elapsed time','1edd:3820:scaler1.T")
mac.add_logging_PV('IC0-front','1edd:3820:scaler1_cts1.B')  
mac.add_logging_PV('IC1-back','1edd:3820:scaler1_cts1.C')
mac.add_logging_PV('NULL','1edd:3820:scaler1_cts1.D)
mac.add_logging_motor(samX)
mac.add_logging_motor(samY)
mac.add_logging_motor(samZ)
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
    PyEpics.caput(horz_prefix + '.PRTM', tframe)
    PyEpics.caput(vert_prefix + '.PRTM', tframe)
    print '###################################################'

sys.exit()
plt.ion()
fig1 = plt.figure(figsize=plt.figaspect(1))
plt.show()
for i in range(ct):
    print '###################################################'
    print 'scanning at ' 
    print 'samX = ' + str(round(xx[i],3)) + ' || ' + 'samY = ' + str(round(yy[i],3)) + ' || ' +  'samZ = ' + str(round(zz[i],3))
    targets = [(samX, xx[i]), (samY, yy[i]), (samZ, zz[i])]
    
    ax = fig1.add_subplot(2, 1, 2, projection='3d')
    ax.plot(xx, yy, zz, 'bo', zdir='z')
    ax.hold(True)
    if i == 0:
        ax.plot([xx[0]], [yy[0]], [zz[0]], 'yo')
    else:
        ax.plot([xx[i]], [yy[i]], [zz[i]], 'yo')
        ax.plot(xx[0:i], yy[0:i], zz[0:i], 'ro')
    ax.set_xlabel('sam X (mm)')
    ax.set_ylabel('sam Y (mm)')
    ax.set_zlabel('sam Z (mm)')
    ax.view_init(45, 45)
    ax.hold(False)
    plt.show(block=False)
    plt.draw()

    # DEFINE DATA FILE NAMES
    horz_val_fname = "horz_det_ptnum_" + str(i) + "_x_" + str(round(xx[i],3)) + "_y_" + str(round(yy[i],3)) + "_z_" + str(round(zz[i],3)) + '_val.data'
    vert_val_fname = "vert_det_ptnum_" + str(i) + "_x_" + str(round(xx[i],3)) + "_y_" + str(round(yy[i],3)) + "_z_" + str(round(zz[i],3)) + '_val.data'
    horz_bg_fname = "horz_det_ptnum_" + str(i) + "_x_" + str(round(xx[i],3)) + "_y_" + str(round(yy[i],3)) + "_z_" + str(round(zz[i],3)) + '_bg.data'
    vert_bg_fname = "vert_det_ptnum_" + str(i) + "_x_" + str(round(xx[i],3)) + "_y_" + str(round(yy[i],3)) + "_z_" + str(round(zz[i],3)) + '_bg.data'
    
    horz_val_pfname = os.path.join(datafile_pname, horz_val_fname);
    vert_val_pfname = os.path.join(datafile_pname, vert_val_fname);
    horz_bg_pfname = os.path.join(datafile_pname, horz_bg_fname);
    vert_bg_pfname = os.path.join(datafile_pname, vert_bg_fname);
    
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
        print 'In experiment mode'
        print 'Motors WILL be moved'
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
            
        ### OPEN SHUTTER IF CLOSED
        if shutter_state.get() == 1:
            shutter_control.put(0)
            spec.sleep(10)
            
        ### TAKE DATA
        horz_EraseStart.put(1)
        vert_EraseStart.put(1)
        
        ### WRITE LOG FILE
        mac.write_logging_parameters(logfile_pfname)
        
        ### WAIT TILL FINISHED
        scan_done = 0
        while scan_done == 0:
            ### 1 = RUNNING, 0 = DONE
            if (horz_status.get() == 0) and (vert_status.get() == 0):
                scan_done = 1
            spec.sleep(0.5)
        
        ### GET SPECTRA DATA FROM DETECTOR
        hval = horz_val.get()
        hbg = horz_bg.get()
        
        vval = vert_val.get()
        vbg = vert_bg.get()
    
    fig1.suptitle('diffraction volume grid # ' + str(i+1) + '/' + str(ct))
    
    ax = fig1.add_subplot(2, 1, 1)
    ax.plot(spectrum_x, hval, 'bo', spectrum_x, vval, 'b^', spectrum_x, hbg, 'go', spectrum_x, vbg, 'g^')
    ax.set_xlabel('channel number (-)')
    ax.set_ylabel('intensity (arb. units)')
    # ax.set_title('spectrum')
    ax.grid(True)
    ax.hold(False)
    plt.draw()
    
    numpy.savetxt(horz_val_pfname, hval, fmt="%d")
    numpy.savetxt(horz_bg_pfname, hbg, fmt="%d")
    
    numpy.savetxt(vert_val_pfname, hval, fmt="%d")
    numpy.savetxt(vert_bg_pfname, hbg, fmt="%d")
    
    ### SAFETY 
    spec.sleep(1)

print 'END OF SCAN - HOPE THE SCAN WORKED!!'
plt.ioff()    
sys.exit()
