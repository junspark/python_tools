## MOTOR CONFIGURATION
# NEED run exp_setup/AFRL_201310.mtrsetup.py.new

## ASSUMPTIONS
# 1. DETECTOR GE2
# - ONE DETECTOR FOR NOW BUT WE CAN THINK ABOUT A DETECTOR LIST DESCRIBING AN ARRAY OF DISSIMILAR DETECTORS
# 2. AEROTECH MOTOR IS THE FASTSWEEP
# - WE CAN EXPAND TO OTHER SYSTEMS (STEPPER MOTORS / PULSERAY SYSTEM
# 3. FPGA / SOFTGLUE SETUP FOR MEASUREMENTS IN E
#
# VERSION OF THE SPEC CODE THAT IS PORTED IS FROM A MIX OF "PUP_AFRL_Oct13" AND "Sharma_Oct13"

import sys
import numpy
import scipy
import math
import logging
import time

import datetime as dt
import matplotlib.pyplot as plt
import epics as ep

#################################################
### THIS IS THE INSTALL FOR S1ID SPECIFIC FUNCTIONALITIES
### POINTS AT THE FOLDER WHERE THE PYTHON SOURCE FILES ARE
#################################################
sys.path.insert(0, '/home/beams/S1IDUSER/new_data/1id_python/APSpy_s1id')

import AD as AD
import macros as mac
import spec as spec
import rst_table as rst_table

spec.EnableEPICS()      # TEMP - WHERE THIS HAPPENS NEED TO BE DETERMINED


#################################################
# DEFINE DETECTOR
#################################################
hydra = [AD.GE2, AD.GE1]

import macros_1id as mac1id
import fpga_1id as fpga1id                # qdo ./macros_PK/FPGA_2013Aug11/FPGA_signals.mac
import AD_1id as AD1id                    # qdo ./macros_PK/hydra_2013Aug11/use_hydra.mac
import sweep_core_1id as sweepcore1id 

## SetupOptionList HOLDS ALL FASTSWEEP SETUP PARAMETERS - THIS IS LIKE OSC VARIABLE IN THE SPEC VERSION
SetupOptionList = {}
# CCD_FILE_EXT
# CCD_DATA_DIR
SetupOptionList['HutchLetter'] = 'C'                                    # HUTCH IDENTIFIER B, C, E
SetupOptionList['Detectors'] = hydra                                    # HYDRA
SetupOptionList['TrigMode'] = 0                                         # HYDRA Trigger mode for hydra_initialize 
SetupOptionList['CCDPV'] = hydra[0].controlprefix                       # CCDPV
SetupOptionList['ADFilePV'] = hydra[0].controlprefix                    # ADFILEPV
SetupOptionList['EpicsDelay'] = 0.02                                    # EPICS_DELAY
SetupOptionList['CallBackTime'] = 10.0                                  # CB_TIME
SetupOptionList['OscThreshold'] = 1000                                  # osc_threshold (ct/sec)
SetupOptionList['OscMonitor'] = 'ic6b'                                  # osc_MON
SetupOptionList['SweepMode'] = 'sweep'                                  # sweep_mode
SetupOptionList['DetDelay'] = 0.5                                       # detDelay
SetupOptionList['ParFile'] = 'PUP_AFRL_Aug13_FF.par'                    # parfile
SetupOptionList['FastParFile'] = 'fastpar_PUP_AFRL_Aug13_FF.par'        # fastparfile

SetupOptionList['FirstFrameNumber'] = 0                                 # first_frame_number'
SetupOptionList['LastFrameNumber'] = 0                                  # New last frame number
SetupOptionList['OscillationMode'] = 'NEED NUMBER'                      # NEW: Flag for Oscillation()
SetupOptionList['ExpTime'] = 0                                          # exposure_time
SetupOptionList['NumFrames'] = 1                                        # nframes, number of frames
SetupOptionList['DefaultGapTime'] = 0.03                                # DEFAULT_GAP_TIME - default gap time in sec between the frames
SetupOptionList['DelayTime'] = 0.03                                     # Delay time
SetupOptionList['ScanTime'] = ( SetupOptionList['ExpTime'] + SetupOptionList['DefaultGapTime'] ) * SetupOptionList['NumFrames']   # scantime
SetupOptionList['RepeatScan'] = 1                                       # ShouldRepeat

sys.exit()





import hookup_1id as hookup1id    # qdo ./macros_PK/fastsweep_BCEhutch_preci_prrot_aero_GE_Retiga_2013Aug11/hookup_macros.mac
import gate_1id as gate1id
import counters_1id as counters1id
import motor_1id as motor1id
import scanrecord_1id as scanrecord1id

import dic_1id as dic1id                  # qdo ./macros_PK/DIC_macros.mac

AlertList = 'jp118@cornell.edu, parkjs@aps.anl.gov'
sys.exit()



SetupOptionList['HydraNum'] = 'NUMBER NEEDED'                           # hydraNum
SetupOptionList['NumArrayElements'] = 2000                              # array_NUSE # Number of array elements in the arrayCalcTools
SetupOptionList['ParamCheck'] = 1                                       # ParamCheck
SetupOptionList['MonScalerPV'] = 'PV NAME NEEDED'                       # Mon_ScalerPV
SetupOptionList['MonICName'] = 'PV NAME NEEDED'                         # MonICName
SetupOptionList['TransmICName'] = 'PV NAME NEEDED'                      # TransmICName
SetupOptionList['MonCountArrayPV'] = 'PV NAME NEEDED'                   # MonCount_ArrayPV
SetupOptionList['TransmCountArrayPV'] = 'PV NAME NEEDED'                # TransmCount_ArrayPV
SetupOptionList['EMonICName'] = 'PV NAME NEEDED'                        # EMonICName
SetupOptionList['ETransmICName'] = 'PV NAME NEEDED'                     # ETransmICName
SetupOptionList['EMonCountArrayPV'] = 'PV NAME NEEDED'                  # EMonCount_ArrayPV
SetupOptionList['ETransmCountArrayPV'] = 'PV NAME NEEDED'               # ETransmCount_ArrayPV
SetupOptionList['ReadoutPV'] = 'PV NAME NEEDED'                         # ReadoutPV
SetupOptionList['SingleExposureGEPV'] = 'PV NAME NEEDED'                # SexGEPV
SetupOptionList['GateSignalPV'] = 'PV NAME NEEDED'                      # GATE_signalPV
SetupOptionList['ScalerTrigPV'] = 'PV NAME NEEDED'                      # ScalerTrigPV
SetupOptionList['ScalerTrigDetPulsePV'] = 'PV NAME NEEDED'              # ScalerTrigDetPulsePV
SetupOptionList['FpgaPV'] = 'PV NAME NEEDED'                            # FPGAPV
SetupOptionList['PSOPV'] = 'PV NAME NEEDED'                             # PSOPV
SetupOptionList['DetReadyPV'] = 'PV NAME NEEDED'                        # DetRdyPV
SetupOptionList['IDFPGAPV'] = 'PV NAME NEEDED'                          # idFPGAPV 
SetupOptionList['DetPulseToADPV'] = 'PV NAME NEEDED'                    # DetPulseToADPV
SetupOptionList['FrameCounterPV'] = 'PV NAME NEEDED'                    # FrameCounterPV
SetupOptionList['FrameCounterTriggerPV'] = 'PV NAME NEEDED'             # FrameCounterTriggerPV
SetupOptionList['DetPulsePV'] = 'PV NAME NEEDED'                        # DetPulsePV
SetupOptionList['TimeStampPV'] = 'PV NAME NEEDED'                       # TimeStampPV
SetupOptionList['TimeStampArrayPV'] = 'PV NAME NEEDED'                  # TimeStampArrayPV
SetupOptionList['FrameSignalPV'] = 'PV NAME NEEDED'                     # FrameSignalPV

SetupOptionList['IntegerTicksArrayPV'] = 'PV NAME NEEDED'               # IntegrTicks_ArrayPV
SetupOptionList['SoftIOCPV'] = 'PV NAME NEEDED'                         # SOFTIOC_PV
SetupOptionList['IntegerICName'] = 'DATA NEEDED'                        # IntegrICName
# SetupOptionList['MotorName'] = 'NEED NAME'                              # motor
SetupOptionList['Speed'] = 1                                            # speed
SetupOptionList['SpeedEGUperSec'] = 1                                   # speed_equ_per_sec
SetupOptionList['MaxSpeed'] = 1                                         # max_speed
SetupOptionList['StepSize'] = 1                                         # step_size
SetupOptionList['Range'] = 1                                            # range
SetupOptionList['Steps'] = 1                                            # steps
SetupOptionList['Base'] = 1                                             # base
SetupOptionList['AccelerationTime'] = 1                                 # atime
SetupOptionList['AccelerationSteps'] = 1                                # asteps
SetupOptionList['AccelerationRange'] = 1                                # Arange
SetupOptionList['Scaler1'] = 1                                          # scaler1
SetupOptionList['Scaler2'] = 1                                          # scaler2
SetupOptionList['OpenSteps'] = 1                                        # open_steps
SetupOptionList['CloseSteps'] = 1                                       # close_steps
SetupOptionList['NormalAccelerationTime'] = 1                           # normal_atime
SetupOptionList['NormaBaseSpeed'] = 1                                   # normal_base (steps/sec)
SetupOptionList['NormalSpeed'] = 1                                      # normal_speed (steps/sec)
SetupOptionList['FPGAType'] = 'VALUE NEEDED'                            # NEW: FPGAType for SetGapAdjustmentTicks : 0 for TIME DRV FPGA, 1 for POS DRV FPGA
# SetupOptionList['GapAdjustmentTicks'] = 'NUMBER NEEDED'                 # GapAdjustmentTicks => SET IN SetGapAdjustmentTicks
# SetupOptionList['DecodingRate'] = 'NUMBER NEEDED'                       # DecodingRate => SET IN SetGapAdjustmentTicks
SetupOptionList['ShutterOpenDelay'] = 0                                 # shutter_open_delay
SetupOptionList['ShutterCloseDelay'] = 0                                # shutter_close_delay

SetupOptionList['CushionTime'] = 0.0                                    # cushion_time
SetupOptionList['ShouldRotateBack'] = 0                                 # Should the rotation stage go back immediately after finishing the fastweep (0:NO)
SetupOptionList['MaxSavingTime'] = 100                                  # Maximum saving time for hydra in seconds that we should wait after the scan before we abort everything and start over. 100 secs typically good for 300 frames
SetupOptionList['UseSoftIOC'] = 0                                       # SOFTIOC_USE
SetupOptionList['IsSweepScan'] = 1                                      # IS_SWEEPSCAN
SetupOptionList['BeamUpWaitTime'] = 50                                  # beam_up_wait_time
# 
# SetupOptionList['ExtraTime'] = 1                                        # extra_time
SetupOptionList['ImagePrefix'] = 'NEED NAME'                            # imgprefix

SetupOptionList['DataFolder'] = 'NAME NEEDED'                           # DataDirectory
SetupOptionList['FileSizeCheck'] = 'NEED NUMBER'                        # HydraFileSizeCheck
SetupOptionList['TriggerMode'] = 0                                      # NEW: HWTRIGGER=0, SWTRIGGER=1
SetupOptionList['DetectorArmMode'] = 'None'                             # NEW: Flag for ArmDetector()
# SetupOptionList['DetectorDisarmMode'] = 'None'                          # NEW: Flag for DisarmDetector()
# SetupOptionList['RisingEdgeGateMode'] = 'None'                          # NEW: Flag for RisingEdgeGate()
# SetupOptionList['FallingEdgeGateMode'] = 'None'                         # NEW: Flag for FallingEdgeGate()
# SetupOptionList['EnableGateMode'] = 0                                   # NEW: Flag for EnableGate()
# SetupOptionList['DisableGateMode'] = 0                                  # NEW: Flag for DisableGate()
SetupOptionList['AlertRecipientList'] = AlertList                       # NEW: Email list for alerts
SetupOptionList['AlertPath'] = './AlertEmailText.txt'                   # NEW: text file of alert email content
SetupOptionList['EnergyMonitorFile'] = 'FILE NAME NEEDED'               # NEW: Energy monitor file (with full path)

MonitorCountArray = numpy.zeros(SetupOptionList['NumArrayElements'])    # global array moncnt[array_NUSE]  # Monitor counter array
TransCountArray = numpy.zeros(SetupOptionList['NumArrayElements'])      # global array trcnt[array_NUSE]   # Transm. counter array
EMonitorCountArray = numpy.zeros(SetupOptionList['NumArrayElements'])   # global array Emoncnt[array_NUSE]  # Monitor counter array
ETransCiybtArray = numpy.zeros(SetupOptionList['NumArrayElements'])     # global array Etrcnt[array_NUSE]   # Transm. counter array
CountTicksArray = numpy.zeros(SetupOptionList['NumArrayElements'])      # global array cntticks[array_NUSE]   # Scaler integration ticks array (in 10MHz ticks currently)
TimeStampArray = numpy.zeros(SetupOptionList['NumArrayElements'])       # global array timestamp[array_NUSE]   # TimeStamp array

###################################################
### THIS IS FROM STARTUP MACRO
### SPEC SPE-TYPE LOGGING NEEDS TO BE TAKEN CARE OF
#cd ~/new_data/PUP_AFRL_Oct13
#on("FullLog.log")
### To check the last scan number use:
### u grep #S PUP_AFRL_Oct13.spe
#global spec_lastscan
#unix("spec_lastscan.sh PUP_AFRL_Oct13.spe", spec_lastscan)
#p "spec_lastscan = ", spec_lastscan
#exit
#newfile PUP_AFRL_Oct13.spe spec_lastscan

###################################################
## CHECK THIS
def PUP_AFRL_Oct13_hydra1(SetupOptionList):
    spec.EnableEPICS()      # TEMP - WHERE THIS HAPPENS NEED TO BE DETERMINED
        
    AD1id.DTHInitialize(SetupOptionList['DetList'], TrigMode=0)
    print '==========================================='
    print 'Active Detector List'
    print '==========================================='
    AD1id.PrintDetList(SetupOptionList)
    print '==========================================='
    
    AD1id.HydraInitialize(SetupOptionList)
    AD1id.DTHInitialize(SetupOptionList['DetList'], TrigMode=0)
    SetupOptionList['DetDelay'] = 0.0
    
    print '==========================================='
    print 'Next file paths:   '
    AD1id.GetPathName(SetupOptionList['DetList'])
    print 'Next file names:   '
    AD1id.GetFileName(SetupOptionList['DetList'])
    print 'Next file formats: '
    AD1id.GetFileNameFormat(SetupOptionList['DetList'])
    print 'Next file numbers: '
    AD1id.GetFileNumber(SetupOptionList['DetList'])
    print '==========================================='
    AD1id.SetAutoStore(SetupOptionList['DetList'], YesOrNo=1)
    AD1id.SetAcquisitionType(SetupOptionList['DetList'], AcqType=2)
    AD1id.SetNumFrames(SetupOptionList['DetList'], numFrames=1)
    print '==========================================='

    # SetupOptionList['ParFile'] = 'PUP_AFRL_Oct13_FF.par'                      # SET THIS OUTSIDE
    # SetupOptionList['FastParFile'] = 'FS_PUP_AFRL_Oct13_FF.par'               # SET THIS OUTSIDE
    
    hookup1id.SetEHutch(SetupOptionList, OpMode = 1)
    sweepcore1id.SetHydra(SetupOptionList, OpMode = 1)
    
    ## CHECK THIS / THIS IS ALREADY SET
    print SetupOptionList['FrameSignalPV']
    print SetupOptionList['DetPulsePV']
    SetupOptionList['FrameSignalPV'] = SetupOptionList['DetPulsePV']
    
    fpga1id.FS_GE2SEControl()
    
    SetupOptionList['OscThreshold'] = -1
    SetupOptionList['DefaultGapTime'] = 0.150
    
    spec.sleep(SetupOptionList['EpicsDelay'])
    
    ## CHECK THIS
    # sync
    ## CHECK THIS
    # printOscGlobals
    return SetupOptionList

###################################################
## For GE2
print SetupOptionList['DetectorArmMode']
fpga1id.FS_GE2SEControl()
SetupOptionList = PUP_AFRL_Oct13_hydra1(SetupOptionList);
print SetupOptionList['DetectorArmMode']

## For Near Field
# fpga1id.FS_RetigaControl()      # FS_Retiga_control
# PUP_AFRL_Oct13_Retiga           ### THIS IS BELOW

## For Tomo
#FS_Retiga_control
#PUP_AFRL_Oct13_Tomo
###################################################


sys.exit()

sweepcore1id.SetScaler('phi', '1idc:scaler1', '1idc:scaler2')    #osc_scaler_set phi 1idc:scaler1 1idc:scaler2
sweepcore1id.SetScaler('ome', '1idc:scaler3', '1idc:scaler4')    #osc_scaler_set ome 1idc:scaler3 1idc:scaler4
