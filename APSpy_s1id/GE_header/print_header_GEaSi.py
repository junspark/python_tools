#!/usr/bin/env python

#
# Reads the header from a GE a-Si Angio Detector
# Using version 8001 of the header from file:
#     c:\adept\core\DefaultImageInfoConfig.csv
#
#  Antonino Miceli
#  Tue Dec  5 13:18:31 CST 2006
# 


import re,string,os,sys,numpy,struct
from math import *

#if len(sys.argv)<2:
#    print "USAGE: print_header_GEaSi.py <raw_GE_data_sequence_file>"
#    print "Example: print_header_GEaSi.py /home/oxygen/AMICELI/GE_a-Si/GE_testing/Linearity80k15sH9 "
#    sys.exit()
    
    
# image_filename = sys.argv[1]
image_filename = 'W:/park_apr2013b/vff_00013.ge2'

print image_filename

fp = open(image_filename,"rb")
fp.seek(0)
#print fp.tell()


#ADEPT
ImageFormat = fp.read(10)
print "ImageFormat \t",
print ImageFormat

# USHORT --> "=H"
# ULONG  --> "=L"
#   = means byte order is native

VersionOfStandardHeader = fp.read(2)
VersionOfStandardHeader = struct.unpack("=H",VersionOfStandardHeader)[0]
print "VersionOfStandardHeader \t",
print VersionOfStandardHeader


StandardHeaderSizeInBytes = fp.read(4)
StandardHeaderSizeInBytes = struct.unpack("=L", StandardHeaderSizeInBytes)[0]
print "StandardHeaderSizeInBytes \t",
print StandardHeaderSizeInBytes

VersionOfUserHeader = fp.read(2)
VersionOfUserHeader = struct.unpack("=H",VersionOfUserHeader)[0]
print "VersionOfUserHeader \t",
print VersionOfUserHeader

UserHeaderSizeInBytes = fp.read(4)
UserHeaderSizeInBytes = struct.unpack("=L", UserHeaderSizeInBytes)[0]
print "UserHeaderSizeInBytes \t",
print UserHeaderSizeInBytes

NumberOfFrames = fp.read(2)
NumberOfFrames =  struct.unpack("=H",NumberOfFrames)[0]
print "NumberOfFrames \t",
print NumberOfFrames


NumberOfRowsInFrame  = fp.read(2)
NumberOfRowsInFrame  =  struct.unpack("=H",NumberOfRowsInFrame)[0]
print "NumberOfRowsInFrame \t",
print NumberOfRowsInFrame

NumberOfColsInFrame  = fp.read(2)
NumberOfColsInFrame  =  struct.unpack("=H",NumberOfColsInFrame)[0]
print "NumberOfColsInFrame \t",
print NumberOfColsInFrame

ImageDepthInBits  = fp.read(2)
ImageDepthInBits  = struct.unpack("=H",ImageDepthInBits)[0]
print "ImageDepthInBits \t",
print ImageDepthInBits

AcquisitionDate = fp.read(20)
print "AcquisitionDate \t",
print AcquisitionDate

AcquisitionTime = fp.read(20)
print "AcquisitionTime \t",
print AcquisitionTime

DUTID =  fp.read(20)
print "DUTID \t",
print DUTID         

Operator =  fp.read(50)
print "Operator \t",
print Operator         

DetectorSignature = fp.read(20)
print "DetectorSignature \t",
print DetectorSignature         

TestSystemName = fp.read(20)
print "TestSystemName \t",
print TestSystemName

TestStationRevision = fp.read(20)
print "TestStationRevision \t",
print TestStationRevision

CoreBundleRevision = fp.read(20)
print "CoreBundleRevision \t",
print CoreBundleRevision

AcquisitionName = fp.read(40)
print "AcquisitionName \t",
print AcquisitionName

AcquisitionParameterRevision = fp.read(20)
print "AcquisitionParameterRevision \t",
print AcquisitionParameterRevision

OriginalNumberOfRows = fp.read(2)
OriginalNumberOfRows = struct.unpack("=H",OriginalNumberOfRows)[0]
print "OriginalNumberOfRows \t",
print OriginalNumberOfRows

OriginalNumberOfColumns = fp.read(2)
OriginalNumberOfColumns = struct.unpack("=H",OriginalNumberOfColumns)[0]
print "OriginalNumberOfColumns \t",
print OriginalNumberOfColumns

RowNumberUpperLeftPointArchiveROI = fp.read(2)
RowNumberUpperLeftPointArchiveROI = struct.unpack("=H",RowNumberUpperLeftPointArchiveROI)[0]
print "RowNumberUpperLeftPointArchiveROI \t",
print RowNumberUpperLeftPointArchiveROI

ColNumberUpperLeftPointArchiveROI = fp.read(2)
ColNumberUpperLeftPointArchiveROI = struct.unpack("=H",ColNumberUpperLeftPointArchiveROI)[0]
print "ColNumberUpperLeftPointArchiveROI \t",
print ColNumberUpperLeftPointArchiveROI

Swapped = fp.read(2) 
Swapped = struct.unpack("=H",Swapped)[0]
print "Swapped \t",
print Swapped

Reordered = fp.read(2) 
Reordered = struct.unpack("=H",Reordered)[0]
print "Reordered \t",
print Reordered

HorizontalFlipped = fp.read(2) 
HorizontalFlipped = struct.unpack("=H",HorizontalFlipped)[0]
print "HorizontalFlipped \t",
print HorizontalFlipped

VerticalFlipped = fp.read(2) 
VerticalFlipped = struct.unpack("=H",VerticalFlipped)[0]
print "VerticalFlipped \t",
print VerticalFlipped

WindowValueDesired = fp.read(2) 
WindowValueDesired = struct.unpack("=H",WindowValueDesired)[0]
print "WindowValueDesired \t",
print WindowValueDesired

LevelValueDesired = fp.read(2) 
LevelValueDesired = struct.unpack("=H",LevelValueDesired)[0]
print "LevelValueDesired \t",
print LevelValueDesired

AcquisitionMode = fp.read(2) 
AcquisitionMode = struct.unpack("=H",AcquisitionMode)[0]
print "AcquisitionMode \t",
print AcquisitionMode

AcquisitionType = fp.read(2) 
AcquisitionType = struct.unpack("=H",AcquisitionType)[0]
print "AcquisitionType \t",
print AcquisitionType

UserAcquisitionCoffFileName1 = fp.read(100) 
print "UserAcquisitionCoffFileName1 \t",
print UserAcquisitionCoffFileName1

UserAcquisitionCoffFileName2 = fp.read(100) 
print "UserAcquisitionCoffFileName2 \t",
print UserAcquisitionCoffFileName2

FramesBeforeExpose = fp.read(2) 
FramesBeforeExpose = struct.unpack("=H",FramesBeforeExpose)[0]
print "FramesBeforeExpose \t",
print FramesBeforeExpose

FramesDuringExpose = fp.read(2)  
FramesDuringExpose = struct.unpack("=H",FramesDuringExpose)[0]
print "FramesDuringExpose \t",
print FramesDuringExpose

FramesAfterExpose = fp.read(2) 
FramesAfterExpose = struct.unpack("=H",FramesAfterExpose)[0]
print "FramesAfterExpose \t",
print FramesAfterExpose

IntervalBetweenFrames = fp.read(2) 
IntervalBetweenFrames = struct.unpack("=H",IntervalBetweenFrames)[0]
print "IntervalBetweenFrames \t",
print IntervalBetweenFrames


ExposeTimeDelayInMicrosecs = fp.read(8) 
ExposeTimeDelayInMicrosecs = struct.unpack("=d",ExposeTimeDelayInMicrosecs)[0]
print "ExposeTimeDelayInMicrosecs \t",
print ExposeTimeDelayInMicrosecs

TimeBetweenFramesInMicrosecs = fp.read(8) 
TimeBetweenFramesInMicrosecs = struct.unpack("=d",TimeBetweenFramesInMicrosecs)[0]
print "TimeBetweenFramesInMicrosecs \t",
print TimeBetweenFramesInMicrosecs

FramesToSkipExpose = fp.read(2) 
FramesToSkipExpose = struct.unpack("=H",FramesToSkipExpose)[0]
print "FramesToSkipExpose \t",
print FramesToSkipExpose

# Rad --> ExposureMode = 1
ExposureMode = fp.read(2) 
ExposureMode = struct.unpack("=H",ExposureMode)[0]
print "ExposureMode \t",
print ExposureMode

PrepPresetTimeInMicrosecs = fp.read(8) 
PrepPresetTimeInMicrosecs = struct.unpack("=d",PrepPresetTimeInMicrosecs)[0]
print "PrepPresetTimeInMicrosecs \t",
print PrepPresetTimeInMicrosecs

ExposePresetTimeInMicrosecs = fp.read(8) 
ExposePresetTimeInMicrosecs = struct.unpack("=d",ExposePresetTimeInMicrosecs)[0]
print "ExposePresetTimeInMicrosecs \t",
print ExposePresetTimeInMicrosecs

AcquisitionFrameRateInFps = fp.read(4) 
AcquisitionFrameRateInFps = struct.unpack("=f",AcquisitionFrameRateInFps)[0]
print "AcquisitionFrameRateInFps \t",
print AcquisitionFrameRateInFps

FOVSelect = fp.read(2)
FOVSelect = struct.unpack("=H",FOVSelect)[0]
#print "FOVSelect \t",
#print FOVSelect

ExpertMode = fp.read(2)
ExpertMode = struct.unpack("=H",ExpertMode)[0]
#print "ExpertMode \t",
#print ExpertMode

SetVCommon1 = fp.read(8)
SetVCommon1 = struct.unpack("=d",SetVCommon1)[0]
#print "SetVCommon1 \t",
#print SetVCommon1

SetVCommon2 = fp.read(8)
SetVCommon2 = struct.unpack("=d",SetVCommon2)[0]
#print "SetVCommon2 \t",
#print SetVCommon2

SetAREF = fp.read(8)
SetAREF = struct.unpack("=d",SetAREF)[0]
#print "SetAREF  \t",
#print SetAREF

SetAREFTrim = fp.read(4)
SetAREFTrim = struct.unpack("=L",SetAREFTrim)[0]
#print "SetAREFTrim \t",
#print SetAREFTrim

SetSpareVoltageSource = fp.read(8)
SetSpareVoltageSource = struct.unpack("=d",SetSpareVoltageSource)[0]
#print "SetSpareVoltageSource \t",
#print SetSpareVoltageSource

SetCompensationVoltageSource = fp.read(8)
SetCompensationVoltageSource = struct.unpack("=d",SetCompensationVoltageSource)[0]
#print "SetCompensationVoltageSource \t",
#print SetCompensationVoltageSource

SetRowOffVoltage = fp.read(8)
SetRowOffVoltage = struct.unpack("=d",SetRowOffVoltage)[0]
#print "SetRowOffVoltage \t",
#print SetRowOffVoltage

SetRowOnVoltage = fp.read(8)
SetRowOnVoltage = struct.unpack("=d",SetRowOnVoltage)[0]
#print "SetRowOnVoltage \t",
#print SetRowOnVoltage

StoreCompensationVoltage = fp.read(4)
StoreCompensationVoltage = struct.unpack("=L",StoreCompensationVoltage)[0]
#print "StoreCompensationVoltage \t",
#print StoreCompensationVoltage

RampSelection = fp.read(2)
RampSelection = struct.unpack("=H",RampSelection)[0]
#print "RampSelection \t",
#print RampSelection

TimingMode = fp.read(2)
TimingMode = struct.unpack("=H",TimingMode)[0]
#print "TimingMode \t",
#print TimingMode

Bandwidth = fp.read(2)
Bandwidth = struct.unpack("=H",Bandwidth)[0]
#print "Bandwidth \t",
#print Bandwidth

ARCIntegrator = fp.read(2)
ARCIntegrator = struct.unpack("=H",ARCIntegrator)[0]
#print "ARCIntegrator \t",
#print ARCIntegrator

ARCPostIntegrator = fp.read(2)
ARCPostIntegrator = struct.unpack("=H",ARCPostIntegrator)[0]
#print "ARCPostIntegrator \t",
#print ARCPostIntegrator

NumberOfRows = fp.read(4)
NumberOfRows = struct.unpack("=L",NumberOfRows)[0]
#print "NumberOfRows \t",
#print NumberOfRows

RowEnable = fp.read(2)
RowEnable = struct.unpack("=H",RowEnable)[0]
#print "RowEnable \t",
#print RowEnable

EnableStretch = fp.read(2)
EnableStretch = struct.unpack("=H",EnableStretch)[0]
#print "EnableStretch \t",
#print EnableStretch

CompEnable = fp.read(2)
CompEnable = struct.unpack("=H",CompEnable)[0]
#print "CompEnable \t",
#print CompEnable

CompStretch = fp.read(2)
CompStretch = struct.unpack("=H",CompStretch)[0]
print "CompStretch \t",
print CompStretch

LeftEvenTristate = fp.read(2)
LeftEvenTristate = struct.unpack("=H",LeftEvenTristate)[0]
print "LeftEvenTristate \t",
print LeftEvenTristate

RightOddTristate = fp.read(2)
RightOddTristate = struct.unpack("=H",RightOddTristate)[0]
print "RightOddTristate \t",
print RightOddTristate

TestModeSelect = fp.read(4)
TestModeSelect = struct.unpack("=L",TestModeSelect)[0]
print "TestModeSelect \t",
print TestModeSelect

AnalogTestSource = fp.read(4)
AnalogTestSource = struct.unpack("=L",AnalogTestSource)[0]
print "AnalogTestSource \t",
print AnalogTestSource

VCommonSelect = fp.read(4)
VCommonSelect = struct.unpack("=L",VCommonSelect)[0]
print "VCommonSelect \t",
print VCommonSelect

DRCColumnSum = fp.read(4)
DRCColumnSum = struct.unpack("=L",DRCColumnSum)[0]
print "DRCColumnSum \t",
print DRCColumnSum

TestPatternFrameDelta = fp.read(4)
TestPatternFrameDelta = struct.unpack("=L",TestPatternFrameDelta)[0]
print "TestPatternFrameDelta \t",
print TestPatternFrameDelta

TestPatternRowDelta = fp.read(4)
TestPatternRowDelta = struct.unpack("=L",TestPatternRowDelta)[0]
print "TestPatternRowDelta \t",
print TestPatternRowDelta

TestPatternColumnDelta = fp.read(4)
TestPatternColumnDelta = struct.unpack("=L",TestPatternColumnDelta)[0]
print "TestPatternColumnDelta \t",
print TestPatternColumnDelta

DetectorHorizontalFlip = fp.read(2)
DetectorHorizontalFlip = struct.unpack("=H",DetectorHorizontalFlip)[0]
print "DetectorHorizontalFlip \t",
print DetectorHorizontalFlip

DetectorVerticalFlip = fp.read(2)
DetectorVerticalFlip = struct.unpack("=H",DetectorVerticalFlip)[0]
print "DetectorVerticalFlip \t",
print DetectorVerticalFlip

DFNAutoScrubOnOff = fp.read(2)
DFNAutoScrubOnOff = struct.unpack("=H",DFNAutoScrubOnOff)[0]
print "DFNAutoScrubOnOff \t",
print DFNAutoScrubOnOff

FiberChannelTimeOutInMicrosecs = fp.read(4)
FiberChannelTimeOutInMicrosecs = struct.unpack("=L",FiberChannelTimeOutInMicrosecs)[0]
print "FiberChannelTimeOutInMicrosecs \t",
print FiberChannelTimeOutInMicrosecs

DFNAutoScrubDelayInMicrosecs = fp.read(4)
DFNAutoScrubDelayInMicrosecs = struct.unpack("=L",DFNAutoScrubDelayInMicrosecs)[0]
print "DFNAutoScrubDelayInMicrosecs \t",
print DFNAutoScrubDelayInMicrosecs
sys.exit()

StoreAECROI = fp.read(2)
StoreAECROI = struct.unpack("=H",StoreAECROI)[0]
print "StoreAECROI \t",
print StoreAECROI

TestPatternSaturationValue = fp.read(2)
TestPatternSaturationValue = struct.unpack("=H",TestPatternSaturationValue)[0]
print "TestPatternSaturationValue \t",
print TestPatternSaturationValue

TestPatternSeed = fp.read(4)
TestPatternSeed = struct.unpack("=L",TestPatternSeed)[0]
print "TestPatternSeed \t",
print TestPatternSeed


ExposureTimeInMillisecs = fp.read(4) 
ExposureTimeInMillisecs = struct.unpack("=f",ExposureTimeInMillisecs)[0]
print "ExposureTimeInMillisecs \t",
print ExposureTimeInMillisecs

FrameRateInFps = fp.read(4) 
FrameRateInFps = struct.unpack("=f",FrameRateInFps)[0]
print "FrameRateInFps \t",
print FrameRateInFps

kVp = fp.read(4) 
kVp = struct.unpack("=f",kVp)[0]
print "kVp \t",
print kVp

mA = fp.read(4) 
mA = struct.unpack("=f",mA)[0]
print "mA \t",
print mA

mAs = fp.read(4) 
mAs = struct.unpack("=f",mAs)[0]
print "mAs \t",
print mAs

FocalSpotInMM = fp.read(4) 
FocalSpotInMM = struct.unpack("=f",FocalSpotInMM)[0]
print "FocalSpotInMM \t",
print FocalSpotInMM

GeneratorType = fp.read(20)
print "GeneratorType \t",
print GeneratorType

StrobeIntensityInFtL = fp.read(4) 
StrobeIntensityInFtL = struct.unpack("=f",StrobeIntensityInFtL)[0]
print "StrobeIntensityInFtL \t",
print StrobeIntensityInFtL

NDFilterSelection = fp.read(2) 
NDFilterSelection = struct.unpack("=H",NDFilterSelection)[0]
print "NDFilterSelection \t",
print NDFilterSelection

RefRegTemp1 = fp.read(8) 
RefRegTemp1 = struct.unpack("=d",RefRegTemp1)[0]
print "RefRegTemp1 \t",
print RefRegTemp1

RefRegTemp2 = fp.read(8) 
RefRegTemp2 = struct.unpack("=d",RefRegTemp2)[0]
print "RefRegTemp2 \t",
print RefRegTemp2

RefRegTemp3 = fp.read(8) 
RefRegTemp3 = struct.unpack("=d",RefRegTemp3)[0]
print "RefRegTemp3 \t",
print RefRegTemp3


Humidity1 = fp.read(4) 
Humidity1 = struct.unpack("=f",Humidity1)[0]
print "Humidity1 \t",
print Humidity1

Humidity2 = fp.read(4) 
Humidity2 = struct.unpack("=f",Humidity2)[0]
print "Humidity2 \t",
print Humidity2

DetectorControlTemp = fp.read(8) 
DetectorControlTemp = struct.unpack("=d",DetectorControlTemp)[0]
print "DetectorControlTemp \t",
print DetectorControlTemp


DoseValueInmR = fp.read(8) 
DoseValueInmR = struct.unpack("=d",DoseValueInmR)[0]
print "DoseValueInmR \t",
print DoseValueInmR


TargetLevelROIRow0 = fp.read(2)
TargetLevelROIRow0 = struct.unpack("=H",TargetLevelROIRow0)[0]
print "TargetLevelROIRow0 \t",
print TargetLevelROIRow0

TargetLevelROICol0 = fp.read(2)
TargetLevelROICol0 = struct.unpack("=H",TargetLevelROICol0)[0]
print "TargetLevelROICol0 \t",
print TargetLevelROICol0

TargetLevelROIRow1 = fp.read(2)
TargetLevelROIRow1 = struct.unpack("=H",TargetLevelROIRow1)[0]
print "TargetLevelROIRow1 \t",
print TargetLevelROIRow1

TargetLevelROICol1 = fp.read(2)
TargetLevelROICol1 = struct.unpack("=H",TargetLevelROICol1)[0]
print "TargetLevelROICol1 \t",
print TargetLevelROICol1

FrameNumberForTargetLevelROI = fp.read(2)
FrameNumberForTargetLevelROI = struct.unpack("=H",FrameNumberForTargetLevelROI)[0]
print "FrameNumberForTargetLevelROI \t",
print FrameNumberForTargetLevelROI

PercentRangeForTargetLevel = fp.read(2)
PercentRangeForTargetLevel = struct.unpack("=H",PercentRangeForTargetLevel)[0]
print "PercentRangeForTargetLevel \t",
print PercentRangeForTargetLevel

TargetValue = fp.read(2)
TargetValue = struct.unpack("=H",TargetValue)[0]
print "TargetValue \t",
print TargetValue

ComputedMedianValue = fp.read(2)
ComputedMedianValue = struct.unpack("=H",ComputedMedianValue)[0]
print "ComputedMedianValue \t",
print ComputedMedianValue

LoadZero = fp.read(2)
LoadZero = struct.unpack("=H",LoadZero)[0]
print "LoadZero \t",
print LoadZero

MaxLUTOut = fp.read(2)
MaxLUTOut = struct.unpack("=H",MaxLUTOut)[0]
print "MaxLUTOut \t",
print MaxLUTOut

MinLUTOut = fp.read(2)
MinLUTOut = struct.unpack("=H",MinLUTOut)[0]
# print "MinLUTOut \t",
# print MinLUTOut

MaxLinear = fp.read(2)
MaxLinear = struct.unpack("=H",MaxLinear)[0]
#print "MaxLinear \t",
#print MaxLinear

Reserved = fp.read(2)
Reserved = struct.unpack("=H",Reserved)[0]
#print "Reserved \t",
#print Reserved

ElectronsPerCount = fp.read(2)
ElectronsPerCount = struct.unpack("=H",ElectronsPerCount)[0]
#print "ElectronsPerCount \t",
#print ElectronsPerCount

ModeGain = fp.read(2)
ModeGain = struct.unpack("=H",ModeGain)[0]
#print "ModeGain \t",
#print ModeGain

TemperatureInDegC = fp.read(8)
TemperatureInDegC = struct.unpack("=d",TemperatureInDegC)[0]
#print "TemperatureInDegC \t",
#print TemperatureInDegC

LineRepaired = fp.read(2)
LineRepaired = struct.unpack("=H",LineRepaired)[0]
#print "LineRepaired \t",
#print LineRepaired

LineRepairFileName = fp.read(100)
#print "LineRepairFileNam \t",
#print LineRepairFileName


CurrentLongitudinalInMM = fp.read(4)
CurrentLongitudinalInMM = struct.unpack("=f",CurrentLongitudinalInMM)[0]
#print "CurrentLongitudinalInMM \t",
#print CurrentLongitudinalInMM

CurrentTransverseInMM = fp.read(4)
CurrentTransverseInMM = struct.unpack("=f",CurrentTransverseInMM)[0]
#print "CurrentTransverseInMM \t",
#print CurrentTransverseInMM

CurrentCircularInMM = fp.read(4)
CurrentCircularInMM = struct.unpack("=f",CurrentCircularInMM)[0]
#print "CurrentCircularInMM \t",
#print CurrentCircularInMM

CurrentFilterSelection = fp.read(4)
CurrentFilterSelection = struct.unpack("=L",CurrentFilterSelection)[0]
#print "CurrentFilterSelection \t",
#print CurrentFilterSelection

DisableScrubAck = fp.read(2)
DisableScrubAck = struct.unpack("=H",DisableScrubAck)[0]
#print "DisableScrubAck \t",
#print DisableScrubAck

ScanModeSelect = fp.read(2)
ScanModeSelect = struct.unpack("=H",ScanModeSelect)[0]
#print "ScanModeSelect \t",
#print ScanModeSelect

DetectorAppSwVersion = fp.read(20)	
#print "DetectorAppSwVersion \t",
#print DetectorAppSwVersion

DetectorNIOSVersion = fp.read(20)	
#print "DetectorNIOSVersion \t",
#print DetectorNIOSVersion

DetectorPeripheralSetVersion = fp.read(20)	
#print "DetectorPeripheralSetVersion \t"
#print DetectorPeripheralSetVersion

DetectorPhysicalAddress	 = fp.read(20)
#print "DetectorPhysicalAddress \t",
#print DetectorPhysicalAddress

PowerDown = fp.read(2)
PowerDown = struct.unpack("=H",PowerDown)[0]
#print "PowerDown \t",
#print PowerDown

InitialVoltageLevel_VCOMMON = fp.read(8)
InitialVoltageLevel_VCOMMON = struct.unpack("=d",InitialVoltageLevel_VCOMMON)[0]
#print "InitialVoltageLevel_VCOMMON \t",
#print InitialVoltageLevel_VCOMMON

FinalVoltageLevel_VCOMMON = fp.read(8)
FinalVoltageLevel_VCOMMON = struct.unpack("=d",FinalVoltageLevel_VCOMMON)[0]
#print "FinalVoltageLevel_VCOMMON \t",
#print FinalVoltageLevel_VCOMMON

DmrCollimatorSpotSize	 = fp.read(10)
#print "DmrCollimatorSpotSize \t",
#print DmrCollimatorSpotSize

DmrTrack	 = fp.read(5)
#print "DmrTrack \t",
#print DmrTrack

DmrFilter	 = fp.read(5)
#print "DmrFilter \t",
#print DmrFilter

FilterCarousel = fp.read(2)
FilterCarousel = struct.unpack("=H",FilterCarousel)[0]
#print "FilterCarousel \t",
#print FilterCarousel

Phantom	 = fp.read(20)
#print "Phantom \t",
#print Phantom

SetEnableHighTime = fp.read(2)
SetEnableHighTime = struct.unpack("=H",SetEnableHighTime)[0]
#print "SetEnableHighTime \t",
#print SetEnableHighTime

SetEnableLowTime = fp.read(2)
SetEnableLowTime = struct.unpack("=H",SetEnableLowTime)[0]
#print "SetEnableLowTime \t",
#print SetEnableLowTime

SetCompHighTime = fp.read(2)
SetCompHighTime = struct.unpack("=H",SetCompHighTime)[0]
#print "SetCompHighTime \t",
#print SetCompHighTime

SetCompLowTime = fp.read(2)
SetCompLowTime = struct.unpack("=H",SetCompLowTime)[0]
#print "SetCompLowTime \t",
#print SetCompLowTime

SetSyncLowTime = fp.read(2)
SetSyncLowTime = struct.unpack("=H",SetSyncLowTime)[0]
#print "SetSyncLowTime \t",
#print SetSyncLowTime

SetConvertLowTime = fp.read(2)
SetConvertLowTime = struct.unpack("=H",SetConvertLowTime)[0]
#print "SetConvertLowTime \t",
#print SetConvertLowTime

SetSyncHighTime = fp.read(2)
SetSyncHighTime = struct.unpack("=H",SetSyncHighTime)[0]
#print "SetSyncHighTime \t",
#print SetSyncHighTime

SetEOLTime = fp.read(2)
SetEOLTime = struct.unpack("=H",SetEOLTime)[0]
#print "SetEOLTime \t",
#print SetEOLTime

SetRampOffsetTime = fp.read(2)
SetRampOffsetTime = struct.unpack("=H",SetRampOffsetTime)[0]
#print "SetRampOffsetTime \t",
#print SetRampOffsetTime


FOVStartingValue = fp.read(2)
FOVStartingValue = struct.unpack("=H",FOVStartingValue)[0]
#print "FOVStartingValue \t",
#print FOVStartingValue

ColumnBinning = fp.read(2)
ColumnBinning = struct.unpack("=H",ColumnBinning)[0]
#print "ColumnBinning \t",
#print ColumnBinning

RowBinning = fp.read(2)
RowBinning = struct.unpack("=H",RowBinning)[0]
#print "RowBinning \t",
#print RowBinning

BorderColumns64 = fp.read(2)
BorderColumns64 = struct.unpack("=H",BorderColumns64)[0]
#print "BorderColumns64 \t",
#print BorderColumns64

BorderRows64 = fp.read(2)
BorderRows64 = struct.unpack("=H",BorderRows64)[0]
#print "BorderRows64 \t",
#print BorderRows64

FETOffRows64 = fp.read(2)
FETOffRows64 = struct.unpack("=H",FETOffRows64)[0]
#print "FETOffRows64 \t",
#print FETOffRows64

FOVStartColumn128 = fp.read(2)
FOVStartColumn128 = struct.unpack("=H",FOVStartColumn128)[0]
#print "FOVStartColumn128 \t",
#print FOVStartColumn128

FOVStartRow128 = fp.read(2)
FOVStartRow128 = struct.unpack("=H",FOVStartRow128)[0]
#print "FOVStartRow128 \t",
#print FOVStartRow128

NumberOfColumns128 = fp.read(2)
NumberOfColumns128 = struct.unpack("=H",NumberOfColumns128)[0]
#print "NumberOfColumns128 \t",
#print NumberOfColumns128

NumberOfRows128 = fp.read(2)
NumberOfRows128 = struct.unpack("=H",NumberOfRows128)[0]
#print "NumberOfRows128 \t",
#print NumberOfRows128

#print fp.tell()

VFPAquisition	 = fp.read(2000)
#print "VFPAquisition \t",
#print VFPAquisition

Comment	 = fp.read(200)
#print "Comment \t",
#print Comment

#print fp.tell()
#fp.seek(8192)
