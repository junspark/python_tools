import sys
import numpy
import scipy
import math
import logging
import time
import csv
import smtplib  # Import smtplib for the actual sending function

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

from email.mime.image import MIMEImage  # Here are the email package modules we'll need
from email.mime.multipart import MIMEMultipart

#################################################
### THIS IS THE INSTALL FOR NOW
### POINTS AT THE FOLDER WHERE THE PYTHON SOURCE FILES ARE
### THIS WILL BE IMPROVED
#################################################
sys.path.insert(0, '/home/beams/S1IDUSER/APSpy/src')

#################################################
# ENABLES PYEPICS
#################################################
spec.EnableEPICS()

#################################################
# PV RECORD
#################################################
def pv_monitor (LogName, TimeInterval):
    print 'monitoring in progress'
    
    # s1id_staff = ['almer@aps.anl.gov', 'okasinski@aps.anl.gov', 'shastri@aps.anl.gov', 'kenesei@aps.anl.gov', 'mashayek@aps.anl.gov', 'parkjs@aps.anl.gov']
    s1id_staff = ['parkjs@aps.anl.gov', 'mashayek@aps.anl.gov']
    
    GE_Temp_Thresh = 27
    
    ###################################################    
    ### INITIATE LOGGING
    ###################################################
    mac.init_logging()
    
    ### INFO FROM TALL PANEL
    mac.add_logging_PV('Iring (mA)','S:SRcurrentAI')
    mac.add_logging_PV('ID Gap (mm)','ID01:Gap.VAL')
    mac.add_logging_PV('Energy (keV)','1id:userTran3.A')

    mac.add_logging_PV('1st Raw Signal A (uA)','FE:01:ID:1XBPM:A:CC')
    mac.add_logging_PV('1st Raw Signal B (uA)','FE:01:ID:1XBPM:B:CC')
    mac.add_logging_PV('1st Raw Signal C (uA)','FE:01:ID:1XBPM:C:CC')
    mac.add_logging_PV('1st Raw Signal D (uA)','FE:01:ID:1XBPM:D:CC')
    
    mac.add_logging_PV('2nd Raw Signal A (uA)','FE:01:ID:2XBPM:A:CC')
    mac.add_logging_PV('2nd Raw Signal B (uA)','FE:01:ID:2XBPM:B:CC')
    mac.add_logging_PV('2nd Raw Signal E (uA)','FE:01:ID:2XBPM:E:CC')
    mac.add_logging_PV('2nd Raw Signal F (uA)','FE:01:ID:2XBPM:F:CC')
    
    mac.add_logging_PV('1XBPM VPOS (mm)','FE:01:ID:1XBPM:VPOS:CC')
    mac.add_logging_PV('2XBPM VPOS (mm)','FE:01:ID:2XBPM:VPOS:CC')
    
    mac.add_logging_PV('1XBPM HPOS (mm)','FE:01:ID:1XBPM:HPOS:CC')
    mac.add_logging_PV('2XBPM HPOS (mm)','FE:01:ID:2XBPM:HPOS:CC')
    
    mac.add_logging_PV('XBPM VPOS Norm @ SRC (mm)','FE:01:ID:VPOSITION:CC')
    mac.add_logging_PV('XBPM VANGLE Norm @ SRC (urad)','FE:01:ID:VANGLE:CC')
    mac.add_logging_PV('XBPM HPOS Norm @ SRC (mm)','FE:01:ID:HPOSITION:CC')
    mac.add_logging_PV('XBPM HANGLE Norm @ SRC (urad)','FE:01:ID:HANGLE:CC')
    
    mac.add_logging_PV('PBPM VPOS (mm)','S1:ID:SrcPt:yPositionM')
    mac.add_logging_PV('PBPM VANGLE (urad)','S1:ID:SrcPt:yAngleM')
    mac.add_logging_PV('PBPM HPOS (mm)','S1:ID:SrcPt:xPositionM')
    mac.add_logging_PV('PBPM HANGLE (urad)','S1:ID:SrcPt:xAngleM')
    
    ### INFO FROM WIDE PANEL
    mac.add_logging_PV('SR Current (mA)','BL01:srCurrent')
    mac.add_logging_PV('SR Life Time (h)','BL01:srLifetime')
    # mac.add_logging_PV('ID Gap (mm)','BL01:Gap')
    # mac.add_logging_PV('Harmonic','BL01:Harmonic')
    # mac.add_logging_PV('Energy (keV)','BL01:Energy')
    
    mac.add_logging_PV('1st Raw Signal A (uA)','BL01:ID:1XBPM:A')
    mac.add_logging_PV('1st Raw Signal B (uA)','BL01:ID:1XBPM:B')
    mac.add_logging_PV('1st Raw Signal C (uA)','BL01:ID:1XBPM:C')
    mac.add_logging_PV('1st Raw Signal D (uA)','BL01:ID:1XBPM:D')
    
    mac.add_logging_PV('2nd Raw Signal A (uA)','BL01:ID:2XBPM:A')
    mac.add_logging_PV('2nd Raw Signal B (uA)','BL01:ID:2XBPM:B')
    mac.add_logging_PV('2nd Raw Signal C (uA)','BL01:ID:2XBPM:E')
    mac.add_logging_PV('2nd Raw Signal D (uA)','BL01:ID:2XBPM:F')
    
    mac.add_logging_PV('RF BPM VPOS Norm @ SRC','BL01:SRID:VPosition')
    mac.add_logging_PV('RF BPM VANGLE Norm @ SRC','BL01:SRID:VAngle')
    mac.add_logging_PV('RF BPM HPOS Norm @ SRC','BL01:SRID:HPosition')
    mac.add_logging_PV('RF BPM HANGLE Norm @ SRC','BL01:SRID:HAngle')
    
    mac.add_logging_PV('1XBPM VPOS (mm)','BL01:ID:1XBPM:VPOS')
    mac.add_logging_PV('2XBPM VPOS (mm)','BL01:ID:2XBPM:VPOS')
    mac.add_logging_PV('VPOS (mm)','BL01:ID:XBPM:VPosition')
    
    mac.add_logging_PV('1XBPM HPOS (mm)','BL01:ID:1XBPM:HPOS')
    mac.add_logging_PV('2XBPM HPOS (mm)','BL01:ID:2XBPM:HPOS')
    mac.add_logging_PV('HPOS (mm)','BL01:ID:XBPM:HPosition')
    
    mac.add_logging_PV('VANGLE (urad)','BL01:ID:XBPM:VAngle')
    mac.add_logging_PV('HANGLE (urad)','BL01:ID:XBPM:HAngle')
    
    ### SR PARAMETERS INFO
    mac.add_logging_PV('BEAM RMS V Motion (um)','SRFB:dsp2:yRMSmotion30HzPkM.VAL')
    mac.add_logging_PV('BEAM RMS H Motion (um)','SRFB:dsp2:xRMSmotion30HzPkM.VAL')
    mac.add_logging_PV('BEAM V EMITTANCE','S:VID1:filteredYemittance')
    mac.add_logging_PV('BEAM H EMITTANCE','S:VID1:filteredXemittance')
    mac.add_logging_PV('Coupling','S:VID1:filteredCoupling')
    
    ### UNDULATOR INFO
    mac.add_logging_PV('US UND GAP (mm)','ID01us:Gap.VAL')
    mac.add_logging_PV('US UND GAP SET (mm)','ID01us:GapSet.VAL')
    mac.add_logging_PV('US UND Harmonic Value','ID01us:HarmonicValue')
    mac.add_logging_PV('DS UND GAP (mm)','ID01ds:Gap.VAL')
    mac.add_logging_PV('DS UND GAP SET (mm)','ID01ds:GapSet.VAL')
    mac.add_logging_PV('DS UND Harmonic Value','ID01ds:HarmonicValue')
    
    ### HEM TEMPERATURE
    mac.add_logging_PV('HEM 1st XSTAL Temp (K)','1ida:LS218:1:ch1_degK.VAL')
    mac.add_logging_PV('HEM 1st XSTAL MANIFOLD T (K)','1ida:LS218:1:ch2_degK.VAL')
    
    ### LOVE CONTROLLER CONTROL VALUES
    mac.add_logging_PV('P1','1ida:love32:Value')
    mac.add_logging_PV('P2','1ida:love33:Value')
    
    ### AMI
    mac.add_logging_PV('Stablizer Level','1ida:AMI286:1:ch1:Level.VAL')
    mac.add_logging_PV('DD Level','1ida:AMI286:1:ch2:Level.VAL')
    mac.add_logging_PV('DD Valve','1ida:AMI286:1:ch2:Fill.VAL')
    mac.add_logging_PV('Buffer Level','1ida:AMI286:2:ch1:Level.VAL')
    mac.add_logging_PV('Vessel Level','1ida:AMI286:2:ch2:Level.VAL')
    mac.add_logging_PV('Vessel Valve','1ida:AMI286:2:ch2:Fill.VAL')
    
    ### HUTCH TEMPERATURES
    mac.add_logging_PV('A-hutch T (deg C)','1ida:DP41:s1:temp.VAL')
    mac.add_logging_PV('B-hutch T (deg C)','1ida:DP41:s2:temp.VAL')
    mac.add_logging_PV('C-hutch T (deg C)','1id:DP41:s1:temp.VAL')
    mac.add_logging_PV('E-hutch T TILT1 (deg C)','1ide:USdig_X3:1:T')
    mac.add_logging_PV('E-hutch T TILT2 (deg C)','1ide:USdig_X3:2:T')
    
    ### WB SLITS
    mac.add_logging_PV('WB Hr Size','1ida:Slit1Ht2.C')
    mac.add_logging_PV('WB Vt Size','1ida:Slit1Vt2.C')
    mac.add_logging_PV('WB Hr Pos','1ida:Slit1Ht2.D')
    mac.add_logging_PV('WB Vt Pos','1ida:Slit1Vt2.D')
    
    ### IC
    mac.add_logging_PV('B-IC1','1id:scaler2.S3')
    mac.add_logging_PV('C-Split IC1','1id:scaler2.S11')
    mac.add_logging_PV('C-Split IC2','1id:scaler2.S12')
    mac.add_logging_PV('E-Split IC1','1ide:S1:scaler1.S2')
    mac.add_logging_PV('E-Split IC2','1ide:S1:scaler1.S3')
    
    ### GAS PRESSURES
    mac.add_logging_PV('Ni P','1idc:DP41:1:Filtered')
    mac.add_logging_PV('He P','1idc:DP41:2:Filtered')
    mac.add_logging_PV('Ar P','1idc:DP41:3:Filtered')
    
    ### GE TEMPERATURES
    mac.add_logging_PV('HYDRA ORANGE LOOP (deg C)','1ide:DP41:s2:temp.VAL')
    mac.add_logging_PV('HYDRA BLUE LOOP (deg C)','1ide:DP41:s3:temp.VAL')
    
    OrgLoopPV = PyEpics.pv.PV('1ide:DP41:s2:temp.VAL')
    BluLoopPV = PyEpics.pv.PV('1ide:DP41:s3:temp.VAL')
    
    while True:
        mac.write_logging_header(LogName)
        mac.write_logging_parameters(LogName)
        
        print 'Do not shut off unless authorized by S1 staff'
        print time.ctime() + ' : wrote PV data'
        
        if (OrgLoopPV.get() > GE_Temp_Thresh) or (BluLoopPV.get() > GE_Temp_Thresh):
            pv_alert(s1id_staff, LogName, TimeInterval, AlertType=1)
            
        spec.sleep(TimeInterval)


def pv_alert(EmailRecipients, LogName, TimeInterval, AlertType=0):
    CommaSpace = ', '
    EmailSender = 's1iduser@aps.anl.gov'
    
    # Create the container (outer) email message.
    msg = MIMEMultipart()
    
    # EmailSender == the sender's email address
    # EmailRecipients = the list of all recipients' email addresses
    msg['From'] = EmailSender
    msg['To'] = CommaSpace.join(EmailRecipients)
    if AlertType is 0:
        msg['Subject'] = 'TEST MODE: python alert: general error'
        msg.preamble = 'TEST MODE: python alert: general error'
    elif AlertType is 1:
        msg['Subject'] = 'TEST MODE: python alert: python says GE is too hot'
        msg.preamble = 'TEST MODE: python alert: python says GE is too hot'
        
        OrgTemp = []
        BluTemp = []
        with open(LogName, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                if reader.line_num > 1:
                    ### GE TEMPERATURES
                    OrgTemp.append(float(row[84]))
                    BluTemp.append(float(row[85]))
            
        x = numpy.linspace(1, len(OrgTemp), len(OrgTemp)) * TimeInterval
        
        plt.ion()
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(x, OrgTemp, 'v', x, BluTemp, '^')
        ax.set_xlabel('time (sec)')
        ax.set_ylabel('GE temperature (deg C)')
        plt.savefig('python_alert_image.png')
        plt.close()
        
        fp = open('python_alert_image.png', 'rb')
        img = MIMEImage(fp.read(), 'png')
        fp.close()
        msg.attach(img)
        
    # Send the email via our own SMTP server.
    s = smtplib.SMTP('localhost')
    s.sendmail(EmailSender, EmailRecipients, msg.as_string())
    s.quit()
