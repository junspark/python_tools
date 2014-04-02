import epics as ep

import datetime as dt

import APSpy.AD_1id as AD1id
import APSpy.fpga_1id as fpga1id

def CheckBeam(OSC, MonitorCounts):           # chk_beam_osc
    ### CHECK THIS
    #if(S[osc_MON]/COUNT_TIME >osc_threshold) {
    #if(S[osc_MON]/OSC["exposure_time"]>osc_threshold) {

	# This can overflow for fastsweep in case of the long integration time
    #if(S[osc_MON]/S[sec]>osc_threshold) {
    
    nFrames = OSC['nFrames']
    ADFilePV = OSC['ADFilePV']
    SweepMode = OSC['SweepMode']
    FirstFrameNumber = OSC['FirstFrameNumber']
    BeamUpWaitTime = OSC['BeamUpWaitTime']
    
    if ( MonitorCounts[0] > OSC['OscThreshold'] ) and ( MonitorCounts[nFrames - 2] > OSC['OscThreshold'] ):
        print 'beam was good'
        return
    else:
        pvname = ADFilePV + 'AutoSave'
        pvvalue = ep.caget(pvname)
        if pvvalue is 'Yes':
            ### CHECK THIS
            if SweepMode is 'sweep':
                print 'need to implement this'
                print 'ccdset_seqnum (ccdget_SeqNumber-1) # Step back by one file, if we are in AutoSave mode'
                return
            elif SweepMode is 'fastsweep':
                print 'need to implement this'
                print 'ccdset_seqnum (OSC["first_frame_number"]) # Step back to the beginning of the scan, if we are in AutoSave mode'
            spec.sleep(0.2)
            ## CHECK THIS
            print 'reset file number to ccdget_SeqNumber' # + str(ccdget_SeqNumber)

        if mac1id.IsBeamOn(MinSRCurrent=20, CheckMode=2) is 0:
            DownTime = datetime.datetime.now()

            while mac1id.IsBeamOn(MinSRCurrent=20, CheckMode=2) is 0:
                DeltaTime = datetime.datetime.now() - DownTime
                print 'beam down for ' + DeltaTime.total_seconds() + ' s'
                spec.sleep(1)

            BackTime = datetime.datetime.now()
            DeltaTime = BackTime - DownTime
            print 'we have beam after ' + DeltaTime.total_seconds() + ' s'

            if BeamUpWaitTime > 0:
                print 'we wait for ' + str(BeamUpWaitTime) + ' s before resuming'
                spec.sleep(BeamUpWaitTime)
                print 'we waited for ' + str(BeamUpWaitTime) + ' s before resuming'

            print 'we resume data acquisition'
    return

def Oscillation(OscillationMode = None, OSC = None, MtrName = None, StartPos = None, EndPos = None, ScanTime = None):
    if OscillationMode is None:
        print 'OscillationMode missing'
        print '0: _oscill_fastsweep'
        print '1: standard oscillation for omega and phi'
        OscillationMode = raw_input('Enter oscillation mode: ')
        OscillationMode = int(OscillationMode)
        
    if OscillationMode == 0:    # _oscill_fastsweep
        ### CHECK THIS
        # global moncnt trcnt Emoncnt Etrcnt
        # global MonCount_ArrayPV TransmCount_ArrayPV Mon_ScalerPV

        Range = EndPos - StartPos
        StartPosBuffered = StartPos - OSC['AccelerationRange']
        EndPosBuffered = EndPos + OSC['AccelerationRange']

        ### CHECK THIS
        #added checkbeam feature

        ### CHECK THIS FOR LOOP
        # for(;;) {  
        SetICCounters(OSC)          # setup_ICcounters OSC["nframes"]

        # moncnt[]=0.0; trcnt[]=0.0; # Resets the arrays
        moncnt=[]; 
        trcnt=[];
        # Emoncnt[]=0.0; Etrcnt[]=0.0; # Resets the E-monitor arrays
        Emoncnt=[]
        Etrcnt=[]

        # cntticks[]=0.0 # Resets the IC interation time counter array
        cntticks=[]

        # timestamp[]=0.0 # Resets the timestamps
        timestamp=[]

        ### CHECK THIS
        DisableGate(OSC)                # disableGATE
        if MtrName is 'aero':
            # Moving to start and initializing the FlyScan
            ArmAero(PsoPV = None, StartPos = None, EndPos = None)
        else:
            SpecMtrName = 'spec.' + MtrName
            spec.mv(SpecMtrName, StartPos, wait=True)

        ### CHECK THIS
        EnableGate(OSC)        # enableGATE

        # Workarounds for the SW trigger Retiga
        if OSC['detector'] is 'Retiga':
            ### CHECK THIS
            SetupDetPulseToAD()     # The Det_pulse goes to Acromag and to AD "Start" button 
            SetupTimeStampArray(OSC)
            
        ### CHECK THIS
        SetupFrameCounter()         # setup_FrameCounter OSC["nframes"] # Counts the triggers to Retiga and stops DetPulseToAD when the frame number reached
        SetupFrameCounterTrigger(OSC)        # setup_FrameCounterTrigger

        # In case of Aerotech the FlyScan adjusts the speeds
        if OSC['motor'] is not 'aero':
            ### CHECK THIS
            OscSetPars(OSC)             # changes the motor speeds (base and velocity)
        elif OSC['motor'] is 'prrot':
            pvname = '1ide:m5.BVEL'
            pvvalue = OSC['speed_equ_per_sec']
            ep.caput(pvname, pvvalue, wait=True)

        ### CHECK THIS
        # arm_scalers;   # this does nothing since preicH is not configured to any scalers 

        ArmICCounters(OSC)

        ### CHECK THIS
        # arm_detector;  # this makes the detector ready for the GATE signal
        ArmDetector(OSC)
        spec.sleep(OSC['EpicsDelay'])

        # Moving the motor
        if MtrName is 'preciH':
            SpecMtrName = 'spec.' + MtrName
            spec.mv(SpecMtrName, EndPos, wait=True)
        elif MtrName is 'prrot':
            SpecMtrName = 'spec.' + MtrName
            spec.mv(SpecMtrName, EndPos, wait=True)
        elif MtrName is 'aero':
            # epics_put(sprintf("%sfly",PSOPV), "Fly") # No callback on thi sbutton
            pvname = PSOPV + 'fly'
            pvvalue = 'Fly'
        else:
            SpecMtrName = 'spec.' + MtrName
            spec.mv(SpecMtrName, EndPos, wait=True)    

    if OscillationMode == 1:
        Range = EndPos - StartPos
        ### CHECK THIS
        StartPosBuffered = StartPos - OSC['AccelerationRange']
        EndPosBuffered = EndPos + OSC['AccelerationRange']

        SpecMtrName = 'spec.' + MtrName
        if MtrName is 'ome':
            spec.mv(SpecMtrName, StartPos - 0.1, wait=True)

        ### CHECK THIS
        # for(;;)
        spec.mv(SpecMtrName, StartPos - 0.1, wait=True)

        ### CHECK THIS
        OscSetPars(OSC)

        ### CHECK THIS
        #to fix scaler hanging problem, dont know why the scaler behave like that
        ResetScalers(OSC)
        
        ### CHECK THIS
        ArmScalers(OSC)

        ### CHECK THIS
        print 'need to find det_trig'
        # det_trig OSC["exposure_time"]+OSC["extra_time"]+OSC["cushion_time"]

        spec.sleep(OSC['DetDelay'])   #synch shutter and detector

        spec.count_em(OSC['ExpTime']+OSC['ExtraTime'])

        spec.mv(SpecMtrName, EndPosBuffered, wait=True)
        
        ### CHECK THIS
        # det_wait
        # waitmove
        # waitcount
        # get_counts
        CheckBeamOsc(OSC, MonitorCounts)
        ### CHECK THE FOR LOOP
        
        OscResetPars(OSC)
    return

def Sweep(OSC = None, MtrName = None, StartPos = None, EndPos = None, NumSteps = None, ExpTime = None):   
    '''
    sweep from sweep_core_mod.mac
    '''
    # OSC['ImagePrefix'] 
    #OSC["imgprefix"] = detget_imgprefix

    IsSweepScan = OSC['IsSweepScan']

    ### CHECK THIS
    #shutter_sweep
    Step = (EndPos - StartPos) / NumSteps

    if NumSteps == 0:
        NumSteps = 1

    ### CHECK THIS
    #_stamp[0]=0
    #_ctime = 0;
    #_stype=1|(1<<8)

    OscCalc(OSC = None, MtrName = None, Range = None, ExpTime = None)
    ### CHECK THIS
    # cdef("cleanup_once","\nsweep_cleanup;","sweep","0x20")

    SoftIOCStartScan(OSC, ScanType = 0)     # softioc_startscan sweep  $1 _first _last

    ### CHECK THIS
    # HEADING = sprintf("sweep %s %g %g %g %g","$1",$2,$3,$4,$5)
    # X_L = motor_mne($1)
    # Y_L = cnt_name(DET)
    # _sx = _first; _fx = _last

    ### CHECK THIS    
    # sweep_fprnt_label

    ### CHECK THIS
    # scan_head
    print '------This is before pre sweep -----------------'

    ### CHECK THIS
    # user defined hooks (beampos etc)
    # user_pre_sweep

    ### CHECK THIS
    #def _scan_on \'
    #    {
    #    p " other _scan_on:: sec 1 "
    #    p "_snum: " _snum " NPTS " NPTS
    #        for (; NPTS < _snum; NPTS++) {
    #            _start = _first+NPTS*_step;
    #            _stop  = _first+(NPTS+1)*_step;

    #           p " start stop " _start  _stop;
    #                _oscill $1 _start _stop _time
    #           p " user_mid_sweep " _start _stop;                
    #           user_mid_sweep
    #           p " sweep print value " _start _stop
    #           sweep_fprnt_value
    #           p " before scan loop " _start _stop
    #           scan_loop
    #           scan_data(NPTS, _start)
    #           scan_plot
    #           }
    #        }
    #	    scan_tail
    #	\'
    #    _scan_on
    #            p "frankie is here after scan_on "

    ### CHECK THIS
    # sweep_cleanup
    SweepCleanUp()
    return  

def SuperSweep(OSC, MtrOut=None, StartOut=None, EndOut=None, NumStepOut=None, MtrIn=None, MtrInType = None, StartIn=None, EndIn=None, NumStepIn=None, ExpTime=None):
    ### CHECK THIS
    #if (($# != 9) && (OSC["detector"]!="bruker")) {
    #p "Usage: supersweep [motorOUT] [start1] [end1] [steps] [motorIN] [start2] [end2] [steps] [seconds] "
    #exit
    #}
    #if (($# != 10) && (OSC["detector"]=="bruker")) {
    #p "Usage: supersweep [motor1] [start1] [end1] [steps] [motor2] [start2] [end2] [steps] [secconds] [brukerbase] "
    #exit
    #}
    # local _step _first _last _snum _time i jj _first1 _last1 _snum1 _step1 v1
    #if($#==10) {
    #     OSC["imgprefix"] = BRUKERFILE["base"]="$10"
    #} else {

    #     OSC["imgprefix"] =detget_imgprefix
    #}

    OSC['IsSweepScan'] = 1

    ### CHECK THIS
    # shutter_sweep

    StartOut                    #_first1=$2
    EndOut                      #_last1 = $3
    NumStepOut = NumStepOut + 1             #_snum1 = _n1=int(($4)+1)
    StepSizeOut = ( EndOut - StartOut ) / NumStepOut        # _step1 = (_last1-_first1)/($4)

    StartIn                     # _first=$6
    EndIn                       # _last=$7
    NumStepIn                   # _snum=_n2=$8
    ExpTime                     # _time=$9
    StepSizeIn = ( EndIn - StartIn ) / NumStepIn            # _step=(_last-_first)/_snum

    ### CHECK THIS
    # _stype= 1|8|(2<<8)
    # _ctime = 0;

    OscCalc(OSC = None, MtrName = MtrIn, Range = StepSizeIn, ExpTime = ExpTime) # osc_calc $5 _step _time

    ### CHECK THIS
    # cdef("cleanup_once","\nsweep_cleanup;","sweep","0x20")

    ### CHECK THIS
    SoftIOCStartScan(OSC, ScanType = None)      # softioc_startscan supersweep $1 _first1 _last1

    ### CHECK THIS
    # HEADING = sprintf("supersweep %s %g %g %g %s %g %g %g %g","$1",$2,$3,$4,"$5",$6,$7,$8,$9)

    ### CHECK THIS
    #X_L = motor_mne($1)
    #Y_L = cnt_name(DET)

    #_sx = $2; _fx = $3

    ### CHECK THIS
    # sweep_fprnt_label

    ### CHECK THIS
    #FPRNT = sprintf("%s  %s","$1",FPRNT);
    #PPRNT = sprintf("%s %s","$1",PPRNT);
    #VPRNT = PPRNT;

    ### CHECK THIS
    # scan_head

    ### CHECK THIS
    #def _scan_on \'
    # {
    #    for(i=0;i<_snum1;i++) {
    #          p " _scan_on:: sec 1 "
    #           v1 =  _first1+i*_step1;   
    #           if("$1" == "table") {
    #               A[M1V]=v1;A[M2V]=v1;A[M3V]=v1;
    #           } else {
    #               A[$1]= v1;
    #           }
    #           p " _scan_on:: sec 2 "
    #           scan_move;
    #           p " _scan_on:: sec3 "
    #           for (jj=0; jj < _snum; jj++) {
    #             _start = _first+jj*_step;
    #             _stop  = _first+(jj+1)*_step;
    #             _oscill $5 _start _stop _time 
    #    		 sweep_fprnt_value  v1
    #             FPRNT = sprintf("%.8g %s",v1,FPRNT);
    #             PPRNT = sprintf("%9.4f %s",v1,PPRNT);
    #             VPRNT = PPRNT;
    #	         scan_loop
    #    		 scan_data(NPTS, A[$1])
    #    		 scan_plot
    #             NPTS++;
    #             
    #          }
    #          p " _scan_on:: sec 4  "
    #   }
    # }
    #scan_tail
    #\'
    
    ### CHECK THIS
    # _scan_on

    SweepCleanUp()
    return

### CHECK THIS    
#cdef("Fheader","\n sweep_header;\n","sweep","0x20");

def SweepCleanUp():                     # sweep_cleanup
    import APSpy.macros_1id as mac1id 
    print '=============sweep_cleanup is started'
    OSC['IsSweepScan'] = 0
    
    print 'before reset parts'
    OscResetPars(OSC)

    print "before reset up scalars "
    ResetScalers(OSC)

    print 'before reset up softioc'
    ResetSoftIOC(OSC)

    ### CHECK THIS
    mac1id.shutter_manual()             # shutter_manual
    return

##--------------------------internal macros used by oscill-----------------------

def ResetSoftIOC(OSC):         # reset_softioc
    if OSC['UseSoftIOC']:
        pvname = OSC['SoftIOCPV'] + 'Busy'
        t = 0
        
        ### CHECK THIS
        while ep.caget(pvname) == 1 and t < 30:
            spec.sleep(0.5)
            t = t + 1

        pvname = OSC['SoftIOCPV'] + 'Busy'
        pvvalue = 0
        ep.caput(pvname, pvvalue, wait=True)

        pvname = OSC['SoftIOCPV'] + 'Status'
        pvvalue = 'Idle'
        ep.caput(pvname, pvvalue, wait=True)

        pvname = OSC['SoftIOCPV'] + 'scantype'
        pvvalue = ''
        ep.caput(pvname, pvvalue, wait=True)
    return

def SoftIOCStartScan(OSC, ScanType = None):     # softioc_startscan
    if ScanType is None:
        print '0: sweep'
        ScanType = raw_input('Enter scan type: ')
        ScanType = int(ScanType)
        
    if OSC['UseSoftIOC']:
        SoftIOCPV = OSC['SoftIOCPV']
        
        pvname = SoftIOCPV + 'scantype'
        if ScanType == 0:
            pvvalue = 'sweep'

        ep.caput(pvname, pvvalue, wait=True)

        pvname = SoftIOCPV + 'motor'
        pvvalue = OSC['MotorName']
        ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%smotor",SOFTIOC_PV),OSC["motor"])

        pvname = SoftIOCPV + 'detname'
        pvvalue = OSC['Detector']
        ep.caput(pvname, pvvale, wait=True)         # epics_put(sprintf("%sdetname",SOFTIOC_PV),OSC["detector"])

        ### CHECK THIS
        #if($#== 4) {
        # epics_put(sprintf("%smotor",SOFTIOC_PV),motor_name($2))
        # epics_put(sprintf("%sstart0",SOFTIOC_PV),$3)
        # epics_put(sprintf("%send0",SOFTIOC_PV),$4) 
        #}

        pvname = SoftIOCPV + 'imgprefix'
        pvvalue = OSC['ImagePrefix']
        ep.caput(pvname, pvvale, wait=True)         # epics_put(sprintf("%simgprefix",SOFTIOC_PV),OSC["imgprefix"])

        ### CHECK THIS
        pvname = SoftIOCPV + 'scann'
        pvvalue = SCAN_N+1
        # ep.caput(pvname, pvvale, wait=True)         # epics_put(sprintf("%sscann",SOFTIOC_PV),SCAN_N+1)

        ### CHECK THIS
        pvname = SoftIOCPV + 'totalPts'
        # pvvalue = (_stype&8? _n1*_n2:_n1)
        # ep.caput(pvname, pvvale, wait=True)         # epics_put(sprintf("%stotalPts",SOFTIOC_PV),(_stype&8? _n1*_n2:_n1))

        pvname = SoftIOCPV + 'NPTS'
        pvvalue = -1
        ep.caput(pvname, pvvale, wait=True)             # epics_put(sprintf("%sNPTS",SOFTIOC_PV),-1);

        pvname = SoftIOCPV + 'Busy'
        pvvalue = 0
        ep.caput(pvname, pvvale, wait=True)             # epics_put(sprintf("%sBusy",SOFTIOC_PV),0)

        pvname = SoftIOCPV + 'Status'
        pvvalue = 'Scanning'
        ep.caput(pvname, pvvale, wait=True)             # epics_put(sprintf("%sStatus",SOFTIOC_PV),"Scanning")        
    return

def OscResetPars(OSC):                         # osc_reset_pars
    ### CHECK THIS
    print 'this needs to be implemented correctly'
    MtrName = 'spec.' + OSC['MotorName']
    mtr_pv = spec.mtrDB[MtrName].mtr_pv
    # motor_par(OSC["motor"],"base_rate",OSC["normal_base"])
    # mtor_par(OSC["motor"],"velocity",OSC["normal_speed"])
    return
    
def OscSetPars(OSC):                        # osc_set_pars
    MtrName = 'spec.' + OSC['MotorName']
    mtr_pv = spec.mtrDB[MtrName].mtr_pv
    
    steps_per_rev = mtr_pv.get('SREV')
    Speed = OSC['Speed'] / steps_per_rev
    
    mtr_pv.put('SBAS', 0.0, wait=True)     # Change motor base_speed
    mtr_pv.put('S', OSC['Speed'], wait=True)      # Change motor speed
    return

def OscCalc(OSC = None, MtrName = None, Range = None, ExpTime = None):      # osc_calc
    Threshold = OSC['ShutterCloseDelay'] - OSC['ShutterOpenDelay']
    if ExpTime < Threshold:
        print 'min exposure time is ' + Threshold + ' s.'
        return

    MtrName = 'spec.' + OSC['MotorName']
    mtr_pv = spec.mtrDB[MtrName].mtr_pv
    
    # tmp = speed of the motor in steps/sec from EPICS MaxSpeed and MotorResolution on Debug screen
    tmp = abs( mtr_pv.get('VMAX') / mtr_pv.get('MRES') )
    
    if tmp == 0:
        print 'Max speed of motor ' + MtrName + ' is not configured, use normal speed as max speed.'
        ## CHECK THIS
        tmp = mtr_pv.get('SBAS')        # tmp =  motor_par($1,"velocity")

    OSC['MaxSpeed'] = int(tmp)
    OSC['NormalAccelerationTime'] = mtr_pv.get('ACCL')
    OSC['NormaBaseSpeed'] = mtr_pv.get('BVEL')
    OSC['NormalSpeed'] = mtr_pv.get('BVEL')             # OSC["normal_speed"]=motor_par($1,"velocity")  # in steps/sec

    ### CHECK THIS
    # Workaround for the MTS motor:
    if OSC['MotorName'] is not 'preciH':
        OSC['NormalAccelerationTime'] = 0.0

    # step_size is given in steps/deg from Epics .SREV/.UREV
    OSC['StepSize'] = abs( mtr_pv.get('SREV') )     # OSC["step_size"]=fabs(motor_par($1,"step_size"))    # fabs needed for negative mot resolution
    OSC['Range'] = Range        # For fastsweep this is the full sweep range
    OSC['ExpTime'] = ExpTime    # For fastsweep this is the full sweep time, called "scantime" = GATE up through GATE down

    Steps = abs( OSC['Range'] * OSC['StepSize'] )
    OSC['Steps'] = Steps
    
    #The motor speed calculation is good if there is gap_time between frames !
    #E.g. range = 180 deg, exp_time = scantime, scantime=numframe*(singleexp_time+gap_time) ==> speed = range*step_size / scantime
    #calculate motor parameters
    Speed = steps / ExpTime  # in steps/sec

    if Speed > OSC['MaxSpeed']:
        print 'desired speed larger than max speed of the motor'
        return

    if ( Speed < (OSC['NormaBaseSpeed'] / 10) ) or ( Speed < 1 ):
        print 'desired speed too slow and may miss steps'

    OSC['Speed'] = Speed
    OSC['SpeedEGUperSec'] = Speed / OSC['StepSize']     # in deg/sec or mm/sec

    if Speed < abs( OSC['NormalBase'] ):
        OSC['Base'] = Speed
    else:
        OSC['Base'] = OSC['NormaBaseSpeed']

    OSC['AccelerationTime'] = OSC['NormalAccelerationTime']

    # calculate ramp parameters
    OSC['OpenSteps'] = int( abs( OSC['ShutterOpenDelay'] * OSC['Speed'] ) )
    OSC['CloseSteps'] = int( abs( OSC['ShutterCloseDelay'] * OSC['Speed'] ) )

    if OSC['Base'] == OSC['Speed']:
        OSC['AccelerationSteps'] = OSC['OpenSteps'] + 1
        OSC['ExtraTime'] = 2 * OSC['AccelerationTime']
    else:
        OSC['AccelerationSteps'] = abs( ( OSC['Speed'] + OSC['Base'] ) / 2 ) * OSC['AccelerationTime'] + OSC['OpenSteps']
        OSC['ExtraTime'] = 2 * ( OSC['AccelerationTime'] + OSC['ShutterOpenDelay'] )

    OSC['AccelerationRange'] = OSC['Range'] / abs( OSC['Range'] ) * OSC['AccelerationSteps'] / abs( OSC['StepSize'] )

    OSC['Scaler1'] = OSC['AccelerationSteps'] - OSC['OpenSteps']
    OSC['Scaler2'] = OSC['AccelerationSteps'] + abs( OSC['Steps'] - OSC['CloseSteps'] )

    print 'desired speed of motor : ' + OSC['Speed']
    print 'motor base speed of motor : ' + OSC['Base']

def SetScaler(MtrName = None):               # osc_scaler_set
    #if ($#!=3) {
    #  p "Usage: osc_scaler_set motor s1_pv s2_pv"
    #  exit
    #}
    aname = 'OSC_SCALER_' + MtrName

    ### CHECK THIS
    #global @aname[]
    #@aname["s1"] = "$2" 
    #@aname["s2"] =  "$3"
    return

def ArmScalers(OSC):        # THIS IS arm_scalers
    ### CHECK THIS
    print 'this needs to be implemented correctly'
    MtrName = OSC['motor']
    aname = 'OSC_SCALER_' + MtrName
    return
#def arm_scalers '{
#    local aname s1 s2
#    aname = sprintf("OSC_SCALER_%s",OSC["motor"])
#    if(whatis(aname)&0x1000000) {
#      s1 = @aname["s1"]  
#      s2 = @aname["s2"]
#      epics_put(sprintf("%s.PR1",s1),OSC["scaler1"])
#      epics_put(sprintf("%s.PR1",s2),OSC["scaler2"])
#      epics_put(sprintf("%s.CNT",s1),1)
#      sleep(0.1)
#      epics_put(sprintf("%s.CNT",s2),1)
#    } else {
#      #printf("Pulse from motor %s is not configured to control the scaler",OSC["motor"])
#      #exit
#    }
#}'

def ResetScalers(OSC):         # THIS IS reset_scalers
    ### CHECK THIS
    print 'this needs to be implemented correctly'
    MtrName = OSC['motor']
    aname = 'OSC_SCALER_' + MtrName
    return
#def reset_scalers '{
#   aname = sprintf("OSC_SCALER_%s",OSC["motor"])
#   if(whatis(aname)&0x1000000) {
#     aname = sprintf("OSC_SCALER_%s",OSC["motor"])
#     s1=@aname["s1"]
#     s2=@aname["s2"]
#     epics_put(sprintf("%s.CNT",s1),0)
#     epics_put(sprintf("%s.CNT",s2),0)
#     #epics_put("1idc:scaler3.CNT",0)
#     #epics_put("1idc:scaler4.CNT",0)
#  } 
#}'

##-------------------initialize  hardware settings of 1id ----------------------------
## CHECK THIS
# osc_scaler_set phi 1idc:scaler1 1idc:scaler2
# osc_scaler_set ome 1idc:scaler3 1idc:scaler4

# def _oscill \'_oscill_sweep\'
# def user_pre_sweep ''
# def user_mid_sweep ''
# def returnNull() '{return("NULL")}'

## define empty macros if they are not defined
#if(!(whatis("det_trig")&&0x0010)) {
#   rdef det_trig ''
#   rdef det_wait ''
#   rdef detget_imgprefix'returnNull()'
#   rdef detget_seqNumber 'returnNull()'
#}
#if(unset("CCDPV")) {
#OSC["detector"]="none"
#CCDPV="dummyPV"
#}

#parfile ="/tmp/sweep_par"
#rdef write_parfile(detname,imgnr,imgprefix,motname,startpos,endpos) '{
#}'

###########################################################################
# OSC FASTSWEEP FPGA HYDRA MACROS FROM
# osc_fastsweep_FPGA_hydra.mac
###########################################################################  
def OscillSweep():      # _oscill_sweep
    '''
    _oscill_sweep
    '''
    print 'implement please'
    return
### preci sweep calculated from preciH but moves the preciS
#### THIS IS NOT WORKING YET !!! TODO Must be tested
#def _oscill_sweep '{
#    if($#!=4) {
#        p "Usage: $0 motor start finish time"
#        exit
#    }
#    local start end range
#    range = ($3)-($2)
#    start = ($2)-OSC["arange"]
#    end = ($3) +OSC["arange"]
#    #added checkbeam feature 
#    for(;;) {  
#        mv $1 start
#        waitmove;
#        osc_set_pars;  # changes the motor speeds
#        arm_scalers;   # this does nothing since preicH is not configured to any scalers 
#        # p "after _sweep arm_scalers"
#        # Added all the times even which are typically zeros
#        #p "det_trig", OSC["exposure_time"]+OSC["extra_time"]+OSC["cushion_time"]
#        det_trig OSC["exposure_time"]+OSC["extra_time"]+OSC["cushion_time"]
#        sleep(OSC["detDelay"])   #synch shutter and detector
#        count_em OSC["exposure_time"]+OSC["extra_time"]+OSC["cushion_time"]
#        # Moving the motor
#        if ("$1" == "preciH") {
#            mv preciS end
#        } else {
#            if ("$1" == "prrot") {
#                mv prrotS end
#            } else {
#                if ("$1" == "aero") {
#                    p "Flying with aero stage"
#                    epics_put(sprintf("%sfly",PSOPV), "Fly") # No callback on this button
#                } else {
#                    mv $1 end
#                }
#            }
#        }
#        det_wait 
#        waitmove
#        waitcount
#        get_counts
#        chk_beam_osc
#    }
#    osc_reset_pars
#}'
  
def SetRetiga(OSC, OpMode = None):           # set_Retiga & set_Retiga_Ehutch & set_Retiga_Ehutch_aero & set_Retiga_Ehutch_prrot & set_Tomo_Ehutch_aero & set_Tomo_Ehutch_prrot
    if OpMode is None:
        print 'Operation mode missing'
        print '0: set_Retiga'
        print '1: set_Retiga_Ehutch_prrot'
        print '2: set_Retiga_Ehutch'
        print '3: set_Retiga_Ehutch_aero'
        print '4: set_Tomo_Ehutch_aero'
        print '5: set_Tomo_Ehutch_prrot'
        OpMode = raw_input('Operation mode: ')
        OpMode = int(OpMode)
    
    if OpMode == 0:   # set_Retiga from osc_fastsweep_FPGA_hydra.mac
        '''
        set_Retiga from osc_fastsweep_FPGA_hydra.mac
        Good for precitech B_hutch posdriven
        '''
        OSC['DetectorArmMode'] = 1      # rdef arm_detector \'arm_detector_HWtriggerRetiga_PosDriven_preci\'
        OSC['DetectorDisarmMode'] = 0   # rdef disarm_detector \'disarm_detector_HWtriggerRetiga\'
        
        OSC['TimeStampPV'] = 'QIMAGE:image1:TimeStamp_RBV'
        OSC['TimeStampArrayPV'] = '1id:userArrayCalc5'
        OSC['DefaultGapTime'] = 0.003   # For Position driven HW trig
        OSC['GapAdjustmentTicks'] = 1   # for position driven 4000DC, 1ms gap_time
        
    elif OpMode == 1:   # set_Retiga_Ehutch_prrot from osc_fastsweep_FPGA_hydra.mac
        '''
        set_Retiga_Ehutch_prrot from osc_fastsweep_FPGA_hydra.mac
        Good for prrot/FPGA E-hutch
        Sets up the Near-field detector
        '''
        OSC['DetectorArmMode'] = 0      # rdef arm_detector \'arm_detector_HWtriggerRetiga_PosDriven_prrot\'
        OSC['DetectorDisarmMode'] = 0   # rdef disarm_detector \'disarm_detector_HWtriggerRetiga\'

        OSC['TimeStampPV'] = 'QIMAGE:image1:TimeStamp_RBV'
        OSC['TimeStampArrayPV'] = '1ide:userArrayCalc5'
        OSC['DefaultGapTime'] = 0.005
        OSC['GapAdjustmentTicks'] = 0   # for prrot/FPGA
        
        OSC['DecodingRate'] = 1
        
    elif OpMode == 2:    # set_Retiga_Ehutch from osc_fastsweep_FPGA_hydra.mac
        '''
        set_Retiga_Ehutch from osc_fastsweep_FPGA_hydra.mac
        Good for prrot E-hutch time-based det_pulses and fake GATE
        '''
        OSC['DetectorArmMode'] = 7          # rdef arm_detector \'arm_detector_HWtriggerRetiga\'
        OSC['DetectorDisarmMode'] = 0       # rdef disarm_detector \'disarm_detector_HWtriggerRetiga\'

        OSC['TimeStampPV'] = 'QIMAGE:image1:TimeStamp_RBV'
        OSC['TimeStampArrayPV'] = '1id:userArrayCalc5'
        OSC['DefaultGapTime'] = 0.05
        OSC['GapAdjustmentTicks'] = 5000  # prrot 0 180 180 1 sec
        
    elif OpMode == 3:   # set_Retiga_Ehutch_aero from osc_fastsweep_FPGA_hydra.mac
        '''
        set_Retiga_Ehutch_aero from osc_fastsweep_FPGA_hydra.mac
        Good for aero/hexFly E-hutch PSO based det_pulses 
        Sets up the Near-field detector
        '''
        OSC['DetectorArmMode'] = 2      # rdef arm_detector \'arm_detector_HWtriggerRetiga_aeroPSOFly\'
        OSC['DetectorDisarmMode'] = 0   # rdef disarm_detector \'disarm_detector_HWtriggerRetiga\'

        OSC['TimeStampPV'] = 'QIMAGE:image1:TimeStamp_RBV'
        OSC['TimeStampArrayPV'] = '1ide:userArrayCalc5'
        OSC['DefaultGapTime'] = 0.002
        OSC['GapAdjustmentTicks'] = 0   # for aero/hexFly

    elif OpMode == 4:   # set_Tomo_Ehutch_aero from osc_fastsweep_FPGA_hydra.mac
        '''
        set_Tomo_Ehutch_aero  from osc_fastsweep_FPGA_hydra.mac
        Good for aero/hexFly E-hutch PSO based det_pulses
        Sets up the Near-field detector
        '''
        OSC['DetectorArmMode'] = 2      # rdef arm_detector \'arm_detector_HWtriggerRetiga_aeroPSOFly\'
        OSC['DetectorDisarmMode'] = 0   # rdef disarm_detector \'disarm_detector_HWtriggerRetiga\'

        OSC['TimeStampPV'] = 'QIMAGE:image1:TimeStamp_RBV'
        OSC['TimeStampArrayPV'] = '1ide:userArrayCalc5'
        OSC['DefaultGapTime'] = 0.001
        OSC['GapAdjustmentTicks'] = 0  # for aero/hexFly

    elif OpMode == 5:   # set_Tomo_Ehutch_prrot from osc_fastsweep_FPGA_hydra.mac
        '''
        set_Tomo_Ehutch_prrot from osc_fastsweep_FPGA_hydra.mac
        Good for prrot/FPGA E-hutch
        Sets up the Near-field detector
        '''
        OSC['DetectorArmMode'] = 0      # rdef arm_detector \'arm_detector_HWtriggerRetiga_PosDriven_prrot\'
        OSC['DetectorDisarmMode'] = 0   # rdef disarm_detector \'disarm_detector_HWtriggerRetiga\'

        OSC['TimeStampPV'] = 'QIMAGE:image1:TimeStamp_RBV'
        OSC['TimeStampArrayPV'] = '1ide:userArrayCalc5'
        OSC['DefaultGapTime'] = 0.001
        OSC['GapAdjustmentTicks'] = 0  # for aero/hexFly
    return OSC

def SetHydra(OSC, OpMode = None):  # set_GE & set_hydra_aero & set_hydra_prrot from osc_fastsweep_FPGA_hydra.mac
    if OpMode is None:
        print 'Operation mode missing'
        print '0: set_GE -  OBSOLETE'   # GE detector with prrot
        print '1: set_hydra_aero'       # GE detector(s) with AeroTech stage, only short trigger pulses
        print '2: set_hydra_prrot'      # GE detector(s) with Pulseray stage, full DetPulse from FPGA
        OpMode = raw_input('Operation mode: ')
        OpMode = int(OpMode)

    if OpMode == 0:         # set_GE from osc_fastsweep_FPGA_hydra.mac
        '''
        set_GE from osc_fastsweep_FPGA_hydra.mac
        THIS IS OBSOLETE
        
        rdef arm_detector \'arm_detector_HWtriggerGE_PosDriven\'
        rdef disarm_detector \'disarm_detector_HWtriggerGE\'
        OSC['DefaultGapTime'] = 0.150
        GapAdjustmentTicks = 5200 # 0 180 180 frames 0.5 sec
        GapAdjustmentTicks = 1 # Position driven
        '''
        print 'This mode is OBSOLETE'
        
    elif OpMode == 1:       # set_hydra_aero from osc_fastsweep_FPGA_hydra.mac
        '''
        set_hydra_aero from osc_fastsweep_FPGA_hydra.mac
        GE detector(s) with AeroTech stage, only short trigger pulses
        '''
        OSC['DetectorArmMode'] = 4      # rdef arm_detector \'arm_detector_HWtriggerGE_FlyScan_Aero_hydra\'
        OSC['DetectorDisarmMode'] = 2   # rdef disarm_detector \'disarm_detector_HWtriggerGE_hydra\'

        OSC['DefaultGapTime'] = 0.150
        OSC['GapAdjustmentTicks'] = 0   # Aero FlyScan --> This is not used
        
    elif OpMode == 2:       # set_hydra_prrot from osc_fastsweep_FPGA_hydra.mac
        '''
        set_hydra_prrot from osc_fastsweep_FPGA_hydra.mac
        GE detector(s) with Pulseray stage, full DetPulse from FPGA
        '''
        OSC['DetectorArmMode'] = 8      # rdef arm_detector \'arm_detector_HWtriggerGE_prrot_hydra_Renishaw\'
        OSC['DetectorDisarmMode'] = 2   # rdef disarm_detector \'disarm_detector_HWtriggerGE_hydra\'
        
        OSC['DefaultGapTime'] = 0.150
        OSC['GapAdjustmentTicks'] = 0   # Position driven
        OSC['DecodingRate'] = 1         # For prrot FPGA    
    return OSC

### TODO - FIGURE OUT HOW THIS FITS IN WITH THE APSPY
def Set_PUP_AFRL_Measurements(hutch=None):      # PUP_AFRL_Aug13_set_Ehutch
    '''
    PUP_AFRL_Aug13_set_Ehutch
    Prototype macro for aero/PSOFly, PSO based FPGA
    '''
    OSC['MonCountArrayPV']='1ide:userArrayCalc1'
    OSC['TransmCountArrayPV']='1ide:userArrayCalc2'
    OSC['MonScalerPV']='1ide:S2:scaler2'
    
    OSC['MonICName']='_cts2.B' # standard IC in E, after the DS slit, before the sample 
    OSC['TransmICName'] = '_cts2.A' # pin diode after the sample    

    # Energy monitoring
    OSC['EMonCountArrayPV']='1ide:userArrayCalc3'
    OSC['ETransmCountArrayPV']='1ide:userArrayCalc4'

    OSC['EMonICName']='_cts4.A' # before the E-calib foil in B 
    OSC['ETransmICName']='_cts4.B' # after the E-calib foil in B
    
    ## Integration time counter
    OSC['IntegerTicksArrayPV']="1ide:userArrayCalc6"
    OSC['IntegerICName'] = "_calc1.VAL" # At the calc fields: A= 1ide:3820:scaler2_calc1.VAL

    OSC['DetPulsePV']='1id:9440:1:bi_0'
    SetupAcromag(OSC, SignalID = 3)

    OSC['ReadoutPV']= '1id:9440:1:bi_1'                 # Retiga Readout for counting the frames
    OSC['SingleExposureGEPV'] = '1id:9440:1:bi_2'       # GE Single EXposure for counting the frames

    SetupAcromag(OSC, SignalID = 2)
    SetupAcromag(OSC, SignalID = 1)

    OSC['GateSignalPV'] = '1id:9440:1:bi_3'
    SetupAcromag(OSC, SignalID = 0)
    
    # Acromag at 1id
    OSC['ScalerTrigDetPulsePV'] = '1ide:sg:FO21_BI'     # Gives the trigger signal to the ScalerTrigPV
    OSC['ScalerTrigPV'] = '1ide:userCalcOut2'
    OSC['DetPulseToADPV'] = '1id:userStringCalc4'
    
    OSC['FrameSignalPV'] = OSC['DetPulsePV']            # This is only the default, it is set later correctly in the detector related macros
    OSC['FrameCounterPV'] = '1id:userTran10'            # The triggered FrameCounter record
    OSC['FrameCounterTriggerPV'] = '1id:userCalcOut2'   # The userCalOut record that triggers the framecounter

    OSC['FpgaPV'] = '1ide:sg:'
    OSC['PsoPV'] = '1ide:PSOFly1:'
    OSC['DetReadyPV'] = '1id:softGlue:DFF-2_OUT_BI' # For waiting when the hydra is ready for work

    OSC['IdFpgaPV']='1id:softGlue:'
    SetupDTHDetRdyFPGA(OSC)
    
    return OSC

def FastSweep(OSC, MtrName=None, StartPos=None, EndPos=None, nFrames=None, ExpTime=None, UserGapTime=None, UserDelayTime=None):
    '''
    FastSweep
    Usage: fastsweep motor start end nframes exp_time
    '''
    ## TODO - IF INPUT INVALID GO DIRECTLY TO fastsweep_end
    # if ($# != 5) {
    #     p "Usage: $0 motor start end nframes exp_time"
    #     fastsweep_end
    #     exit
    # }
    
    if MtrName is None:
        MtrName = raw_input('Enter motor name: ')
        # TODO - CHECK IF MOTOR EXISTS IN MOTOR DB
        
    if StartPos is None:
        StartPos = raw_input('Enter start position: ')
        StartPos = float(StartPos)

    if EndPos is None:
        EndPos = raw_input('Enter end position: ')
        EndPos = float(EndPos)

    if nFrames is None:
        nFrames = raw_input('Enter number of frames: ')
        nFrames = int(nFrames)

    if ExpTime is None:
        ExpTime = raw_input('Enter exposure time: ')
        ExpTime = float(ExpTime)

    if (MtrName is 'prrot') and (StartPos >= EndPos):
        print 'THE prrot CAN BE USED ONLY IN POSITIVE DIRECTION'
        return
    
    OSC['SweepMode'] = 'FastSweep'                                      # OSC["sweep_mode"] = "fastsweep"
    OSC['FirstFrameNumber'] = AD1id.GetFileNumber(OSC['DetList'])       # OSC["first_frame_number"] = detget_seqNumber
    
    fpga1id.FS_SweepControl()               # FS_Sweep_control
    
    ## TODO - IF MULTIPLE DET IN DETLIST, THIS NEEDS TO BE CHANGED
    print 'First frame of the fastsweep scan: ' + str(OSC['FirstFrameNumber'][0])
    
    OSC['OscillationMode'] = 0      # this chooses _oscill_fastsweep in Oscillation
    
    ## CHECK THIS
    # cdef("cleanup_once", "\n fastsweep_cleanup;", "sweep_fastsweep", "0x20")

    
    # The exp time must be corrected according to the gaps between frames
    if UserGapTime is not None:
        OSC['GapTime'] = UserGapTime                # users can change this value
    if UserDelayTime is not None:
        OSC['DelayTime'] = UserDelayTime            # users can change this value

    # Update OSC['ScanTime']
    OSC['ScanTime']= (  ExpTime + OSC['GapTime'] ) * nFrames

    print 'Sweep ' + MtrName + ' ' + str(StartPos) + ' ' + str(EndPos) + ' 1 ' + str( OSC['ScanTime'] )
    Sweep(OSC, MtrName, StartPos, EndPos, NumSteps = 1, OSC['ScanTime'])

    ## TODO FILE I/O CHECK
    
    FastSweepEnd(OSC)
    return

def FastSweepParamCheck(OSC):       # fastsweep_paramcheck
    '''
    Checks the FastSweep parameters
    '''
    
    OSC['IdealExpSteps'] = OSC['ExpTime'] * OSC['Speed'] / OSC['DecodingRate']  # OSC["Ideal_Exp_steps"]=OSC["exposure_time"]*OSC["speed"]/DecodingRate
    OSC['IdealGapSteps'] = OSC['GapTime'] * OSC['Speed'] / OSC['DecodingRate'] + OSC['GapAdjustmentTicks']  # OSC["Ideal_Gap_steps"]=OSC["gap_time"]*OSC["speed"]/DecodingRate + GapAdjustmentTicks

    OSC['AppliedExpSteps'] = int( OSC['IdealExpSteps'] )    # OSC["Applied_Exp_steps"]=int(OSC["Ideal_Exp_steps"])
    OSC['AppliedGapSteps'] = int( OSC['IdealGapSteps'] )    # OSC["Applied_Gap_steps"]=int(OSC["Ideal_Gap_steps"])

    OSC['DetTrigSteps'] = OSC['nFrames'] * ( OSC['AppliedExpSteps'] + OSC['AppliedGapSteps'] )      # OSC["Dettrig_steps"]=OSC["nframes"]*(OSC["Applied_Exp_steps"]+OSC["Applied_Gap_steps"])

    OSC['LostSteps'] = int( OSC['Steps'] / OSC['DecodingRate'] - OSC['DetTrigSteps'] )      # OSC["Lost_steps"]=int(OSC["steps"]/DecodingRate)-OSC["Dettrig_steps"]
    OSC['LostPosition'] = OSC['LostSteps'] * OSC['DecodingRate'] / OSC['StepSize']          # OSC["Lost_pos"]=OSC["Lost_steps"]*DecodingRate/OSC["step_size"]

    OSC['SuggestedGap'] = OSC['Steps'] / OSC['DecodingRate'] / OSC['nFrames'] - OSC['AppliedExpSteps'] - OSC['AppliedGapSteps']     #OSC["Suggest_Gap"]= (OSC["steps"]/DecodingRate/OSC["nframes"]-OSC["Applied_Exp_steps"]-OSC["Applied_Gap_steps"])
    OSC['SuggestedMinimumGapTime'] = 2 / OSC['Speed'] * OSC['DecodingRate']                 # OSC["Suggest_MinGapTime"]= 2/OSC["speed"]*DecodingRate

    print '---- Sweep summary -----------------------'
    print 'All steps are in encoder units: ' + str(OSC['DecodingRate']) + ' x EPICS motor steps'
    print 'Acceleration range/steps/time:  ' + str(OSC['AccelerationRange']) + 'egu /' + str(OSC['AccelerationSteps'] / OSC['DecodingRate']) + 'steps /' + str(OSC['AccelerationTime']), 'sec'
    print 'Sweep range/steps/time:         ', OSC['Range'], 'egu /',  OSC['Steps']/OSC['DecodingRate'], 'steps /', OSC['ScanTime'], 'sec'
    print 'Full motion range/steps:        ', OSC['Range'] + 2*OSC['AccelerationRange'], 'deg /',  (OSC['Steps']+2*OSC['AccelerationSteps'])/OSC['DecodingRate'], 'steps'
    print 'DEFAULT_GAP_TIME/GapAdjustmentTicks: ', OSC['DefaultGapTime'], '/', OSC['GapAdjustmentTicks']
    print 'Ideal/applied Exp steps:        ', OSC['IdealExpSteps'], '/', OSC['AppliedExpSteps'] 
    print 'Ideal/applied Gap steps:        ', OSC['IdealGapSteps'], '/', OSC['AppliedGapSteps']
    print 'Number of frames:               ', OSC['nFrames']
    print 'Rotation speed:                 ', OSC['SpeedEGUperSec'], 'egu/sec =', OSC['Speed']/OSC['DecodingRate'], 'steps/sec' 
    print 'Resolution:                     ', OSC['StepSize']/OSC['DecodingRate'], 'steps/egu'
    print 'Exposure/Gap/Sweep steps:       ', OSC['AppliedExpSteps'], '/', OSC['AppliedGapSteps'], ' /', OSC['Steps'] / OSC['DecodingRate']
    print 'Exposure/Gap/Sweep time:        ', OSC['ExpTime'], 'sec /', OSC['GapTime'], 'sec /', OSC['Steps'], 'sec'
    print 'Exposure/Gap/Sweep range:       ', OSC['AppliedExpSteps']*OSC['DecodingRate']/OSC['StepSize'], 'egu /', OSC['AppliedGapSteps']*OSC['DecodingRate']/OSC['StepSize'], 'egu /', OSC['Range'], 'egu'
    print '------------------------------------------'
    print 'Lost steps overall/per-frame:    ', OSC['LostSteps'], 'steps /', OSC['LostSteps']/OSC['nFrames'], 'steps' 
    print 'Lost position overall/per-frame: ', OSC['LostPosition'], 'egu /', OSC['LostPosition']/OSC['nFrames'], 'egu' 
    print '------------------------------------------'

    BoolWarning = 0
    if (OSC['GapAdjustmentTicks'] < 0):
        print 'WARNING: GapAdjustmentTicks is less than zero.'
        print 'You have to increase the GapAdjustmentTicks.'
        BoolWarning = 1

    OSC['DetList']
    if (OSC['DetList'] is GE) and (OSC['DefaultGapTime'] < 0.140):
        print 'WARNING: DEFAULT_GAP_TIME is too small.'
        print 'You have to increase the DEFAULT_GAP_TIME.'
        BoolWarning = 1

    if (OSC['DetList'] is Retiga) and (OSC['DefaultGapTime'] < 0.001):
        print 'WARNING: DEFAULT_GAP_TIME is too small.'
        print 'You have to increase the DEFAULT_GAP_TIME.'
        print 'Suggestion for min DEFAULT_GAP_TIME: ' + str( OSC['SuggestedMinimumGapTime'] )
        BoolWarning = 1

    if OSC['AppliedGapSteps'] < 2:
        print 'WARNING: The gap is too short for triggering the detector.'
        print 'You can increase the GapAdjustmentTicks or the DEFAULT_GAP_TIME.'
        print 'Suggestion for min DEFAULT_GAP_TIME: ' + str( OSC['SuggestedMinimumGapTime'] )
        BoolWarning = 1

    if (OSC['DetList'] is Retiga) and (OSC['LostSteps'] / OSC['Speed'] * OSC['DecodingRate'] > 0.2):
        print 'WARNING: The Lost steps are too big (>readout). There will be at least one more frame at the end of the sweep.'
        print 'You can increase the GapAdjustmentTicks.'
        print 'Suggestion for GapAdjustmentTicks: ' + str( OSC['SuggestedGap'] )
        BoolWarning = 1

    if OSC['LostSteps'] < 0:
        print 'WARNING: The Lost steps are negative. The last frame(s) will be chopped.'
        print 'You may want to decrease the GapAdjustmentTicks or increase the DEFAULT_GAP_TIME.'
        BoolWarning = 1

    if abs( OSC['LostSteps'] ) > ( OSC['AppliedExpSteps'] / 2): 
        print 'WARNING: The Lost position is too big (> frame/2). You will have inaccurate frame positions.'
        print 'You may want to increase the GapAdjustmentTicks.'
        print 'Suggestion for GapAdjustmentTicks: ' + str( OSC['SuggestedGap'] )
        BoolWarning = 1

    if ( OSC['MotorName'] is 'prrot' ) and ( OSC['SpeedEGUperSec'] < 0.1 ):
        print 'WARNING: The speed is too low. The motion may be non-even.'
        print 'You can decrease the exposure time.'
        BoolWarning = 1

    if BoolWarning is 0:
        print 'No Warning.'
        
    print '------------------------------------------'

    if (OSC['ParamCheck'] is 1) or (ParamWarning is 1):
        print 'End of parameter checking. Exiting.'
        FastSweepCleanUp(OSC)
        sys.exit()
    return

def PreSweep(OSC, ExpTime, nFrames):   # user_pre_sweep from sweep
    '''
    user_pre_sweep from sweep
    Set up exposure time and number of frames for sweep
    '''
    OSC['ExpTime'] = ExpTime
    OSC['nFrames'] = nFrames
    
    OSC['ExtraTime'] = 0
    return OSC
    
def FastSweepEnd(OSC):     # fastsweep_end
    '''
    fastsweep_end
    This is runs when the scan finishes correctly - undefines the fastsweep macros
    '''
    print 'FastSweepEnd started'
    
    OSC['SweepMode'] = 'Sweep'
    hydra1id.Wait(OSC['DetList'])           # det_wait # for GE mostly

    det = OSC['DetList'][0]
    if det.detectortype is 'Retiga':
        fpga1id.FS_RetigaControl
    elif det.detectortype is 'GE':
        fpga1id.FS_GE2SEControl

    return OSC
    
def FastSweepCleanup(OSC):                          # fastsweep_cleanup
    '''
    fastsweep_cleanup
    Runs when Ctrl+C a fastsweep scan
    '''
    print 'FastSweepCleanup started'

    AD1id.Abort(OSC['DetList'])
    
    if OSC['MotorName'] is 'Aero':
        pvname = OSC['PsoPV'] + 'fly'
        pvvalue = 'Done'
        ep.caput(pvname, pvvalue, wait=True)        # Stop the hexFly

        pvname = '1ide:m9.STOP'
        pvvalue = 1
        ep.caput(pvname, pvvalue, wait=True)        # Stop the motor
        
        pvname = '1ide:sg:AND-1_IN2_Signal'
        pvvalue = 0
        ep.caput(pvname, pvvalue, wait=True)        # Disable_pulses_FPGA
        spec.sleep(0.1)
        
        pvname = '1ide:sg:BUFFER-1_IN_Signal.PROC'
        pvvalue = 1
        ep.caput(pvname, pvvalue, wait=True)        # clear GATE state
        spec.sleep(0.1)
        
        pvname = '1ide:userCalcOut4.B'
        pvvalue = 0
        ep.caput(pvname, pvvalue, wait=True)        # Disable FakeGATE stop
        spec.sleep(0.1)
    
    AD1id.DisarmDetector(OSC)                       # disarm_detector
    counters1id.DisarmICCounters(OSC)               # disarm_ICcounters 
    
    FastSweepEnd(OSC)
    return OSC

##########################################################################################
# Setup FUNCTIONS
##########################################################################################
def SetGapAdjustmentTicks(OSC):
    FPGAType = OSC['FpgaType']
    if FPGAType == 0:   # TIME DRV FPGA
        OSC['GapAdjustmentTicks'] = 170
        OSC['DecodingRate'] = None
    elif FPGAType == 1: # POSITION DRV FPGA
        OSC['GapAdjustmentTicks'] = 1
        
        # DecodingRate=2 # 1x, 2x, 4x typically
        # For B-hutch, Precitech 4x decoder for the controller and 2x decoder for the FPGA ticks
        # So this value is 2, because the number of steps reported by EPICS is twice as large as the number of ticks arrives to the FPGA
        OSC['DecodingRate'] = 2
    return OSC
    
def SetupFrameCounter(OSC):            # setup_FrameCounter
    '''
    setup_FrameCounter
    Sets up the DetPulseCounter userTransform for stopping the DetPulseToAD when the "nframes" are reached

    ##
    epics_put(sprintf("%s.DESC", FrameCounterPV), "FrameCounter"); # Name
    epics_put(sprintf("%s.SCAN", FrameCounterPV), "Passive"); # Mode

    epics_put(sprintf("%s.INPA", FrameCounterPV), ""); # clear
    epics_put(sprintf("%s.INPB", FrameCounterPV), ""); # clear
    epics_put(sprintf("%s.INPC", FrameCounterPV), ""); # clear
    epics_put(sprintf("%s.INPD", FrameCounterPV), ""); # clear
    epics_put(sprintf("%s.INPE", FrameCounterPV), ""); # clear

    # The order is important
    epics_put(sprintf("%s.CMTA", FrameCounterPV), "a nframes"); # Number of frames
    epics_put(sprintf("%s.A", FrameCounterPV), $1); # Just for logging the starting number
    epics_put(sprintf("%s.CLCA", FrameCounterPV), ""); # clear

    epics_put(sprintf("%s.CMTB", FrameCounterPV), "b counter"); # Counter
    epics_put(sprintf("%s.CLCB", FrameCounterPV), "C?(B-1):B"); # Counting down
    epics_put(sprintf("%s.B", FrameCounterPV), 0); # Just for Initializing 

    epics_put(sprintf("%s.CMTC", FrameCounterPV), "c enable"); # Enables the counter
    epics_put(sprintf("%s.C", FrameCounterPV), 0); # Disabled now, if switched to enable immediately counts down by one
    epics_put(sprintf("%s.CLCC", FrameCounterPV), ""); # clear

    epics_put(sprintf("%s.CMTD", FrameCounterPV), "d disbl DetP_AD"); # Enab/Disables the DetPulseToAD signals
    epics_put(sprintf("%s.D", FrameCounterPV), 0); # Enab/Disables the DetPulseToAD signals
    epics_put(sprintf("%s.CLCD", FrameCounterPV), "(B<=0)?0:1"); # If the detector triggering should be stopped
    
    epics_put(sprintf("%s.COPT", FrameCounterPV), "Conditional");
    epics_put(sprintf("%s.OUTB", FrameCounterPV), sprintf("%s.B NPP NMS", FrameCounterPV));
    epics_put(sprintf("%s.OUTD", FrameCounterPV), sprintf("%s.C NPP NMS", DetPulseToADPV));

    # Setting the good number
    epics_put(sprintf("%s.B", FrameCounterPV), ($1)+1); # nframes+1 because of enabling with C
    '''    
    # Setting up the triggering tool
    pvname = OSC['FrameCounterPV'] + '.DESC'
    pvvalue = 'FrameCounter'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.DESC", FrameCounterPV), "FrameCounter"); # Name
    
    pvname = OSC['FrameCounterPV'] + '.SCAN'
    pvvalue = 'Passive'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.SCAN", FrameCounterPV), "Passive"); # Mode

    pvname = OSC['FrameCounterPV'] + '.INPA'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPA", FrameCounterPV), ""); # clear
    
    pvname = OSC['FrameCounterPV'] + '.INPB'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPB", FrameCounterPV), ""); # clear
    
    pvname = OSC['FrameCounterPV'] + '.INPC'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPC", FrameCounterPV), ""); # clear
    
    pvname = OSC['FrameCounterPV'] + '.INPD'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPD", FrameCounterPV), ""); # clear
    
    pvname = OSC['FrameCounterPV'] + '.INPE'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPE", FrameCounterPV), ""); # clear

    # The order is important
    pvname = OSC['FrameCounterPV'] + '.CMTA'
    pvvalue = 'a nframes'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.CMTA", FrameCounterPV), "a nframes"); # Number of frames
    
    pvname = OSC['FrameCounterPV'] + '.A'
    pvvalue = OSC['nFrames']
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.A", FrameCounterPV), $1); # Just for logging the starting number
    
    pvname = OSC['FrameCounterPV'] + '.CLCA'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.CLCA", FrameCounterPV), ""); # clear
    
    pvname = OSC['FrameCounterPV'] + '.CMTB'
    pvvalue = 'b counter'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.CMTB", FrameCounterPV), "b counter"); # Counter

    pvname = OSC['FrameCounterPV'] + '.CLCB'
    pvvalue = 'C?(B-1):B'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.CLCB", FrameCounterPV), "C?(B-1):B"); # Counting down
    
    pvname = OSC['FrameCounterPV'] + '.B'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.B", FrameCounterPV), 0); # Just for Initializing 

    pvname = OSC['FrameCounterPV'] + '.CMTC'
    pvvalue = 'c enable'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.CMTC", FrameCounterPV), "c enable"); # Enables the counter
    
    pvname = OSC['FrameCounterPV'] + '.C'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.C", FrameCounterPV), 0); # Disabled now, if switched to enable immediately counts down by one
    
    pvname = OSC['FrameCounterPV'] + '.CLCC'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.CLCC", FrameCounterPV), ""); # clear

    pvname = OSC['FrameCounterPV'] + '.CMTD'
    pvvalue = 'd disbl DetP_AD'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.CMTD", FrameCounterPV), "d disbl DetP_AD"); # Enab/Disables the DetPulseToAD signals
    
    pvname = OSC['FrameCounterPV'] + '.D'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.D", FrameCounterPV), 0); # Enab/Disables the DetPulseToAD signals
    
    pvname = OSC['FrameCounterPV'] + '.CLCD'
    pvvalue = '(B<=0)?0:1'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.CLCD", FrameCounterPV), "(B<=0)?0:1"); # If the detector triggering should be stopped
    
    pvname = OSC['FrameCounterPV'] + '.COPT'
    pvvalue = 'Conditional'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.COPT", FrameCounterPV), "Conditional");
    
    pvname = OSC['FrameCounterPV'] + '.OUTB'
    pvvalue = OSC['FrameCounterPV'] + '.B NPP NMS'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.OUTB", FrameCounterPV), sprintf("%s.B NPP NMS", FrameCounterPV));
    
    pvname = OSC['FrameCounterPV'] + '.OUTD'
    pvvalue =  OSC['DetPulseToADPV'] + '.C NPP NMS'
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.OUTD", FrameCounterPV), sprintf("%s.C NPP NMS", DetPulseToADPV));

    # Setting the good number
    pvname = OSC['FrameCounterPV'] + '.B'
    pvvalue = OSC['nFrames'] + 1
    ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.B", FrameCounterPV), ($1)+1); # nframes+1 because of enabling with C
    return

def SetupFrameCounterTrigger(OSC):         # setup_FrameCounterTrigger
    '''
    setup_FrameCounterTrigger
    Setting up the userCalc to keep pressing the PROC button on the DetPulseCounter when the DetPulsePV.VAL changes from 0 to 1
    '''
    
    pvname = OSC['FrameCounterTriggerPV'] + '.DESC'
    pvvalue = 'FrameCounterTrigger'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.DESC", FrameCounterTriggerPV), "FrameCounterTrigger"); 
    
    pvname = OSC['FrameCounterTriggerPV'] + '.SCAN'
    pvvalue = 'Passive'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.SCAN", FrameCounterTriggerPV), "Passive"); # Mode
    
    pvname = OSC['FrameCounterTriggerPV'] + '.A'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.A", FrameCounterTriggerPV), 0); # Initial value, 0
    
    pvname = OSC['FrameCounterTriggerPV'] + '.B'
    pvvalue = 0 
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.B", FrameCounterTriggerPV), 0); # Initial value, Disable
    
    pvname = OSC['FrameCounterTriggerPV'] + '.INPA'
    pvvalue = OSC['FrameSignalPV'] + '.VAL CP NMS'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.INPA", FrameCounterTriggerPV), sprintf("%s.VAL CP NMS", FrameSignalPV)); # Input PV with Det_pulses
    
    pvname = OSC['FrameCounterTriggerPV'] + '.OOPT'
    pvvalue = 'Transition To Non-zero'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.OOPT", FrameCounterTriggerPV), "Transition To Non-zero");
    
    pvname = OSC['FrameCounterTriggerPV'] + '.DOPT'
    pvvalue = 'Use OCAL'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.DOPT", FrameCounterTriggerPV), "Use OCAL");
    
    pvname = OSC['FrameCounterTriggerPV'] + '.CALC'
    pvvalue = 'A==1'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.CALC", FrameCounterTriggerPV), "A==1"); 
    
    pvname = OSC['FrameCounterTriggerPV'] + '.OCAL'
    pvvalue = '1'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.OCAL", FrameCounterTriggerPV), "1"); 
    
    pvname = OSC['FrameCounterTriggerPV'] + '.OUT'
    pvvalue = OSC['FrameCounterPV'] + '.PROC PP NMS'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.OUT", FrameCounterTriggerPV), sprintf("%s.PROC PP NMS", FrameCounterPV));
    return

def SetupTimeStampArray(OSC):           # setup_TimeStampArray
    '''
    setup_TimeStampArray
    Timestamps saving into an array

    ###
    epics_put(sprintf("%s.DESC", TimeStampArrayPV), "TimeStamps");
    epics_put(sprintf("%s.NUSE", TimeStampArrayPV), array_NUSE);
    epics_put(sprintf("%s.SCAN", TimeStampArrayPV), "Passive");
    epics_put(sprintf("%s.INPA", TimeStampArrayPV), ""); # clear
    epics_put(sprintf("%s.INPB", TimeStampArrayPV), ""); # clear
    epics_put(sprintf("%s.INPC", TimeStampArrayPV), ""); # clear
    epics_put(sprintf("%s.A", TimeStampArrayPV), OSC["nfames"]); # Number of frames
    epics_put(sprintf("%s.B", TimeStampArrayPV), 0); # clear
    epics_put(sprintf("%s.C", TimeStampArrayPV), 0); # Disabled
    epics_put(sprintf("%s.INAA", TimeStampArrayPV), sprintf("%s CP NMS", TimeStampPV)); # Input array
    epics_put(sprintf("%s.INBB", TimeStampArrayPV), ""); # Storage array
    epics_put(sprintf("%s.BB", TimeStampArrayPV), 0); # Reset
    epics_put(sprintf("%s.CALC", TimeStampArrayPV), "C?(BB>>1)+AA:BB"); # The formula
    epics_put(sprintf("%s.ODLY", TimeStampArrayPV), 0.0); # Delay
    epics_put(sprintf("%s.OEVT", TimeStampArrayPV), 0); # Output Event
    epics_put(sprintf("%s.OOPT", TimeStampArrayPV), "Every Time"); # Processing
    epics_put(sprintf("%s.DOPT", TimeStampArrayPV), "Use CALC"); # Use CALC
    epics_put(sprintf("%s.OUT", TimeStampArrayPV), sprintf("%s.BB NPP NMS", TimeStampArrayPV)); # output PV
    epics_put(sprintf("%s.WAIT", TimeStampArrayPV), "NoWait"); # No waiting
    ''' 
    pvname = OSC['TimeStampArrayPV'] + '.DESC'
    pvvalue = 'TimeStamps'
    ep.caput(pvname, pvvalue, wait=True)        # epics_put(sprintf("%s.DESC", TimeStampArrayPV), "TimeStamps");
    
    pvname = OSC['TimeStampArrayPV'] + '.NUSE'
    pvvalue = OSC['NumArrayElements']
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.NUSE", TimeStampArrayPV), array_NUSE);
    
    pvname = OSC['TimeStampArrayPV'] + '.SCAN'
    pvvalue = 'Passive'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.SCAN", TimeStampArrayPV), "Passive");
    
    pvname = OSC['TimeStampArrayPV'] + '.INPA'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.INPA", TimeStampArrayPV), ""); # clear
    
    pvname = OSC['TimeStampArrayPV'] + '.INPB'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.INPB", TimeStampArrayPV), ""); # clear
    
    pvname = OSC['TimeStampArrayPV'] + '.INPC'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.INPC", TimeStampArrayPV), ""); # clear

    pvname = OSC['TimeStampArrayPV'] + '.A'
    pvvalue = OSC['nFrames']
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.A", TimeStampArrayPV), OSC["nfames"]); # Number of frames
        
    pvname = OSC['TimeStampArrayPV'] + '.B'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.B", TimeStampArrayPV), 0); # clear
    
    pvname = OSC['TimeStampArrayPV'] + '.C'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.C", TimeStampArrayPV), 0); # Disabled
    
    pvname = OSC['TimeStampArrayPV'] + '.INAA'
    pvvalue = TimeStampPV + ' CP NMS'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.INAA", TimeStampArrayPV), sprintf("%s CP NMS", TimeStampPV)); # Input array
    
    pvname = OSC['TimeStampArrayPV'] + '.INBB'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.INBB", TimeStampArrayPV), ""); # Storage array
    
    pvname = OSC['TimeStampArrayPV'] + '.BB'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.BB", TimeStampArrayPV), 0); # Reset
    
    pvname = OSC['TimeStampArrayPV'] + '.CALC'
    pvvalue = 'C?(BB>>1)+AA:BB'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.CALC", TimeStampArrayPV), "C?(BB>>1)+AA:BB"); # The formula
    
    pvname = OSC['TimeStampArrayPV'] + '.ODLY'
    pvvalue = 0.0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.ODLY", TimeStampArrayPV), 0.0); # Delay
    
    pvname = OSC['TimeStampArrayPV'] + '.OEVT'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.OEVT", TimeStampArrayPV), 0); # Output Event
    
    pvname = OSC['TimeStampArrayPV'] + '.OOPT'
    pvvalue = 'Every Time'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.OOPT", TimeStampArrayPV), "Every Time"); # Processing
    
    pvname = OSC['TimeStampArrayPV'] + '.DOPT'
    pvvalue = 'Use CALC'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.DOPT", TimeStampArrayPV), "Use CALC"); # Use CALC
    
    pvname = OSC['TimeStampArrayPV'] + '.OUT'
    pvvalue = OSC['TimeStampArrayPV'] + '.BB NPP NMS'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.OUT", TimeStampArrayPV), sprintf("%s.BB NPP NMS", TimeStampArrayPV)); # output PV
    
    pvname = OSC['TimeStampArrayPV'] + '.WAIT'
    pvvalue = NoWait
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.WAIT", TimeStampArrayPV), "NoWait"); # No waiting
    return

def SetupAcromag(OSC, SignalID = None)
    '''
    SetupAcromag
    SignalID
    print '0 : Gate'
    print '1 : GE Single Exposure '
    print '2 : Readout'
    print '3 : DetPulse'
    '''
    if SignalID is None:
        print 'Signal ID missing'
        print '0 : Gate'
        print '1 : GE Single Exposure '
        print '2 : Readout'
        print '3 : DetPulse'
        SignalID = raw_input('Signal ID : ')
        SignalID = int(SignalID)

    if SignalID is 0:       # setup_GATEsignalPV_Acromag : Setup Acromag for GATE signals, FPGA output to Acromag input
        GATE_signalPV  = OSC['GateSignalPV']           
        pvname = GATE_signalPV + '.DESC'
        pvvalue = 'GATEsignal'
        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.DESC", GATE_signalPV), "GATEsignal"); # Mode

        pvname = GATE_signalPV + '.SCAN'
        pvvalue = 'I/O Intr'
        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.SCAN", GATE_signalPV), "I/O Intr"); # Enable Acromag
        
    elif SignalID is 1:     # setup_SEXGEPV_Acromag : Setup Acromag for Single Exposure PV signals, GE output to Acromag input
        SEXGEPV = OSC['SingleExposureGEPV']
            
        pvname = SEXGEPV + '.DESC'
        pvvalue = 'SEX_GE'
        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.DESC", SEXGEPV), "SEX_GE"); # Mode

        pvname = SEXGEPV + '.SCAN'
        pvvalue = 'I/O Intr'
        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.SCAN", SEXGEPV), "I/O Intr"); # Enable Acromag
        
    elif SignalID is 2:     # setup_ReadoutPV_Acromag : Setup Acromag for READOUT signals, B-hutch, Retiga output to Acromag input
        ReadoutPV = OSC['ReadoutPV']
           
        pvname = ReadoutPV + '.DESC'
        pvvalue = 'Readout'
        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.DESC", ReadoutPV), "Readout"); # Mode

        pvname = ReadoutPV + '.SCAN'
        pvvalue = 'I/O Intr'
        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.SCAN", ReadoutPV), "I/O Intr"); # Enable Acromag
        
    elif SignalID is 3:     # setup_DetPulsePV_Acromag : Setup Acromag for Det_Pulse signals, FPGA det_pulses output to Acromag input
        DetPulsePV=OSC['DetPulsePV']
            
        pvname = DetPulsePV + '.DESC'
        pvvalue = 'det_pulses'
        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.DESC", DetPulsePV), "det_pulses"); # Mode

        pvname = DetPulsePV + '.SCAN'
        pvvalue = 'I/O Intr'
        ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.SCAN", DetPulsePV), "I/O Intr"); # Enable Acromag
    return

def SetupDTHDetRdyFPGA(OSC): # setup_DTHDetRdy_FPGA 
    '''
    setup_DTHDetRdy_FPGA
    Generating the latch circuit in the FPGA for sensing the DetRdy signal
    '''
    pvname = OSC['IdFpgaPV'] + 'FI4_Signal'
    pvvalue = 'DTHDetRdy'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sFI4_Signal", idFPGAPV), "DTHDetRdy"); # Mode

    pvname = OSC['IdFpgaPV'] + 'DFF-2_CLOCK_Signal'
    pvvalue = 'DTHDetRdy'                   
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDFF-2_CLOCK_Signal", idFPGAPV), "DTHDetRdy"); # CLOCK

    pvname = OSC['IdFpgaPV'] + 'DFF-2_SET_Signal'
    pvvalue = '1'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDFF-2_SET_Signal", idFPGAPV), 1); # SET

    pvname = OSC['IdFpgaPV'] + 'DFF-2_D_Signal'
    pvvlaue = 1
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDFF-2_D_Signal", idFPGAPV), 1); # DATA

    pvname = OSC['IdFpgaPV'] + 'DFF-2_CLEAR_Signal'
    pvvlaue = 'clrDetRdy'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sDFF-2_CLEAR_Signal", idFPGAPV), "clrDetRdy"); # DATA

    pvname = OSC['IdFpgaPV'] + 'BUFFER-4_OUT_Signal'
    pvvlaue = 'clrDetRdy'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-4_OUT_Signal", idFPGAPV), "clrDetRdy"); # BUF-out

    pvname = OSC['IdFpgaPV'] + 'BUFFER-4_IN_Signal'
    pvvlaue = '0!'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sBUFFER-4_IN_Signal", idFPGAPV), "0!"); # BUF-in
    return
