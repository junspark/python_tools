def RisingEdgeGate(OSC):
    '''
    OSC['RisingEdgeGateMode'] == 0
    def Rising_GATE_Bhutch 'epics_get(sprintf("%s.VAL",GATE_signalPV)) != 1'
    OSC['RisingEdgeGateMode'] == 1
    def Rising_GATE_Ehutch 'epics_get(sprintf("%s.VAL",GATE_signalPV)) != 1'
    OSC['RisingEdgeGateMode'] == 2
    def Rising_GATE_Aero 'epics_get(sprintf("%s.VAL",GATE_signalPV)) != 1'
    
    This was the previous implementation
    # RisingEdge_GATE for Bhutch (Rising_GATE_Bhutch)
    if OSC['RisingEdgeGateMode'] == 0:
        pvname = OSC['GateSignalPV'] + '.VAL'
    # RisingEdge_GATE for Ehutch (Rising_GATE_Ehutch)
    elif OSC['RisingEdgeGateMode'] == 1:
        pvname = OSC['GateSignalPV'] + '.VAL'
    # RisingEdge_GATE for Aero (Rising_GATE_Aero)
    elif OSC['RisingEdgeGateMode'] == 2:
        pvname = OSC['GateSignalPV'] + '.VAL'
    '''
    pvname = OSC['GateSignalPV'] + '.VAL'
    OutBool = ep.caget(pvname) != 1    
    return OutBool

def FallingEdgeGate(OSC):
    '''
    OSC['FallingEdgeGateMode'] == 0
    def Falling_GATE_Bhutch 'epics_get(sprintf("%s.VAL",GATE_signalPV)) != 0'
    OSC['FallingEdgeGateMode'] == 1
    def Falling_GATE_Ehutch 'epics_get(sprintf("%s.VAL",GATE_signalPV)) != 0'
    OSC['FallingEdgeGateMode'] == 2
    def Falling_GATE_Aero 'epics_get(sprintf("%s.VAL",GATE_signalPV)) != 0'
    
    This was the previous implementation
    # FallingEdge_GATE for Bhutch (Falling_GATE_Bhutch)
    if OSC['FallingEdgeGateMode'] == 0:
        pvname = OSC['GateSignalPV'] + '.VAL'
    # FallingEdge_GATE for Ehutch (Falling_GATE_Ehutch)
    elif OSC['FallingEdgeGateMode'] == 1:
        pvname = OSC['GateSignalPV'] + '.VAL'
    # FallingEdge_GATE for Aero (Falling_GATE_Aero)
    elif OSC['FallingEdgeGateMode'] == 2:
        pvname = OSC['GateSignalPV'] + '.VAL'
    '''
    
    pvname = OSC['GateSignalPV'] + '.VAL'
    OutBool = ep.caget(pvname) != 0
    return OutBool
    
def DisableGate(OSC):               # disableGATE
    '''
    disableGATE
    OSC['DisableGateMode'] = 0
    rdef disableGATE \' \'
    
    This was the previous implementation
    if OSC['DisableGateMode'] == 0:
        print 'DisableGate : nothing to do'
    '''
    
    print 'DisableGate : nothing to do'
    return

def EnableGate(OSC):                # enableGATE
    '''
    enableGATE
    OSC['EnableGateMode'] = 0
    rdef enableGATE \' \'
    
    This was the previous implementation
    if OSC['EnableGateMode'] == 0:
        print 'EnableGate : nothing to do'
    '''
    
    print 'EnableGate : nothing to do'
    return

def SetupFakeGatePulse(OSC):            # setup_FakeGATEandDetPulse
    '''
    setup_FakeGATEandDetPulse
    For E-hutch
    Setting up the fake gate pulses
    '''
    
    ## COMMON STUFF
    FpgaPV = OSC['FpgaPV']
    
    if OSC['MotorName'] is 'Aero':
        '''
        setup_FakeGATEandDetPulse_aero (gate portion)
        '''
        PsoPV = OSC['PsoPV']
        FakeGATEPV = '1ide:userCalcOut4'
        
        pvname = FakeGATEPV + '.DESC'
        pvvalue = 'AERO rot stopGATE'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.DESC", FakeGATEPV), "AERO rot stopGATE");
        
        pvname = FakeGATEPV + '.INPA'
        pvvalue = PsoPV + 'fly CP NMS'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPA", FakeGATEPV), sprintf("%sfly CP NMS", PSOPV)); # Input PV for status of Fly

        pvname = FakeGATEPV + '.ODLY'
        pvvalue = 0.0
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.ODLY", FakeGATEPV), 0.0);
        
        pvname = FakeGATEPV + '.OOPT'
        pvvalue = 'Transition To Zero'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.OOPT", FakeGATEPV), "Transition To Zero");
    else:
        '''
        setup_FakeGATEandDetPulse (gate portion)
        '''       
        FakeGATEPV = '1ide:userCalcOut1'
        
        pvname = FakeGATEPV + '.DESC'
        pvvalue = 'MTS rot. dev. GATE'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.DESC", FakeGATEPV), "MTS rot. dev. GATE");
        
        pvname = FakeGATEPV + '.INPA'
        pvvalue = '1ide:m5.DMOV CP NMS'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.INPA", FakeGATEPV), "1ide:m5.DMOV CP NMS"); # Input PV with Det_pulses

        pvname = FakeGATEPV + '.OOPT'
        pvvalue = 'Every Time'
        ep.caput(pvname, pvvalue, wait=True)    #epics_put(sprintf("%s.OOPT", FakeGATEPV), "Every Time");

    ## COMMON STUFF
    pvname = FakeGATEPV + '.SCAN'
    pvvalue = 'Passive'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.SCAN", FakeGATEPV), "Passive"); # Mode
    
    pvname = FakeGATEPV + '.A'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.A", FakeGATEPV), 0); # Initial value

    pvname = FakeGATEPV + '.B'
    pvvalue = 0
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.B", FakeGATEPV), 0); # Initial value, Disable
    
    pvname = FakeGATEPV + '.DOPT'
    pvvalue = 'Use CALC'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.DOPT", FakeGATEPV), "Use CALC");

    pvname = FakeGATEPV + '.CALC'
    pvvalue = '(B&A)?1:0'
    ep.caput(pvname, pvvalue, wait=True)        #epics_put(sprintf("%s.CALC", FakeGATEPV), "(B&A)?1:0");

    #epics_put(sprintf("%s.OUT", FakeGATEPV), sprintf("%sBUFFER-1_IN_Signal.PROC PP NMS", FPGAPV));
    pvname = FakeGATEPV + '.OUT'
    pvvalue = FpgaPV + 'BUFFER-1_IN_Signal.PROC PP NMS'
    ep.caput(pvname, pvvalue, wait=True)
    
    return
