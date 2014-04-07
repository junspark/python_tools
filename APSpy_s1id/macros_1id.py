"""
*Macros specific to 1-ID*
-------------------------

These macros reference 1-ID PV's or are customized for 1-ID in some other manner.

===============================   ============================================================
1-ID specific routines            Description	      
===============================   ============================================================
:func:`Cclose`                    Close 1-ID fast shutter in B hutch
:func:`Copen`                     Open 1-ID fast shutter in B hutch
:func:`shutter_sweep`             Set 1-ID fast shutter to external control
:func:`shutter_manual`            Set 1-ID fast shutter to manually control
:func:`check_beam_shutterA`       Open 1-ID Safety shutter to bring beam into 1-ID-A
:func:`check_beam_shutterC`       Open 1-ID Safety shutter to bring beam into 1-ID-C
:func:`MakeMtrDefaults`           Create a file with default motor assignments
:func:`SaveMotorStatus`           Create a file with soft limits for off-line simulations
:func:`ImportMotorSymbols`        Imports motor symbols into global workspace
:func:`beep_dac`                  Causes a beep to sound
:func:`EnergyMonitor`             Energy monitor using foil
===============================   ============================================================
"""


########### SVN repository information ###################
# $Date: 2013-04-24 18:41:03 -0500 (Wed, 24 Apr 2013) $
# $Author: jemian $
# $Revision: 1281 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/branches/1id_afrl/src/bl_1ID/macros_1id.py $
# $Id: macros_1id.py 1281 2013-04-24 23:41:03Z jemian $
########### SVN repository information ###################

import sys
import os.path
import time
import datetime as dt

import APSpy.spec
import APSpy.macros as mac

EPICS = False
try:
    import epics as ep  #from epics import PV
    EPICS = True
except:
    pass

if EPICS:
    PV = ep.PV
    beeper = PV('1id:DAC1_8.VAL')
    shutterA_state = PV('PA:01ID:A_SHTRS_CLOSED')
    shutterA_openPV = PV('1id:rShtrA:Open.PROC')
    shutterC_state = PV('PA:01ID:C_SHTRS_CLOSED')
    shutterC_openPV = PV('1id:rShtrC:Open.PROC')

    fastshtr_man = PV('1id:9440:1:bo_3.VAL')
    fastshtr_remote = PV('1id:9440:1:bo_5.VAL')

###########################################################################
# SHUTTER CONTROLLERS
###########################################################################
def Cclose(): #arm shutters
    '''Close 1-ID fast shutter in B hutch
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Closing Fast Shutter"
        return
    fastshtr_man.put(0)
    return
    
def Copen(): #arm shutters    
    '''Open 1-ID fast shutter in B hutch
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Opening Fast Shutter"
        return
    fastshtr_man.put(1)
    return
    
def shutter_sweep(): 
    ''' Set 1-ID fast shutter so that it will be controlled by an external electronic control
    (usually the GE TTL signal)
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Set Fast Shutter to sweep"
        return
    Cclose()  #p "Close shutter before changing"    
    fastshtr_remote.put(1)  # p "shutter to sweep mode"
    return
    
def shutter_manual():    
    ''' Set 1-ID fast shutter so that it will not be controlled by the GE TTL signal
    and can be manually opened and closed with Copen() and Cclose()
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Set Fast Shutter to manual"
        return
    Cclose()  #p "Close the shutter, to be sure it is closed"
    fastshtr_remote.put(0)  # p "shutter to manual"
    return
       
def check_beam_shutterA():
    '''If not already open, open 1-ID-A Safety shutter to bring beam into 1-ID-A.
    Keep trying in an infinite loop until the shutter opens.
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Confirm A-Hutch Shutter is open"
        return
    i = 0
    while shutterA_state.get() != 0: # 1 is Closed
        print "sleeping due to beam dump"
        if i == 0: 
            p = PV(shutterA_openPV)
        i += 1
        p.put(1) # send a open command to PV in shutterA_openPV (1=Open)
        spec.sleep(10)
    return

def check_beam_shutterC(): #arm shutters
    '''If not already open, open 1-ID-C Safety shutter to bring beam into 1-ID-C.
    Keep trying in an infinite loop until the shutter opens.
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Confirm C-Hutch Shutter is open"
        return
    while shutterC_state.get() != 0: #true if shutter is closed (0=Open)
        print "opening C shutter"
        shutterC_openPV.put(1)
        spec.sleep(6) #open the shutter & wait
    return

###########################################################################
# MOTOR RELATED STUFF
###########################################################################                   
def MakeMtrDefaults(fil=None, out=None):
    '''
    Creates an initialization file from a spreadsheet describing
    the 1-ID beamline motor assignments

    :param str fil: input file to read. By default opens file ../1ID/1ID_stages.csv relative to
       the location of the current file.   

    :param str out: output file to write. By default writes file ../1ID/mtrsetup.py.new
       Note that if the default file name is used, the output file must be
       renamed before use to mtrsetup.py
    '''
    import csv

    # DEFINE INPUT & OUTPUT FILES
    if fil is None:
        fil = os.path.join(
            os.path.split(os.path.split(os.path.abspath(__file__))[0])[0],
            '1ID',
            '1ID_stages.csv')
    print('reading file: '+str(fil))
    if out is None:
        out = os.path.join(
            os.path.split(os.path.split(os.path.abspath(__file__))[0])[0],
            '1ID',
           'mtrsetup.py.new')
    print('writing file: '+str(out))
    
    fo = open(out,'w')
    fo.write("# created " + mac.specdate() + "\n")
    fo.write("import sys\n")
    fo.write('sys.path.append("'+os.path.split(os.path.abspath(__file__))[0]+'")\n')
    fo.write("import APSpy.spec as spec\n")
    fo.write("spec.EnableEPICS()\n")
    fo.write("spec.DefineScaler('1id:scaler1',16)\n")
    
    # define column number symbols (N.B. numbering starts with 0)
    crate = 0
    mnum = 1
    msym = 2
    comments = 3
    with open(fil, 'rUb') as fp:
        reader = csv.reader(fp)
        i = 0
        for row in reader:
            i += 1
            if i==1: 
                continue # skip 1st row
            if row[crate].strip() == "": 
                continue

            fo.write("spec.DefineMtr(" +
                     "'" + row[msym].strip() + "', " + 
                     "'" + row[crate].strip() + ':m' + row[mnum].strip() + "', " + 
                     "'" + row[comments].strip() + "') \t # " + str(i) + "\n")
    fp.close()
    fo.close()
    return

def SaveMotorStatus(out=None):
    '''Routine in Development:
    Creates an initialization file for simulation use with the limits for
    every motor PV that is found in the current 1-ID beamline motor assignments.
    import mtrsetup.py or equivalent first. Scans each PV from 1 to the max number defined.

    :param str out: output file to write, writes file motorlimits.dat.new in the same
       directory as this file by default.
       Note that if the default file name is used, the output file must be
       renamed before use to motorlimits.dat
    '''
    if not EPICS:
        print 'This can only be run with EPICS on-line'
        return
        
    print 'saving motor settings ...'
    
    if out is None:
        out = os.path.join(
            os.path.split(os.path.abspath(__file__))[0],
            'motorlimits.dat.new')

    fo = open(out,'w')
    for m in spec.ListMtrs():
        mtrdict = spec.GetMtrInfo(spec.Sym2MtrVal(m))
        mtrstr = str(mtrdict['PV'])
        mtrcomment = str(mtrdict['info'])
        mtrsym = str(mtrdict['symbol'])
        try:
            idx1 = mtrstr.find(': ') + 2
            idx2 = mtrstr.find(':m')
            ioc = mtrstr[idx1:idx2]

            idx1 = mtrstr.find(':m') + 2
            idx2 = mtrstr.find('.:')
            mtrnum = mtrstr[idx1:idx2]
        except Exception:
            break

        PVroot = ioc + ':m' + mtrnum + '.'
        try:
            fo.write(ioc + ',' + mtrnum + ',' + mtrsym + ',' + mtrcomment)
            fo.write(str(ep.caget(PVroot + 'HLM')) + ',')
            fo.write(str(ep.caget(PVroot + 'LLM')) + ',')
            fo.write(str(ep.caget(PVroot + 'SMAX')) + ',')
            fo.write(str(ep.caget(PVroot + 'S')) + ',')
            fo.write(str(ep.caget(PVroot + 'SBAK')) + ',')
            fo.write(str(ep.caget(PVroot + 'SBAS')) + ',')
            fo.write(str(ep.caget(PVroot + 'ACCL')) + ',')
            fo.write(str(ep.caget(PVroot + 'BACC')) + ',')
            fo.write(str(ep.caget(PVroot + 'BDST')) + ',')
            fo.write(str(ep.caget(PVroot + 'FRAC')) + ',')
            fo.write(str(ep.caget(PVroot + 'HVEL')) + ',')
            fo.write(str(ep.caget(PVroot + 'DIR')) + ',')
            fo.write(str(ep.caget(PVroot + 'EGU')) + ',')
            fo.write(str(ep.caget(PVroot + 'SREV')) + ',')
            fo.write(str(ep.caget(PVroot + 'UREV')) + ',')
            fo.write(str(ep.caget(PVroot + 'ERES')) + ',')
            fo.write(str(ep.caget(PVroot + 'RRES')) + ',')
            fo.write(str(ep.caget(PVroot + 'UEIP')) + ',')
            fo.write(str(ep.caget(PVroot + 'URIP')) + ',')
            fo.write(str(ep.caget(PVroot + 'RDBD')) + ',')
            fo.write(str(ep.caget(PVroot + 'RTRY')) + ',')
            fo.write(str(ep.caget(PVroot + 'PREC')) + ',')
            fo.write(str(ep.caget(PVroot + 'NTM')) + ',')
            fo.write(str(ep.caget(PVroot + 'NTMF')) + ',')
            fo.write(str(ep.caget(PVroot + 'MRES')) + ',')
            fo.write('\n')
        except:
            pass
    fo.close()
    return
    
def ImportMotorSymbols():
    '''
    Makes motor symbols in spec into GLOBAL variables.
    I'd be careful with this .... .... 
    '''
    exec( spec.DefineMotorSymbols( spec.mtrDB, make_global=True ) )
    return
    
###########################################################################
# MISC STUFF
########################################################################### 
def beep_dac(beeptime=1.0):
    '''
    Set the 1-ID beeper on for a fixed period, which defaults to 1 second
    uses PV object beeper (defined as 1id:DAC1_8.VAL)
    makes sure that the beeper is actually turned on and off
    throws exception if beeper fails

    :param float beeptime: time to sound the beeper (sec), defaults to 1.0

    '''
    if not (EPICS and spec.UseEPICS()): # in simulation, use the terminal bell
        print('\a\a\a')
        return
    volume = 9 # beeper volume setting
    # part 1: set DAC to ON
    val = 0 # value of DAC (initialized)
    i = 0 # loop counter
    while abs(val-volume)>0.1: # within 0.1 V is OK by me
        if i > 10: # give up after 10 tries
            raise Exception,'Set Beep failed in 10 tries'
        i+=1
        beeper.put(volume, True, 10.) # set on
        val = beeper.get(use_monitor=False) # read value; force rereading of current value
        if val != volume: spec.sleep(0.01) # wait before trying again
        if val is None: val = 9999  # don't crash, even if beeper.get fails on read
        
    # part 2: delay while on
    spec.sleep(beeptime)
    
    # part 3: turn DAC OFF
    i = 0
    while abs(val)>0.1:
        if i > 10: 
            raise Exception,'Clear Beep failed in 10 tries'
        i += 1
        beeper.put(0, True, 10.)   # 0 is beeper off
        spec.sleep(0.001)
        val = beeper.get()
        if val is None: val = 9999  # don't crash, even if beeper.get fails on read
    # all done
    return

def IsLightOn(pvname=None):
    '''
    IsLightOn
    determines whether the overhead light in a hutch is on or off based on photodiode readings. 
    only implemented in the e-hutch.

    :param str pvname: pv name of the photo diode (default = '1ide:D1Ch3_raw.VAL')

    :return bool LightIsOn: 0 for off, 1 for on.
    '''
    if pvname is None:
        # THIS IS THE PHOTODIODE IN THE E-HUTCH
        pvname = '1ide:D1Ch3_raw.VAL'
        DiodeThresholdVoltage = 0.130
    else:
        print 'diode not implemented'
        return
        
    if ep.caget(pvname) > DiodeThresholdVoltage:
        print 'lights are on'
        LightIsOn = 1
    else:
        print 'lights are off'
        LightIsOn = 0

    return LightIsOn

def CheckDiskSpace(pname=None, SpaceThresh=0.70, alertlist=None):
    '''
    CheckDiskSpace
    checks the disk space and alerts the users in the variable 'alertlist'.

    :param str pname: path where the data are saved. this function will check the mount point associated with this path name, 

    :param float SpaceThresh: useage threashold that triggers the alerts (default =  0.70).

    :param str alertlist: list of emails separated by commas that will get the alert message. (eg. 'kimdotcom@mega.com, kimdotcom@megaupload.com')
    '''
    if pname is None:
        print 'path name missing'
        pname = raw_input('enter path name where images are being saved :')

    cmdline = 'df -Phk ' + pname
    restxt = [s.split() for s in os.popen(cmdline).read().splitlines()]
    pctUse = float(restxt[1][4][:-1])/100
    
    if pctUse < SpaceThresh:
        print 'plenty of space in ' + pname
    else:
        print 'space is limited ' + pname

        if alertlist is None:
            print 'no one will be notified'
        else:
            email_program = '/usr/lib/sendmail'
            if os.path.exists(email_program):
                from_addr = 's1id@aps.anl.gov'

                subject = 'disk space warning'
                message = 'ADIVAC had 3000 vacuum tubes. Simon says make some space.'
                mailprogram = "%s -F %s -t %s" % (email_program, from_addr, alertlist)
                mail_command = [mailprogram, 'Subject: ' + subject, message]

                cmd = '''cat << +++ | %s\n+++''' % "\n".join(mail_command)
                os.popen(cmd)    # send the message
                print 'email sent to ' + alertlist
            else:
                print 'no such email program ' + email_program

            print 'program paused'
            UserIput = raw_input('press enter if appropriate action has been taken: ')
    return

def PrintOSC(OSC = None):
    print 'Current OSC entries'
    for item in OSC:
        print item + '\t\t:' + str(OSC[item])
    return

def IsBeamOn(MinSRCurrent=None, CheckMode=None):
    '''
    IsBeamOn
    determines whether the beam is on

    :param float MinSRCurrent: minimum storage ring current

    :param int CheckMode: determines which hutches to check for beam

    :return bool BeamIsOn: 0 for off, 1 for on.
    '''
    if MinSRCurrent is None:
        MinSRCurrent = 10

    if CheckMode is None:
        print '0: Check Hutch A'
        print '1: Check Hutch A & B'
        print '2: Check Hutch A & B & C'
        CheckMode = raw_input('Enter choice: ')
    
    SRCurrent = ep.caget('S:SRcurrentAI')
    BeamActiveHutchA = ep.caget('PA:01ID:A_BEAM_ACTIVE.VAL')
    BeamActiveHutchB = ep.caget('PA:01ID:B_BEAM_ACTIVE.VAL')
    BeamActiveHutchC = ep.caget('PA:01ID:C_BEAM_ACTIVE.VAL')

    if CheckMode == 0:
        if BeamActiveHutchA:
            BeamActive = 1
        else:
            BeamActive = 0
    elif CheckMode == 1:
        if BeamActiveHutchA and BeamActiveHutchB:
            BeamActive = 1
        else:
            BeamActive = 0
    elif CheckMode == 2:
        if BeamActiveHutchA and BeamActiveHutchB and BeamActiveHutchC:
            BeamActive = 1
        else:
            BeamActive = 0

    if (SRCurrent > MinSRCurrent) and BeamActive:
        BeamIsOn = 1
    else:
        BeamIsOn = 0

    return BeamIsOn

def SendAlert(OSC):
    CommandText = 'sendmail ' + OSC['AlertRecipientList'] + ' <' + OSC['AlertPath']
    os.system(CommandText)
    return
    
###########################################################################
# ACROMAG ATTENUATORS
# FROM ./macros_PK/Atten.mac
###########################################################################
def SetAttenuator(OnOffFlag):
    ''' 
    Set the state of acromag attenuators
    
    :param bool array OnOffFlag: [4 x 1] array of on / off flag.
    "0: Attenuator in"
    "1: Attenuator out"
    '''
    pv_root = '1id:9440:1:bo_'
    pv_num = [0, 1, 2, 4]
    ct = 0;
    for ii in OnOffFlag:
        pvname = pv_root + str(pv_num[ct]) + '.VAL'
        ct = ct + 1
        ep.caput(pvname, ii)
    return

def GetAttenuator():
    ''' 
    Get the state of acromag attenuators

    :param bool array OnOffFlag: [4 x 1] array of on / off flag.
    "0: Attenuator in"
    "1: Attenuator out"
    '''
    pv_root = '1id:9440:1:bo_'
    pv_num = [0, 1, 2, 4]
    OnOffFlag = [None, None, None, None]
    ct = 0;
    for ii in OnOffFlag:
        pvname = pv_root + str(pv_num[ct]) + '.VAL'
        OnOffFlag[ct] = int(ep.caget(pvname))
        ct = ct + 1
    return OnOffFlag
    
###########################################################################
# BEAM POSITION MONITOR
########################################################################### 
def BeamPositionMonitor(OpMode = None):       # THIS IS beampos / NEED TO IMPLEMENT HRM VERSION AT SOMEPOINT
    if OpMode is None:
        print 'BeamPositionMonitor operation mode undefined'
        print '0: No action'
        print '1: correction using split ion chamber for C hutch'
        print '2: correction using split ion chamber for E hutch'
        OpMode = raw_input('Enter operation mode: ')
        OpMode = int(OpMode)

    if OpMode == 0:
        return
    elif OpMode == 1:
        print 'not implemented yet'
    elif OpMode == 2:
        print 'not implemented yet'
    else:
        print 'unknown operation mode'
    return
###########################################################################
# ENERGY MONITOR
########################################################################### 
def EnergyMonitor(pfname=None, elename=None):
    ''' 
    Energy monitoring macro 
    Foil configuration needs to be checked to make sure that it is up to date.

    :param str pfname: output file for energy monitoring result. 
    if nonthing is provided, results is written in the default file.

    :param int/str elename: element name or number for energy monitor. 
    if nothing is provided, user gets to choose before the function spins the wheel.
    '''

    # DEFINE INPUT & OUTPUT FILES
    if pfname is None:
        # pfname = os.path.join(
        #     os.path.split(os.path.split(os.path.abspath(__file__))[0])[0],
        #     '1ID',
        #     'EnergyMonitor.data')
        pfname = './exp_setup/energymonitortest.data'
    print('writing energy monitor results to file: '+str(pfname))

    if elename is None:
        print '65: Tb, 51.996 keV'
        print '70: Yb, 61.332 keV'
        print '72: Hf, 65.351 keV'
        print '79: Au, 80.723 keV'
        print '83: Bi, 90.527 keV'
        elename = raw_input('enter appropriate element number to start energy monitor: ')
        elename = int(elename)
    
    # MOVE FOIL IN
    if elename == 65 or elename is 'Tb':
        spec.umv(spec.foilB, 135)
    elif elename == 70 or elename is 'Yb':
        spec.umv(spec.foilB, 90)
    elif  elename == 72 or elename is 'Hf':
        spec.umv(spec.foilB, -135)
    elif  elename == 83 or elename is 'Bi':
        spec.umv(spec.foilB, 45)
    else:
        raise NameError('foil not on the wheel.')
    spec.sleep(0.25)

    # COUNT / CALCULATE
    spec.count_em(5); spec.wait_count()
    print (mac.specdate() + ', ' + 
             str(ep.caget('1id:userCalc9.VAL')) + ', ' +
             str(ep.caget('1id:scaler1.S3')) + ', ' +
             str(ep.caget('1id:scaler1.S5')) + ', ' +
             str(ep.caget('1id:scaler1.T')))
    fo = open(pfname, 'a')
    fo.write(mac.specdate() + ', ' + 
             str(ep.caget('1id:userCalc9.VAL')) + ', ' +
             str(ep.caget('1id:scaler1.S3')) + ', ' +
             str(ep.caget('1id:scaler1.S5')) + ', ' +
             str(ep.caget('1id:scaler1.T')) + '\n')
    fo.close()

    # MOVE FOIL OUT
    spec.umv('foilB', 0)
    return

######################################################################
# WRITING PAR FILES
# write_parfile_general.mac
######################################################################
## TODO
def WriteParfile():
    '''
    write_parfile_fast(detname, imgnr, imgprefix, motname, startpos, endpos)
    '''
    print 'implement please'
    return
#def write_parfile_fast(detname, imgnr, imgprefix, motname, startpos, endpos) '{
#    # For E-hutch NF/FF experiments
#    
#    global OSC
#    global moncnt trcnt Emoncnt Etrcnt
#    global cntticks  # In 10 MHz ticks, we convert it to seconds
#    global timestamp
#    global parfile fastparfile
#    local iframe filenum icnt enddate
#    local icsec
#    local omegapos
#    
#    get_angles
#    sleep(0.1)
#    
#    # One line for each frame
#    on(parfile);offt
#    enddate=date()
#    filenum = imgnr-OSC["nframes"]+1
#    for (iframe=0; iframe<OSC["nframes"]; iframe++) {
#        filenum = imgnr-OSC["nframes"]+1+iframe
#        icnt=OSC["nframes"]-1-iframe # Reverse order
#        omegapos=startpos+(endpos-startpos)/OSC["nframes"]*iframe
#        # PUP_AFRL_Oct13 (per frame)
#        printf("%s %s %8f %8f %8f %8f %8f %8f %8f %8f %s %8f %8f %8f %5f %s %05d %05d %04d %12f %12f %12f %12f %12f %15.8f\n",\
#          enddate, detname, A[DetZ], A[DetX], A[nf_YE], A[mtsXE], S[fedrl], A[mtsYE], 9999, 9999, motname, startpos,\
#          endpos, omegapos, OSC["exposure_time"], imgprefix, filenum, \
#          OSC["first_frame_number"], iframe+1, moncnt[icnt], trcnt[icnt], \
#          Emoncnt[icnt], Etrcnt[icnt], cntticks[icnt]/50e6, timestamp[icnt])          
#          # We should put in the elapsed time based on the scaler trigger and 10MHz clock
#          # We may put here the current calculated omega position of a frame
#    }       
#    ont;off(parfile)
#    
#    # One line for each scan
#    on(fastparfile);offt
#    icsec=S[sec]
#    if (icsec==0) icsec=-1.0

#    # PUP_AFRL_Oct13_Jul13 (per scan)
#    local displenc loadcell stress
#    #displenc=epics_get("1ide:Fed:s1:probe_2")  # Federal Encoder on the load frame
#    loadcell=epics_get("1ide:D1Ch7_raw.VAL") # Load cell voltage in Volts (OWIS)
#    stress=epics_get("1ide:D1Ch7_calc.VAL") # Load in N on the load cell
#    tensionmot=epics_get("1idc:m33.RBV") # tension motor position
#    printf("%s %s %8f %8f %8f %8f %8f %8f %8f %s %5g %5g %4d %5g %s %05d %05d %12f %12f %12f %12f %12f %12f %12f %8f %8f %8f %8f %15.8f %12f %12f %8f %8f\n",\
#      enddate, detname, A[imgXE], A[imgZE], A[imgYE], A[mtsXE], A[mtsYE], 9999, 9999, motname,\
#      startpos, endpos, OSC["nframes"], OSC["exposure_time"], imgprefix, OSC["first_frame_number"], imgnr,\
#      S[ic1e]/icsec, S[ic2e]/icsec, S[ic3e]/icsec, S[ic4e]/icsec, S[ic5e]/icsec, S[ic6e]/icsec, \
#      S[fedrl], icsec, displenc, loadcell, stress, tensionmot, S[bpEus], S[bpEds], A[foil], S[fotr], S[bposC])
#    ont;off(fastparfile)
#  
#}'
