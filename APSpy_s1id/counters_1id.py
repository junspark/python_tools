import epics as ep

def ArmICCounters(OSC):     # arm_ICcounters
    '''
    arm_ICcounters
    '''
    pvname = OSC['MonCountArrayPV'] + '.C'
    pvvalue = 1.0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.C", MonCount_ArrayPV), 1.0); # Enable
    
    pvname = OSC['TransmCountArrayPV'] + '.C'
    pvvalue = 1.0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.C", TransmCount_ArrayPV), 1.0); # Enable
    
    pvname = OSC['EMonCountArrayPV'] + '.C'
    pvvalue = 1.0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.C", EMonCount_ArrayPV), 1.0); # Enable
    
    pvname = OSC['ETransmCountArrayPV'] + '.C'
    pvvalue = 1.0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.C", ETransmCount_ArrayPV), 1.0); # Enable
    
    pvname = OSC['IntegerTicksArrayPV'] + '.C'
    pvvalue = 1.0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.C", IntegrTicks_ArrayPV), 1.0); # Enable

    if OSC['MotorName'] is 'Aero':
        pvname = '1ide:sg:In_21Do.OUT'
        pvvalue = OSC['ScalerTrigPV'] + '.A PP NMS'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s", "1ide:sg:In_21Do.OUT"), sprintf("%s.A PP NMS",ScalerTrigPV)); # Enable Det Pulses to IC Scaler, for E-hutch

        pvname = '1ide:sg:In_21IntEdge'
        pvvalue = 'Both'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s", "1ide:sg:In_21IntEdge"), "Both"); # Enable Det Pulses to IC Scaler, for E-hutch
    elif OSC['MotorName'] is 'prrot':
        pvname = '1ide:sg:FI3_Signal.DESC'
        pvvalue = 'Sc'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s", "1ide:sg:FI3_Signal.DESC"), "Sc"); # Enable Det Pulses to IC Scaler, for E-hutch
        pvname = '1ide:sg:In_3Do.OUT'
        pvvalue = OSC['ScalerTrigPV'] + '.A PP NMS'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s", "1ide:sg:In_3Do.OUT"), sprintf("%s.A PP NMS",ScalerTrigPV)); # Enable Det Pulses to IC Scaler, for E-hutch

        pvname = '1ide:sg:In_3IntEdge'
        pvvalue = 'Both'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s", "1ide:sg:In_3IntEdge"), "Both"); # Enable Det Pulses to IC Scaler, for E-hutch
    
    pvname = OSC['ScalerTrigPV'] + '.B'
    pvvalue = 1
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.B", ScalerTrigPV), 1); # Enabling the det_pulses to go to the Scaler
    
    pvname = '1ide:sg:In_21Do.OUT'
    pvvalue = OSC['ScalerTrigPV'] + '.A PP NMS'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s", "1ide:sg:In_21Do.OUT"), sprintf("%s.A PP NMS",ScalerTrigPV)); # Enable Det Pulses to IC Scaler, for E-hutch
    return

def DisarmICCounters(OSC):     # disarm_ICcounters
    '''
    disarm_ICcounters
    '''
    pvname =OSC['MonCountArrayPV'] + '.C'
    pvvalue = 0.0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", MonCount_ArrayPV), 0.0); # Disable

    pvname = OSC['TransmCountArrayPV'] + '.C'
    pvvalue = 0.0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", TransmCount_ArrayPV), 0.0); # Disable

    pvname = OSC['EMonCountArrayPV'] + '.C'
    pvvalue = 0.0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", EMonCount_ArrayPV), 0.0); # Disable

    pvname = OSC['ETransmCountArrayPV'] + '.C'
    pvvalue = 0.0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", ETransmCount_ArrayPV), 0.0); # Disable

    pvname = OSC['IntegerTicksArrayPV'] + '.C'
    pvvalue = 0.0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", IntegrTicks_ArrayPV), 0.0); # Disable
    return

def SetICCounters(OSC):    # setup_ICcounters
    '''
    setup_ICcounters
    Sets up the Monitor Counter and Transmitted Intensity Counter
    for fastsweep scans accumulating the data per frame in an array.
    The data are in reverse order and normalized to 1 sec
    '''
        
    # Setting up the scaler
    pvname = OSC['MonScalerPV'] + '.CONT'
    pvvalue = 'OneShot'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.CONT", Mon_ScalerPV), "OneShot"); # Single triggering

    pvname = OSC['MonScalerPV'] + '.CNT'
    pvvalue = 'Done'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.CNT", Mon_ScalerPV), "Done"); # Stop counting

    pvname = OSC['MonScalerPV'] + '_calc_ctrl.VAL'
    pvvalue = 'Cts/sec'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s_calc_ctrl.VAL", Mon_ScalerPV), "Cts/sec"); # Normalized counts

    for iii in (0, 16):
        pvname = OSC['MonScalerPV'] + '.G' + str(iii + 1)
        pvvalue = 'N'
        ep.caput(pvname, pvvalue, wait=True)

    pvname = OSC['MonScalerPV'] + '_calcEnable.VAL'
    pvvalue = 'ENABLE'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s_calcEnable.VAL", Mon_ScalerPV), "ENABLE"); # Enable calcs
    
    pvname = OSC['MonScalerPV'] + '.DLY'
    pvvalue = 0.0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.DLY", Mon_ScalerPV), 0.0);  # Delay in sec

    pvname = OSC['MonScalerPV'] + '.RATE'
    pvvalue = 2.0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.RATE", Mon_ScalerPV), 2.0); # DisplayFreq in Hz

    pvname = OSC['MonScalerPV'] + '.CNT'
    pvvalue = 'Done'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.CNT", Mon_ScalerPV), "Done"); # Stop counting
    
    # Setting up the triggering tool --> non StringCalc version
    pvname = OSC['ScalerTrigPV'] + '.DESC'
    pvvalue = 'DetPulseToScaler'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.DESC", ScalerTrigPV), "DetPulseToScaler"); # Mode

    pvname = OSC['ScalerTrigPV'] + '.SCAN'
    pvvalue = 'Passive'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.SCAN", ScalerTrigPV), "Passive"); # Mode

    pvname = OSC['ScalerTrigPV'] + '.A'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.A", ScalerTrigPV), 0); # Initial value

    pvname = OSC['ScalerTrigPV'] + '.B'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.B", ScalerTrigPV), 0); # Initial value, Disable 

    pvname = OSC['ScalerTrigPV'] + '.INPA'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.INPA", ScalerTrigPV), ""); # Input PV with Det_pulses, E-hutch scaler, this field will be written by FPGA 1ide:sg
    
    pvname = OSC['ScalerTrigPV'] + '.OOPT'
    pvvalue = 'On Change'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.OOPT", ScalerTrigPV), "On Change");

    pvname = OSC['ScalerTrigPV'] + '.DOPT'
    pvvalue = 'Use OCAL'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.DOPT", ScalerTrigPV), "Use OCAL");

    pvname = OSC['ScalerTrigPV'] + '.CALC'
    pvvalue = '(A&B)'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.CALC", ScalerTrigPV), "(A&B)"); # If B enabled then trigger the Scaler
    
    pvname = OSC['ScalerTrigPV'] + '.OCAL'
    pvvalue = '(A&B)?1:0'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.OCAL", ScalerTrigPV), "(A&B)?1:0"); # If B enabled an there is change on CALC then trigger the Scaler
    
    pvname = OSC['ScalerTrigPV'] + '.OUT'
    pvvalue = OSC['MonScalerPV'] + '.CNT PP NMS'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.OUT", ScalerTrigPV), sprintf("%s.CNT PP NMS", Mon_ScalerPV));
    
    # Monitor Counter (before the sample)
    ArrayPV = OSC['MonCountArrayPV']        # _arrayPV=MonCount_ArrayPV
    UserCalcName = 'Fastsweep MonCnt'       # _userCalcName="Fastsweep MonCnt";
    ICName = OSC['MonICName']               # _ICname=MonICName # from the orange field on the scaler MEDM window
    PopulateArrayCalcFields(OSC, ArrayPV, UserCalcName, ICName)
    
    # Transmitted Intensity Counter (after the sample)
    ArrayPV = OSC['TransmCountArrayPV']     # _arrayPV=TransmCount_ArrayPV
    UserCalcName = 'Fastsweep TransmCnt'    # _userCalcName="Fastsweep TransmCnt";
    ICName = OSC['TransmICName']            # _ICname=TransmICName 
    PopulateArrayCalcFields(OSC, ArrayPV, UserCalcName, ICName)

    # E-Monitor Counter (before the sample)
    ArrayPV = OSC['EMonCountArrayPV']       # _arrayPV=EMonCount_ArrayPV
    UserCalcName = 'Fastswp E-MonCnt'       # _userCalcName="Fastswp E-MonCnt";
    ICName = OSC['EMonICName']              # _ICname=EMonICName # from the orange field on the scaler MEDM window
    PopulateArrayCalcFields(OSC, ArrayPV, UserCalcName, ICName)

    # Transmitted Intensity Counter (after the sample)
    ArrayPV = OSC['ETransmCountArrayPV']    # _arrayPV=ETransmCount_ArrayPV
    UserCalcName = 'Fastswp E-TransmCnt'    # _userCalcName="Fastswp E-TransmCnt";
    ICName = OSC['ETransmICName']           # _ICname=ETransmICName 
    PopulateArrayCalcFields(OSC, ArrayPV, UserCalcName, ICName)

    # Transmitted Intensity Counter (after the sample)
    ArrayPV = OSC['IntegerTicksArrayPV']    # _arrayPV=IntegrTicks_ArrayPV
    UserCalcName = 'Fastswp Integr.Ticks'   # _userCalcName="Fastswp Integr.Ticks";
    ICName = OSC['IntegerICName']           # _ICname=IntegrICName 
    PopulateArrayCalcFields(OSC, ArrayPV, UserCalcName, ICName)
    return

def PopulateArrayCalcFields(OSC, ArrayPV, UserCalcName, ICName):    # _fill_ArrayCalcfields
    '''
    _fill_ArrayCalcfields from setup_ICcounters
    '''
    pvname = ArrayPV + '.DESC'
    pvvalue = UserCalcName
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.DESC", _arrayPV), _userCalcName);

    pvname = ArrayPV + '.NUSE'
    pvvalue = OSC['NumArrayElements']
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.NUSE", _arrayPV), array_NUSE);

    pvname = ArrayPV + '.SCAN'
    pvvalue = 'Passive'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.SCAN", _arrayPV), "Passive");

    pvname = ArrayPV + '.INPA'
    pvvalue = OSC['MonScalerPV'] + ICName + ' NPP NMS'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.INPA", _arrayPV), sprintf("%s%s NPP NMS", Mon_ScalerPV, _ICname)); # selected IC

    pvname = ArrayPV + '.INPB'
    pvvalue = OSC['MonScalerPV'] + '_cts1.A NPP NMS'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.INPB", _arrayPV), sprintf("%s_cts1.A NPP NMS", Mon_ScalerPV)); # 10MHz

    pvname = ArrayPV + '.INPC'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.INPC", _arrayPV), ""); # Disabled

    pvname = ArrayPV + '.C'
    pvvalue = 0.0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.C", _arrayPV), 0.0); # Disabled

    pvname = ArrayPV + '.INAA'
    pvvalue = OSC['MonScalerPV'] + ICName + ' CP NMS'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.INAA", _arrayPV), sprintf("%s%s CP NMS", Mon_ScalerPV, _ICname)); # Input array

    pvname = ArrayPV + '.INBB'
    pvvalue = ''
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.INBB", _arrayPV), ""); # Storage array

    pvname = ArrayPV + '.BB'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.BB", _arrayPV), 0); # Reset

    pvname = ArrayPV + '.CALC'
    pvvalue = 'C?(BB>>1)+AA:BB'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.CALC", _arrayPV), "C?(BB>>1)+AA:BB"); # The formula

    pvname = ArrayPV + '.ODLY'
    pvvalue = 0.0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.ODLY", _arrayPV), 0.0); # Delay

    pvname = ArrayPV + '.OEVT'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.OEVT", _arrayPV), 0); # Output Event

    pvname = ArrayPV + '.OOPT'
    pvvalue = 'Every Time'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.OOPT", _arrayPV), "Every Time"); # Processing

    pvname = ArrayPV + '.DOPT'
    pvvalue = 'Use CALC'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.DOPT", _arrayPV), "Use CALC"); # Use CALC

    pvname = ArrayPV + '.OUT'
    pvvalue = ArrayPV + '.BB NPP NMS'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.OUT", _arrayPV), sprintf("%s.BB NPP NMS", _arrayPV)); # output PV

    pvname = ArrayPV + '.WAIT'
    pvvalue = 'NoWait'
    ep.caput(pvname, pvvalue, wait=True)    # epics_put(sprintf("%s.WAIT", _arrayPV), "NoWait"); # No waiting
    return
