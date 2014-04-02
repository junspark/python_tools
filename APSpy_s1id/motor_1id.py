def ArmAero(OSC, StartPos = None, EndPos = None):      # FROM arm_aero IN _oscill_fastsweep
    '''
    FROM arm_aero IN _oscill_fastsweep
    '''
    PsoPV = OSC['PsoPV']

    # Disable_pulses_FPGA
    pvname = '1ide:sg:AND-1_IN2_Signal'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put("1ide:sg:AND-1_IN2_Signal", 0, CB_TIME)
    spec.sleep(OSC['EpicsDelay'])           # sleep(EPICS_DELAY)

    # clear GATE state
    pvname = '1ide:sg:BUFFER-1_IN_Signal.PROC'
    pvvalue = 1
    ep.caput(pvname, pvvalue, wait=True)    # epics_put("1ide:sg:BUFFER-1_IN_Signal.PROC", 1, CB_TIME)
    spec.sleep(OSC['EpicsDelay'])           # sleep(EPICS_DELAY)

    # set PSO
    pvname = PsoPV + 'startPos'
    pvvalue = StartPos
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sstartPos",PSOPV), $2, CB_TIME)
    
    pvname = PsoPV + 'endPos'
    pvvalue = EndPos
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sendPos",PSOPV), $3, CB_TIME)

    pvname = PsoPV + 'slewSpeed'
    pvvalue = OSC['SpeedEGUperSec']
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sslewSpeed",PSOPV), OSC["speed_equ_per_sec"], CB_TIME)
    
    pvname = PsoPV + 'scanDelta'
    pvvalue = abs( EndPos - StartPos ) / OSC['nFrames']
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sscanDelta",PSOPV), fabs(($3)-($2))/OSC["nframes"], CB_TIME)

    pvname = PsoPV + 'detSetupTime'
    pvvalue = OSC['GapTime']
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%sdetSetupTime",PSOPV), OSC["gap_time"], CB_TIME) # gap time in sec
    spec.sleep(OSC['EpicsDelay'])  # sleep(EPICS_DELAY)
   
    print 'Taxi start'
    pvname = PsoPV + 'taxi'
    pvvalue = 'Taxi'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%staxi",PSOPV), "Taxi", 400.0)  # This will wait (PSOFlyScan) while the taxi is finished, or time out after 400 sec    
    spec.sleep(OSC['EpicsDelay'])      # sleep(EPICS_DELAY)
    
    while ep.caget(pvname) is not 'Done':
        print 'waiting for aerotech taxi completion'
        spec.sleep(0.1)
    print 'Taxi end'

    # arm PSO
    # clear GATE state
    pvname = '1ide:sg:BUFFER-1_IN_Signal.PROC'
    pvvalue = 1
    ep.caput(pvname, pvvalue, wait=True)        # epics_put("1ide:sg:BUFFER-1_IN_Signal.PROC", 1, CB_TIME)
    spec.sleep(OSC['EpicsDelay'])               # sleep(EPICS_DELAY)

    # Enable_pulses_FPGA
    pvname = '1ide:sg:AND-1_IN2_Signal'
    pvvalue = 1
    ep.caput(pvname, pvvalue, wait=True)        # epics_put("1ide:sg:AND-1_IN2_Signal", 1, CB_TIME)
    spec.sleep(OSC['EpicsDelay'])               # sleep(EPICS_DELAY)

    # Enable FakeGATE stop
    pvname = '1ide:userCalcOut4.B'
    pvvalue = 1
    ep.caput(pvname, pvvalue, wait=True)        # epics_put("1ide:userCalcOut4.B", 1, CB_TIME)
    spec.sleep(OSC['EpicsDelay'])               # sleep(EPICS_DELAY)
    return
