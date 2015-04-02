# -*- coding: utf-8 -*-
"""
Created on Thu Feb 19 08:41:50 2015

@author: abeaudoi

This program sums (averages) over several peaks, using a little pyramid
weighting.  The notion is to get out some of the texture effect, which was
very evident in the variation of EDD peaks.

"""

import numpy
import matplotlib
import matplotlib.pyplot as plt
import PeakFitting

import math

# The parameters for the dataset follow:
dirName = 'mach_feb15/NC_RS5_MapA'

# Averaging of peaks is used for the cruciform (NC_RS... samples),
# but not for the small lap weld samples (LapMap...)
Averaging = True

# The fast and slow dimensions of the scan
sd = 12
fd = 79

# For the Lap #7 sample
#Averaging = False
#dirName = 'mach_feb15/LapMap7/'
#sd = 7
#fd = 16

# For the Lap #4 sample
Averaging = False
dirName = 'mach_feb15/LapMap7'
sd = 16
fd = 7


npoints = sd * fd 

# Cut-offs for background removal (defines region about peak for background)
# Was 0.02 and 0.04
loCut = 0.010
hiCut = 0.015

##############################################################################
# ASSIGN BASED ON PEAK & DETECTOR
#
# The peak centers, assigned well below in the code as based on reflection,
# are listed in a normalized energy -- from 0 to 1.  In this way, the 
# detector calibration can be updated, and the peak locations for a
# particular detector stay the same (for the experiment)

yd = numpy.zeros((fd,sd,2048))

xd = numpy.linspace(1.,2048.,num=2048)
xd = xd / 2048.

if Averaging:
   NormE = numpy.zeros( (fd-2,sd-2) )
   dHKL = numpy.zeros( (fd-2,sd-2) ) 
else:
   NormE = numpy.zeros( (fd,sd) )
   dHKL = numpy.zeros( (fd,sd) ) 
        
for detOrientation in ['horz', 'vert']:
    
    ##########################################################################        
    # Load all of the data into an array
            
    cnt = 0
    for j in range(0,sd):
        for i in range(0,fd):
    
            filename = dirName + '/' + detOrientation + '_det_' + str(cnt) + '_val.data'
            print filename
    
            a = numpy.loadtxt(filename,dtype=float)
        
            yd[i,j,:] = 1.0*a
            
            cnt = cnt + 1
    
    ##########################################################################
    # Now for the summing 
        
    if Averaging:
        yAvg = numpy.zeros((fd-2,sd-2,2048))
                
        for j in range(1,sd-1):
            for i in range(1,fd-1):
                # A weighted sum
                #yAvg[i-1,j-1,:] = yd[i,j,:] + \
                #    0.5 * \
                #    (yd[i-1,j,:] + yd[i+1,j,:] + yd[i,j-1,:] + yd[i,j+1]) + \
                #    (0.5/1.414) * \
                #    (yd[i-1,j-1,:] + yd[i+1,j-1,:] + yd[i+1,j-1,:] + yd[i+1,j+1])
            
                # Just sum
                yAvg[i-1,j-1,:] = yd[i,j,:] + \
                    1.0 * \
                    (yd[i-1,j,:] + yd[i+1,j,:] + yd[i,j-1,:] + yd[i,j+1]) + \
                    1.0 * \
                    (yd[i-1,j-1,:] + yd[i+1,j-1,:] + yd[i+1,j-1,:] + yd[i+1,j+1])
    else:
        yAvg = numpy.copy(yd)
    
    ##########################################################################   
    # Loop over the peaks    
    
    for pidx, peakID in enumerate(['211', '220', '310', '321']):
            
        d0 = 1.0 / math.sqrt( float(peakID[0])**2 + float(peakID[1])**2 + 
            float(peakID[2])**2)    
        
        # multiply by a0
        if detOrientation == 'horz':
            # d0 = d0*2.868
            d0 = d0*2.869
        else:
            d0 = d0*2.868
            
        # Assign the location of the (normalized) peak center, corresponding
        # to the detector orientation
        if detOrientation == 'horz':
            # Horizontal scan        
            if peakID == '211':
                peakCtr = 0.46
            elif peakID == '220':
                peakCtr = 0.53  # Horizontal
            elif peakID == '310':
                peakCtr = 0.593
            elif peakID == '222':
                peakCtr = 0.65
            elif peakID == '321':
                peakCtr = 0.70
              
        else:
            # Vertical scan
            if peakID == '211':
                peakCtr = 0.44
            elif peakID == '220':
                peakCtr = 0.51  # Horizontal
            elif peakID == '310':
                peakCtr = 0.571
            elif peakID == '222': 
                peakCtr = 0.626
            elif peakID == '321':
                peakCtr = 0.675
                                
        for jj in range(0,yAvg.shape[1]):
            for ii in range(0,yAvg.shape[0]):
        
                print ii,jj
                
                idx = (xd>(peakCtr-hiCut)) & (xd<(peakCtr+hiCut))
        
                x = xd[idx]
                y = yAvg[ii,jj,idx]
                
                # This provides filtering of the peak
                #y = savitzky_golay(y,11,3)
                y = PeakFitting.savitzky_golay(y,7,3)
        
                ## SORTING ASCENDING ORDER ##
                y_temp = []
                x_temp = []
            
                ind_sort = numpy.lexsort((y,x))
                for j in ind_sort:
                    y_temp.append(y[j])
                    x_temp.append(x[j])
        
                x = numpy.array((x_temp))
                y = numpy.array((y_temp))
        
                background = PeakFitting.developBackground(x,y,peakCtr,loCut,hiCut) 
        
                # removing fitted background #
                y_bg_corr = y - background
        
                fit, best_parameters = PeakFitting.fitPeak(x, y_bg_corr, peakCtr)
                print best_parameters[1]
                NormE[ii,jj] = best_parameters[1]
        
        # Plot the last peak    
        plt.figure(pidx)
        plt.clf()
        plt.plot(x,y_bg_corr,'wo')
        plt.plot(x,fit,'r-',lw=2)
        plt.xlabel('Energy', fontsize=18)
        plt.ylabel('Counts', fontsize=18)
        plt.show()
        
        ######################################################################
        # COMPUTE THE LATTICE PARAMETER BASED ON DETECTOR
       
        if detOrientation == 'horz':
            # %%% HORZ
            # ChToEnergyConversion    = [0.092570164886107  -0.077311622210394];
            # TOA     =  6.970451365881403;
            ### NormE*2048 gives channel ###
        
            NormE = (0.092570164886107 * NormE*2048) - 0.077311622210394
            dHKL = 6.199 / ( NormE*math.sin((6.970451365881403*(math.pi/180.))/2.0) )
        
        else:
            # %%% VERT
            # ChToEnergyConversion    = [0.097317328321570  -0.009544487593012];
            # TOA     = 6.886258908378000;
        
            NormE = (0.097317328321570 * NormE*2048) - 0.009544487593012
            dHKL = 6.199 / ( NormE*math.sin((6.886258908378000*(math.pi/180.))/2.0) )
            
        ######################################################################
        # OUTPUT THE DATA
        
        #%%
        strain = numpy.log(dHKL / d0)
        
        filename = dirName + detOrientation + '_' + peakID + '.dat'
        
        numpy.savetxt(filename,strain)
        
