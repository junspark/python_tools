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
import csv

import datetime as dt
import matplotlib.pyplot as plt

from scipy.special import erf
from scipy.optimize import curve_fit
from pprint import pprint
from mpl_toolkits.mplot3d import axes3d

#### ENABLE TAB COMPLETION
readline.parse_and_bind('tab: complete')

#################################################
### OTHER FUNCTIONS
#################################################
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

###################################################
### USER INPUT
### THIS MUST BE COPIED FROM DATA ACQUISITION FILE
###################################################

###################################################
### SCRIPT TESTING MODE FLAG
###################################################
testing_flag = True

###################################################
### PATH NAME OF THE DATA FILES
datafile_pname = '/home/beams/S1BMUSER/Desktop/Data/parkjs/APSpy_1bm_dev/data/'

###################################################
### PATH AND FILE NAME OF THE PKFIT FILES
hval_pkfit_fname = 'hval_pkfit.pkfit'
vval_pkfit_fname = 'vval_pkfit.pkfit'
hbg_pkfit_fname = 'hbg_pkfit.pkfit'
vbg_pkfit_fname = 'vbg_pkfit.pkfit'
hval_pkfit_pfname = os.path.join(datafile_pname, hval_pkfit_fname);
vval_pkfit_pfname = os.path.join(datafile_pname, vval_pkfit_fname);
hbg_pkfit_pfname = os.path.join(datafile_pname, hbg_pkfit_fname);
vbg_pkfit_pfname = os.path.join(datafile_pname, vbg_pkfit_fname);

###################################################
### PATH AND FILE NAME OF THE PAR FILE - NOT USED AT THIS POINT
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
## INITIAL GUESS FOR PEAK POSITIONS
## OTHER PARAMETERS ARE ESTIMATED FROM SPECTRUM
numpk = 3
pkpos = numpy.array([110, 230, 410])
pkLB = pkpos - 45
pkUB = pkpos + 45

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

###################################################
### END OF DEFINE DV COORDINATES
###################################################

###################################################    
### PERFORM SCANS
###################################################

plt.close('all')
plt.ion()
fig1 = plt.figure(figsize=plt.figaspect(1))
fig2 = plt.figure(figsize=plt.figaspect(0.5))
plt.show()
for i in range(ct):
    print '###################################################'
    print 'peak fitting at ' 
    print str(i) + ' : samX = ' + str(round(xx[i],3)) + ' || ' + 'samY = ' + str(round(yy[i],3)) + ' || ' +  'samZ = ' + str(round(zz[i],3))

    # DEFINE DATA FILE NAMES
    horz_val_fname = "horz_det_ptnum_" + str(i) + "_x_" + str(round(xx[i],3)) + "_y_" + str(round(yy[i],3)) + "_z_" + str(round(zz[i],3)) + '_val.data'
    vert_val_fname = "vert_det_ptnum_" + str(i) + "_x_" + str(round(xx[i],3)) + "_y_" + str(round(yy[i],3)) + "_z_" + str(round(zz[i],3)) + '_val.data'
    horz_bg_fname = "horz_det_ptnum_" + str(i) + "_x_" + str(round(xx[i],3)) + "_y_" + str(round(yy[i],3)) + "_z_" + str(round(zz[i],3)) + '_bg.data'
    vert_bg_fname = "vert_det_ptnum_" + str(i) + "_x_" + str(round(xx[i],3)) + "_y_" + str(round(yy[i],3)) + "_z_" + str(round(zz[i],3)) + '_bg.data'
    
    horz_val_pfname = os.path.join(datafile_pname, horz_val_fname);
    vert_val_pfname = os.path.join(datafile_pname, vert_val_fname);
    horz_bg_pfname = os.path.join(datafile_pname, horz_bg_fname);
    vert_bg_pfname = os.path.join(datafile_pname, vert_bg_fname);
    
    ## LOAD DATA FILES
    print '###################################################'
    while (os.path.isfile(horz_val_pfname) is False) or (os.path.isfile(vert_val_pfname) is False) or (os.path.isfile(horz_bg_pfname) is False) or (os.path.isfile(vert_bg_pfname) is False):
        print 'Files do not exist. Waiting ...'
        time.sleep(10)
    print '###################################################'
        
    print '###################################################'
    print 'Files exist & loaded for fitting'
    print '###################################################'
    hval = numpy.loadtxt(horz_val_pfname, dtype = int)
    vval = numpy.loadtxt(vert_val_pfname, dtype = int)
    hbg = numpy.loadtxt(horz_bg_pfname, dtype = int)
    vbg = numpy.loadtxt(vert_bg_pfname, dtype = int)
    spectrum_x = numpy.linspace(1, len(hval), len(hval))
    
    fig1.suptitle('diffraction volume grid # ' + str(i+1) + '/' + str(len(hval)))
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
    
    ax = fig1.add_subplot(2, 1, 1)
    ax.plot(spectrum_x, hval, 'bo', spectrum_x, vval, 'b^', spectrum_x, hbg, 'go', spectrum_x, vbg, 'g^')
    ax.set_xlabel('channel number (-)')
    ax.set_ylabel('intensity (arb. units)')
    ax.grid(True)
    ax.hold(False)
    fig1.show()
    
    ax1 = fig2.add_subplot(2, 2, 1);
    ax1.plot(spectrum_x, hval, 'bo')
    ax1.set_xlabel('channel number (-)')
    ax1.set_ylabel('intensity (arb. units)')
    ax1.set_title('h-val')
    ax1.grid(True)
    ax1.hold(True)
    
    ax2 = fig2.add_subplot(2, 2, 2);
    ax2.plot(spectrum_x, vval, 'b^')
    ax2.set_xlabel('channel number (-)')
    ax2.set_ylabel('intensity (arb. units)')
    ax2.set_title('h-val')
    ax2.grid(True)
    ax2.hold(True)
    
    ax3 = fig2.add_subplot(2, 2, 3);
    ax3.plot(spectrum_x, hbg, 'go')
    ax3.set_xlabel('channel number (-)')
    ax3.set_ylabel('intensity (arb. units)')
    ax3.set_title('h-val')
    ax3.grid(True)
    ax3.hold(True)
    
    ax4 = fig2.add_subplot(2, 2, 4);
    ax4.plot(spectrum_x, vbg, 'g^')
    ax4.set_xlabel('channel number (-)')
    ax4.set_ylabel('intensity (arb. units)')
    ax4.set_title('h-val')
    ax4.grid(True)
    ax4.hold(True)
    
    ### FITTING
    for j in range(numpk):
        print '###################################################'
        print 'peak number ' + str(j)
        
        idxLB = spectrum_x > pkLB[j]
        idxUB = spectrum_x < pkUB[j]
        
        xj = spectrum_x[idxLB & idxUB]
        hvalj = hval[idxLB & idxUB]
        vvalj = vval[idxLB & idxUB]
        hbgj = hbg[idxLB & idxUB]
        vbgj = vbg[idxLB & idxUB]

        ### CURVEFIT ROUTINES GOES HERE
        p0 = numpy.array([max(hvalj)/2, 2, pkpos[j], 0, numpy.mean(hvalj)])
        phvalj, cov = curve_fit(pkGaussian, xj, hvalj, p0=p0)
        hvalj_fit0 = pkGaussian(xj, *p0)
        hvalj_fit = pkGaussian(xj, *phvalj)
        
        pvvalj, cov = curve_fit(pkGaussian, xj, vvalj, p0=p0)
        vvalj_fit0 = pkGaussian(xj, *p0)
        vvalj_fit = pkGaussian(xj, *pvvalj)
        
        phbgj, cov = curve_fit(pkGaussian, xj, hbgj, p0=p0)
        hbgj_fit0 = pkGaussian(xj, *p0)
        hbgj_fit = pkGaussian(xj, *phbgj)
        
        pvbgj, cov = curve_fit(pkGaussian, xj, vbgj, p0=p0)
        vbgj_fit0 = pkGaussian(xj, *p0)
        vbgj_fit = pkGaussian(xj, *pvbgj)

        ax1.plot(xj, hvalj, 'ro', xj, hvalj_fit0, 'r-', xj, hvalj_fit, 'k-')
        ax2.plot(xj, vvalj, 'r^', xj, vvalj_fit0, 'r-', xj, vvalj_fit, 'k-')
        ax3.plot(xj, hbgj, 'ro', xj, hbgj_fit0, 'r-', xj, hbgj_fit, 'k-')
        ax4.plot(xj, vbgj, 'r^', xj, vbgj_fit0, 'r-', xj, vbgj_fit, 'k-')
        
    fig2.show()
    ax1.hold(False)
    ax2.hold(False)
    ax3.hold(False)
    ax4.hold(False)
    plt.draw()
    
    ### CURVE FIT RESULTS SAVE
    with open(hval_pkfit_pfname, 'a') as f_handle:
        outdata = numpy.append([i, round(xx[i],3), round(yy[i],3), round(zz[i],3)], phvalj, axis=2)
        f_handle.write('%d %f %f %f %f %f %f %f %f\n' % (outdata[0], outdata[1], outdata[2], outdata[3], outdata[4], outdata[5], outdata[6], outdata[7], outdata[8]))
        
    ### SAFETY 
    time.sleep(1)

print 'END OF SCAN - HOPE THE FITTING WORKED!!'
plt.ioff()    
sys.exit()
