# -*- coding: utf-8 -*-
"""
Created on Mon Feb 23 06:34:55 2015

@author: abeaudoi

Peak fitting routines are adapted from the fitting example given in:

    http://mesa.ac.nz/?page_id=2195


"""
import numpy

from scipy.optimize import leastsq # Levenberg-Marquadt Algorithm #
from savitzky_golay import savitzky_golay ## Smoothing algorithm ##
from scipy.interpolate import interp1d ##Interpolation ##

# Two sided Lorentz function
def lorentzian(x,p):
    min_step = x[1] - x[0]
    ind1 = (x< p[1])  
    x1 = x[ind1]  
    ind2 = (x > p[1])
    x2 = x[ind2]
    numerator_left = (p[0]**2 )
    denominator_left = ( x1 - (p[1]) )**2 + p[0]**2
    numerator_right = (p[2]**2 )
    denominator_right = ( x2 - (p[1]) )**2 + p[2]**2
    y_left = p[3]*(numerator_left/denominator_left)
    y_right = p[3]*(numerator_right/denominator_right)
    lin_comb = numpy.hstack((y_left,y_right))
    return lin_comb
 
def residuals(p,y,x):
    err = y - lorentzian(x,p)
    return err

def fitPeak(x,y_bg_corr,peakCtr):  
    
    # initial values #
    # vert p = [0.002,0.513,0.002,600.0] # [hwhm1, peak center, hwhm2, intensity] #
    p = [0.002,peakCtr,0.002,600.0] # [hwhm1, peak center, hwhm2, intensity] #
    # optimization #
    pbest = leastsq(residuals,p,args=(y_bg_corr,x),full_output=1)
    best_parameters = pbest[0]

    # fit to data #
    fit = lorentzian(x,best_parameters)
    return fit, best_parameters
    
def developBackground(x,y,peakCtr,loCut,hiCut): 
    # defining the 'background' part of the spectrum #
    ind_bg_low = (x > (peakCtr-hiCut)) & (x < (peakCtr-loCut)) 
    ind_bg_high = (x > (peakCtr+loCut)) & (x < (peakCtr+hiCut))
    
    x_bg = numpy.concatenate((x[ind_bg_low],x[ind_bg_high]))
    y_bg = numpy.concatenate((y[ind_bg_low],y[ind_bg_high]))
    #matplotlib.plot(x_bg,y_bg)
    
    # interpolating the background #
    f = interp1d(x_bg,y_bg)
    background = f(x)
    return background
    
