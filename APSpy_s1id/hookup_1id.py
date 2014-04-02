import APSpy.sweep_core_1id as sweepcore1id

## HUTCH SETUP
def SetBhutch(OSC):            # set_Bhutch from osc_fastsweep_FPGA_hydra.mac
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

    OSC['FpgaPV'] = '1mini1:sg:'
    OSC['GateSignalPV'] = '1id:9440:1:bi_3'
    
    # OSC['RisingEdgeGateMode'] = 0       # rdef RisingEdge_GATE \'Rising_GATE_Bhutch\'  # For waiting for the 
    # OSC['FallingEdgeGateMode'] = 0      # rdef FallingEdge_GATE \'Falling_GATE_Bhutch\'
    
    # OSC['DisableGateMode'] = 0          # DisableGate(Gate=0) # rdef disableGATE \' \'
    # OSC['EnableGateMode'] = 0           # rdef enableGATE \' \'
    return OSC

def SetEHutch(OSC, OpMode = None):
    if OpMode is None:
        print 'Operation mode missing'
        print '0: PUP_AFRL_Oct13_set_Ehutch'
        print '1: Sharma_Oct13_set_Ehutch'
        OpMode = raw_input('Operation mode: ')
        OpMode = int(OpMode)
    
    ##
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
    
    OSC['PsoPV'] = '1ide:PSOFly1:'
    OSC['DetReadyPV'] = '1id:softGlue:DFF-2_OUT_BI'     # For waiting when the hydra is ready for work
    OSC['IdFpgaPV'] = '1id:softGlue:'
    
    sweepcore1id.SetupDTHDetRdyFPGA(OSC)
    
    # OSC['RisingEdgeGateMode'] = 1   # rdef RisingEdge_GATE \'Rising_GATE_Ehutch\'
    # OSC['FallingEdgeGateMode'] = 1  # rdef FallingEdge_GATE \'Falling_GATE_Ehutch\'
    
    # OSC['DisableGateMode'] = 0      # rdef disableGATE \' \' # For stopping the generation of signals during positioning the stage
    # OSC['EnableGateMode'] = 0       # rdef enableGATE \' \'
    if OpMode == 0:         # PUP_AFRL_Oct13_set_Ehutch
        '''
        PUP_AFRL_Oct13_set_Ehutch
        prrot in E-hutch
        '''
        # Acromag at 1id
        OSC['ScalerTrigDetPulsePV'] = '1ide:sg:FO21_BI'         # Gives the trigger signal to the ScalerTrigPV
        
        OSC['FpgaPV'] = '1ide:sg:'
    elif OpMode == 1:       # Sharma_Oct13_set_Ehutch
        '''
        Sharma_Oct13_set_Ehutch
        Aero in E-hutch
        '''
        # Acromag at 1id
        # E-FPGA, #21, det_pulses for aero
        OSC['ScalerTrigDetPulsePV'] = '1ide:sg2:FO21_BI'        # Gives the trigger signal to the ScalerTrigPV
        
        OSC['FpgaPV'] = '1ide:sg2:'
    return OSC
