# -*- coding: utf-8 -*-
"""
Created on Thu Feb 19 10:08:33 2015

@author: abeaudoi
"""
import numpy
import matplotlib
import matplotlib.pyplot as plt

dirName = 'mach_feb15/NC_RS5_MapA'
dirName = 'mach_feb15/LapMap7'

detOrientation = 'vert'

Hstrain = numpy.array([])

reflections = ['211', '220', '310', '321']

for idx, refl in enumerate( reflections ):
    print idx, refl
    filename = dirName + '/' + detOrientation + '_' + refl + '.dat'
    s = numpy.loadtxt(filename)
    if idx == 0:
        Vstrain = numpy.copy(s)
    else:
        Vstrain = Vstrain + s
        
Vstrain = Vstrain / len(reflections)  

detOrientation = 'horz'

Hstrain = numpy.array([])

reflections = ['211', '220', '310', '321']

for idx, refl in enumerate( reflections ):
    print idx, refl
    filename = dirName + '/' + detOrientation + '_' + refl + '.dat'
    s = numpy.loadtxt(filename)
    if idx == 0:
        Hstrain = numpy.copy(s)
    else:
        Hstrain = Hstrain + s
        
Hstrain = Hstrain / len(reflections)        

#%%

EpVert = Vstrain
EpHorz = Hstrain
nu = 0.3
E = 205470 #MPa
Ep33 = (-nu/(1-nu))*(EpVert+EpHorz)

#SigmaVert
SgVert = (E/(1+nu))*(EpVert+(nu/(1-2*nu))*(EpVert+EpHorz+Ep33))
#SigmaHorz
SgHorz = (E/(1+nu))*(EpHorz+(nu/(1-2*nu))*(EpVert+EpHorz+Ep33))

lvls = numpy.arange(-450.,500.,50.)
plt.figure(7)
plt.clf()
plt.contourf(SgVert,levels=lvls)
plt.axis('equal')
plt.colorbar()
plt.suptitle(r'$\sigma_{\rm vertical}$',fontsize=24)

lvls = numpy.arange(-450.,500.,50.)
plt.figure(8)
plt.clf()
plt.contourf(SgHorz,levels=lvls)
plt.axis('equal')
plt.colorbar()
plt.suptitle(r'$\sigma_{\rm horizontal}$',fontsize=24)

plt.figure(9)
plt.clf()
elvls = numpy.arange(-0.0018,0.0018,0.0002)
plt.contourf(Vstrain,levels=elvls)
plt.axis('equal')
plt.colorbar()
plt.suptitle(r'$\varepsilon_{\rm vertical}$',fontsize=24)

plt.figure(10)
plt.clf()
plt.contourf(Hstrain,levels=elvls)
plt.axis('equal')
plt.colorbar()
plt.suptitle(r'$\varepsilon_{\rm horizontal}$',fontsize=24)

plt.show()
