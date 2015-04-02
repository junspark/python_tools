### TODO ###
### NEED TO ADD 
### RUN /APSshare/epd/rh6-x86_64/bin/ipython --pylab='auto'
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

from scipy.optimize import curve_fit
from scipy.optimize import minimize
from pprint import pprint
from mpl_toolkits.mplot3d import axes3d

#################################################
### PEAK FUNCTIONS
#################################################
def pkBackground(x, *p):
    '''
    pkBackground
    
    Polynominal background function using numpy.polyval
    If `p` is of length N, this function returns the value:

    ``p[0]*x**(N-1) + p[1]*x**(N-2) + ... + p[N-2]*x + p[N-1]``
    
    '''
    ybkg = numpy.polyval(p, x)
    return ybkg

def pkGaussian(x, *p):
    '''
    c0    : constant 4*log(2)
    A     : intensity
    x     : (tth-tth_peak)/Gamma
    Gamma : FWHM
    '''
    c0 = 4*numpy.log(2)
    
    A = p[0]
    Gamma = p[1]
    xPeak = p[2]
    
    pbkg = p[3:]
    ybkg = pkBackground(x, *pbkg)
    
    delx = (x - xPeak)/Gamma
    yG = A*(c0**0.5/Gamma/numpy.pi**0.5)*numpy.exp(-c0*delx**2)
    
    ypk = ybkg + yG
    return ypk

def pkLorentzian(x, *p):
    '''
    f = A*(c1^.5/Gamma/pi)./(1 + c1*x^2);
    c0 : constant 4
    A : intensity
    x : (tth-tth_peak)/Gamma
    Gamma : FWHM
    '''
    c1 = 4
    
    A = p[0]
    Gamma = p[1]
    xPeak = p[2]
    
    pbkg = p[3:]
    ybkg = pkBackground(x, *pbkg)
    
    delx = (x - xPeak)/Gamma
    yL = (A*c1**0.5/Gamma/numpy.pi)*(1 / (1 + c1*delx*delx))
    
    ypk = ybkg + yL
    return ypk

def pkPseudoVoight(x, *p):
    '''
    f = n * G + (1 - n) * L
    A     : intensity
    x     : (tth-tth_peak)/Gamma
    Gamma : FWHM
    n     : mixing parameter
    
    NEEDS CONSTRAINED OPTIMIZATION
    '''
    
    A = p[0]
    Gamma = p[1]
    n = p[2]
    xPeak = p[3]
    
    pbkg = p[4:]
    ybkg = pkBackground(x, *pbkg)
        
    pG = numpy.array([A, Gamma, xPeak])
    pL = numpy.array([A, Gamma, xPeak])
    
    print n
    
    yG = pkGaussian(x, *pG)
    yL = pkLorentzian(x, *pL)
    
    ypk = ybkg + n * yG + (1 - n) * yL
           
    return ypk

# def pkFunction(p, xdata, ydata):
#     pbkg = p[4:]
#     
#     
#     pkPseudoVoight(xdata, *p)
#     
#     
#     return resnorm
              
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
datafile_pname = '/home/beams/S1IDUSER/new_data/1id_python/APSpy_s1bm/data/'

###################################################
### OUTPUT PATH AND FILE NAME OF THE PKFIT FILES
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
logfile_pname = '/home/beams/S1IDUSER/new_data/1id_python/APSpy_s1bm/'
logfile_fname = 'template_log.pypar'
logfile_pfname = os.path.join(logfile_pname, logfile_fname);

###################################################
### DIFFRACTION VOLUME COORDINATES
dv_crd_file = True
dv_crd_pname = '/home/beams/S1IDUSER/new_data/1id_python/APSpy_s1bm/'
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
## INITIAL GUESS FOR PEAK POSITIONS
## OTHER PARAMETERS ARE ESTIMATED FROM SPECTRUM
###################################################
numpk = 3
pkpos = numpy.array([110., 230., 410.])
Gamma0 = numpy.array([5., 5., 5.])
        
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
### PERFORM FITS
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

        ### CURVE FIT
        A0 = max(hvalj)*Gamma0[j]
        p0 = numpy.array([A0, Gamma0[j], pkpos[j], 0.0, numpy.mean(hvalj)])
        
        phvalj, cov = curve_fit(pkLorentzian, xj, hvalj, p0=p0)
        hvalj_fit0 = pkLorentzian(xj, *p0)
        hvalj_fit = pkLorentzian(xj, *phvalj)
        
        pvvalj, cov = curve_fit(pkLorentzian, xj, vvalj, p0=p0)
        vvalj_fit0 = pkLorentzian(xj, *p0)
        vvalj_fit = pkLorentzian(xj, *pvvalj)
        
        phbgj, cov = curve_fit(pkLorentzian, xj, hbgj, p0=p0)
        hbgj_fit0 = pkLorentzian(xj, *p0)
        hbgj_fit = pkLorentzian(xj, *phbgj)
        
        pvbgj, cov = curve_fit(pkLorentzian, xj, vbgj, p0=p0)
        vbgj_fit0 = pkLorentzian(xj, *p0)
        vbgj_fit = pkLorentzian(xj, *pvbgj)
        
        ### SAVE CURVE FIT RESULTS
        with open(hval_pkfit_pfname, 'a') as f_handle:
            outdata = numpy.append([i, round(xx[i],3), round(yy[i],3), round(zz[i],3)], phvalj, axis=2)
            f_handle.write('%d %f %f %f %f %f %f %f %f\n' % (outdata[0], outdata[1], outdata[2], outdata[3], outdata[4], outdata[5], outdata[6], outdata[7], outdata[8]))
            
        with open(vval_pkfit_pfname, 'a') as f_handle:
            outdata = numpy.append([i, round(xx[i],3), round(yy[i],3), round(zz[i],3)], pvvalj, axis=2)
            f_handle.write('%d %f %f %f %f %f %f %f %f\n' % (outdata[0], outdata[1], outdata[2], outdata[3], outdata[4], outdata[5], outdata[6], outdata[7], outdata[8]))
        
        with open(hbg_pkfit_pfname, 'a') as f_handle:
            outdata = numpy.append([i, round(xx[i],3), round(yy[i],3), round(zz[i],3)], phbgj, axis=2)
            f_handle.write('%d %f %f %f %f %f %f %f %f\n' % (outdata[0], outdata[1], outdata[2], outdata[3], outdata[4], outdata[5], outdata[6], outdata[7], outdata[8]))
            
        with open(vbg_pkfit_pfname, 'a') as f_handle:
            outdata = numpy.append([i, round(xx[i],3), round(yy[i],3), round(zz[i],3)], pvbgj, axis=2)
            f_handle.write('%d %f %f %f %f %f %f %f %f\n' % (outdata[0], outdata[1], outdata[2], outdata[3], outdata[4], outdata[5], outdata[6], outdata[7], outdata[8]))

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
        
    ### SAFETY 
    time.sleep(1)

print 'END OF FITTING - HOPE THE FITTING WORKED!!'
plt.ioff()    
sys.exit()
