### TODO ###
### RUN /APSshare/anaconda/x86_64/bin/ipython --pylab='auto'
### then '>>>run exp_tracking.py'
### then '>>>bpm_monitor(logname)'
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

alldone = PyEpics.PV('1ida:alldone')

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

def bpm_monitor (logname):
    print 'monitoring in progress'
    
    while True:
        mac.write_logging_header(logname)
        mac.write_logging_parameters(logname)
        
        print 'do not shut off unless authorized by users'
        # print time.ctime() + ' : wrote GE temperature data to ' + logname
        spec.sleep(5) 
        # spec.sleep(1) 

spec.EnableEPICS()

# logname = './pokharel_jul26_exp_tracking1.pypar'
logname = './pokharel_jul26_exp_tracking2.pypar'

###################################################    
### DEFINE MOTORS & SCALARS & SPECIAL PVs
###################################################
## GE/Pilatus DETECTOR

spec.DefineMtr('hydraZE',  '1idc:m7', 'hydraZE (mm)')
spec.DefineMtr('geXE',  '1ide1:m103', 'geXE (mm)')
spec.DefineMtr('geZE',  '1ide1:m50', 'geZE (mm)')

# # Tomo det
# spec.DefineMtr('ImgXE',  '1ide1:m63', 'ImgXE (mm)')
# spec.DefineMtr('ImgYE',  '1ide1:m40', 'ImgYE (mm)')
# spec.DefineMtr('ImgZE',  '1ide1:m62', 'ImgZE (mm)')
# spec.DefineMtr('ImgChiE',  '1ide1:m38', 'ImgChiE (deg)')

# # NF DET
# spec.DefineMtr('DetX',  '1ide1:m6', 'DetX (mm)')
# spec.DefineMtr('NFYE',  '1ide1:m59', 'NFYE (mm)')
# spec.DefineMtr('DetZ',  '1ide1:m7', 'DetZE (mm)')
# spec.DefineMtr('bbYE',  '1ide1:m39', 'bbYE (mm)')
# spec.DefineMtr('focus',  '1ide1:m12', 'NFfocus (mm)')
# spec.DefineMtr('bbPhi',  '1ide1:m57', 'NFbbPhi (mm)')
# spec.DefineMtr('NFtiltX',  '1ide1:m5', 'NFTiltX (mm)')
# spec.DefineMtr('NFtiltY',  '1ide1:m6', 'NFTiltY (mm)')
# spec.DefineMtr('NFX',  '1ide1:m111', 'NFX (mm)')

# # LENSES IN E VERTICAL FOCUS
# spec.DefineMtr('L1th',  '1ide1:m30', 'L1th (mm)')
# spec.DefineMtr('L1y',  '1ide1:m28', 'L1y (mm)')
# spec.DefineMtr('L2th',  '1ide1:m32', 'L2th (mm)')
# spec.DefineMtr('L2y',  '1ide1:m29', 'L2y (mm)')

# # LENSES IN E Horizontal FOCUS
# spec.DefineMtr('L3x',  '1ide1:m82', 'L3x (mm)')
# spec.DefineMtr('L3ph',  '1ide1:m83', 'L3ph (deg)')
# spec.DefineMtr('L4x',  '1ide1:m85', 'L4xy (mm)')
# spec.DefineMtr('L4ph',  '1ide1:m88', 'L4ph (deg)')

"""
# LENSES IN B VERTICAL FOCUS
spec.DefineMtr('L1piv',  '1idb:m47', 'L1piv (mm)')
spec.DefineMtr('L1gap',  '1idb:m29', 'L1gap (mm)')
spec.DefineMtr('L2piv',  '1idb:m22', 'L2piv (mm)')
spec.DefineMtr('L2gap',  '1idb:m24', 'L2gap (mm)')
"""

"""
# LENGELER LENSES IN B
spec.DefineMtr('RLxb',  '1idb:m54', 'RLxb (mm)')
spec.DefineMtr('RLyb',  '1idb:m44', 'RLyb (mm)')
spec.DefineMtr('RLthb',  '1idb:m53', 'RLthb (deg)')
spec.DefineMtr('RLphib',  '1idb:m49', 'RLphib (deg)')
"""

"""
# US CRL LENSES IN B
spec.DefineMtr('CRL1Y',  '1ida:m21', 'CRL1Y (mm)')
spec.DefineMtr('CRL1Th',  '1ida:m31', 'CRL1Th (deg)')
spec.DefineMtr('CRL2Y',  '1ida:m26', 'CRL2Y (mm)')
spec.DefineMtr('CRL2Th',  '1ida:m24', 'CRL2Th (deg)')
"""

"""
# CRL LENSES IN DS C
spec.DefineMtr('LCx',  '1idc:m42', 'LCx (mm)')
spec.DefineMtr('LCy',  '1idc:m43', 'LCy (mm)')
spec.DefineMtr('LCth',  '1idc:m41', 'LCth (deg)')
spec.DefineMtr('LCphi',  '1idc:m44', 'LCphi (deg)')
"""

# Foils. attens
spec.DefineMtr('atten', '1idb:m50', 'attenwh (deg)')
spec.DefineMtr('foil', '1idb:m18', 'foil (deg)')
spec.DefineMtr('attenC', '1idc:m16', 'attenC (deg)')


# MTS+RAMS1+OXYGON setup
spec.DefineMtr('mtsX2E',  '1ide1:m9', 'mtsX2E (mm)')
spec.DefineMtr('phi',  '1ide1:m4', 'phi (deg)')
spec.DefineMtr('mtsXE',  '1ide1:m13', 'mtsYE (mm)')
spec.DefineMtr('mtsYE',  '1ide1:m16', 'mtsYE (mm)')
spec.DefineMtr('mtsZE',  '1ide1:m14', 'mtsYE (mm)')
spec.DefineMtr('mtsY1',  '1ide1:m1', 'mtsY1 (mm)')
spec.DefineMtr('mtsY2',  '1ide1:m2', 'mtsY2 (mm)')
spec.DefineMtr('mtsY3',  '1ide1:m3', 'mtsY3 (mm)')
# spec.DefineMtr('rams1',  '1idrams1:m1', 'rams1 (deg)')
# spec.DefineMtr('oxyPhi',  '1ide1:m91', 'oxyPhi (deg)')

# # Aero setup
# spec.DefineMtr('samXE',  '1ide1:m34', 'samXE (mm)')
# spec.DefineMtr('samYE',  '1ide1:m35', 'samYE (mm)')
# spec.DefineMtr('samZE',  '1ide1:m36', 'samZE (mm)')
# spec.DefineMtr('th',  '1ide1:m86', 'th (deg)')  ## CHECK the arcs sometimes swapped
# spec.DefineMtr('chi',  '1ide1:m87', 'chi (deg)')
# spec.DefineMtr('aero',  '1ide:m9', 'ome (deg)')
# spec.DefineMtr('tension',  '1ide1:m33', 'tension (um)')
# spec.DefineMtr('aeroXE',  '1ide1:m101', 'aeroXE (mm)')
# spec.DefineMtr('aeroZE',  '1ide1:m102', 'aeroZE (mm)')

"""
# MAMC setup
spec.DefineMtr('msamXC',  '1idc:m12', 'samXC (mm)')
spec.DefineMtr('msamYC',  '1idc:m14', 'samYC (mm)')
spec.DefineMtr('msamZC',  '1idc:m13', 'samZC (mm)')
spec.DefineMtr('momeC',  '1idc:m9', 'ome (deg)')
spec.DefineMtr('mrotXC',  '1idc:m15', 'mrotXC (mm)')
"""

"""
# RF Furnace
spec.DefineMtr('coilPhi',  '1ide1:m60', 'coil phi (deg)')
spec.DefineMtr('coilZ',  '1ide1:m61', 'coil z (mm)')
spec.DefineMtr('coilY',  '1ide1:m56', 'coil y (mm)')
"""

"""
# AM chamber setup
spec.DefineMtr('samX',  '1ide1:m95', 'samX (mm)')
spec.DefineMtr('samZ',  '1ide1:m96', 'samZ (mm)')
spec.DefineMtr('samY',  '1ide1:m79', 'samY (mm)')
spec.DefineMtr('chmY',  '1ide1:m76', 'chamber_Y (mm)')
spec.DefineMtr('chmX',  '1ide1:m68', 'chamber_X (mm)')
"""

"""
# CMU Suter / Basil furnace motors
spec.DefineMtr('cmufx',  '1ide1:m17', 'cmu furnace X (mm)')
spec.DefineMtr('cmufz',  '1ide1:m18', 'cmu furnace Z (mm)')
spec.DefineMtr('cmufy',  '1ide1:m94', 'cmu furnace Y (mm)')
"""

"""
# Shields
spec.DefineMtr('shieldX',  '1ide1:m42', 'shieldX (mm)') # LinTech stage
spec.DefineMtr('SAXpinX',  '1ide1:m66', 'SAXpinX (mm)') # for pixirad
spec.DefineMtr('dexX',  '1ide1:m47', 'dexX (mm)') # for LPA, dexela motor
"""

ImportMotorSymbols()
spec.ListMtrs()

###################################################    
### END OF DEFINE MOTORS & SCALARS
###################################################

###################################################    
### INITATE LOGGING
###################################################
mac.init_logging()


mac.add_logging_PV('Iring', 'S:SRcurrentAI')

# GEs
mac.add_logging_motor(hydraZE)
mac.add_logging_motor(geXE)
mac.add_logging_motor(geZE)

# # Tomo det
# mac.add_logging_motor(ImgXE)
# mac.add_logging_motor(ImgYE)
# mac.add_logging_motor(ImgZE)
# mac.add_logging_motor(ImgChiE)

"""
# NF DET
mac.add_logging_motor(DetX)
mac.add_logging_motor(NFYE)
mac.add_logging_motor(DetZ)
mac.add_logging_motor(bbYE)
mac.add_logging_motor(focus)
mac.add_logging_motor(bbPhi)
mac.add_logging_motor(NFtiltX)
mac.add_logging_motor(NFtiltY)
mac.add_logging_motor(NFX)
"""

# DETECTORS frame number
mac.add_logging_PV('ge1 fnum', 'GE1:cam1:FileNumber_RBV')
mac.add_logging_PV('ge2 fnum', 'GE2:cam1:FileNumber_RBV')
mac.add_logging_PV('ge3 fnum', 'GE3:cam1:FileNumber_RBV')
mac.add_logging_PV('ge4 fnum', 'GE4:cam1:FileNumber_RBV')
mac.add_logging_PV('ge5 fnum', 'GE5:cam1:FileNumber_RBV')

# mac.add_logging_PV('Q2 tomo fnum', 'QIMAGE2:TIFF1:FileNumber_RBV')
# mac.add_logging_PV('PG1 tomo fnum', '1idPG1:TIFF1:FileNumber_RBV')
# mac.add_logging_PV('PG1 tomo fnum', '1idGH1:TIFF1:FileNumber_RBV')
# mac.add_logging_PV('dexela fnum', '1idDEX:TIFF1:FileNumber')
# mac.add_logging_PV('PG5 fnum', '1idPG5:TIFF1:FileNumber')
# mac.add_logging_PV('NF fnum', 'QIMAGE1:TIFF1:FileNumber_RBV')
# mac.add_logging_PV('Lambda fnum', 'dp_lambda_xrd30:TIFF1:FileNumber_RBV')
# mac.add_logging_PV('dic fname', 's1_gx2750:TIFF1:FileName_RBV', as_string=True)
# mac.add_logging_PV('dic fnum', 's1_gx2750:TIFF1:FileNumber_RBV')
# mac.add_logging_PV('vff fnum', 'dp_mar165_xrd82:cam1:FileNumber_RBV')
# mac.add_logging_PV('vff fnum', 'QMPX3:TIFF1:FileNumber_RBV')


# # Pilatus
# mac.add_logging_PV('PilNextFileNr','1idPil:TIFF1:FileNumber_RBV')
# mac.add_logging_PV('PilExpTime (s)','1idPil:cam1:AcquireTime_RBV')
# mac.add_logging_PV('PilNumImages','1idPil:cam1:NumImages_RBV')

## PIXIRAD2
#mac.add_logging_PV('saxs fnum', 's1_pixirad2:TIFF1:FileNumber_RBV')
#mac.add_logging_PV('saxs fnum', 's1_pixirad2:HDF1:FileNumber_RBV')
#mac.add_logging_PV('set pt temp', 's1_pixirad2:cam1:Temperature_RBV')
#mac.add_logging_PV('actual temp', 's1_pixirad2:cam1:TemperatureActual')
#mac.add_logging_PV('box temp', 's1_pixirad2:cam1:BoxTemperature_RBV')
#mac.add_logging_PV('box humidity', 's1_pixirad2:cam1:BoxHumidity_RBV')
#mac.add_logging_PV('dew pt', 's1_pixirad2:cam1:DewPoint_RBV')
#mac.add_logging_PV('saxs peltier power', 's1_pixirad2:cam1:PeltierPower_RBV')

# # LENSES
# mac.add_logging_motor(L1th)
# mac.add_logging_motor(L1y)
# mac.add_logging_motor(L2th)
# mac.add_logging_motor(L2y)
# mac.add_logging_motor(L3ph)
# mac.add_logging_motor(L3x)
# mac.add_logging_motor(L4ph)
# mac.add_logging_motor(L4x)

# mac.add_logging_PV('L5B Y', '1idb:m47.RBV')
# mac.add_logging_PV('L5B Th', '1idb:m29.RBV')
# mac.add_logging_PV('L4B Y', '1idb:m22.RBV')
# mac.add_logging_PV('L4B Th', '1idb:m24.RBV')

#mac.add_logging_motor(RLxb)
#mac.add_logging_motor(RLyb)
#mac.add_logging_motor(RLthb)
#mac.add_logging_motor(RLphib)

#mac.add_logging_motor(LCx)
#mac.add_logging_motor(LCy)
#mac.add_logging_motor(LCth)
#mac.add_logging_motor(LCphi)

"""
# LENSES IN B CRL, upstream
mac.add_logging_PV('CRL 1 Th', '1ida:m31.RBV')
mac.add_logging_PV('CRL 1 Y', '1ida:m21.RBV')
mac.add_logging_PV('CRL 2 Th', '1ida:m24.RBV')
mac.add_logging_PV('CRL 2 Y', '1ida:m26.RBV')
"""

# Foils, attens
mac.add_logging_motor(atten)
mac.add_logging_motor(foil)
mac.add_logging_motor(attenC)

# MTS+RAMS1 setup
mac.add_logging_motor(mtsX2E)
mac.add_logging_motor(phi)
mac.add_logging_motor(mtsXE)
mac.add_logging_motor(mtsYE)
mac.add_logging_motor(mtsZE)
mac.add_logging_motor(mtsY1)
mac.add_logging_motor(mtsY2)
mac.add_logging_motor(mtsY3)
# mac.add_logging_motor(rams1)
# mac.add_logging_motor(oxyPhi)

# # # Aero setup
# mac.add_logging_motor(samXE)
# mac.add_logging_motor(samYE)
# mac.add_logging_motor(samZE)
# mac.add_logging_motor(th)
# mac.add_logging_motor(chi)
# mac.add_logging_motor(aero)
# mac.add_logging_motor(aeroXE)
# mac.add_logging_motor(aeroZE)
# mac.add_logging_motor(tension)
# mac.add_logging_PV('Fedrl1 (mm)', '1ide:Fed:s1:probe_1')
# # mac.add_logging_PV('Fedrl2 (mm)', '1ide:Fed:s1:probe_2')

"""
# MAMC setup
mac.add_logging_motor(msamXC)
mac.add_logging_motor(msamYC)
mac.add_logging_motor(msamZC)
mac.add_logging_motor(momeC)
mac.add_logging_motor(mrotXC)
"""

"""
# RF Furnace
mac.add_logging_motor(coilPhi)
mac.add_logging_motor(coilZ)
mac.add_logging_motor(coilY)
"""

"""
# AM chamber
mac.add_logging_motor(samX)
mac.add_logging_motor(samZ)
mac.add_logging_motor(samY)
mac.add_logging_motor(chmY)
mac.add_logging_motor(chmX)
"""

# # Shields
# mac.add_logging_motor(shieldX)
# mac.add_logging_motor(SAXpinX)
# mac.add_logging_motor(dexX)
# mac.add_logging_PV('afrl_shield (-)',  '1ide:Unidig1Bo2') # AFRL shield


# Monochromator
mac.add_logging_PV('HEM E (keV)', '1id:userTran3.A')
mac.add_logging_PV('Th1 offset', '1id:userTran3.B')
# mac.add_logging_PV('SCU1 Current (A)', 'ID01ds:MainCurrentRdbk.VAL')
# mac.add_logging_PV('UndA Gap (mm)', 'S01ID:DSID:GapM.VAL')
mac.add_logging_PV('Undulator gap (mm)', 'S01ID:DSID:GapM.VAL')
mac.add_logging_PV('HEM Th1 (deg)', '1ida:m30.RBV')
mac.add_logging_PV('HEM Th2 (deg)', '1ida:m32.RBV')
mac.add_logging_PV('HEM Z2 (mm)', '1idsft1:m1.RBV')
mac.add_logging_PV('HEM Chi2 (deg)', '1ida:m17.RBV')

# Slits
mac.add_logging_PV('B Kohzu H size (mm)', '1idb:SlitHt2.C')
mac.add_logging_PV('B Kohzu V size (mm)', '1idb:SlitVt2.C')
mac.add_logging_PV('B Kohzu H pos (mm)', '1idb:SlitHt2.D')
mac.add_logging_PV('B Kohzu V pos (mm)', '1idb:SlitVt2.D')

mac.add_logging_PV('C Kohzu DS H size (mm)', '1idc:KslitdsHt2.C')
mac.add_logging_PV('C Kohzu DS V size (mm)', '1idc:KslitdsVt2.C')
mac.add_logging_PV('C Kohzu DS H pos (mm)', '1idc:KslitdsHt2.D')
mac.add_logging_PV('C Kohzu DS V pos (mm)', '1idc:KslitdsVt2.D')
mac.add_logging_PV('C Kohzu US H size (mm)', '1idc:KslitusHt2.C')
mac.add_logging_PV('C Kohzu US V size (mm)', '1idc:KslitusVt2.C')
mac.add_logging_PV('C Kohzu US H pos (mm)', '1idc:KslitusHt2.D')
mac.add_logging_PV('C Kohzu US V pos (mm)', '1idc:KslitusVt2.D')

mac.add_logging_PV('E Kohzu DS H size (mm)', '1ide1:Kohzu_E_dnHt2.C')
mac.add_logging_PV('E Kohzu DS V size (mm)', '1ide1:Kohzu_E_dnVt2.C')
mac.add_logging_PV('E Kohzu DS H pos (mm)', '1ide1:Kohzu_E_dnHt2.D')
mac.add_logging_PV('E Kohzu DS V pos (mm)', '1ide1:Kohzu_E_dnVt2.D')
mac.add_logging_PV('E Kohzu US H size (mm)', '1ide1:Kohzu_E_upHt2.C')
mac.add_logging_PV('E Kohzu US V size (mm)', '1ide1:Kohzu_E_upVt2.C')
mac.add_logging_PV('E Kohzu US H pos (mm)', '1ide1:Kohzu_E_upHt2.D')
mac.add_logging_PV('E Kohzu US V pos (mm)', '1ide1:Kohzu_E_upVt2.D')

"""
# Beam positions
mac.add_logging_PV('SR BPM H pos (mm)', 'S1:ID:SrcPt:xPositionM')
mac.add_logging_PV('SR BPM H angle (urad)', 'S1:ID:SrcPt:xAngleM')
mac.add_logging_PV('SR BPM V pos (mm)', 'S1:ID:SrcPt:yPositionM')
mac.add_logging_PV('SR BPM V angle (urad)', 'S1:ID:SrcPt:yAngleM')

mac.add_logging_PV('XBPM H pos (mm)', 'FE:01:ID:HPOSITION:CC')
mac.add_logging_PV('XBPM H angle (urad)', 'FE:01:ID:HANGLE:CC')
mac.add_logging_PV('XBPM V pos (mm)', 'FE:01:ID:VPOSITION:CC')
mac.add_logging_PV('XBPM V angle (urad)', 'FE:01:ID:VANGLE:CC')

mac.add_logging_PV('BPM_C (mm)', '1ide2:S1:scaler1_calc3.VAL')
mac.add_logging_PV('BPM_E (mm)', '1ide2:S1:scaler1_calc5.VAL')
"""

# IC from scaler1 in 1id
mac.add_logging_PV('IC-B1 (cts)', '1id:S1:scaler1_cts1.C')
mac.add_logging_PV('IC-B2 (cts)', '1id:S1:scaler1_cts1.D')
mac.add_logging_PV('IC-B3 (cts)', '1id:S1:scaler1_cts2.A')
mac.add_logging_PV('IC-B4 (cts)', '1id:S1:scaler1_cts2.B')
mac.add_logging_PV('IC-B5 (cts)', '1id:S1:scaler1_cts2.C')
mac.add_logging_PV('IC-B8 (cts)', '1id:S1:scaler1_cts2.D')
mac.add_logging_PV('IC-B6 (cts)', '1id:S1:scaler1_cts3.A')
mac.add_logging_PV('IC-B7 (cts)', '1id:S1:scaler1_cts3.B')
mac.add_logging_PV('IC-C1 (cts)', '1id:S1:scaler1_cts3.D')
mac.add_logging_PV('IC-C2 (cts)', '1id:S1:scaler1_cts4.A')
mac.add_logging_PV('IC-C3 (cts)', '1id:S1:scaler1_cts4.B')
mac.add_logging_PV('IC-C4 (cts)', '1id:S1:scaler1_cts4.C')
mac.add_logging_PV('IC-C5 (cts)', '1id:S1:scaler1_cts4.D')
mac.add_logging_PV('IC-C6 (cts)', '1id:S1:scaler1_cts5.A')
mac.add_logging_PV('mut (-)', '1id:S1:scaler1_calc8.VAL')

# IC from scaler1 in 1ide
mac.add_logging_PV('IC-C1 (cts)', '1ide2:S1:scaler1_cts4.C')
mac.add_logging_PV('IC-C2 (cts)', '1ide2:S1:scaler1_cts4.D')
mac.add_logging_PV('IC-E1 (cts)', '1ide2:S1:scaler1_cts1.C')
mac.add_logging_PV('IC-E2 (cts)', '1ide2:S1:scaler1_cts1.D')
mac.add_logging_PV('IC-E3 (cts)', '1ide2:S1:scaler1_cts2.A')
mac.add_logging_PV('IC-E4 (cts)', '1ide2:S1:scaler1_cts2.C')
mac.add_logging_PV('IC-E5 (cts)', '1ide2:S1:scaler1_cts2.B')
mac.add_logging_PV('IC-E6 (cts)', '1ide2:S1:scaler1_cts2.D')
mac.add_logging_PV('IC-B5e (cts)', '1ide2:S1:scaler1_cts4.A')
mac.add_logging_PV('IC-B8e (cts)', '1ide2:S1:scaler1_cts4.B')
mac.add_logging_PV('IC-C1e (cts)', '1ide2:S1:scaler1_cts4.C')
mac.add_logging_PV('IC-C2e (cts)', '1ide2:S1:scaler1_cts4.D')
mac.add_logging_PV('IC-C3 (cts)', '1ide2:S1:scaler1_cts5.C')
mac.add_logging_PV('IC-C4 (cts)', '1ide2:S1:scaler1_cts5.D')

"""
## HRM
mac.add_logging_PV('world angle (urad)', '1ida:HR1_worldOffAO.VAL')
mac.add_logging_PV('E_hrm (keV)', '1ida:HR1_ERdbkAO')
mac.add_logging_PV('pzt1 (um)', '1idPI518:PIE518:1:p1_position')
mac.add_logging_PV('pzt2 (um)', '1idPI518:PIE518:1:p2_position')
mac.add_logging_PV('pzt1 (V)', '1idPI518:PIE518:1:p1_volts')
mac.add_logging_PV('pzt2 (V)', '1idPI518:PIE518:1:p2_volts')
mac.add_logging_PV('bpm_c (mm)', '1ide2:S1:scaler1_calc3.VAL')
mac.add_logging_PV('bpm_e (mm)', '1ide2:S1:scaler1_calc5.VAL')
"""

# TILT SENSORS
mac.add_logging_PV('Aero tiltX', '1ide:USdig_X3:1:A1.VAL')
mac.add_logging_PV('Aero tiltX offset', '1ide:USdig_X3:1:A1.B.VAL')
mac.add_logging_PV('Aero tiltZ', '1ide:USdig_X3:1:A2.VAL')
mac.add_logging_PV('Aero tiltZ offset', '1ide:USdig_X3:1:A2.B.VAL')

mac.add_logging_PV('MTS tiltZ', '1ide:USdig_X3:2:A1')
mac.add_logging_PV('MTS tiltZ offset', '1ide:USdig_X3:2:A1.B')
mac.add_logging_PV('MTS tiltX', '1ide:USdig_X3:2:A2')
mac.add_logging_PV('MTS tiltX offset', '1ide:USdig_X3:2:A2.B')

# # KEYENCE
# mac.add_logging_PV('keyence1', '1ide:Keyence:1:ch1.VAL')
# mac.add_logging_PV('keyence2', '1ide:Keyence:1:ch2.VAL')

"""
# Federal/Solartron Encoders for position monitoring from E-hutch
mac.add_logging_PV('Fedrl1 (mm)', '1ide:Fed:s1:probe_1')
mac.add_logging_PV('Fedrl2 (mm)', '1ide:Fed:s1:probe_2')
# mac.add_logging_PV('Fedrl3 (mm)', '1ide:Fed:s1:probe_3')
# mac.add_logging_PV('Fedrl4 (mm)', '1ide:Fed:s1:probe_4')
# mac.add_logging_PV('Fedrl5 (mm)', '1ide:Fed:s1:probe_5')
# mac.add_logging_PV('Fedrl6 (mm)', '1ide:Fed:s1:probe_6')
# mac.add_logging_PV('Fedrl7 (mm)', '1ide:Fed:s1:probe_7')
# mac.add_logging_PV('Fedrl8 (mm)', '1ide:Fed:s1:probe_8')
"""

"""
# Federal/Solartron Encoders for position monitoring from C-hutch
mac.add_logging_PV('Fedrl1 (mm)', '1id:Fed:s1:probe_1')
mac.add_logging_PV('Fedrl2 (mm)', '1id:Fed:s1:probe_2')
mac.add_logging_PV('Fedrl3 (mm)', '1id:Fed:s1:probe_3')
mac.add_logging_PV('Fedrl4 (mm)', '1id:Fed:s1:probe_4')
mac.add_logging_PV('Fedrl5 (mm)', '1id:Fed:s1:probe_5')
mac.add_logging_PV('Fedrl6 (mm)', '1id:Fed:s1:probe_6')
mac.add_logging_PV('Fedrl7 (mm)', '1id:Fed:s1:probe_7')
mac.add_logging_PV('Fedrl8 (mm)', '1id:Fed:s1:probe_8')
"""

# # Compact loadframe
# mac.add_logging_PV('Disp (mm)', '1idc:m33.RBV')
# mac.add_logging_PV('Load E (V)', '1ide:D1Ch7_raw.VAL')
# mac.add_logging_PV('Load E (N)', '1ide:D1Ch7_calc.VAL')
# mac.add_logging_PV('Load C (V)', '1id:D2Ch11_raw.VAL')
# mac.add_logging_PV('Load C (N)', '1id:D2Ch11_calc.VAL')


# # meimei psylotech load frame
# mac.add_logging_PV('Load (V)', '1ide:D1Ch17_raw.VAL')
# mac.add_logging_PV('Load (N)', '1ide:D1Ch17_calc.VAL')

"""
# Compact loadframe UL / DESY
mac.add_logging_PV('Disp (mm)', '1idc:m33.RBV')
mac.add_logging_PV('Load (V)', '1ide:D1Ch22_raw.VAL')
mac.add_logging_PV('Load (N)', '1ide:D1Ch22_calc.VAL')
mac.add_logging_PV('sg1 (V)', '1ide:D1Ch21_raw.VAL')
mac.add_logging_PV('sg1 (strain)', '1ide:D1Ch21_calc.VAL')
mac.add_logging_PV('sg2 (V)', '1ide:D1Ch23_raw.VAL')
mac.add_logging_PV('sg2 (strain)', '1ide:D1Ch23_calc.VAL')
"""

"""
# OWIS compression type
mac.add_logging_PV('Disp (mm)', '1idc:m79.RBV')
mac.add_logging_PV('Load (V)', '1ide:D1Ch7_raw.VAL')
mac.add_logging_PV('Load (N)', '1ide:D1Ch7_calc.VAL')
"""

# MTS
mac.add_logging_PV('MTS crosshead (V)', '1ide:D1Ch11_raw.VAL')
mac.add_logging_PV('MTS crosshead (mm)', '1ide:D1Ch11_calc.VAL')
mac.add_logging_PV('MTS load (V)', '1ide:D1Ch12_raw.VAL')
mac.add_logging_PV('MTS load (mm)', '1ide:D1Ch12_calc.VAL')

# ## NIST BOULDER CONNOLLY H2 CHAMBER
# mac.add_logging_PV('Chamber load (V)', '1ide:D1Ch20_raw.VAL')
# mac.add_logging_PV('Chamber load (N)', '1ide:D1Ch20_calc.VAL')
# mac.add_logging_PV('Chamber extensometer (V)', '1ide:D1Ch13_raw.VAL')
# mac.add_logging_PV('Chamber extensometer (strain)', '1ide:D1Ch13_calc.VAL')

# handshake signals
mac.add_logging_PV('MTS In1', '1id:softGlue2:FI11_BI')
mac.add_logging_PV('MTS In2', '1id:softGlue2:FI12_BI')
mac.add_logging_PV('MTS In3', '1id:softGlue2:FI13_BI')
mac.add_logging_PV('MTS Out1', '1id:9440:1:bo_10.VAL')
mac.add_logging_PV('MTS Out2', '1id:9440:1:bo_11.VAL')
mac.add_logging_PV('MTS Out3', '1id:9440:1:bo_12.VAL')

"""
# RAMS1
mac.add_logging_PV('ramsrot (deg)','1idrams1:m1.RBV')
"""

"""
# MTS - BIAXIAL
mac.add_logging_PV('ch31 (V)', '1ide:D1Ch31_raw.VAL')
mac.add_logging_PV('ch32 (V)', '1ide:D1Ch32_raw.VAL')
mac.add_logging_PV('ch33 (V)', '1ide:D1Ch33_raw.VAL')
mac.add_logging_PV('ch34 (V)', '1ide:D1Ch34_raw.VAL')
mac.add_logging_PV('ch35 (V)', '1ide:D1Ch35_raw.VAL')
mac.add_logging_PV('ch36 (V)', '1ide:D1Ch36_raw.VAL')
mac.add_logging_PV('ch37 (V)', '1ide:D1Ch37_raw.VAL')
mac.add_logging_PV('ch38 (V)', '1ide:D1Ch38_raw.VAL')
"""

### IR FURNACE
mac.add_logging_PV('Furnace T1 (C)','1id:ET_RI:Temp1')
mac.add_logging_PV('Furnace T2 (C)','1id:ET_RI:Temp2')
mac.add_logging_PV('Furnace T3 (C)','1id:ET_RI:Temp3')
mac.add_logging_PV('User set point (C)','1id:ET_RI:SP1')
mac.add_logging_PV('Set point (C)','1id:ET_RI:Sp1')
mac.add_logging_PV('Output power (pct)','1id:ET_RI:OP1')
mac.add_logging_PV('Ramp rate (C per min)','1id:ET_RI:RRt1')
mac.add_logging_PV('Ramp rate RBV (C per min)','1id:ET_RI:RR1')

"""
### LANL RF FURNACE
mac.add_logging_PV('RF set point (C)','Smarts:Lake:GetSP3')
mac.add_logging_PV('RF set point input (C)','Smarts:Lake:SetSP3')
mac.add_logging_PV('RF Tc (C)','Smarts:Lake:GetCelsiusC')
mac.add_logging_PV('RF Td (C)','Smarts:Lake:GetCelsiusD')
mac.add_logging_PV('RF Heater range','Smarts:Lake:GetRange3')
mac.add_logging_PV('RF power limit3 RBV (-)', 'Smarts:Lake:GetPower3')
mac.add_logging_PV('RF power limit3 (-)', 'Smarts:Lake:PowerLimit3')
mac.add_logging_PV('RF set ramp3 (C)', 'Smarts:Lake:SetRamp3')
mac.add_logging_PV('RF get TlimC (C)', 'Smarts:Lake:GetTLimC')
mac.add_logging_PV('RF get TlimC (C)', 'Smarts:Lake:SetTLimC')
mac.add_logging_PV('RF get TlimD (C)', 'Smarts:Lake:GetTLimD')
mac.add_logging_PV('RF set TlimD (C)', 'Smarts:Lake:SetTLimD')
"""

# ### LANL CHILLER
# mac.add_logging_PV('RF set point 1 (C)','Smarts:Lake:GetSP1')
# mac.add_logging_PV('RF set point input 1 (C)','Smarts:Lake:SetSP1')
# mac.add_logging_PV('RF set point 2 (C)','Smarts:Lake:GetSP2')
# mac.add_logging_PV('RF set point input 2 (C)','Smarts:Lake:SetSP2')
# mac.add_logging_PV('RF Tc A (C)','Smarts:Lake:GetKelvinA')
# mac.add_logging_PV('RF Td B (C)','Smarts:Lake:GetKelvinB')
# mac.add_logging_PV('RF Heater range 1','Smarts:Lake:GetRange1')
# mac.add_logging_PV('RF power limit1 RBV (-)', 'Smarts:Lake:GetPower1')
# mac.add_logging_PV('RF power limit1 (-)', 'Smarts:Lake:PowerLimit1')
# mac.add_logging_PV('RF Heater range 2','Smarts:Lake:GetRange2')
# mac.add_logging_PV('RF power limit2 RBV (-)', 'Smarts:Lake:GetPower2')
# mac.add_logging_PV('RF power limit2 (-)', 'Smarts:Lake:PowerLimit2')
# mac.add_logging_PV('RF set ramp1 (C)', 'Smarts:Lake:SetRamp1')
# mac.add_logging_PV('RF set ramp2 (C)', 'Smarts:Lake:SetRamp2')
# mac.add_logging_PV('RF get TlimC (C)', 'Smarts:Lake:GetTLimA')
# mac.add_logging_PV('RF get TlimC (C)', 'Smarts:Lake:SetTLimA')
# mac.add_logging_PV('RF get TlimD (C)', 'Smarts:Lake:GetTLimB')
# mac.add_logging_PV('RF set TlimD (C)', 'Smarts:Lake:SetTLimB')
"""
mac.add_logging_PV('Heating Sample Temp (K)', 'Brandon:LakeshoreB:SensorA')
mac.add_logging_PV('Heating Heater Output (%)', 'Brandon:LakeshoreB:HeaterOutput1')
mac.add_logging_PV('Heating Setpoint (C)', 'Brandon:LakeshoreB:Setpoint1')
mac.add_logging_PV('Heating Sample Temp (K)', 'Brandon:LakeshoreA:SensorA')
mac.add_logging_PV('Cooling Setpoint (C)', 'Brandon:LakeshoreA:Setpoint1')
mac.add_logging_PV('Cooling Heater Output (%)', 'Brandon:LakeshoreA:HeaterOutput1')
mac.add_logging_PV('Pyrometer Temperature (C)', 'Brandon:Pyro:Temperature')
"""
# ### LANL WELDER
# mac.add_logging_PV('LANL TA C (C)', 'Belial:LakeshoreA:GetCelsiusC')
# mac.add_logging_PV('LANL TA D (C)', 'Belial:LakeshoreA:GetCelsiusD')
# mac.add_logging_PV('LANL TB C (C)', 'Belial:LakeshoreB:GetCelsiusC')
# mac.add_logging_PV('LANL TB D (C)', 'Belial:LakeshoreB:GetCelsiusD')

# ### LINKAM FURNACE
# mac.add_logging_PV('Linkam rate Cps','1ide:ci94:setRate')
# mac.add_logging_PV('Linkam T1 input (C)','1ide:ci94:setLimit')
# mac.add_logging_PV('Linkam T1 (C)','1ide:ci94:temp')
# mac.add_logging_PV('Linkam T2 (C)','1ide:ci94:temp2')
# mac.add_logging_PV('Linkam status','1ide:ci94:status')
# mac.add_logging_PV('Linkam DSC','1ide:ci94:dsc')

# ### SUTER-BASIL FURNACE
# mac.add_logging_PV('CMU Furnace T (deg C)', '1ide:ET2k:1:Temperature.VAL')
# mac.add_logging_PV('CMU Ramp rate (degC per min)','1ide:ET2k:1:WriteRampRate.VAL')
# mac.add_logging_PV('CMU Ramp rate readback (degC per min)','1ide:ET2k:1:ReadRampRate.VAL')
# mac.add_logging_PV('CMU Furnce output (pct)','1ide:ET2k:1:RBV_Output')
# mac.add_logging_PV('CMU Read set pt (deg C)','1ide:ET2k:1:ReadSetPoint.VAL')
# mac.add_logging_PV('CMU Read wset pt (deg C)','1ide:ET2k:1:ReadWSetPoint.VAL')
# mac.add_logging_PV('CMU Write set pt (deg C)','1ide:ET2k:1:WriteSetPoint.VAL')
# # mac.add_logging_PV('CMU Gas flow meter (V)','1idadam:adam_6017:1:AI0')
# mac.add_logging_PV('Tsam (deg C)','1idTC32:Ti7')
# mac.add_logging_PV('CMU T housing (deg C)','1idTC32:Ti24')

# ### HASTINGS FURNACE
# mac.add_logging_PV('Furnace T1 (C)','1mini2:ET2k:1:Temp')
# mac.add_logging_PV('Furnace T2 (C)','1idTC32:Ti8')
# mac.add_logging_PV('User set point (C)','1mini2:ET2k:1:SP')
# mac.add_logging_PV('Set point (C)','1mini2:ET2k:1:Sp')
# mac.add_logging_PV('Output power (pct)','1mini2:ET2k:1:OP')
# mac.add_logging_PV('Ramp rate (C per min)','1mini2:ET2k:1:RRt')
# mac.add_logging_PV('Ramp rate RBV (C per min)','1mini2:ET2k:1:RR')

# ### FZHANG COLD SINTER FURNACE
# mac.add_logging_PV('FZHANG Furnace Force (-)', '9idcCOLD:force')
# mac.add_logging_PV('FZHANG Furnace Force RBV (-)', '9idcCOLD:force_RBV')
# mac.add_logging_PV('FZHANG Furnace Pressure (MPa)', '9idcCOLD:pressure.VAL')
# mac.add_logging_PV('FZHANG Furnace piston (ustep)', '9idcCOLD:piston')
# mac.add_logging_PV('FZHANG Furnace piston RBV (ustep)', '9idcCOLD:piston_RBV')
# mac.add_logging_PV('FZHANG Furnace extension (mm)', '9idcCOLD:extension.VAL')
# mac.add_logging_PV('FZHANG Furnace temperature target (deg C)', '9idcCOLD:temp')
# mac.add_logging_PV('FZHANG Furnace temperature RBV (deg C)', '9idcCOLD:temp_RBV')
# mac.add_logging_PV('FZHANG Furnace heat rate (deg C / min)', '9idcCOLD:hrate')
# mac.add_logging_PV('FZHANG Furnace heat rate RBV (deg C / min)', '9idcCOLD:hrate_RBV')
# mac.add_logging_PV('FZHANG Furnace P(-)', '9idcCOLD:Kp')
# mac.add_logging_PV('FZHANG Furnace P RBV (-)', '9idcCOLD:Kp_RBV')
# mac.add_logging_PV('FZHANG Furnace I (-)', '9idcCOLD:Ki')
# mac.add_logging_PV('FZHANG Furnace I RBV (-)', '9idcCOLD:Ki_RBV')
# mac.add_logging_PV('FZHANG Furnace D (-)', '9idcCOLD:Kd')
# mac.add_logging_PV('FZHANG Furnace D RBV (-)', '9idcCOLD:Kd_RBV')
# mac.add_logging_PV('FZHANG Furnace auto state (-)', '9idcCOLD:auto')
# mac.add_logging_PV('FZHANG Furnace stop state (-)', '9idcCOLD:stop')

### RAMS3
# mac.add_logging_PV('rams3 Slow Out1 (V)', '1ide:D1Ch21_raw.VAL')
# mac.add_logging_PV('rams3 Slow Out1 (-)', '1ide:D1Ch21_calc.VAL')
# mac.add_logging_PV('rams3 Fast LoadA (V)', '1ide:D1Ch22_raw.VAL')
# mac.add_logging_PV('rams3 Fast LoadA (N)', '1ide:D1Ch22_calc.VAL')
# mac.add_logging_PV('rams3 Slow Out2 (V)', '1ide:D1Ch23_raw.VAL')
# mac.add_logging_PV('rams3 Slow Out2 (-)', '1ide:D1Ch23_calc.VAL')
# mac.add_logging_PV('rams3 Fast LoadB (V)', '1ide:D1Ch24_raw.VAL')
# mac.add_logging_PV('rams3 Fast LoadB (N)', '1ide:D1Ch24_calc.VAL')
# mac.add_logging_PV('rams3 Torsion (V)', '1ide:D1Ch25_raw.VAL')
# mac.add_logging_PV('rams3 Torsion (N-m)', '1ide:D1Ch25_calc.VAL')
# mac.add_logging_PV('rams3 Load cellA-dig (N)', '1ide:RAMS3_LC:Force1')
# mac.add_logging_PV('rams3 Load cellB-dig (N)', '1ide:RAMS3_LC:Force2')
# mac.add_logging_PV('rams3 TopRot (deg)','1idrams3:m1.RBV')
# mac.add_logging_PV('rams3 BotRot (deg)','1idrams3:m2.RBV')
# mac.add_logging_PV('rams3 tension (mm)','1idrams3:m3.RBV')
# mac.add_logging_PV('rams3 rot (deg)','1idrams3:m4.RBV')
# mac.add_logging_PV('rams3 offset (deg)','1idrams3:m5.RBV')
# mac.add_logging_PV('rams3 rotX (mm)','1idc:m2.RBV')
# mac.add_logging_PV('rams3 tiltX (deg)','1idc:m4.RBV')
# mac.add_logging_PV('rams3 tiltZ (deg)','1idc:m3.RBV')
# mac.add_logging_PV('rams3 samY (mm)','1idc:m6.RBV')
# mac.add_logging_PV('rams3 tableY (mm)','1idc:m5.RBV')
# mac.add_logging_PV('rams3 sam top rotation encoder (deg)','1ide:userStringCalc10.VAL')


### THERMOCOUPLE
# mac.add_logging_PV('TC1 (C)','1ide:DP41:s1:temp.VAL')
# mac.add_logging_PV('TC2 (C)','1ide:DP41:s2:temp.VAL')
# mac.add_logging_PV('TC2 (C)','1ide:DP41:s3:temp.VAL')
"""
mac.add_logging_PV('T24-surface (C)','1idTC32:Ti24')
mac.add_logging_PV('TCC (C)','1idTC32:Ti3')
mac.add_logging_PV('TCD (C)','1idTC32:Ti4')
mac.add_logging_PV('TCE (C)','1idTC32:Ti5')
mac.add_logging_PV('TCF (C)','1idTC32:Ti6')
mac.add_logging_PV('TCG (C)','1idTC32:Ti7')
mac.add_logging_PV('TCH (C)','1idTC32:Ti8')
"""

# mac.add_logging_PV('T1 (C)','1id:ET_RI:Temp1')
# mac.add_logging_PV('T2 (C)','1id:ET_RI:Temp2')
# mac.add_logging_PV('T3 (C)','1id:ET_RI:Temp3')

"""
mac.add_logging_PV('Tsurf (C)','1idTC32:Ti1')
mac.add_logging_PV('Tsurf (C)','1idTC32:Ti11')
mac.add_logging_PV('Tsurf (C)','1idTC32:Ti7')
"""

# ### FLOW METER 
# mac.add_logging_PV('FLOW (V)','1ide:D1Ch8_raw.VAL')
# mac.add_logging_PV('FLOW (LPM)','1ide:D1Ch8_calc.VAL')

"""
# Hutch monitoring thermocouples
mac.add_logging_PV('TC16 (C)','1idTC32:Ti16')
mac.add_logging_PV('TC17 (C)','1idTC32:Ti17')
mac.add_logging_PV('TC18 (C)','1idTC32:Ti18')
mac.add_logging_PV('TC19 (C)','1idTC32:Ti19')
mac.add_logging_PV('TC20 (C)','1idTC32:Ti20')

mac.add_logging_PV('TRIBO-A-raw (V)','1ide:D1Ch28_raw.VAL')
mac.add_logging_PV('TRIBO-B-raw (V)','1ide:D1Ch29_raw.VAL')
mac.add_logging_PV('TRIBO-A-calc','1ide:D1Ch28_calc.VAL')
mac.add_logging_PV('TRIBO-B-calc','1ide:D1Ch29_calc.VAL')
mac.add_logging_PV('TTLTrigger','1ide:sg2:FI6_BI')
"""

"""
# AGILENT FUNC GEN
mac.add_logging_PV('offset (V)','1ide:33220A:1:offset_V.A')
mac.add_logging_PV('offset_rbk (V)','1ide:33220A:1:offset')
"""

"""
# VOLTAGE SIGNAL POKHAREL_MAR18
mac.add_logging_PV('Sample (V)','1ide:D1Ch21_calc.VAL')
"""
mac.write_logging_header(logname)
