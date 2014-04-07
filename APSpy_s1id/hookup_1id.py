import AD_1id as AD1id
import sweep_core_1id as sweepcore1id

#################################################
### HUTCH SETUP
#################################################
def SetupHutch(OSC):
    if OSC['HutchLetter'] is 'B':
        OSC['MonCountArrayPV'] = '1id:userArrayCalc1'
        OSC['TransmCountArrayPV'] = '1id:userArrayCalc3'
        OSC['MonScalerPV'] = '1id:scaler2'

        OSC['MonICName'] = '_cts2.C'	    # before the sample (from the orange field)
        OSC['TransmICName'] = '_cts2.D'     # after the sample

        # Integration time counter
        OSC['IntegerTicksArrayPV'] = '1id:userArrayCalc6'
        OSC['IntegerICName'] = '_calc5.VAL'             # At the calc fields: A= 1id:scaler2_calc5.VAL
        OSC['DetPulsePV'] = '1id:9440:1:bi_0'           # For getting the det_pulses for Scaler Triggering via the Acromag
        
        OSC['ReadoutPV'] = '1id:9440:1:bi_1'            # Input ch1, Counts the Retiga READOUT signals now it is easier and more reliable
        OSC['SingleExposureGEPV'] = '1id:9440:1:bi_2'   # Input ch2, Counts the GE EXPOSURE signals
        
        OSC['ScalerTrigPV'] = '1id:userCalcOut3'
        OSC['DetPulseToADPV'] = '1id:userStringCalc4'   # This is not enabled with HW triggering
        
        OSC['FrameCounterPV'] = '1id:userTran10'
        OSC['FrameCounterTriggerPV'] = '1id:userCalcOut2'

        OSC['FPGAPV'] = '1mini1:sg:'
        OSC['GateSignalPV'] = '1id:9440:1:bi_3'

        OSC['RisingEdgeGateMode'] = 0       # rdef RisingEdge_GATE \'Rising_GATE_Bhutch\'  # For waiting for the GATE
        OSC['FallingEdgeGateMode'] = 0      # rdef FallingEdge_GATE \'Falling_GATE_Bhutch\'

        OSC['DisableGateMode'] = 0          # DisableGate(Gate=0) # rdef disableGATE \' \'
        OSC['EnableGateMode'] = 0           # rdef enableGATE \' \'
        
    elif OSC['HutchLetter'] is 'C':
        OSC['MonCountArrayPV'] = '1id:userArrayCalc1'
        OSC['TransmCountArrayPV'] = '1id:userArrayCalc2'
        OSC['MonScalerPV'] = '1id:scaler2'

        OSC['MonICName'] = '_cts4.A'        # standard IC, ic3c, after the DS slit, before the sample 
        OSC['TransmICName'] = '_cts3.A'     # IC downstream of hydra (ic7b or IC6)

        # Energy monitoring
        OSC['EMonCountArrayPV'] = '1id:userArrayCalc3'
        OSC['ETransmCountArrayPV'] = '1id:userArrayCalc4'
        OSC['EMonICName'] = '_cts3.C'       # before the E-calib foil in B 
        OSC['ETransmICName'] = '_cts3.D'    # after the E-calib foil in B

        # Integration time counter
        OSC['IntegerTicksArrayPV'] = '1id:userArrayCalc6'
        OSC['IntegerICName'] = '_calc5.VAL' # Be sure: At the calc fields: 1id:scaler2_calc5.CALC = A => 1id:scaler2_calc5.VAL

        OSC['DetPulsePV'] = '1id:9440:1:bi_0'
        sweepcore1id.SetupDetPulsePVAcromag(OSC)    # setup_DetPulsePV_Acromag
        
        OSC['ReadoutPV'] = '1id:9440:1:bi_1'        # Retiga Readout for counting the frames
        sweepcore1id.SetupReadoutPVAcromag(OSC)     # setup_ReadoutPV_Acromag

        OSC['SingleExposureGEPV'] = '1id:9440:1:bi_2'       # GE Single EXposure for counting the frames
        sweepcore1id.SetupSingleExposureGEPVAcromag(OSC)    # setup_SEXGEPV_Acromag

        OSC['ScalerTrigPV'] = '1id:userCalcOut3'
        OSC['DetPulseToADPV'] = '1id:userStringCalc4'

        OSC['FrameSignalPV'] = OSC['DetPulsePV']            # This is only the default, it is set later correctly in the detector related macros
        OSC['FrameCounterPV'] = '1id:userTran10'            # The triggered FrameCounter record
        OSC['FrameCounterTriggerPV'] = "1id:userCalcOut2"   # The userCalOut record that triggers the framecounter

        OSC['FPGAPV'] = '1ide:sg2:'
        OSC['PSOPV'] = '1ide:PSOFly1:'
        OSC['DetReadyPV'] = '1id:softGlue:DFF-2_OUT_BI' # For waiting when the hydra is ready for work
        OSC['IDFPGAPV'] = '1id:softGlue:'
        
        OSC['ScalerTrigDetPulsePV']='1id:softGlue:FO3_BI'   # Gives the trigger signal to the ScalerTrigPV
        # sweepcore1id.SetupDTHDetRdyFPGA(OSC)              # setup_DTHDetRdy_FPGA
        
        #GATE_signalPV="1ide:userCalcOut1" # for prrot
        OSC['GateSignalPV'] = '1id:9440:1:bi_3'
        sweepcore1id.SetupGATESignalPVAcromag(OSC)
        
        # rdef RisingEdge_GATE \'Rising_GATE_Ehutch\'  # For waiting for the GATE
        # rdef FallingEdge_GATE \'Falling_GATE_Ehutch\'
        # setup_FakeGATEandDetPulse_aero # Stopping the GATE signal at the end of sweep only
        # rdef disableGATE \' \' # For stopping the generation of signals during positioning the stage
        # rdef enableGATE \' \'
        
    elif OSC['HutchLetter'] is 'E':
        # COMMON ITEMS
        OSC['MonCountArrayPV'] = '1ide:userArrayCalc1'
        OSC['TransmCountArrayPV'] = '1ide:userArrayCalc2'
        OSC['MonScalerPV'] = '1ide:S2:scaler2'

        OSC['MonICName'] = '_cts2.B'        # standard IC in E, after the DS slit, before the sample 
        OSC['TransmICName'] = '_cts2.A'     # pin diode after the sample

        # Energy monitoring
        OSC['EMonCountArrayPV'] = '1ide:userArrayCalc3'
        OSC['ETransmCountArrayPV'] = '1ide:userArrayCalc4'
        OSC['EMonICName'] = '_cts4.A'       # before the E-calib foil in B 
        OSC['ETransmICName'] = '_cts4.B'    # after the E-calib foil in B

        # Integration time counter
        OSC['IntegerTicksArrayPV'] = '1ide:userArrayCalc6'
        OSC['IntegerICName'] = '_calc1.VAL' # At the calc fields: A= 1ide:3820:scaler2_calc1.VAL

        OSC['DetPulsePV'] = '1id:9440:1:bi_0'
        sweepcore1id.SetupDetPulsePVAcromag(OSC)

        OSC['ReadoutPV'] = '1id:9440:1:bi_1'    # Retiga Readout for counting the frames
        sweepcore1id.SetupReadoutPVAcromag(OSC)

        OSC['SingleExposureGEPV'] = '1id:9440:1:bi_2'      # GE Single EXposure for counting the frames
        sweepcore1id.SetupSingleExposureGEPVAcromag(OSC)

        OSC['GateSignalPV'] = '1id:9440:1:bi_3'
        sweepcore1id.SetupGATESignalPVAcromag(OSC)

        OSC['ScalerTrigPV'] = '1ide:userCalcOut2'
        OSC['DetPulseToADPV'] = '1id:userStringCalc4'

        OSC['FrameSignalPV'] = OSC['DetPulsePV']            # This is only the default, it is set later correctly in the detector related macros
        OSC['FrameCounterPV'] = '1id:userTran10'            # The triggered FrameCounter record
        OSC['FrameCounterTriggerPV'] = '1id:userCalcOut2'   # The userCalOut record that triggers the framecounter

        OSC['PSOPV'] = '1ide:PSOFly1:'
        OSC['DetReadyPV'] = '1id:softGlue:DFF-2_OUT_BI'     # For waiting when the hydra is ready for work
        OSC['IDFPGAPV'] = '1id:softGlue:'

        # sweepcore1id.SetupDTHDetRdyFPGA(OSC)

        # OSC['RisingEdgeGateMode'] = 1   # rdef RisingEdge_GATE \'Rising_GATE_Ehutch\'
        # OSC['FallingEdgeGateMode'] = 1  # rdef FallingEdge_GATE \'Falling_GATE_Ehutch\'
        
        # OSC['DisableGateMode'] = 0      # rdef disableGATE \' \' # For stopping the generation of signals during positioning the stage
        # OSC['EnableGateMode'] = 0       # rdef enableGATE \' \'
        
        OSC['ScalerTrigDetPulsePV'] = '1ide:sg:FO21_BI'         # Gives the trigger signal to the ScalerTrigPV

        #### CHECK THIS - HOW WE DEFINE MOTOR NAME
        if motorname is 'prrot':
            OSC['FPGAPV'] = '1ide:sg:'
        elif motorname is 'aero':
            OSC['FPGAPV'] = '1ide:sg2:'
    else:
        print 'Unknown hutch identifier'
        sys.exit()

    # THIS IS USER_DATE_hydra1 & USER_DATE_combined
    for det in OSC['Detectors']:
        print 'Hydra is composed of the following detectors :'
        print det.controlprefix

    AD1id.HydraInitialize(OSC)
    AD1id.DTHInitialize(hydra, TrigMode=OSC['TrigMode'])

    print 'Hydra initialized'
    OSC['DetDelay']=0.0

    print 'Hydra file paths :'
    print AD.AD_get(hydra, 'filepath')
    print 'Hydra file names :'
    print AD.AD_get(hydra, 'filename')
    print 'Hydra file formats :'
    print AD.AD_get(hydra, 'filetemplate')
    print 'Hydra file numbers :'
    print AD.AD_get(hydra, 'filenumber')

    AD.AD_set(hydra, 'frames', 1)
    AD.AD_set(hydra, 'buffer1', 250)
    AD1id.SetAutoStore(hydra, YesOrNo=1)
    AD1id.SetAcquisitionType(hydra, AcqType=2)
    
    return OSC

#def balogh_march14_hydra1 '{

#    #balogh_march14_set_Ehutch
#    balogh_march14_set_Chutch
#    set_hydra_aero
#    #set_hydra_prrot
#    FrameSignalPV=DetPulsePV
# 
#    FS_GE2SE_control
#    
#    # Only for test purposes
#    # Comment out
#    osc_threshold = -1
#    #parfile="./test.par"
#    DEFAULT_GAP_TIME=0.150
#    # epics_put("1ide:m5.CNEN", "Enable") # Enabling the Torque on PulseRay prrot motor
#    sleep(EPICS_DELAY)
#    sync
#    printOscGlobals
#}'





#global EPICS_DELAY
#global CB_TIME
#EPICS_DELAY=0.02
#CB_TIME = 10.0  # The max time in seconds for waiting for the Callback in epics_put commands


##DO_DIR="./macros_PK/fastsweep_BCEhutch_preci_prrot_aero_GE_Retiga_2013Aug11/"
#DO_DIR="macros_PK/fastsweep_BCEhutch_preci_prrot_aero_GE_Retiga_2014Feb24/"
#qdo beampos.mac
#qdo sweep_core_mod.mac
#qdo osc_fastsweep_FPGA_hydra.mac
#qdo write_parfile_general.mac



## Overwriting this interactive macro
## /home/beams/SPECADM/1id_macros/HEDM/sweep_det.mac
#def osc_setup_mod '{
#        local det
#        #OSC["shutteropen_delay"] =getval("Shutter open delay (Sec)",OSC["shutteropen_delay"])
#        OSC["shutteropen_delay"] = 0 
#        #OSC["shutterclose_delay"] =getval("Shutter close delay (Sec)",OSC["shutterclose_delay"])
#        OSC["shutterclose_delay"] = 0
#        
#        #if(SOFTIOC_USE=yesno("Use soft ioc to communicate with matlab?",SOFTIOC_USE)) {
#        #  SOFTIOC_PV = getval("Need to know the soft ioc prefix:",SOFTIOC_PV) 
#        #}
#        SOFTIOC_USE=0
#        
#        printf("\nPlease run the following setup macro based on detector type\n")
#        printf("####################################\n")
#        for(det in CCD_DET) {
#           printf("\t%s: %s\n",det,CCD_DET[det])
#        }
#      
#}'

#osc_setup_mod

#def balogh_march14_hydra1 '{
#    # Single GE2 with hydra scripts for aero/hexFly in E-hutch, PSO based FPGA control
#    
#    local ihydra
#    
#	#set_hydra_AutoStoreNo
#	#set_hydra_UserSingle
#	#qdo ./macros/use_hydra.mac
#    p "Hydra original:", hydra
#	# Select GE2
#	
#	### 3 PANEL HYDRA
#	#hydraNum=3
#    #hydra[1]=1 ;  hydra[2]=3 ; hydra[3]=4 ; hydra[4]=0 
#    #use_ge_hydra "GE3:cam1:"    # This is not important any more
#    
#    ### 1 PANEL HYDRA
#    hydraNum=1
#    hydra[1]=3 ;  hydra[2]=0 ; hydra[3]=0 ; hydra[4]=0 
#    use_ge_hydra "GE3:cam1:"    # This is not important any more
#    
#    p "Hydra new:", hydra
#    
#    hydra_Initialize
#	
#	p "Hydra initialized:", hydra
#    OSC["detDelay"]=0.0
#    printf("Hydra array:       ")
#    for (ihydra=1 ; ihydra<=hydraNum; ihydra= ihydra+1) { 
#        printf("  %d", hydra[ihydra])
#    }
#    printf("\n")
#	printf("Next file paths:   ")
#	get_hydra_AllFilePaths
#	printf("Next file names:   ")
#	get_hydra_AllFileNames
#	printf("Next file formats:   ")
#	get_hydra_AllFileNameFormats
#	printf("Next file numbers: ")
#	get_hydra_AllFileNumbers

#	set_hydra_AutoStoreYes
#	#set_ge_AutoStoreNo
#	set_hydra_MultiDetSW
##	set_hydra_MultiDetEdge
##	set_hydra_MultiDetPulse
##	set_hydra_RadMode
#	set_hydra_NumberOfImagesPerDetTrig 1
#	set_hydra_BufferSize 290  # for GE3 GE4 and GE1 computers
#	#  for GE2 only 250, so do not need to do anything here
#	
#  
#    parfile="balogh_march14_FF.par"
#    fastparfile="fastpar_balogh_march14_FF.par"

#    #sxparfile="fastpar_balogh_march14_SX.par"

#	# setting up the osc
#    #balogh_march14_set_Ehutch
#    balogh_march14_set_Chutch
#    set_hydra_aero
#    #set_hydra_prrot
#    FrameSignalPV=DetPulsePV
# 
#    FS_GE2SE_control
#    
#    # Only for test purposes
#    # Comment out
#    osc_threshold = -1
#    #parfile="./test.par"
#    DEFAULT_GAP_TIME=0.150
#    # epics_put("1ide:m5.CNEN", "Enable") # Enabling the Torque on PulseRay prrot motor
#    sleep(EPICS_DELAY)
#    sync
#    printOscGlobals
#}'


#def balogh_march14_combined '{
#    # Single GE2 with hydra scripts for prrot in E-hutch, AFRL
#    # Combined with teh near field Retiga detector called as QIMAGE1
#    
#    local ihydra
#    
#	# Select GE2
#	hydraNum=1
#    hydra[1]=2 ;  hydra[2]=0 ; hydra[3]=0 ; hydra[4]=0 

#    hydra_Initialize
#	
#	p "Hydra initialized:", hydra
#    OSC["detDelay"]=0.0
#    printf("Hydra array:       ")
#    for (ihydra=1 ; ihydra<=hydraNum; ihydra= ihydra+1) { 
#        printf("  %d", hydra[ihydra])
#    }
#    printf("\n")
#	printf("Next hydra file paths:   ")
#	get_hydra_AllFilePaths
#	printf("Next hydra file names:   ")
#	get_hydra_AllFileNames
#	printf("Next hydra file formats:   ")
#	get_hydra_AllFileNameFormats
#	printf("Next hydra file numbers: ")
#	get_hydra_AllFileNumbers

#	set_hydra_AutoStoreYes
#	#set_ge_AutoStoreNo
#	set_hydra_MultiDetSW
##	set_hydra_MultiDetEdge
##	set_hydra_MultiDetPulse
##	set_hydra_RadMode
#	set_hydra_NumberOfImagesPerDetTrig 1
#	set_hydra_BufferSize 290  # for GE3 GE4 and GE1 computers
#	#  for GE2 only 250, so do not need to do anything here

#    # setting up the NF detector
#    use_ad_retiga "QIMAGE1:cam1:" "QIMAGE1:TIFF1:"
#	OSC["detDelay"]=0.0
#	p  "Next Retiga file name:", detget_imgprefix
#	p  "Next Reatiga file number:", detget_seqNumber

#	OSC["detector"]="NFFF"
#    
#    parfile="balogh_march14_NFFF.par"
#    fastparfile="fastpar_balogh_march14_NFFF.par"

#    #sxparfile="fastpar_balogh_march14_SX.par"

#	# setting up the osc
#    balogh_march14_set_Ehutch
#    #balogh_march14_set_Chutch
#    #set_hydra_aero
#    #set_hydra_prrot
#    set_combined_prrot  # TODO set_combined_aero
#    #FrameSignalPV=DetPulsePV
#    FrameSignalPV=ReadoutPV # NF is the master

#    #FS_GE2SE_control
#    NFDet_select
#    FS_Retiga_control
#    
#    # Only for test purposes
#    # Comment out
#    osc_threshold = -1

#    # epics_put("1ide:m5.CNEN", "Enable") # Enabling the Torque on PulseRay prrot motor
#    sleep(EPICS_DELAY)
#    sync
#    printOscGlobals
#}' # combined setup


#def balogh_march14_Retiga '{
#    ## Suter feb13, aero/hexFly PSO based, Retiga in E-hutch
#    
#    use_ad_retiga "QIMAGE1:cam1:" "QIMAGE1:TIFF1:"
#	OSC["detDelay"]=0.0
#	p  "Next file name:", detget_imgprefix
#	p  "Next file number:", detget_seqNumber
#    parfile="balogh_march14_NF.par"
#    fastparfile="fastpar_balogh_march14_NF.par"
#    #qdo ./write_parfile_general.mac
#    #qdo write_parfile_Retiga.mac
#    #def write_parfile_fast \'write_parfile_fast_Bhutch \'
#    #def write_parfile_fast \'write_parfile_fast_Ehutch \'
#	#def _write_line \'_write_GE2_line\'

#    # Only for test purposes
#    # Comment out
#    osc_threshold = -1
#    #parfile="./test.par"

#	# setting up the osc
#    # balogh_march14_set_Ehutch
#    balogh_march14_set_Chutch
#    set_Retiga_aero
#    #set_Retiga_Ehutch_prrot
#    
#    FrameSignalPV=ReadoutPV

#    #DEFAULT_GAP_TIME=0.04

#    NFDet_select
#    FS_Retiga_control
#    
#    #epics_put("1ide:m5.CNEN", "Enable") # Enabling the Torque on PulseRay prrot motor
#    sleep(EPICS_DELAY)
#    sync
#    printOscGlobals
#}'

#def balogh_march14_Tomo '{
#    ## Suter feb13, aero/hexFly PSO based, Retiga in E-hutch
#    ## Suter Apr13 Tomo with QTEST and old Retiga
#    
##    use_ad_retiga "QTEST:cam1:" "QTEST:TIFF1:"
#    use_ad_retiga "QIMAGE1:cam1:" "QIMAGE1:TIFF1:" # This is for Aszu from AD NEW8
##    use_ad_retiga "QIMAGE1:cam1:" "QIMAGE1:TIFF1:"  # This is for Malbec

#	OSC["detDelay"]=0.0
#	p  "Next file name:", detget_imgprefix
#	p  "Next file number:", detget_seqNumber
#    parfile="balogh_march14_Tomo.par"
#    fastparfile="fastpar_balogh_march14_Tomo.par"
#    #qdo ./write_parfile_general.mac
#    #qdo write_parfile_Retiga.mac
#    #def write_parfile_fast \'write_parfile_fast_Bhutch \'
#    #def write_parfile_fast \'write_parfile_fast_Ehutch \'
#	#def _write_line \'_write_GE2_line\'

#    # Only for test purposes
#    # Comment out
#    osc_threshold = -1
#    #parfile="./test.par"

## NO OSC, NO fastsweep, ONLY for TOMO
#	# setting up the osc
#    #balogh_march14_set_Ehutch
#    balogh_march14_set_Chutch
#    set_Tomo_Ehutch_aero
#    #set_Tomo_Ehutch_prrot
#    FrameSignalPV=ReadoutPV

#    #DEFAULT_GAP_TIME=0.04

#    TomoDet_select
#    #NFDet_select
#    FS_Retiga_control
#    #epics_put("1ide:m5.CNEN", "Enable") # Enabling the Torque on PulseRay prrot motor
#    sleep(EPICS_DELAY)
#    sync
#    printOscGlobals
#}'

#def printvar '{
#    p "$1 =", $1 
#}'

#def printOscGlobals '{
#    p ""
#    printvar Mon_ScalerPV
#    printvar MonICName 
#    printvar TransmICName
#    printvar MonCount_ArrayPV 
#    printvar TransmCount_ArrayPV
#    printvar EMonICName 
#    printvar ETransmICName
#    printvar EMonCount_ArrayPV
#    printvar ETransmCount_ArrayPV

#    printvar DetPulsePV
#    printvar ReadoutPV
#    printvar SEXGEPV
#    printvar GATE_signalPV
#    printvar ScalerTrigPV 
#    printvar ScalerTrigDetPulsePV
#    printvar FPGAPV
#    printvar PSOPV
#    printvar DetRdyPV
#    printvar idFPGAPV
#    printvar DetPulseToADPV
#    printvar FrameCounterPV
#    printvar FrameCounterTriggerPV   
#    printvar DetPulsePV
#    printvar TimeStampPV
#    printvar TimeStampArrayPV
#    printvar FrameSignalPV
#    p ""
#    printvar parfile
#    printvar fastparfile
#    printvar osc_threshold
#    printvar EPICS_DELAY
#    printvar DEFAULT_GAP_TIME 
#    printvar GapAdjustmentTicks
#    printvar DecodingRate
#    printvar ShouldRotateBack
#    printvar DataDirectory
#    printvar FileSizeCheck    
#    
#    printvar hydraNum
#    printvar hydra
#    p ""
#    
#    printvar ALERTLIST
#    p ""
#}'

## /home/beams/SPECADM/1id_macros/HEDM/sweep_det.mac
##def use_ge_new '{
##        ccdhook_adge $*
##        OSC["detector"]="GE_NEW"
### PK - Correction is here
###        if($#==1) CCDPV="$1"
##        if($#==1) ADFILEPV=CCDPV="$1"
##        else  ADFILEPV=CCDPV=getsval("detector PV prefix","GE2:cam1:")
##        
##        def det_trig \'_adtrig_xtime\'
##        def det_wait \'_adwait\'
##        def detget_imgprefix \'detget_imgprefix_ad\'
##        def detget_seqNumber \'detget_seqNumber_ad\'
##        def detabort \'detabort_ad_ge\'
##        def ccdset_expNum_ad \'ccdset_expNum_ad_ge\'
##        OSC["detDelay"] = 0.5
##        OSC["cushion_time"]=0.0
##        printf("Detector related macros are re-defined to %s\n",OSC["detector"])
##}'

##def detabort_ad_ge '{
##    p "Aborting the GE detector..."
##    epics_put(sprintf("%sAcquire", CCDPV), "Done");
##    while(epics_get(sprintf("%sAcquire", CCDPV))!="Done") {
##        sleep(0.02)
##    }
##    p "DONE"
##    epics_put(sprintf("1iddth1:DTH:resetLogicBO", CCDPV), 1);
##    sleep(2.0)
##    p "FPGA trigger module is reset."
##    
##}'

##def ccdset_expNum_ad_ge '{
##    # Usage: $0 numframes
##    local imnum
##    imnum=($1)
##	epics_put(sprintf("%sNumImages",CCDPV), imnum)
##	sleep(0.2)    
##}'


##def set_ge_AutoStoreYes '{
##    local ihydra
##    for (ihydra=1 ; ihydra<=4; ihydra= ihydra+1) { 
##		epics_put(sprintf("%sAutoStore",CCDPV), "YES")
##	}
##    sleep(0.2)
##	p CCDPV, "detector in SAVE mode"
##}'

##def set_ge_AutoStoreNo '{
##    local ihydra
##    for (ihydra=1 ; ihydra<=4; ihydra= ihydra+1) { 
##		epics_put(sprintf("%sAutoStore",CCDPV), "NO")
##	}
##    sleep(0.2)
##	p CCDPV, "detector in NOSAVE mode"
##}'

##def set_ge_UserSingle '{
##    epics_put(sprintf("%sTriggerMode",CCDPV), "USER SINGLE")
##    sleep(0.2)
##	p CCDPV, "detector in USER SINGLE mode"
##}'


