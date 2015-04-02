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
#import math
#import logging
import time
#import rlcompleter
#import readline
#import csv

#import datetime as dt
import matplotlib.pyplot as plt

#from scipy.optimize import curve_fit
from lmfit import minimize, Parameters, Parameter, report_fit
#from scipy.optimize import minimize
#from pprint import pprint
from mpl_toolkits.mplot3d import axes3d

#################################################
### PEAK FUNCTIONS
#################################################
def pkBackground(x, p):
    '''
    pkBackground
    
    Polynominal background function using numpy.polyval
    If `p` is of length N, this function returns the value:

    ``p[0]*x**(N-1) + p[1]*x**(N-2) + ... + p[N-2]*x + p[N-1]``
    
    '''
    ybkg = numpy.polyval(p, x)
    return ybkg

def pkGaussian(x, p):
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
    ybkg = pkBackground(x, pbkg)
    
    delx = (x - xPeak)/Gamma
    yG = A*(c0**0.5/Gamma/numpy.pi**0.5)*numpy.exp(-c0*delx**2)
    
    ypk = ybkg + yG
    return ypk

def pkLorentzian(x, p):
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
    ybkg = pkBackground(x, pbkg)
    
    delx = (x - xPeak)/Gamma
    yL = (A*c1**0.5/Gamma/numpy.pi)*(1 / (1 + c1*delx*delx))
    
    ypk = ybkg + yL
    return ypk

# define objective function: returns the array to be minimized
def pkfunc(params, x, data):
    '''
    model decaying sine wave, subtract data
    '''    
    A = params['A'].value
    Gamma = params['Gamma'].value
    n = params['n'].value
    xPeak = params['xPeak'].value
    pbkg = numpy.array([params['bkg1'].value, params['bkg2'].value])
    
    pG = numpy.array([A, Gamma, xPeak])
    pL = numpy.array([A, Gamma, xPeak])

    ybkg = pkBackground(x, pbkg)
    yG = pkGaussian(x, pG)
    yL = pkLorentzian(x, pL)

    ypk = ybkg + n * yG + (1 - n) * yL

    res = ypk - data
    return res
              
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
datafile_pname = './data/'

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
logfile_pname = './'
logfile_fname = 'template_log.pypar'
logfile_pfname = os.path.join(logfile_pname, logfile_fname);

###################################################
### DIFFRACTION VOLUME COORDINATES
dv_crd_file = True
dv_crd_pname = './'
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
Gamma0 = numpy.array([3.0, 3.0, 3.0])
        
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
fig1 = plt.figure(figsize=plt.figaspect(0.25))

### INITIALIZE LIST OF FAILED FIT 
dv_pk_h = []
dv_pk_v = []
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
    spectrum_x = numpy.linspace(1, len(hval), len(hval))

    ax0 = fig1.add_subplot(1, 3, 1, projection='3d')
    ax0.plot(xx, yy, zz, 'bo', zdir='z')
    ax0.hold(True)
    if i == 0:
        ax0.plot([xx[0]], [yy[0]], [zz[0]], 'yo')
    else:
        ax0.plot([xx[i]], [yy[i]], [zz[i]], 'yo')
        ax0.plot(xx[0:i], yy[0:i], zz[0:i], 'ro')
    ax0.set_xlabel('sam X (mm)')
    ax0.set_ylabel('sam Y (mm)')
    ax0.set_zlabel('sam Z (mm)')
    ax0.view_init(45, 45)
    ax0.hold(False)
    
    ax1 = fig1.add_subplot(1, 3, 2)
    ax1.plot(spectrum_x, hval, 'bo', spectrum_x, vval, 'b^')
    ax1.set_xlabel('channel number (-)')
    ax1.set_ylabel('intensity (arb. units)')
    ax1.grid(True)
    ax1.hold(True)
    
    ax2 = fig1.add_subplot(1, 3, 3)
    ax2.plot(spectrum_x, vval, 'b^')
    ax2.set_xlabel('channel number (-)')
    ax2.set_ylabel('intensity (arb. units)')
    ax2.set_title('h-val')
    ax2.grid(True)
    ax2.hold(True)
    
    ### FITTING
    for j in range(numpk):
        print '###################################################'
        print 'peak number ' + str(j)
        
        idxLB = spectrum_x > pkLB[j]
        idxUB = spectrum_x < pkUB[j]
        
        xj = spectrum_x[idxLB & idxUB]
        hvalj = hval[idxLB & idxUB]
        vvalj = vval[idxLB & idxUB]

        # create a set of Parameters
        phvalj = Parameters()
        phvalj.add('A', value = max(hvalj)*Gamma0[j], min = 0.0)
        phvalj.add('Gamma', value = Gamma0[j], min = 0.0)
        phvalj.add('n', value = 0.5, min = 0.0, max = 1.0)
        phvalj.add('xPeak', value = pkpos[j])
        phvalj.add('bkg1', value = 0.0)
        phvalj.add('bkg2', value = numpy.mean(hvalj))
        
        # create a set of Parameters
        pvvalj = Parameters()
        pvvalj.add('A', value = max(vvalj)*Gamma0[j], min = 0.0)
        pvvalj.add('Gamma', value = Gamma0[j], min = 0.0)
        pvvalj.add('n', value = 0.5, min = 0.0, max = 1.0)
        pvvalj.add('xPeak', value = pkpos[j])
        pvvalj.add('bkg1', value = 0.0)
        pvvalj.add('bkg2', value = numpy.mean(vvalj))
        
        ### CURVE FIT
        result_hvalj = minimize(pkfunc, phvalj, args=(xj, hvalj))
        hvalj_fit = hvalj + result_hvalj.residual
        report_fit(phvalj)

        result_vvalj = minimize(pkfunc, pvvalj, args=(xj, vvalj))
        vvalj_fit = vvalj + result_vvalj.residual
        report_fit(pvvalj)
        
        ### SAVE CURVE FIT RESULTS
        with open(hval_pkfit_pfname, 'a') as f_handle:
            outdata = numpy.array([i, round(xx[i],3), round(yy[i],3), round(zz[i],3), result_hvalj.values['A'], result_hvalj.values['Gamma'], result_hvalj.values['n'], result_hvalj.values['xPeak'], result_hvalj.values['bkg1'], result_hvalj.values['bkg2'], result_hvalj.success])
            
            f_handle.write('%d %f %f %f %f %f %f %f %f %f %d\n' % (outdata[0], outdata[1], outdata[2], outdata[3], outdata[4], outdata[5], outdata[6], outdata[7], outdata[8], outdata[9], outdata[10]))
            
        with open(vval_pkfit_pfname, 'a') as f_handle:
            outdata = numpy.array([i, round(xx[i],3), round(yy[i],3), round(zz[i],3), result_vvalj.values['A'], result_vvalj.values['Gamma'], result_vvalj.values['n'], result_vvalj.values['xPeak'], result_vvalj.values['bkg1'], result_vvalj.values['bkg2'], result_vvalj.success])
            
            f_handle.write('%d %f %f %f %f %f %f %f %f %f %d\n' % (outdata[0], outdata[1], outdata[2], outdata[3], outdata[4], outdata[5], outdata[6], outdata[7], outdata[8], outdata[9], outdata[10]))

        if result_hvalj.success:
            ax1.plot(xj, hvalj, 'ro', xj, hvalj_fit, 'k-')
        else:
            ax1.plot(xj, hvalj, 'ro', xj, hvalj_fit, 'r:')
            dv_pk_h = dv_pk_h.append([i, j])

        if result_vvalj.success:
            ax2.plot(xj, vvalj, 'r^', xj, vvalj_fit, 'k-')
        else:
            ax2.plot(xj, vvalj, 'r^', xj, vvalj_fit, 'r:')
            dv_pk_v = dv_pk_v.append([i, j])
        
    ax1.hold(False)
    ax2.hold(False)
    fig1.show()
    ### SAFETY 
    time.sleep(1)

plt.ioff()

if len(dv_pk_h) == 0 and  len(dv_pk_v) == 0:
    print 'END OF FITTING - SEEMS LIKE FITTING WORKED FOR ALL PEAKS AND DVs'
else:
    print 'END OF FITTING - FITTING DID NOT WORK FOR SOME PEAKS AND DVs'
