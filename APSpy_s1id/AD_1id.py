###########################################################################
# HYDRA
# FROM ./macros_PK/hydra_2013Aug11/use_hydra.mac 
###########################################################################
import os as os

import epics as ep

import AD as AD
import spec as spec

import macros_1id as mac1id

####################
## CHECK THESE
#def ccdhook_adge '
#    ccdhook_adcommon $*
#    def ccdtrig \'_ccdtrig_ad\'
#
#def ccdhook_adcommon '
#    CCDPV="$1" ;  ADFILEPV="$2"; ADROIPV="$3";
#    if($#==4) {
#      ADSTATPV="$4"; CCD_MONITOR_ROI= ADROIPV;
#    }else {
#      CCD_MONITOR_ROI = ADROIPV "0:"
#    }
# 
# /home/beams/SPECADM/1id_macros/HEDM/ccdscan/ccd_ad.mac
#def ccdsetup_ad '{
#   CCDPV=getval("The EPICS prefix of the detector:",CCDPV);
#   ADFILEPV=getval("The EPICS prefix of the detector file I/O :",ADFILEPV);
#   ADROIPV=getval("The EPICS prefix of the ROI plugin:",ADROIPV);
#   ADSTATPV=getval("The EPICS prefix of the ROI plugin:",ADSTATPV);
#   CCD_DATA_DIR = getval("The directory where the Image Server saves the data:",CCD_DATA_DIR)
#   if(is_winpath(CCD_DATA_DIR) ) DIR_SLASH ="\\"
#   else DIR_SLASH = "/"
#   if(substr(CCD_DATA_DIR,length(CCD_DATA_DIR)) != DIR_SLASH  ) {
#        CCD_DATA_DIR = CCD_DATA_DIR DIR_SLASH
#      
#   } 
#   if(yesno("Do yo have the ccd data directory mounted on the local computer?",1) ){
#      MNT_MAP["server"]= CCD_DATA_DIR
#      smb_map
#   }
#   if(yesno("\nSetup a pseudo counter to monitor some ROIs from spec?",1)) {
#      CCD_CNTR=getval("The pseudo counter name:",CCD_CNTR);
#      if(chk_ccdc()) {
#        if(chk_ccdc()) {
#        if(ADSTATPV) {
#            setccdc_ad
#        }else {
#            setccdc_ad 0
#        } 
#         
#      } else {
#         printf("%c%sPlease configure a pseudo counter \"%s\"(None type) with config%c%s.\n",27,"[31m",CCD_CNTR,27,"[0m")
#      }
#     printf("\nUse setccdc_ad {ROI#} (i.e. setccdc_ad 0)  to change monitored ROI\n")
#   }
#
#}'

# /home/beams/SPECADM/1id_macros/HEDM/ccdscan/ccd_ad.mac
#def ccdset_roi_ad '{
# local vstart,hstart,vlength,hlength
#      if($#==5) {
#         vstart=$2
#         vlength=$3
#         hstart=$4
#         hlength=$5
#       }else {
#        p "usage: ccdset_roi ROIPV vstart vlength hstart hlength"
#        exit
#       }
#       epics_put(sprintf("%sUse",$1),1)
#       epics_put(sprintf("%sMinY",$1),vstart)
#       epics_put(sprintf("%sSizeY",$1),vlength)
#       epics_put(sprintf("%sMinX",$1),hstart)
#       epics_put(sprintf("%sSizeX",$1),hlength)
#       sleep(0.5)
#}'

# /home/beams/SPECADM/1id_macros/HEDM/ccdscan/ccd_ad.mac
#def ccdget_ROIdim_ad(ROIPV) '{
#   local array d[4]
#   d[0]=epics_get(sprintf("%sMinY",ROIPV))
#   d[1]=epics_get(sprintf("%sSizeY",ROIPV))
#   d[2]=epics_get(sprintf("%sMinX",ROIPV))
#   d[3]=epics_get(sprintf("%sSizeX",ROIPV))
#   return d
#}'

# /home/beams/SPECADM/1id_macros/HEDM/ccdscan/ccd_ad.mac
#def ccdtrig_ad '{
#    if(epics_get(sprintf("%sImageMode",CCDPV)) != "Multiple") {
#             epics_put(sprintf("%sImageMode",CCDPV),"Multiple")
#    }
#    _ccdtrig_ad $*
#}'

# /home/beams/SPECADM/1id_macros/HEDM/ccdscan/ccd_ad.mac
#def ccd_addcolumn_ad '{
#    if($# !=1) {
#       print "Usage: ccd_addcolum stat_pv"
#       exit
#    }
#    local name cmd _pv
#    
#    epics_put(sprintf("%sEnableCallbacks","$1"),1)
#    epics_put(sprintf("%sBlockingCallbacks","$1"),1)
#    _pv= sprintf("%sComputeStatistics","$1")
#    epics_put(_pv,1);
#    name =epics_get(sprintf("%sNDArrayPort_RBV","$1"))
#    _pv = sprintf("%sTotal_RBV","$1");
#    cmd = sprintf("epics_get(\"%s\")",_pv);
#    u_column_add(name,"%.8g",cmd,"ccdroi");
#    printf("%s will be saved to the data file\n",name);
#    u_column_show;
#}'

# /home/beams/SPECADM/1id_macros/HEDM/ccdscan/ccd_ad.mac
#def ccdscan_fname_ad() '{
#         local foo2
#	 if(CCD_REPEATS==1) {
#              ccdset_filetemplate_ad( sprintf("%s%s","%s%s.",CCD_FILE_EXT))
#         }else{
#              ccdset_filetemplate_ad( sprintf("%s%s","%s%s_%3.3d.",CCD_FILE_EXT))
#	 }
#	 foo2 = sprintf("%s_s%d_%d",get_datafilename(),SCAN_N,NPTS)
#         return(foo2)
#}'

# /home/beams/SPECADM/1id_macros/HEDM/ccdscan/ccd_ad.mac
#def ccdget_ccdc_ad(roi) '{
#    if(ADSTATPV && CCD_MONITOR_ROI!="None")     return(epics_get(sprintf("%sTotal_RBV",ADSTATPV)))
#    else return(0)
#}'

def Trigger(hydra, expTime = None, numFrames = None):   # _adtrig_xtime_hydra & _ccdtrig_ad
    ''' 

    Trigger macro
    sets the exposure time for the hydra array and triggers image acquisition

    :param list hydra: list of detectors
    
    :param float expTime: exposure time (seconds)

    :param int numFrames: number of exposures
    '''

    if expTime == None:
        print 'Exposure time missing.'
        expTime = raw_input('Enter exposure time in seconds: ')
        expTime = float(expTime)

    if numFrames == None:
        print 'Number of frames missing.'
        print 'Setting number of exposures to 1'
        numFrames = int(1)

    AD.AD_done(hydra, wait=True)                # _adwait_hydra
    AD.AD_set(hydra, 'acquire_time', expTime)   # ccdset_expTime_hydra
    AD.AD_set(hydra, 'frames', numFrames)
    # AD.AD_set(hydra, 'acquire', 'Acquire')    # epics_put(sprintf("GE%d:cam1:Acquire",hydra[ihydra]),"Acquire");
    return

def Abort(hydra):  # hydra_abort & ccdabort_ad & detabort_ad_ge & allGE_abort & ccdabort_ad
    ''' 

    Abort macro
    aborts hydra array data collection and return state to 'Done' / 'Idle'

    :param list hydra: list of detectors
    '''

    AD.AD_set(hydra, 'acquire', 0)

    ep.caput('1iddth1:DTH:resetLogicBO', 1, wait=True)
    print 'FPGA trigger module is reset.'
    return

def HydraInitialize(OSC):          # use_ge_hydra & ccdset_Initialize
    '''
    use_ge_hydra & ccdset_Initialize
    '''
    
    OSC['DetDelay'] = 0.5          # For software mode
    OSC['CushionTime'] = 0.0
    return OSC

def DTHInitialize(hydra, TrigMode=None):      # hydra_Initialize
    ''' 
    HydraInitialize macro
    Initializes detector trigger hydra (DTH)

    :param list hydra: list of detectors
    '''
    print 'Resetting the FPGA'
    ep.caput('dth1:DTH:resetLogicBO', 1, wait=True)

    # TRIGGER DEFAULTS IN DETECTOR TRIGGER HYDRA
    ep.caput('dth1:DTH:triggerDelayLO.VAL', 0, wait=True)
    ep.caput('dth1:DTH:triggerDelayStepLO.VAL', 1, wait=True)
    ep.caput('dth1:DTH:triggerWidthLO.VAL', 0, wait=True)
    ep.caput('dth1:DTH:triggerWidthStepLO.VAL', 1, wait=True)

    if TrigMode is None:
        print 'trigger mode unspecified'
        print '0: MultiDet SW'
        print '1: MultiDet Edge'
        print '2: MultiDet Pulse'
        print '3: Test PV Trig'
        TrigMode = raw_input('enter appropriate element number to start energy monitor: ')
        TrigMode = int(TrigMode)

    if TrigMode == 0:    
        ep.caput('dth1:DTH:ModeMBBO', '0', wait=True) # MultiDet SW: Software controlled trigger
    elif TrigMode == 1:
        ep.caput('dth1:DTH:ModeMBBO', '1', wait=True) # MultiDet Edge : HW signal controlled trigger with TTL rising edge (min pulse size is 2 usec)
    elif TrigMode == 2:
        ep.caput('dth1:DTH:ModeMBBO', '2', wait=True) # MultiDet Pulse : HW signal controlled trigger while TTL pulse is high (min pulse size is 4 usec)
    elif TrigMode == 3:
        ep.caput('dth1:DTH:ModeMBBO', '3', wait=True) # Test PV Trig : CUSTOM TRIGGER / CHECK
    
    # 1. SET ALL GE PANELS TO UNUSED STATE
    detList = [AD.GE1, AD.GE2, AD.GE3, AD.GE4]
    for det in detList:
        dth_pvname = 'dth1:DTH:Ge' + det.symbol[-1] + 'UsedBO'
        # 0 : USED
        # 1 : UNUSED
        ep.caput(dth_pvname, 1, wait=True)

    # 2. SET CURRENT HYDRA PANELS TO USED STATE
    for det in hydra:
        if det is not None:
            if det.detectortype is 'GE':
                dth_pvname = 'dth1:DTH:Ge' + det.symbol[-1] + 'UsedBO'
                # 0 : USED
                # 1 : UNUSED
                ep.caput(dth_pvname, 0, wait=True)
            else:
                print det.symbol + ' does not need DTH initialization'

    AD.AD_set(hydra, 'buffer1', 250)
    return

########################################
# SET MACROS
########################################
# AD.AD_set(hydra, 'acquire_time', ExposureTime) = ccdset_expTime_hydra, set_hydra_expTime, ccdset_expTime_allGE, set_allGE_expTime, ccdset_time_ad, SetExposureTime(hydra, expTime = None)        
# AD.AD_set(hydra, 'filename', 'testXX') = SetFileName & set_hydra_FileName & set_allGE_FileName & ccdset_filename_ad
# AD.AD_set(hydra, 'filepath', 'W:\balogh_march14') = SetPathName(hydra, pname=None), set_hydra_FilePath & set_allGE_FilePath & ccdset_filepath_ad
# AD.AD_set(hydra, 'filenumber, '1300) = SetFileNumber(hydra, fnum=None), set_hydra_FileNumber & set_allGE_FileNumber & ccdset_time_ad & ccdset_seqnum_ad
# AD.AD_set(hydra, 'frames', 250) = SetNumberOfFrames(hydra, numFrames=None), set_Hydra_NumberOfImagesPerDetTrig & set_allGE_NumberOfImagesPerDetTrig
# AD.AD_set(hydra, 'buffer1', 250) = SetBufferSize(hydra, buffersize=250), set_allGE_BufferSize, set_hydra_BufferSize

def SetFileNameFormat(hydra, fnamefmt=None, AddExtension=True): # set_hydra_FileNameFormat & set_allGE_FileNameFormat & ccdset_filetemplate_ad
    ''' 
    SetFileNameFormat macro
    sets file name format for the hydra array

    :param list hydra: list of detectors

    :param str fnamefmt: file name format string

    :param bool AddExtension: adds extension to the file name format (ie. *.ge2, *.ge3 ...)
    '''

    if fnamefmt == None:
        print 'File name format missing.'
        fnamefmt = raw_input('Enter file name format: ')
        
    for det in hydra:
        if det is not None:
            if AddExtension is True:
                AD.AD_set(det, 'filetemplate', fnamefmt + '.' + det.symbol.lower())
            else:
                AD.AD_set(det, 'filetemplate', fnamefmt)

    GetFileNameFormat(hydra)
    return

def SetAutoStore(hydra, YesOrNo=None):  # set_hydra_AutoStoreYes, set_hydra_AutoStoreNo, set_allGE_AutoStoreYes, set_allGE_AutoStoreNo, ccdsave_ad, ccdset_AutoSaveNo
    ''' 
    SetAutoStore macro
    sets auto store option for the hydra array

    :param list hydra: list of detectors

    :param bool YesOrNo: 0: Autosave No, 1: Autosave Yes
    '''

    if YesOrNo == None:
        print 'Auto store flag missing.'
        YesOrNo = raw_input('Enter auto store flag (0 = No, 1 = Yes): ')
        YesOrNo = bool(YesOrNo)
        
    for det in hydra:
        if det.detectortype is 'GE':
            AD.AD_set(det, 'autostore', YesOrNo)
        else:
            AD.AD_set(det, 'autosave', YesOrNo)
            
    if YesOrNo:
        print 'Hydra is in SAVE mode'
    else:
        print 'Hydra is NOT in SAVE mode'        
    return

def SetWindowAndLevel(hydra, winlevel=None, levelval=None):    # set_hydra_WindowAndLevel & set_allGE_WindowAndLevel
    ''' 
    SetWindowAndLevel macro
    sets parameters for the hydra array visualization

    :param list hydra: list of detectors

    :param int winlevel: window level

    :param int levelval: level value
    '''
    
    if winlevel is None:
        print 'Window level missing.'
        winlevel = raw_input('Enter window level: ')
        winlevel = int(winlevel)
        
    if levelval is None:
        print 'Level value missing.'
        levelval = raw_input('Enter level value: ')
        levelval = int(levelval)

    for det in hydra:
        if det.detectortype is 'GE':
            AD.AD_set(det, 'levelvalue', levelval)
            AD.AD_set(det, 'windowlevel', winlevel)
    return

def SetAcquisitionType(hydra, AcqType=None):
    ''' 
    SetAcquisitionType macro
    sets image acquisition mode for the hydra array

    :param list hydra: list of detectors

    :param int AcqType: image acquisition type
    '''
    
    if AcqType is None:
        print 'hydra acquisition type undefined'
        print '0: Angio'
        print '1: RAD'                          # set_hydra_RadMode & set_allGE_RadMode
        print '2: MultiDet SW'                  # set_hydra_MultiDetSW & set_allGE_MultiDetSW
        print '3: MultiDet Edge'                # set_hydra_MultiDetEdge & set_allGE_MultiDetEdge
        print '4: MultiDet Pulse'               # set_hydra_MultiDetPulse & set_allGE_MultiDetPulse
        print '5: MultiDet Custom'
        AcqType = raw_input('Enter hydra acquisition type: ')
        AcqType = int(AcqType)
    
    for det in hydra:
        if det.detectortype is 'GE':
            AD.AD_set(det, 'trigger_mode', AcqType)
            if (AcqType == 1) or (AcqType == 2):            # RAD & MultiDet SW
                ep.caput('dth1:DTH:ModeMBBO', 0, wait=True) # Software controlled trigger
            elif AcqType == 3:
                ep.caput('dth1:DTH:ModeMBBO', 1, wait=True) # HW signal controlled trigger with TTL rising edge (min pulse size is 2 usec)
            elif AcqType == 4:
                ep.caput('dth1:DTH:ModeMBBO', 2, wait=True) # HW signal controlled trigger with TTL rising edge (min pulse size is 2 usec)
            elif AcqType == 5:
                ep.caput('dth1:DTH:ModeMBBO', 3, wait=True) # HW signal controlled trigger with TTL rising edge (min pulse size is 2 usec)
    return

def GetAutoStore(hydra):   # get_hydra_AutoStore & ccdget_AutoSave
    ''' 
    GetAutoStore macro
    gets auto store status in a hydra array

    :param list hydra: list of detectors
    ''' 
    AutoStoreList = []
    for det in hydra:
        if det.detectortype is 'GE':
            AutoStoreState = AD.AD_get(det, 'autostore')
            if AutoStoreState:
                print det.symbol + ' is autosaving'
            else:
                print det.symbol + ' is not autosaving'   
        else:
            AutoStoreState = AD.AD_get(det, 'autosave')

        AutoStoreList.append(AutoStoreState)
    return AutoStoreList

########################################
# GET MACROS
########################################

########################################
# AD.AD_get(hydra, 'filenumber') = def GetFileNumber(hydra):   # get_hydra_FileNumber & get_hydra_AllFileNumbers & get_allGE_AllFileNumbers & ccdget_SeqNumber_ad & detget_seqNumber_ad
# AD.AD_get(hydra, 'frames') = def GetBufferSize(hydra):   # get_allGE_AllBufferSize
# AD.AD_get(hydra, 'filename') = def GetFileName(hydra):        # get_hydra_FileName & get_hydra_AllFileNames & get_allGE_AllFileNames & ccdget_filename_ad & adget_filename & detget_imgprefix_ad
# AD.AD_get(hydra, 'filepath') = def GetPathName(hydra):        # get_hydra_FilePath & get_hydra_AllFilePaths & get_allGE_AllFilePaths & ccdget_filepath_ad
# AD.AD_get(hydra, 'filetemplate') = get_hydra_AllFileNameFormats & get_allGE_AllFileNameFormats
# AD.AD_get(hydra, 'acquire_time') = def GetExposureTime(hydra) # ccdget_expTime_ad
# AD.AD_get(hydra, 'lastfilename') = GetLastFileName(hydra): # ccdget_fullfilename_ad from /home/beams/SPECADM/1id_macros/HEDM/ccdscan/ccd_ad.mac

def GetDetectorType(hydra):
    '''
    GetDetType
    '''
    DetectorTypeList = []
    for det in hydra:
        DetectorTypeList.append(det.detectortype)
                    
    return DetectorTypeList

######################################################################
# CHECK FILE SIZES
######################################################################
def CheckFileOutput(OSC):
    LastFileNameHydra = AD.AD_get(OSC['Detectors'], 'lastfilename')
    for ii in range(0, len(LastFileNameHydra)):
        LastFileNameHydra[ii] = LastFileNameHydra[ii].replace("'\'", '/')
        if LastFileNameHydra[ii][0] is 'W':
            LastFileNameHydra[ii] = LastFileNameHydra[ii].replace('W:', '/home/beams/S1IDUSER/mnt/WAXS')
        elif LastFileNameHydra[ii][0] is 'V':
            LastFileNameHydra[ii] = LastFileNameHydra[ii].replace('V:', '/home/beams/S1IDUSER/mnt/HEDM')
        
        CalculatedSize = ( OSC['NumFrames'] * 2048 * 2048 * 2 + 8192)
        statinfo = os.stat(LastFileNameHydra[ii])
        print 'Last file for ' + OSC['Detectors'][ii].controlprefix + ' : ' + LastFileNameHydra[ii]
        print 'File size calculated :' + str(CalculatedSize)
        print 'File size actual     :' + str(statinfo.st_size)
        
        if statinfo.st_size != CalculatedSize:
            OSC['RepeatScan'] = 1
            break
        else:
            OSC['RepeatScan'] = 0
            
    return OSC
            
####################
### THESE MAY BELONG HERE

#def SetupDetPulseToAD(OSC):        # setup_DetPulseToAD
#    '''
#    setup_DetPulseToAD
#    Sets up the DetPulseToDet userStringCalc for pressing the "Start" button on AD
#    '''
#    # Setting up the triggering tool
#    pvname = OSC['DetPulseToADPV'] + '.DESC'
#    pvvalue = 'DetPulseToAD'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.DESC", DetPulseToADPV), "DetPulseToAD"); # Mode

#    pvname = OSC['DetPulseToADPV'] + '.SCAN'
#    pvvalue = 'Passive'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.SCAN", DetPulseToADPV), "Passive"); # Mode

#    pvname = OSC['DetPulseToADPV'] + '.A'
#    pvvalue = 0
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.A", DetPulseToADPV), 0); # Initial value

#    pvname = OSC['DetPulseToADPV'] + '.INPA'
#    pvvalue = OSC['DetPulsePV'] + '.VAL CP NMS'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPA", DetPulseToADPV), sprintf("%s.VAL CP NMS", DetPulsePV)); # Input PV with Det_pulses
#    pvname = OSC['DetPulseToADPV'] + '.INPB'
#    pvvalue = ''
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPB", DetPulseToADPV), ""); # clear

#    pvname = OSC['DetPulseToADPV'] + '.B'
#    pvvalue = 0
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.B", DetPulseToADPV), 0); # Initial value, Disable for disarming

#    pvname = OSC['DetPulseToADPV'] + '.C'
#    pvvalue = 0
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.C", DetPulseToADPV), 0); # Initial value, Disable for DetPulseCounter
#   
#    pvname = OSC['DetPulseToADPV'] + '.AA'
#    pvvalue = 'Acquire'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.AA", DetPulseToADPV), "Acquire"); # Initial value

#    pvname = OSC['DetPulseToADPV'] + '.BB'
#    pvvalue = 'NOP'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.BB", DetPulseToADPV), "NOP"); # Initial value

#    pvname = OSC['DetPulseToADPV'] + '.CALC'
#    pvvalue = '(A&B)&C'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.CALC", DetPulseToADPV), "(A&B)&C"); # Is the triggering is Enabled?

#    pvname = OSC['DetPulseToADPV'] + '.OCAL'
#    pvvalue = 'AA'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.OCAL", DetPulseToADPV), "AA"); # Output string

#    pvname = OSC['DetPulseToADPV'] + '.OOPT'
#    pvvalue = 'Transition To Non-zero'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.OOPT", DetPulseToADPV), "Transition To Non-zero");

#    pvname = OSC['DetPulseToADPV'] + '.DOPT'
#    pvvalue = '"Use OCAL'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.DOPT", DetPulseToADPV), "Use OCAL");

#    pvname = OSC['DetPulseToADPV'] + '.OUT'
#    pvvalue = OSC['CcdPV'] + 'Acquire PP NMS'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.OUT", DetPulseToADPV), sprintf("%sAcquire PP NMS", CCDPV));

#    pvname = OSC['DetPulseToADPV'] + '.WAIT'
#    pvvalue = 'NoWait'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.WAIT", DetPulseToADPV), "NoWait");
#    return
#    
#def SetupFakeDetPulse(OSC):             # setup_FakeGATEandDetPulse
#    '''
#    setup_FakeGATEandDetPulse (DET PART)
#    For E-hutch
#    Setting up the fake det pulses

#    '''
#    
#    DetPulsePV = OSC['DetPulsePV']
#    
#    pvname = DetPulsePV + '.DESC'
#    pvvalue = 'DetPulses in'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.DESC", DetPulsePV), "DetPulses in"); 
#    
#    pvname = DetPulsePV + '.DESC'
#    pvvalue = 'Passive'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.SCAN", DetPulsePV), "Passive"); # Mode
#    
#    pvname = DetPulsePV + '.A'
#    pvvalue = 0
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.A", DetPulsePV), 0); # Initial value This receives interrupt from SoftGlue Field I/O 1
#    
#    pvname = DetPulsePV + '.B'
#    pvvalue = 0
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.B", DetPulsePV), 0); # Initial value
#    
#    pvname = DetPulsePV + '.INPA'
#    pvvalue = ''
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPA", DetPulsePV), ""); # Input PV with Det_pulses
#    
#    pvname = DetPulsePV + '.INPB'
#    pvvalue = ''
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPB", DetPulsePV), ""); # Input PV with Det_pulses
#    
#    pvname = DetPulsePV + '.OOPT'
#    pvvalue = 'Every Time'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.OOPT", DetPulsePV), "Every Time");
#    
#    pvname = DetPulsePV + '.DOPT'
#    pvvalue = 'Use CALC'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.DOPT", DetPulsePV), "Use CALC");
#    
#    pvname = DetPulsePV + '.CALC'
#    pvvalue = 'A'
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.CALC", DetPulsePV), "A"); 
#    
#    pvname = DetPulsePV + '.OUT'
#    pvvalue = ''
#    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.OUT", DetPulsePV), "");
#    return

#def ArmDetector(OSC):
#    if OSC['DetectorArmMode'] is None:
#        print 'Detector arm mode missing'
#        print '0 : arm_detector_HWtriggerRetiga_PosDriven_prrot'
#        print '1 : arm_detector_HWtriggerRetiga_PosDriven_preci'
#        print '2 : arm_detector_HWtriggerRetiga_aeroPSOFly'
#        print '6 : arm_detector_HWtriggerRetiga_aerohexFly'
#        print '7 : arm_detector_HWtriggerRetiga'
#        print '12: arm_detector_HWtriggerGE'
#        print '3 : arm_detector_HWtriggerGE_PosDriven'
#        print '4 : arm_detector_HWtriggerGE_FlyScan_Aero_hydra'
#        print '5 : arm_detector_HWtriggerGE_prrot_hydra'
#        print '8 : arm_detector_HWtriggerGE_prrot_hydra_Renishaw'
#        print '11: arm_detector_HWtriggerRetiga_PosDriven_prrot_Renishaw'
#        print '9 : arm_detector_SWRetiga'
#        print '10: arm_detector_SWRetiga_PosDriven'
#        OSC['DetectorArmMode'] = raw_input('enter detector arm mode: ')
#        OSC['DetectorArmMode'] = int(OSC['DetectorArmMode'])
#    
#    if OSC['DetectorArmMode'] == 0:    # arm_detector_HWtriggerRetiga_PosDriven_prrot
#        ## CHECK THIS
#        # Put the detector to NoSave
#        # savemode=ccdget_AutoSave
#        # ccdset_AutoSaveNo
#        SaveMode = AD1id.GetAutoStore(OSC['DetList'])
#        AD1id.SetAutoStore(OSC['DetList'], YesOrNo=0)
#    
#        SoftMtrRes = ep.caget('1ide:userTran2.D')   # softmotres
#        StepConversion = SoftMtrRes/0.000264706     # Ratio of the softmotor resolution and the hard motor resolution

#        pvname = OSC['FpgaPV'] + 'DnCntr-1_PRESET'
#        pvvalue = int( OSC['ExpTime'] * OSC['Speed'] / StepConversion / OSC['DecodingRate'])
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sDnCntr-1_PRESET", FPGAPV), int(OSC["exposure_time"]*OSC["speed"]/StepConversion/DecodingRate), CB_TIME)
#        
#        pvname = OSC['FpgaPV'] + 'DnCntr-2_PRESET'
#        pvvalue = OSC['GapTime'] * OSC['Speed'] / StepConversion / OSC['DecodingRate'] + OSC['GapAdjustmentTicks']
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sDnCntr-2_PRESET", FPGAPV), int(OSC["gap_time"]*OSC["speed"]/StepConversion/DecodingRate + GapAdjustmentTicks), CB_TIME) # Gap Time, ext. TTL
#        
#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(1), CB_TIME) # Arms pulses signal. Just for sure, the soft motor does it anyway.
#        
#        pvname = OSC['FpgaPV'] + 'BUFFER-2_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait = True)      # epics_put(sprintf("%sBUFFER-2_IN_Signal.PROC", FPGAPV), int(1), CB_TIME) # Workaround for the unwanted signal before the GATE (When this is reset there is a short pulse on the det_pulses line, if we do it here, then when teh softmotor do it automatically there is no more signal)

#        ### CHECK THIS
#        # detector related settings
#        # ccdset_expNum_ad OSC["nframes"] # This has no effect in Continuous mode and HWtrigger moder
#        # ccdset_time OSC["exposure_time"] # per frame, This has no effect in PulseHi/StrobeHi mode, but in EdgeHi
#        
#        pvname = OSC['CcdPV'] + 'ImageMode'
#        pvvalue = 'Single'
#        ep.caput(pvname, pvvalue, wait=True)   # epics_put(sprintf("%sImageMode",CCDPV),"Single", CB_TIME)
#        
#        pvname = OSC['CcdPV'] + 'TriggerMode'
#        pvvalue = 'StrobeHi'
#        ep.caput(pvname, pvvalue, wait=True)   # epics_put(sprintf("%sTriggerMode",CCDPV),"StrobeHi", CB_TIME) # external TTL  This mode is good for the 4000DC for overlapped HWtrigger
#        
#        ## CHECK THIS
#        # For HW triggering we need to Initialize the Retiga but do not need to Acquire
#        # ccdset_Initialize
#        
#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 0
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.B", DetPulseToADPV), 0, CB_TIME) # Disabling the DetPulseToAD signals

#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", FrameCounterPV), 1, CB_TIME); # Enabling the counter, if switched to enable immediately counts down by one
#        
#        # When this gets enabled, it will have immediately an element (junk) in the array!
#        pvname = OSC['TimeStampArrayPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", TimeStampArrayPV), 1, CB_TIME) # Enabling the TimeStampArray

#        # FPGA interrupts
#        # userCalc activation
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None", CB_TIME) # no GATEToDetector signal in case of external TTL
#        
#        spec.sleep(OSC['EpicsDelay'])

#        ## CHECK THIS
#        # Put the detector to the original Save mode
#        # if savemode:
#        #     ccdset_AutoSaveYes 
#        # else:
#        #     ccdset_AutoSaveNo
#        
#    elif OSC['DetectorArmMode'] == 1:    # arm_detector_HWtriggerRetiga_PosDriven_preci
#        ## CHECK THIS
#        # Put the detector to NoSave
#        # savemode=ccdget_AutoSave
#        # ccdset_AutoSaveNo
#        SaveMode = AD1id.GetAutoStore(OSC['DetList'])
#        AD1id.SetAutoStore(OSC['DetList'], YesOrNo=0)

#        # Position driven Det_pulses
#        pvname = OSC['FpgaPV'] + 'DnCntr-1_PRESET'
#        pvvalue = int( OSC['ExpTime'] * OSC['Speed'] / OSC['DecodingRate'] ) 
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDnCntr-1_PRESET", FPGAPV), int(OSC["exposure_time"]*OSC["speed"]/DecodingRate), CB_TIME) # Exp Time, ext. TTL

#        pvname = OSC['FpgaPV'] + 'DnCntr-2_PRESET'
#        pvvalue = int(OSC['GapTime'] * OSC['Speed'] / OSC['DecodingRate'] + GapAdjustmentTicks)
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDnCntr-2_PRESET", FPGAPV), int(OSC["gap_time"]*OSC["speed"]/DecodingRate + GapAdjustmentTicks), CB_TIME) # Gap Time, ext. TTL
#                
#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(1), CB_TIME) #

#        print 'Workaround FPGA position driven StrobeHi'
#        pvname = OSC['FpgaPV'] + 'BUFFER-2_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-2_IN_Signal.PROC", FPGAPV), int(1), CB_TIME) # Workaround for the unwanted signal before the GATE

#        ## CHECK THIS
#        # detector related settings
#        # ccdset_expNum_ad OSC["nframes"] # This has no effect in Continuous mode
#        # ccdset_time OSC["exposure_time"] # per frame, This has no effect in PulseHi/StrobeHi mode, but in EdgeHi
#        
#        pvname = OSC['CcdPV'] + 'ImageMode'
#        pvvalue = 'Single'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sImageMode",CCDPV),"Single", CB_TIME)
#        
#        pvname = OSC['CcdPV'] + 'TriggerMode'
#        pvvalue = 'StrobeHi'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sTriggerMode",CCDPV),"StrobeHi", CB_TIME) # external TTL  This mode is good for the 4000DC for overlapped HWtrigger

#        ## CHECK THIS
#        # For HW triggering we need to Initialize the Retiga but do not need to Acquire
#        # ccdset_Initialize
#        
#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 0
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.B", DetPulseToADPV), 0, CB_TIME) # Disabling the DetPulseToAD signals

#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", FrameCounterPV), 1, CB_TIME); # Enabling the counter, if switched to enable immediately counts down by one

#        # When this gets enabled, it will have immediately an element (junk) in the array!
#        pvname = OSC['TimeStampArrayPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", TimeStampArrayPV), 1, CB_TIME) # Enabling the TimeStampArray

#        # FPGA interrupts
#        # userCalc activation
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None", CB_TIME) # no GATEToDetector signal in case of external TTL
#        
#        spec.sleep(OSC['EpicsDelay'])

#        ## CHECK THIS
#        # Put the detector to the original Save mode
#        # if savemode:
#        #     ccdset_AutoSaveYes
#        # else:
#        #     ccdset_AutoSaveNo
#        
#    elif OSC['DetectorArmMode'] == 2:      # arm_detector_HWtriggerRetiga_aeroPSOFly
#        ## CHECK THIS
#        # Put the detector to NoSave
#        # savemode=ccdget_AutoSave
#        # ccdset_AutoSaveNo
#        SaveMode = AD1id.GetAutoStore(OSC['DetList'])
#        AD1id.SetAutoStore(OSC['DetList'], YesOrNo=0)

#        ## CHECK THIS
#        # detector related settings
#        # ccdset_expNum_ad OSC["nframes"] # This has no effect in Continuous mode
#        # ccdset_time OSC["exposure_time"] # per frame, This has no effect in PulseHi/StrobeHi mode, but in EdgeHi

#        pvname = OSC['CcdPV'] + 'ImageMode'
#        pvvalue = 'Single'
#        ep.caget(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sImageMode",CCDPV),"Single", CB_TIME)
#        
#        pvname = OSC['CcdPV'] + 'TriggerMode'
#        pvvalue = 'StrobeHi'
#        ep.caget(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sTriggerMode",CCDPV),"StrobeHi", CB_TIME) # external TTL  This mode is good for the 4000DC for overlapped HWtrigger
#        
#        ## CHECK THIS
#        # For HW triggering we need to Initialize the Retiga but do not need to Acquire
#        # ccdset_Initialize
#        
#        # FrameCounter on FPGA should be reset: clearNFExpCnt
#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = int(OSC['DelayTime'] * 8e6)
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(OSC["delay_time"]*8e6)) # Delay Time, ext. TTL

#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 0
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.B", DetPulseToADPV), 0, CB_TIME) # Disabling the DetPulseToAD signals

#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", FrameCounterPV), 1, CB_TIME); # Enabling the counter, if switched to enable immediately counts down by one

#        # When this gets enabled, it will have immediately an element (junk) in the array!
#        pvname = OSC['TimeStampArrayPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", TimeStampArrayPV), 1, CB_TIME) # Enabling the TimeStampArray

#        spec.sleep(OSC['EpicsDelay'])

#        ## CHECK THIS
#        # Put the detector to the original Save mode
#        # if (savemode) ccdset_AutoSaveYes else ccdset_AutoSaveNo
#        # if savemode:
#        #     ccdset_AutoSaveYes
#        # else:
#        #     ccdset_AutoSaveNo
#    elif OSC['DetectorArmMode'] == 6:      # arm_detector_HWtriggerRetiga_aerohexFly
#        ## CHECK THIS
#        # Put the detector to NoSave
#        # savemode=ccdget_AutoSave
#        # ccdset_AutoSaveNo
#        SaveMode = AD1id.GetAutoStore(OSC['DetList'])
#        AD1id.SetAutoStore(OSC['DetList'], YesOrNo=0)
#        
#        ## CHECK THIS
#        # detector related settings
#        # ccdset_expNum_ad OSC["nframes"] # This has no effect in Continuous mode
#        # ccdset_time OSC["exposure_time"] # per frame, This has no effect in PulseHi/StrobeHi mode, but in EdgeHi
#        
#        pvname = OSC['CcdPV'] + 'ImageMode'
#        pvvalue = 'Single'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sImageMode",CCDPV),"Single", CB_TIME)
#        
#        pvname = OSC['CcdPV'] + 'TriggerMode'
#        pvvalue = 'StrobeHi'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sTriggerMode",CCDPV),"StrobeHi", CB_TIME) # external TTL  This mode is good for the 4000DC for overlapped HWtrigger
#        
#        ## CHECK THIS
#        # For HW triggering we need to Initialize the Retiga but do not need to Acquire    
#        # ccdset_Initialize

#        spec.sleep(1.0)
#        
#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 0
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.B", DetPulseToADPV), 0, CB_TIME) # Disabling the DetPulseToAD signals

#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.C", FrameCounterPV), 1, CB_TIME); # Enabling the counter, if switched to enable immediately counts down by one
#        
#        # When this gets enabled, it will have immediately an element (junk) in the array!
#        pvname = OSC['TimeStampArrayPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.C", TimeStampArrayPV), 1, CB_TIME) # Enabling the TimeStampArray
#        
#        # FPGA interrupts
#        # userCalc activation
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None", CB_TIME) # no GATEToDetector signal in case of external TTL

#        spec.sleep(OSC['EpicsDelay'])

#        ## CHECK THIS
#        # Put the detector to the original Save mode
#        # if (savemode) ccdset_AutoSaveYes else ccdset_AutoSaveNo
#    elif OSC['DetectorArmMode'] == 7:  # arm_detector_HWtriggerRetiga
#        ## CHECK THIS
#        # Put the detector to NoSave
#        # savemode=ccdget_AutoSave
#        # ccdset_AutoSaveNo
#        SaveMode = AD1id.GetAutoStore(OSC['DetList'])
#        AD1id.SetAutoStore(OSC['DetList'], YesOrNo=0)
#    
#        # Programming the detector trigger signal
#        pvname = OSC['FpgaPV'] + 'DnCntr-1_PRESET'
#        pvvalue = 8e6 * OSC['ExpTime']
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDnCntr-1_PRESET", FPGAPV), int(OSC["exposure_time"]*8e6), CB_TIME) # Exp Time, ext. TTL
#        
#        # WARNING: Workaround for the FPGA Det_pulses generation: No extra one frame at the end of the scan
#        pvname = OSC['FpgaPV'] + 'DnCntr-2_PRESET'
#        pvvalue = 8e6 *OSC['GapTime'] + OSC['GapAdjustmentTicks']
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDnCntr-2_PRESET", FPGAPV), int(OSC["gap_time"]*8e6 + GapAdjustmentTicks), CB_TIME) # Gap Time, ext. TTL

#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(1), CB_TIME)

#        ## CHECK THIS
#        # detector related settings
#        # ccdset_expNum_ad OSC["nframes"] # This has no effect in Continuous mode
#        # ccdset_time OSC["exposure_time"] # per frame, This has no effect in PulseHi mode

#        pvname = OSC['CcdPV'] + 'ImageMode'
#        pvvalue = 'Single'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sImageMode",CCDPV),"Single", CB_TIME)

#        pvname = OSC['CcdPV'] + 'TriggerMode'
#        pvvalue = 'StrobeHi'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sTriggerMode",CCDPV),"StrobeHi", CB_TIME) # external TTL  This mode is good for the 4000DC for overlapped HWtrigger

#        # For HW triggering we need to Initialize the Retiga but do not need to Acquire
#        pvname = OSC['CcdPV'] + 'qInitialize'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sqInitialize",CCDPV),1, CB_TIME)
#        
#        spec.sleep(1.0)     # For settling (Retiga AD)
#        
#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 0
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.B", DetPulseToADPV), 0, CB_TIME) # Disabling the DetPulseToAD signals
#        
#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", FrameCounterPV), 1, CB_TIME); # Enabling the counter, if switched to enable immediately counts down by one

#        # When this gets enabled, it will have immediately an element (junk) in the array!
#        pvname = OSC['TimeStampArrayPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", TimeStampArrayPV), 1, CB_TIME) # Enabling the TimeStampArray

#        # FPGA interrupts
#        # userCalc activation
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None", CB_TIME) # no GATEToDetector signal in case of external TTL
#        
#        spec.sleep(OSC['EpicsDelay'])

#        ## CHECK THIS
#        # Put the detector to the original Save mode
#        # if (savemode) ccdset_AutoSaveYes else ccdset_AutoSaveNo
#        
#        spec.sleep(0.5) 
#    elif OSC['DetectorArmMode'] == 12:    # arm_detector_HWtriggerGE
#        # Programming the detector trigger signal
#        pvname = OSC['FpgaPV'] + 'DnCntr-1_PRESET'
#        pvvalue = int( OSC['ExpTime'] * 8e6 )
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sDnCntr-1_PRESET", FPGAPV), int(OSC["exposure_time"]*8e6), CB_TIME) # Exp Time, ext. TTL

#        #WARNING: Workaround for the FPGA Det_pulses generation: No extra one frame at the end of the scan
#        pvname = OSC['FpgaPV'] + 'DnCntr-2_PRESET'
#        pvvalue = int( OSC['GapTime'] * 8e6 + OSC['GapAdjustmentTicks'] )
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sDnCntr-2_PRESET", FPGAPV), int(OSC["gap_time"]*8e6+ GapAdjustmentTicks), CB_TIME) # Gap Time, ext. TTL

#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = int( 1 )
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(1), CB_TIME)

#        # FPGA interrupts
#        # userCalc activation
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None", CB_TIME) # no GATEToDetector signal in case of external TTL

#        ## CHECK THIS
#        # detector related settings
#        # ccdset_expNum_ad OSC["nframes"] # This has no effect in Continuous mode
#        # ccdset_time OSC["exposure_time"] # per frame, This has no effect in PulseHi mode

#        pvname = OSC['CcdPV'] + 'TriggerMode'
#        pvvalue = 'Multi Det'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sTriggerMode",CCDPV),"MULTI DET", CB_TIME) # Modified Coff file: slave_noscrub

#        ## CHECK THIS
#        # For HW triggering we need to Initialize the Retiga but do not need to Acquire    
#        # For GE we have to press the Acquire button in both SW and HW trigger
#        # det_trig OSC["exposure_time"]

#        spec.sleep(OSC['EpicsDelay'] + 1)
#        
#    elif OSC['DetectorArmMode'] == 3:  # arm_detector_HWtriggerGE_PosDriven
#        # Position driven Det_pulses
#        pvname = OSC['FpgaPV'] + 'DnCntr-1_PRESET'
#        pvvalue = int( OSC['ExpTime'] * OSC['Speed'] / OSC['DecodingRate'] )
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDnCntr-1_PRESET", FPGAPV), int(OSC["exposure_time"]*OSC["speed"]/DecodingRate)) # Exp Time, ext. TTL

#        pvname = OSC['FpgaPV'] + 'DnCntr-2_PRESET'
#        pvvalue = int(OSC['GapTime'] * OSC['Speed'] / OSC['DecodingRate'] + GapAdjustmentTicks)
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDnCntr-2_PRESET", FPGAPV), int(OSC["gap_time"]*OSC["speed"]/DecodingRate + GapAdjustmentTicks)) # Gap Time, ext. TTL
#        
#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(1)) 

#        # FPGA interrupts
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None") # no GATEToDetector signal in case of external TTL

#        ## CHECK THIS
#        ## detector related settings
#        # ccdset_expNum_ad OSC["nframes"] # This has no effect in Continuous mode
#        # ccdset_time OSC["exposure_time"] # per frame, This has no effect in PulseHi mode

#        pvname = OSC['CcdPV'] + 'TriggerMode'
#        pvvalue = 'MULTI DET'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sTriggerMode",CCDPV),"MULTI DET") # Modified Coff file: slave_noscrub

#        ## CHECK THIS
#        ## For HW triggering we need to Initialize the Retiga but do not need to Acquire    
#        # det_trig OSC["exposure_time"]

#        spec.sleep(OSC['EpicsDelay'])
#    elif OSC['DetectorArmMode'] == 4:           # arm_detector_HWtriggerGE_FlyScan_Aero_hydra
#        # FPGA interrupts
#        # userCalc activation
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None") # no GATEToDetector signal in case of external TTL
#        
#        hydra1id.SetNumFrames(hydra, numFrames = OSC['nFrames'])            # set_hydra_NumberOfImagesPerDetTrig OSC["nframes"]
#        hydra1id.SetExposureTime(hydra, expTime = OSC['ExpTime'])           # ccdset_expTime_hydra OSC["exposure_time"]

#        ### CHECK THIS
#        hydra1id.SetAcquisitionType(hydra, AcqType=4)

#        pvname = OSC['IdFpgaPV'] + 'BUFFER-4_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sBUFFER-4_IN_Signal.PROC", idFPGAPV), int(1))  # Clearing the latch for the DetRdy signal

#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 0
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.B", DetPulseToADPV), 0, CB_TIME) # Disabling the DetPulseToAD signals

#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.C", FrameCounterPV), 1, CB_TIME) # Enabling the counter, if switched to enable immediately counts down by one
#        
#        # Clears the latches in the DTH module
#        pvname = 'dth2:DTH:resetTriggerBO'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put("dth2:DTH:resetTriggerBO", 1, CB_TIME)

#        ## CHECK THIS
#        # For HW triggering on GE/hydra we need to press the "Acquire" button
#        # det_trig OSC["exposure_time"]

#        spec.sleep(OSC['EpicsDelay'])
#        
#        hydra1id.Wait(OSC['DetList'])       # wait_for_DetRdy
#    elif OSC['DetectorArmMode'] == 5:      # arm_detector_HWtriggerGE_prrot_hydra
#        ## CHECK THIS
#        pvname = '1ide:userTran2.D'
#        SoftMtrRes = ep.caget(pvname)               # softmotres=epics_get("1ide:userTran2.D")
#        StepConversion = SoftMtrRes / 0.000264706   # StepConversion = softmotres/0.000264706  # Ratio of the softmotor resolution and the hard motor resolution

#        pvname = OSC['FpgaPV'] + 'DnCntr-1_PRESET'
#        pvvalue = OSC['ExpTime'] * OSC['Speed'] / StepConversion / OSC['DecodingRate']
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sDnCntr-1_PRESET", FPGAPV), int(OSC["exposure_time"]*OSC["speed"]/StepConversion/DecodingRate), CB_TIME) # Exp Time, ext. TTL
#        
#        pvname = OSC['FpgaPV'] + 'DnCntr-2_PRESET'
#        pvvalue = OSC['GapTime'] * OSC['Speed'] / StepConversion / OSC['DecodingRate'] + GapAdjustmentTicks
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sDnCntr-2_PRESET", FPGAPV), int(OSC["gap_time"]*OSC["speed"]/StepConversion/DecodingRate + GapAdjustmentTicks), CB_TIME) # Gap Time, ext. TTL

#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(1), CB_TIME)
#        
#        pvname = OSC['FpgaPV'] + 'BUFFER-2_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sBUFFER-2_IN_Signal.PROC", FPGAPV), int(1), CB_TIME) # Workaround for the unwanted signal before the GATE (When this is reset there is a short pulse on the det_pulses line, if we do it here, then when teh softmotor do it automatically there is no more signal)
#        
#        # FPGA interrupts
#        # userCalc activation
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None", CB_TIME) # no GATEToDetector signal in case of external TTL
#        
#        hydra1id.SetNumFrames(OSC['DetList'], OSC['nFrames'])     # set_hydra_NumberOfImagesPerDetTrig OSC["nframes"]
#        hydra1id.SetExposureTime(OSC['DetList'], OSC['ExpTime'])    # set_hydra_expTime OSC["exposure_time"]
#        hydra1id.SetAcquisitionType(hydra, AcqType=4)               # set_hydra_MultiDetPulse
#        
#        pvname = OSC['IdFpgaPV'] + 'BUFFER-4_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sBUFFER-4_IN_Signal.PROC", idFPGAPV), int(1))  # Clearing the latch for the DetRdy signal
#        
#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 0
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.B", OSC['DetPulseToADPV']), 0, CB_TIME) # Disabling the DetPulseToAD signals
#        
#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.C", FrameCounterPV), 1, CB_TIME); # Enabling the counter, if switched to enable immediately counts down by one
#        
#        # Clears the latches in the DTH module
#        pvname = 'dth2:DTH:resetTriggerBO'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put("dth2:DTH:resetTriggerBO", 1, CB_TIME)

#        ## CHECK THIS
#        # For HW triggering on GE/hydra we need to press the "Acquire" button
#        # det_trig OSC["exposure_time"]
#        spec.sleep(OSC['EpicsDelay'])
#        sleep(EPICS_DELAY)
#        
#        hydra1id.Wait(OSC['DetList'])   # wait_for_DetRdy
#        
#    elif OSC['DetectorArmMode'] == 8:   # arm_detector_HWtriggerGE_prrot_hydra_Renishaw
#        FastSweepParamCheck(OSC)

#        pvname = OSC['FpgaPV'] + 'DnCntr-1_PRESET'
#        pvvalue = int( OSC['ExpTime'] * OSC['Speed'] / OSC['DecodingRate'] )
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDnCntr-1_PRESET", FPGAPV), int(OSC["exposure_time"]*OSC["speed"]/DecodingRate), CB_TIME) # Exp Time, ext. TTL
#        
#        pvname = OSC['FpgaPV'] + 'DnCntr-2_PRESET'
#        pvvalue = int( OSC['ExpTime'] * OSC['Speed'] / OSC['DecodingRate'] + OSC['GapAdjustmentTicks'] )
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDnCntr-2_PRESET", FPGAPV), int(OSC["gap_time"]*OSC["speed"]/DecodingRate + GapAdjustmentTicks), CB_TIME) # Gap Time, ext. TTL

#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(1), CB_TIME) # 

#        pvname = OSC['FpgaPV'] + 'BUFFER-2_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-2_IN_Signal.PROC", FPGAPV), int(1), CB_TIME) # Workaround for the unwanted signal before the GATE (When this is reset there is a short pulse on the det_pulses line, if we do it here, then when teh softmotor do it automatically there is no more signal)
#        
#        # FPGA interrupts
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None", CB_TIME) # no GATEToDetector signal in case of external TTL

#        hydra1id.SetNumFrames(OSC['DetList'], numFrames = OSC['nFrames']) 
#        hydra1id.SetExposureTime(OSC['DetList'], expTime = OSC['ExpTime'])
#        SetAcquisitionType(OSC['DetList'], AcqType=4)

#        pvname = OSC['IdFpgaPV'] + 'BUFFER-4_IN_Signal.PROC'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-4_IN_Signal.PROC", idFPGAPV), int(1))  # Clearing the latch for the DetRdy signal

#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.B", DetPulseToADPV), 0, CB_TIME) # Disabling the DetPulseToAD signals

#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", FrameCounterPV), 1, CB_TIME); # Enabling the counter, if switched to enable immediately counts down by one
#        
#        pvname = 'dth1:DTH:resetTriggerBO'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put("dth1:DTH:resetTriggerBO", 1, CB_TIME) # Clears the latches in the DTH module
#        
#        # For HW triggering on GE/hydra we need to press the "Acquire" button
#        Trigger(OSC['DetList'], expTime = OSC['ExpTime'])       # det_trig OSC["exposure_time"]
#        spec.sleep(OSC['EpicsDelay'])
#        hydra1id.Wait(OSC['DetList'])       # wait_for_DetRdy
#        
#    elif OSC['DetectorArmMode'] == 11:    # arm_detector_HWtriggerRetiga_PosDriven_prrot_Renishaw
#        ## CHECK THIS
#        # Put the detector to NoSave
#        # savemode=ccdget_AutoSave
#        # ccdset_AutoSaveNo
#        SaveMode = AD1id.GetAutoStore(OSC['DetList'])
#        AD1id.SetAutoStore(OSC['DetList'], YesOrNo=0)

#        FastSweepParamCheck(OSC)

#        # Position driven Det_pulses
#        pvname = OSC['FpgaPV'] + 'DnCntr-1_PRESET'
#        pvvalue = int( OSC['ExpTime'] * OSC['Speed'] / OSC['DecodingRate'] )
#        ep.caput(pvname, pvvalue, wait=True)            # epics_put(sprintf("%sDnCntr-1_PRESET", FPGAPV), int(OSC["exposure_time"]*OSC["speed"]/DecodingRate), CB_TIME) # Exp Time, ext. TTL
#        
#        pvname = OSC['FpgaPV'] + 'DnCntr-2_PRESET'
#        pvvalue = int( OSC['GapTime'] * OSC['Speed'] / OSC['DecodingRate'] + OSC['GapAdjustmentTicks'] )
#        ep.caput(pvname, pvvalue, wait=True)            # epics_put(sprintf("%sDnCntr-2_PRESET", FPGAPV), int(OSC["gap_time"]*OSC["speed"]/DecodingRate + GapAdjustmentTicks), CB_TIME) # Gap Time, ext. TTL
#        
#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)            # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(1), CB_TIME) # Arms pulses signal. Just for sure, the soft motor does it anyway.

#        pvname = OSC['FpgaPV'] + 'BUFFER-2_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)            # epics_put(sprintf("%sBUFFER-2_IN_Signal.PROC", FPGAPV), int(1), CB_TIME) # Workaround for the unwanted signal before the GATE (When this is reset there is a short pulse on the det_pulses line, if we do it here, then when the softmotor do it automatically there is no more signal)

#        ## CHECK THIS
#        # detector related settings
#        # ccdset_expNum_ad OSC["nframes"] # This has no effect in Continuous mode and HWtrigger mode
#        # ccdset_time OSC["exposure_time"] # per frame, This has no effect in PulseHi/StrobeHi mode, but in EdgeHi

#        pvname = OSC['CcdPV'] + 'ImageMode'
#        pvvalue = 'Single'
#        ep.caput(pvname, pvvalue, wait=True)            # epics_put(sprintf("%sImageMode",CCDPV),"Single", CB_TIME)

#        pvname = OSC['CcdPV'] + 'TriggerMode'
#        pvvalue = 'StrobeHi'    
#        ep.caput(pvname, pvvalue, wait=True)            # epics_put(sprintf("%sTriggerMode",CCDPV),"StrobeHi", CB_TIME) # external TTL  This mode is good for the 4000DC for overlapped HWtrigger

#        ## CHECK THIS
#        # For HW triggering we need to Initialize the Retiga but do not need to Acquire    
#        # ccdset_Initialize

#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 0
#        ep.caput(pvname, pvvalue, wait=True)            # epics_put(sprintf("%s.B", DetPulseToADPV), 0, CB_TIME) # Disabling the DetPulseToAD signals

#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)            # epics_put(sprintf("%s.C", FrameCounterPV), 1, CB_TIME); # Enabling the counter, if switched to enable immediately counts down by one

#        # When this gets enabled, it will have immediately an element (junk) in the array!
#        pvname = OSC['TimeStampArrayPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)            # epics_put(sprintf("%s.C", TimeStampArrayPV), 1, CB_TIME) # Enabling the TimeStampArray

#        # FPGA interrupts
#        pvname = OSC['FpgaPV'] + '.In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)            # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None", CB_TIME) # no GATEToDetector signal in case of external TTL

#        spec.sleep(OSC['EpicsDelay'])

#        ## CHECK THIS
#        # Put the detector to the original Save mode
#        # if (savemode) ccdset_AutoSaveYes else ccdset_AutoSaveNo
#        
#    elif OSC['DetectorArmMode'] == 9:       # arm_detector_SWRetiga
#        # Software triggering on Retiga

#        ## CHECK THIS
#        # Put the detector to NoSave
#        # savemode=ccdget_AutoSave
#        # ccdset_AutoSaveNo
#        SaveMode = AD1id.GetAutoStore(OSC['DetList'])
#        AD1id.SetAutoStore(OSC['DetList'], YesOrNo=0)

#        ## CHECK THIS
#        # detector related settings
#        # ccdset_expNum_ad OSC["nframes"] # This has no effect in Continuous mode
#        # ccdset_time OSC["exposure_time"] # per frame, This has no effect in PulseHi mode

#        pvname = OSC['CcdPV'] + 'ImageMode'
#        pvvalue = 'Single'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sImageMode",CCDPV),"Single")
#        
#        pvname = OSC['CcdPV'] + 'TriggerMode'
#        pvvalue = 'Software'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sTriggerMode",CCDPV),"Software") # Pressing the "Start" button

#        ## CHECK THIS
#        # ccdset_Initilaize

#        # Programming the detector trigger signal
#        pvname = OSC['FpgaPV'] + 'DnCntr-1_PRESET'
#        pvvalue = int( OSC['ExpTime'] * 8e6 )
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDnCntr-1_PRESET", FPGAPV), int(OSC["exposure_time"]*8e6)) # Exp Time, ext. TTL89

#        pvname = OSC['FpgaPV'] + 'DnCntr-2_PRESET'
#        pvvalue = int( OSC['GapTime'] * 8e6 + OSC['GapAdjustmentTicks'] )
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDnCntr-2_PRESET", FPGAPV), int(OSC["gap_time"]*8e6 + GapAdjustmentTicks)) # Gap Time, ext. TTL
#        
#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(1)) # 

#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.B", DetPulseToADPV), 1) # Enabling the DetPulseToAD signals

#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", FrameCounterPV), 1); # Enabling the counter, if switched to enable immediately counts down by one

#        # When this gets enabled, it will have immediately an element (junk) in the array!
#        pvname = OSC['TimeStampArrayPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", TimeStampArrayPV), 1) # Enabling the TimeStampArray

#        # FPGA interrupts
#        # userCalc activation
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None") # no GATEToDetector signal in case of external TTL
#        
#        spec.sleep(OSC['EpicsDelay'])           # sleep(EPICS_DELAY)

#        ## CHECK THIS
#        # Put the detector to the original Save mode
#        # if (savemode) ccdset_AutoSaveYes else ccdset_AutoSaveNo
#        
#    elif OSC['DetectorArmMode'] == 10:          # arm_detector_SWRetiga_PosDriven
#        '''
#        arm_detector_SWRetiga_PosDriven

#        Software triggering on Retiga
#        '''
#        ## CHECK THIS
#        # Put the detector to NoSave
#        # savemode=ccdget_AutoSave
#        # ccdset_AutoSaveNo
#        SaveMode = AD1id.GetAutoStore(OSC['DetList'])
#        AD1id.SetAutoStore(OSC['DetList'], YesOrNo=0)

#        ## CHECK THIS
#        # detector related settings
#        # ccdset_expNum_ad OSC["nframes"]         # This has no effect in Continuous mode
#        # ccdset_time OSC["exposure_time"]        # per frame, This has no effect in PulseHi mode
#        pvname = OSC['CcdPV'] + 'ImageMode'
#        pvvalue = 'Single'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sImageMode",CCDPV),"Single")

#        pvname = OSC['CcdPV'] + 'TriggerMode'
#        pvvalue = 'Software'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sTriggerMode",CCDPV),"Software") # Pressing the "Start" button

#        ## CHECK THIS
#        # For HW triggering we need to Initialize the Retiga but do not need to Acquire    
#        # ccdset_Initialize  

#        # Position driven Det_pulses
#        pvname = OSC['FpgaPV'] + 'DnCntr-1_PRESET'
#        pvvalue = int( OSC['ExpTime'] * OSC['Speed'] / OSC['DecodingRate'] )
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sDnCntr-1_PRESET", FPGAPV), int(OSC["exposure_time"]*OSC["speed"]/DecodingRate)) # Exp Time, ext. TTL

#        pvname = OSC['FpgaPV'] + 'DnCntr-2_PRESET'
#        pvvalue = int( OSC['GapTime'] * OSC['Speed'] / OSC['DecodingRate'] + OSC['GapAdjustmentTicks'] ) 
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sDnCntr-2_PRESET", FPGAPV), int(OSC["gap_time"]*OSC["speed"]/DecodingRate + GapAdjustmentTicks)) # Gap Time, ext. TTL

#        pvname = OSC['FpgaPV'] + 'BUFFER-3_IN_Signal.PROC'
#        pvvalue = int(1)
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sBUFFER-3_IN_Signal.PROC", FPGAPV), int(1)) # 

#        pvname = OSC['DetPulseToADPV'] + '.B'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.B", DetPulseToADPV), 1) # Enabling the DetPulseToAD signals

#        pvname = OSC['FrameCounterPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.C", FrameCounterPV), 1); # Enabling the counter, if switched to enable immediately counts down by one

#        # When this gets enabled, it will have immediately an element (junk) in the array!
#        pvname = OSC['TimeStampArrayPV'] + '.C'
#        pvvalue = 1
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.C", TimeStampArrayPV), 1) # Enabling the TimeStampArray

#        # FPGA interrupts
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%sIn_17IntEdge", FPGAPV), "None") # no GATEToDetector signal in case of external TTL

#        
#        spec.sleep(OSC['EpicsDelay'])               # sleep(EPICS_DELAY)
#        spec.sleep(1.0)                             # sleep(1.0) # For settling (Retiga AD)

#        ## CHECK THIS
#        # Put the detector to the original Save mode
#        # if (savemode) ccdset_AutoSaveYes else ccdset_AutoSaveNo        
#    return
#    
#def DisarmDetector(OSC):        # disarm_detector
#    '''

#    disarm_detector
#    
#    formally, 
#    print 'Detector disarm mode 
#    print '0: disarm_detector_HWtriggerRetiga'
#    print '1: disarm_detector_HWtriggerGE'

#    print '2: disarm_detector_HWtriggerGE_hydra'
#    print '3: disarm_detector_SWRetiga'
#    
#    this is now broken down into trigger mode and detector type
#    '''

#    for det in OSC['DetList']:
#        print 'Disarming ' + det.symbol
#        
#        # PRESERVE SAVE MODE IF RETIGA
#        if det.detectortype is 'Retiga':
#            SaveMode = AD1id.GetAutoStore([det])[0]
#            AD1id.SetAutoStore([det], YesOrNo=0)
#            
#        # COMMON STUFF FOR HWT & SWT
#        spec.sleep(EpicsDelay)
#        
#        # FPGA interrupts
#        # userCalc deactivation
#        # GATEToDetector signal
#        pvname = OSC['FpgaPV'] + 'In_17IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put( sprintf("%sIn_17IntEdge", FPGAPV),"None", CB_TIME)
#        
#        # DetTrigToICscalers signal through EPICS
#        pvname = OSC['FpgaPV'] + 'In_19IntEdge'
#        pvvalue = 'None'
#        ep.caput(pvname, pvvalue, wait=True)        # epics_put( sprintf("%sIn_19IntEdge", FPGAPV),"None", CB_TIME)    
#            
#        # BREAK DOWN INTO MODES
#        if TriggerMode is 0:
#            print 'Hardware triggering'
#            # Disabling the DetPulseToAD signals
#            pvname = OSC['DetPulseToADPV'] + '.B'
#            pvvalue = 0
#            ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.B", DetPulseToADPV), 0, CB_TIME)
#                
#            # Disabling the counter
#            pvname = OSC['FrameCounterPV'] + '.C'
#            pvvalue = 0
#            ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.C", FrameCounterPV), 0, CB_TIME);
#            
#            if det.detectortype is 'Retiga':       # disarm_detector_HWtriggerRetiga
#                AD1id.Wait([Detector])
#                AD1id.FilePluginWait([Detector])
#                spec.sleep(2)            
#                
#                # Disabling the TimeStampArray
#                pvname = OSC['TimeStampArrayPV'] + '.C'
#                pvvalue = 0
#                ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", TimeStampArrayPV), 0, CB_TIME)
#                
#            elif det.detectortype is 'GE':         # disarm_detector_HWtriggerGE_hydra
#                # Clearing the latch for the DetRdy signal
#                pvname = OSC['IdFpgaPV'] + 'BUFFER-4_IN_Signal.PROC'
#                pvvalue = int(1)
#                ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-4_IN_Signal.PROC", idFPGAPV), int(1))
#                    
#        elif TriggerMode is 1:
#            print 'Software triggering'
#            if det.detectortype is 'Retiga':   # disarm_detector_SWRetiga
#                # Disabling the DetPulseToAD signals
#                pvname = OSC['DetPulseToADPV'] + '.B'
#                pvvalue = 'None'
#                ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.B", DetPulseToADPV), 0, CB_TIME)
#                
#                # Disabling the counter
#                pvname = OSC['FrameCounterPV'] + '.C'
#                pvvalue = 'None'
#                ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.C", FrameCounterPV), 0, CB_TIME);
#                
#                # Disabling the TimeStampArray
#                pvname = OSC['TimeStampArrayPV'] + '.C'
#                pvvalue = 'None'
#                ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.C", TimeStampArrayPV), 0, CB_TIME);

#                pvname = OSC['FrameCounterPV'] + '.B'
#                FramesLeft = ep.caget(pvname)
#                if FramesLeft is not 0:
#                    print 'WARNING! ' + str(FramesLeft) + 'frame(s) missing from the fastsweep.'
#                    
#        else:
#            print 'ERROR: Specifed trigger mode not supported'
#            print '0: Hardware trigger'
#            print '1: Software trigger'
#        
#        # detector back to normal state
#        if det.detectortype is 'Retiga':
#            pvname = OSC['CcdPV'] + '.C'
#            pvvalue = 'Single'
#            ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sImageMode",CCDPV),"Single", CB_TIME)
#            
#            pvname = OSC['CcdPV'] + 'TriggerMode'
#            pvvalue = 'Software'
#            ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sTriggerMode",CCDPV),"Software", CB_TIME)
#            
#            pvname = OSC['CcdPV'] + 'qInitialize'
#            pvvalue = 1
#            ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sqInitialize",CCDPV),1, CB_TIME)
#            spec.sleep(1.0)
#            
#            # Put the detector to the original Save mode
#            if SaveMode:
#                AD1id.SetAutoStore([det], YesOrNo=1)
#            else:
#                AD1id.SetAutoStore([det], YesOrNo=0)
#        elif det.detectortype is 'GE':
#            # detector back to normal state
#            AD1id.SetAcquisitionType([det], AcqType=2)      # set_hydra_MultiDetSW
#        
#        print 'Next image number: ' + str( AD1id.GetFileNumber([det])[0] )
#        spec.sleep(EpicsDelay)
#    return

#def PrintDetList(OSC):       # /home/beams/SPECADM/1id_macros/HEDM/ccdscan/ccd_ad.mac
#    '''
#    ccdinfo_ad mapped to ccdinfo
#    prints the detector information
#    '''
#    hydra = OSC['DetList']
#    for det in hydra:
#        if det is not None:
#            print '==========================================='
#            print det.symbol
#            print '==========================================='
#            print 'Type           : ' + AD.AD_get(det, 'manufacturer')
#            print 'Control prefix : ' + det.controlprefix
#            print 'Image prefix   : ' + det.imageprefix
#            
#            ## TODO ROI STUFF
#            # printf("Image data extension type: %s\n",CCD_FILE_EXT)
#            # if(exists("MNT_MAP","client") ){
#            #     printf("Image data directory at client(spec): %s\n",MNT_MAP["client"])
#            # }
#            # printf("ROI plugin prefix: %s\n",ADROIPV)
#    return

#def FilePluginWait(hydra):        # Retiga_FilePluginWait
#    '''
#    Retiga_FilePluginWait
#    '''
#    for det in hydra:
#        waittime = 0
#        dtime = 0.1
#        
#        if det is not None:
#            if det.detectortype is 'Retiga':
#                pvname = OSC['ADFilePV'] + 'WriteFile_RBV'
#                while ~ep.caget(pvname):
#                    sleep(dtime)
#                    waittime = waittime + dtime
#                    if waittime >= 30:
#                        print 'ERROR: Waited for the detector file saving plugin more than 30 sec.'
#                        print 'ERROR: Check ' + det.symbol + ' for its status.'
#            else:
#                print 'FilePluginWait not applicable for ' + det.symbol
#        else:
#            print 'FilePluginWait not applicable'
#    return
