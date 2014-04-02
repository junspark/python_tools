import sys
import numpy
import scipy
import math
import logging
import time

import datetime as dt
import epics as PyEpics  ## import epics as ep  #from epics import PV
import matplotlib.pyplot as plt
import APSpy.spec as spec
import APSpy.macros as mac
import APSpy.rst_table as rst_table
import APSpy.AD as AD

from scipy.special import erf
from scipy.optimize import curve_fit
from pprint import pprint

#################################################
### THIS IS THE INSTALL FOR NOW
### POINTS AT THE FOLDER WHERE THE PYTHON SOURCE FILES ARE
### THIS WILL BE IMPROVED
#################################################
sys.path.insert(0, '/home/beams/S1IDUSER/APSpy/src')

alldone = PyEpics.PV('1idc:alldone')

### SHOULDNT THIS BE PART OF THE STANDARD LIB?
def ImportMotorSymbols():
    exec( spec.DefineMotorSymbols( spec.mtrDB, make_global=True ) )

#################################################
# PV RECORD
#################################################
def bpm_monitor (logname):
    print 'monitoring in progress'
    
    while True:
        mac.write_logging_header(logname)
        mac.write_logging_parameters(logname)
        
        print 'do not shut off unless authorized by ali'
        print time.ctime() + ' : wrote bpm data to ' + logname
        spec.sleep(10)

spec.EnableEPICS()

###################################################    
### MOTOR MOTION & FIT
### DEF MOTORS FIRST
###################################################
spec.DefineMtr('m1v', '1idc:m19', 'm1v (mm)')
spec.DefineScaler('1id:scaler1',16)

ImportMotorSymbols()
spec.ListMtrs()

###################################################
### USER INPUT
###################################################
logname = '/home/1-id/s1iduser/mashayekhi_jan14/mashayekhi_jan14_bpm.par' ## PATH WHERE PAR FILE LIVES

###################################################    
### INITIATE LOGGING
###################################################
mac.init_logging()
mac.add_logging_PV('Iring',"BL01:srCurrent")
mac.add_logging_PV('energy',"1id:userTran3.A")
mac.add_logging_PV('FE:01:ID:1XBPM:A:CC',"FE:01:ID:1XBPM:A:CC")
mac.add_logging_PV('FE:01:ID:1XBPM:B:CC',"FE:01:ID:1XBPM:B:CC")
mac.add_logging_PV('FE:01:ID:1XBPM:C:CC',"FE:01:ID:1XBPM:C:CC")
mac.add_logging_PV('FE:01:ID:1XBPM:D:CC',"FE:01:ID:1XBPM:D:CC")
mac.add_logging_PV('FE:01:ID:2XBPM:A:CC',"FE:01:ID:2XBPM:A:CC")
mac.add_logging_PV('FE:01:ID:2XBPM:B:CC',"FE:01:ID:2XBPM:B:CC")
mac.add_logging_PV('FE:01:ID:1XBPM:VPOS:CC',"FE:01:ID:1XBPM:VPOS:CC")
mac.add_logging_PV('FE:01:ID:2XBPM:VPOS:CC',"FE:01:ID:2XBPM:VPOS:CC")
mac.add_logging_PV('FE:01:ID:1XBPM:HPOS:CC',"FE:01:ID:1XBPM:HPOS:CC")
mac.add_logging_PV('FE:01:ID:2XBPM:HPOS:CC',"FE:01:ID:2XBPM:HPOS:CC")
mac.add_logging_PV('FE:01:ID:VPOSITION:CC',"FE:01:ID:VPOSITION:CC")
mac.add_logging_PV('FE:01:ID:VANGLE:CC',"FE:01:ID:VANGLE:CC")
mac.add_logging_PV('FE:01:ID:HPOSITION:CC',"FE:01:ID:HPOSITION:CC")
mac.add_logging_PV('FE:01:ID:HANGLE:CC',"FE:01:ID:HANGLE:CC")
mac.add_logging_PV('ID01:Gap.VAL',"ID01:Gap.VAL")
mac.add_logging_PV('S1:ID:SrcPt:xPositionM',"S1:ID:SrcPt:xPositionM")
mac.add_logging_PV('S1:ID:SrcPt:xAngleM',"S1:ID:SrcPt:xAngleM")
mac.add_logging_PV('S1:ID:SrcPt:yPositionM',"S1:ID:SrcPt:yPositionM")
mac.add_logging_PV('S1:ID:SrcPt:yAngleM',"S1:ID:SrcPt:yAngleM")
mac.add_logging_PV('BL01:srCurrent',"BL01:srCurrent")
mac.add_logging_PV('BL01:srLifetime',"BL01:srLifetime")
mac.add_logging_PV('BL01:Gap',"BL01:Gap")
mac.add_logging_PV('BL01:Harmonic',"BL01:Harmonic")
mac.add_logging_PV('BL01:Energy',"BL01:Energy")
mac.add_logging_PV('BL01:ID:1XBPM:A',"BL01:ID:1XBPM:A")
mac.add_logging_PV('BL01:ID:1XBPM:B',"BL01:ID:1XBPM:B")
mac.add_logging_PV('BL01:ID:1XBPM:C',"BL01:ID:1XBPM:C")
mac.add_logging_PV('BL01:ID:1XBPM:D',"BL01:ID:1XBPM:D")
mac.add_logging_PV('BL01:ID:2XBPM:A',"BL01:ID:2XBPM:A")
mac.add_logging_PV('BL01:ID:2XBPM:E',"BL01:ID:2XBPM:E")
mac.add_logging_PV('BL01:ID:2XBPM:B',"BL01:ID:2XBPM:B")
mac.add_logging_PV('BL01:ID:2XBPM:F',"BL01:ID:2XBPM:F")
mac.add_logging_PV('BL01:SRID:HPosition',"BL01:SRID:HPosition")
mac.add_logging_PV('BL01:SRID:HAngle',"BL01:SRID:HAngle")
mac.add_logging_PV('BL01:SRID:VPosition',"BL01:SRID:VPosition")
mac.add_logging_PV('BL01:SRID:VAngle',"BL01:SRID:VAngle")
mac.add_logging_PV('BL01:ID:1XBPM:HPOS',"BL01:ID:1XBPM:HPOS")
mac.add_logging_PV('BL01:ID:2XBPM:HPOS',"BL01:ID:2XBPM:HPOS")
mac.add_logging_PV('BL01:ID:XBPM:HPosition',"BL01:ID:XBPM:HPosition")
mac.add_logging_PV('BL01:ID:1XBPM:VPOS',"BL01:ID:1XBPM:VPOS")
mac.add_logging_PV('BL01:ID:2XBPM:VPOS',"BL01:ID:2XBPM:VPOS")
mac.add_logging_PV('BL01:ID:XBPM:VPosition',"BL01:ID:XBPM:VPosition")
mac.add_logging_PV('BL01:ID:XBPM:HAngle',"BL01:ID:XBPM:HAngle")
mac.add_logging_PV('BL01:ID:XBPM:VAngle',"BL01:ID:XBPM:VAngle")
mac.add_logging_PV('SRFB:dsp2:xRMSmotion30HzPkM.VAL',"SRFB:dsp2:xRMSmotion30HzPkM.VAL")
mac.add_logging_PV('SRFB:dsp2:yRMSmotion30HzPkM.VAL',"SRFB:dsp2:yRMSmotion30HzPkM.VAL")
mac.add_logging_PV('S:VID1:filteredXemittance',"S:VID1:filteredXemittance")
mac.add_logging_PV('S:VID1:filteredYemittance',"S:VID1:filteredYemittance")
mac.add_logging_PV('S:VID1:filteredCoupling',"S:VID1:filteredCoupling")
mac.add_logging_PV('ID01us:Gap.VAL',"ID01us:Gap.VAL")
mac.add_logging_PV('ID01us:GapSet.VAL',"ID01us:GapSet.VAL")
mac.add_logging_PV('ID01us:HarmonicValue',"ID01us:HarmonicValue")
mac.add_logging_PV('ID01ds:Gap.VAL',"ID01ds:Gap.VAL")
mac.add_logging_PV('ID01ds:GapSet.VAL',"ID01ds:GapSet.VAL")
mac.add_logging_PV('ID01ds:HarmonicValue',"ID01ds:HarmonicValue")
mac.add_logging_PV('1st xstal T',"1ida:LS218:1:ch1_degK.VAL")
mac.add_logging_PV('1st xstal manifold T',"1ida:LS218:1:ch2_degK.VAL")
mac.add_logging_PV('P1',"1ida:love32:Value")
mac.add_logging_PV('P2',"1ida:love33:Value")
mac.add_logging_PV('Stablizer Level',"1ida:AMI286:1:ch1:Level.VAL")
mac.add_logging_PV('DD Level',"1ida:AMI286:1:ch2:Level.VAL")
mac.add_logging_PV('DD Valve',"1ida:AMI286:1:ch2:Fill.VAL")
mac.add_logging_PV('Buffer Level',"1ida:AMI286:2:ch1:Level.VAL")
mac.add_logging_PV('Vessel Level',"1ida:AMI286:2:ch2:Level.VAL")
mac.add_logging_PV('Vessel Valve',"1ida:AMI286:2:ch2:Fill.VAL")
mac.add_logging_PV('A-hutch T',"1ida:DP41:s1:temp.VAL")
mac.add_logging_PV('B-hutch T',"1ida:DP41:s2:temp.VAL")
mac.add_logging_PV('C-hutch T',"1id:DP41:s1:temp.VAL")
mac.add_logging_PV('WB Hr Size',"1ida:Slit1Ht2.C")
mac.add_logging_PV('WB Vt Size',"1ida:Slit1Vt2.C")
mac.add_logging_PV('WB Hr Pos',"1ida:Slit1Ht2.D")
mac.add_logging_PV('WB Vt Pos',"1ida:Slit1Vt2.D")
mac.add_logging_PV('B-IC1',"1id:scaler2.S3")
mac.add_logging_PV('C-Split IC1',"1id:scaler2.S11")
mac.add_logging_PV('C-Split IC2',"1id:scaler2.S12")
mac.add_logging_PV('E-Split IC1',"1ide:S1:scaler1.S2")
mac.add_logging_PV('E-Split IC2',"1ide:S1:scaler1.S3")
mac.add_logging_PV('Ni P',"1idc:DP41:1:Filtered")
mac.add_logging_PV('He P',"1idc:DP41:2:Filtered")
mac.add_logging_PV('Ar P',"1idc:DP41:3:Filtered")
### IF THERE ARE OTHER MOTIONS, WE ADD
# mac.add_logging_motor(m1v)
### IF THERE ARE OTHER CHANNELS, WE ADD
# mac.add_logging_PV('keyence1',"1id:Keyence:1:ch1.VAL") 
# mac.add_logging_PV('keyence2',"1id:Keyence:1:ch2.VAL") 
# mac.add_logging_PV('cross',"1id:D2Ch1_calc.VAL") 
# mac.add_logging_PV('load',"1id:D2Ch2_calc.VAL") 
# mac.add_logging_PV('extensometer',"1id:D2Ch3_calc.VAL") 
# mac.add_logging_PV('mts4',"1id:D2Ch4_calc.VAL") 
# mac.add_logging_PV('temp1',"1id:ET_RI:Temp1")
# mac.add_logging_PV('temp2',"1id:ET_RI:Temp2") 
# mac.add_logging_PV('temp3',"1id:ET_RI:Temp3")
