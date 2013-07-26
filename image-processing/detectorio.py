#!/usr/bin/python
def CheckGE(filename):
    # CheckGE - checks the GE file for consistency
    #
    #   INPUT:
    #
    #   filename
    #       name of the GE image stack file name
    #
    #   OUTPUT:
    #
    #   status
    #       check result (1 = good, 0 = oh no!)
    import os
    GE_buffer = 8192
    num_X = 2048
    num_Y = 2048
    
    header = ReadGEHeader(filename)
    
    filesize = os.path.getsize(filename)
    nFrames = (filesize - GE_buffer) / (2 * num_X * num_Y)
    
    status = 1
    if ( header['NumberOfFrames'] != nFrames ):
        status = 0
    elif ( header['NumberOfColsInFrame'] != num_X ) or ( header['NumberOfRowsInFrame'] != num_Y ):
        status = 0
    
    return status    
    
def ReadGEHeader(filename):
    # ReadGEHeader - read header information from GE file
    #
    #   INPUT:
    #
    #   filename
    #       name of the GE image stack file name
    #
    #   OUTPUT:
    #
    #   header
    #       header information
    import struct
    
    fileobj = open(filename,'rb')
    fileobj.seek(0)
    
    header = dict()
    
    ImageFormat = fileobj.read(10)
    header['ImageFormat'] = ImageFormat
    
    VersionOfStandardHeader = fileobj.read(2)
    VersionOfStandardHeader = struct.unpack("=H",VersionOfStandardHeader)[0]
    header['VersionOfStandardHeader'] = VersionOfStandardHeader
    
    StandardHeaderSizeInBytes = fileobj.read(4)
    StandardHeaderSizeInBytes = struct.unpack("=L",StandardHeaderSizeInBytes)[0]
    header['StandardHeaderSizeInBytes'] = StandardHeaderSizeInBytes
    
    VersionOfUserHeader = fileobj.read(2)
    VersionOfUserHeader = struct.unpack("=H",VersionOfUserHeader)[0]
    header['VersionOfUserHeader'] = VersionOfUserHeader
    
    UserHeaderSizeInBytes = fileobj.read(4)
    UserHeaderSizeInBytes = struct.unpack("=L",UserHeaderSizeInBytes)[0]
    header['UserHeaderSizeInBytes'] = UserHeaderSizeInBytes
    
    NumberOfFrames = fileobj.read(2)
    NumberOfFrames =  struct.unpack("=H",NumberOfFrames)[0]
    header['NumberOfFrames'] = NumberOfFrames
    
    NumberOfRowsInFrame  = fileobj.read(2)
    NumberOfRowsInFrame  =  struct.unpack("=H",NumberOfRowsInFrame)[0]
    header['NumberOfRowsInFrame'] = NumberOfRowsInFrame
    
    NumberOfColsInFrame  = fileobj.read(2)
    NumberOfColsInFrame  =  struct.unpack("=H",NumberOfColsInFrame)[0]
    header['NumberOfColsInFrame'] = NumberOfColsInFrame
    
    ImageDepthInBits  = fileobj.read(2)
    ImageDepthInBits  = struct.unpack("=H",ImageDepthInBits)[0]
    header['ImageDepthInBits'] = ImageDepthInBits
    
    AcquisitionDate = fileobj.read(20)
    header['AcquisitionDate'] = AcquisitionDate
    
    AcquisitionTime = fileobj.read(20)
    header['AcquisitionTime'] = AcquisitionTime
    
    DUTID =  fileobj.read(20)
    header['DUTID'] = DUTID
    
    Operator =  fileobj.read(50)
    header['Operator'] = Operator
    
    DetectorSignature = fileobj.read(20)
    header['DetectorSignature'] = DetectorSignature
    
    TestSystemName = fileobj.read(20)
    header['TestSystemName'] = TestSystemName
    
    TestStationRevision = fileobj.read(20)
    header['TestStationRevision'] = TestStationRevision
    
    CoreBundleRevision = fileobj.read(20)
    header['CoreBundleRevision'] = CoreBundleRevision
    
    AcquisitionName = fileobj.read(40)
    header['AcquisitionName'] = AcquisitionName
    
    AcquisitionParameterRevision = fileobj.read(20)
    header['AcquisitionParameterRevision'] = AcquisitionParameterRevision
    
    OriginalNumberOfRows = fileobj.read(2)
    OriginalNumberOfRows = struct.unpack("=H",OriginalNumberOfRows)[0]
    header['OriginalNumberOfRows'] = OriginalNumberOfRows
    
    OriginalNumberOfColumns = fileobj.read(2)
    OriginalNumberOfColumns = struct.unpack("=H",OriginalNumberOfColumns)[0]
    header['OriginalNumberOfColumns'] = OriginalNumberOfColumns
    
    RowNumberUpperLeftPointArchiveROI = fileobj.read(2)
    RowNumberUpperLeftPointArchiveROI = struct.unpack("=H",RowNumberUpperLeftPointArchiveROI)[0]
    header['RowNumberUpperLeftPointArchiveROI'] = RowNumberUpperLeftPointArchiveROI
    
    ColNumberUpperLeftPointArchiveROI = fileobj.read(2)
    ColNumberUpperLeftPointArchiveROI = struct.unpack("=H",ColNumberUpperLeftPointArchiveROI)[0]
    header['ColNumberUpperLeftPointArchiveROI'] = ColNumberUpperLeftPointArchiveROI
    
    Swapped = fileobj.read(2) 
    Swapped = struct.unpack("=H",Swapped)[0]
    header['Swapped'] = Swapped
    
    Reordered = fileobj.read(2) 
    Reordered = struct.unpack("=H",Reordered)[0]
    header['Reordered'] = Reordered
    
    HorizontalFlipped = fileobj.read(2) 
    HorizontalFlipped = struct.unpack("=H",HorizontalFlipped)[0]
    header['HorizontalFlipped'] = HorizontalFlipped
    
    VerticalFlipped = fileobj.read(2) 
    VerticalFlipped = struct.unpack("=H",VerticalFlipped)[0]
    header['VerticalFlipped'] = VerticalFlipped
    
    WindowValueDesired = fileobj.read(2) 
    WindowValueDesired = struct.unpack("=H",WindowValueDesired)[0]
    header['WindowValueDesired'] = WindowValueDesired
    
    LevelValueDesired = fileobj.read(2) 
    LevelValueDesired = struct.unpack("=H",LevelValueDesired)[0]
    header['LevelValueDesired'] = LevelValueDesired
    
    AcquisitionMode = fileobj.read(2) 
    AcquisitionMode = struct.unpack("=H",AcquisitionMode)[0]
    header['AcquisitionMode'] = AcquisitionMode
    
    AcquisitionType = fileobj.read(2) 
    AcquisitionType = struct.unpack("=H",AcquisitionType)[0]
    header['AcquisitionType'] = AcquisitionType
    
    UserAcquisitionCoffFileName1 = fileobj.read(100) 
    header['UserAcquisitionCoffFileName1'] = UserAcquisitionCoffFileName1
    
    UserAcquisitionCoffFileName2 = fileobj.read(100) 
    header['UserAcquisitionCoffFileName2'] = UserAcquisitionCoffFileName2
    
    FramesBeforeExpose = fileobj.read(2)
    FramesBeforeExpose = struct.unpack("=H",FramesBeforeExpose)[0]
    header['FramesBeforeExpose'] = FramesBeforeExpose
    
    FramesDuringExpose = fileobj.read(2)  
    FramesDuringExpose = struct.unpack("=H",FramesDuringExpose)[0]
    header['FramesDuringExpose'] = FramesDuringExpose
    
    FramesAfterExpose = fileobj.read(2) 
    FramesAfterExpose = struct.unpack("=H",FramesAfterExpose)[0]
    header['FramesAfterExpose'] = FramesAfterExpose
    
    IntervalBetweenFrames = fileobj.read(2) 
    IntervalBetweenFrames = struct.unpack("=H",IntervalBetweenFrames)[0]
    header['IntervalBetweenFrames'] = IntervalBetweenFrames
    
    ExposeTimeDelayInMicrosecs = fileobj.read(8) 
    ExposeTimeDelayInMicrosecs = struct.unpack("=d",ExposeTimeDelayInMicrosecs)[0]
    header['ExposeTimeDelayInMicrosecs'] = ExposeTimeDelayInMicrosecs
    
    TimeBetweenFramesInMicrosecs = fileobj.read(8) 
    TimeBetweenFramesInMicrosecs = struct.unpack("=d",TimeBetweenFramesInMicrosecs)[0]
    header['TimeBetweenFramesInMicrosecs'] = TimeBetweenFramesInMicrosecs
    
    FramesToSkipExpose = fileobj.read(2) 
    FramesToSkipExpose = struct.unpack("=H",FramesToSkipExpose)[0]
    header['FramesToSkipExpose'] = FramesToSkipExpose
    
    # Rad --> ExposureMode = 1
    ExposureMode = fileobj.read(2) 
    ExposureMode = struct.unpack("=H",ExposureMode)[0]
    header['ExposureMode'] = ExposureMode
    
    PrepPresetTimeInMicrosecs = fileobj.read(8)
    header['PrepPresetTimeInMicrosecs'] = PrepPresetTimeInMicrosecs
    
    PrepPresetTimeInMicrosecs = struct.unpack("=d",PrepPresetTimeInMicrosecs)[0]
    header['PrepPresetTimeInMicrosecs'] = PrepPresetTimeInMicrosecs
    
    ExposePresetTimeInMicrosecs = fileobj.read(8) 
    ExposePresetTimeInMicrosecs = struct.unpack("=d",ExposePresetTimeInMicrosecs)[0]
    header['ExposePresetTimeInMicrosecs'] = ExposePresetTimeInMicrosecs
    
    AcquisitionFrameRateInFps = fileobj.read(4) 
    AcquisitionFrameRateInFps = struct.unpack("=f",AcquisitionFrameRateInFps)[0]
    header['AcquisitionFrameRateInFps'] = AcquisitionFrameRateInFps
    
    FOVSelect = fileobj.read(2)
    FOVSelect = struct.unpack("=H",FOVSelect)[0]
    header['FOVSelect'] = FOVSelect
    
    ExpertMode = fileobj.read(2)
    ExpertMode = struct.unpack("=H",ExpertMode)[0]
    header['ExpertMode'] = ExpertMode
    
    SetVCommon1 = fileobj.read(8)
    SetVCommon1 = struct.unpack("=d",SetVCommon1)[0]
    header['SetVCommon1'] = SetVCommon1
    
    SetVCommon2 = fileobj.read(8)
    SetVCommon2 = struct.unpack("=d",SetVCommon2)[0]
    header['SetVCommon2'] = SetVCommon2
    
    SetAREF = fileobj.read(8)
    SetAREF = struct.unpack("=d",SetAREF)[0]
    header['SetAREF'] = SetAREF
    
    SetAREFTrim = fileobj.read(4)
    SetAREFTrim = struct.unpack("=L",SetAREFTrim)[0]
    header['SetAREFTrim'] = SetAREFTrim
    
    SetSpareVoltageSource = fileobj.read(8)
    SetSpareVoltageSource = struct.unpack("=d",SetSpareVoltageSource)[0]
    header['SetSpareVoltageSource'] = SetSpareVoltageSource
    
    SetCompensationVoltageSource = fileobj.read(8)
    SetCompensationVoltageSource = struct.unpack("=d",SetCompensationVoltageSource)[0]
    header['SetCompensationVoltageSource'] = SetCompensationVoltageSource
    
    SetRowOffVoltage = fileobj.read(8)
    SetRowOffVoltage = struct.unpack("=d",SetRowOffVoltage)[0]
    header['SetRowOffVoltage'] = SetRowOffVoltage
    
    SetRowOnVoltage = fileobj.read(8)
    SetRowOnVoltage = struct.unpack("=d",SetRowOnVoltage)[0]
    header['SetRowOnVoltage'] = SetRowOnVoltage
    
    StoreCompensationVoltage = fileobj.read(4)
    StoreCompensationVoltage = struct.unpack("=L",StoreCompensationVoltage)[0]
    header['StoreCompensationVoltage'] = StoreCompensationVoltage
    
    RampSelection = fileobj.read(2)
    RampSelection = struct.unpack("=H",RampSelection)[0]
    header['RampSelection'] = RampSelection
    
    TimingMode = fileobj.read(2)
    TimingMode = struct.unpack("=H",TimingMode)[0]
    header['TimingMode'] = TimingMode
    
    Bandwidth = fileobj.read(2)
    Bandwidth = struct.unpack("=H",Bandwidth)[0]
    header['Bandwidth'] = Bandwidth
    
    ARCIntegrator = fileobj.read(2)
    ARCIntegrator = struct.unpack("=H",ARCIntegrator)[0]
    header['ARCIntegrator'] = ARCIntegrator
    
    ARCPostIntegrator = fileobj.read(2)
    ARCPostIntegrator = struct.unpack("=H",ARCPostIntegrator)[0]
    header['ARCPostIntegrator'] = ARCPostIntegrator
    
    NumberOfRows = fileobj.read(4)
    NumberOfRows = struct.unpack("=L",NumberOfRows)[0]
    header['NumberOfRows'] = NumberOfRows
    
    RowEnable = fileobj.read(2)
    RowEnable = struct.unpack("=H",RowEnable)[0]
    header['RowEnable'] = RowEnable
    
    EnableStretch = fileobj.read(2)
    EnableStretch = struct.unpack("=H",EnableStretch)[0]
    header['EnableStretch'] = EnableStretch
    
    CompEnable = fileobj.read(2)
    CompEnable = struct.unpack("=H",CompEnable)[0]
    header['CompEnable'] = CompEnable
    
    CompStretch = fileobj.read(2)
    CompStretch = struct.unpack("=H",CompStretch)[0]
    header['CompStretch'] = CompStretch
    
    LeftEvenTristate = fileobj.read(2)
    LeftEvenTristate = struct.unpack("=H",LeftEvenTristate)[0]
    header['LeftEvenTristate'] = LeftEvenTristate
    
    RightOddTristate = fileobj.read(2)
    RightOddTristate = struct.unpack("=H",RightOddTristate)[0]
    header['RightOddTristate'] = RightOddTristate
    
    TestModeSelect = fileobj.read(4)
    TestModeSelect = struct.unpack("=L",TestModeSelect)[0]
    header['TestModeSelect'] = TestModeSelect
    
    AnalogTestSource = fileobj.read(4)
    AnalogTestSource = struct.unpack("=L",AnalogTestSource)[0]
    header['AnalogTestSource'] = AnalogTestSource
    
    VCommonSelect = fileobj.read(4)
    VCommonSelect = struct.unpack("=L",VCommonSelect)[0]
    header['VCommonSelect'] = VCommonSelect
    
    DRCColumnSum = fileobj.read(4)
    DRCColumnSum = struct.unpack("=L",DRCColumnSum)[0]
    header['DRCColumnSum'] = DRCColumnSum
    
    TestPatternFrameDelta = fileobj.read(4)
    TestPatternFrameDelta = struct.unpack("=L",TestPatternFrameDelta)[0]
    header['TestPatternFrameDelta'] = TestPatternFrameDelta
    
    TestPatternRowDelta = fileobj.read(4)
    TestPatternRowDelta = struct.unpack("=L",TestPatternRowDelta)[0]
    header['TestPatternRowDelta'] = TestPatternRowDelta
    
    TestPatternColumnDelta = fileobj.read(4)
    TestPatternColumnDelta = struct.unpack("=L",TestPatternColumnDelta)[0]
    header['TestPatternColumnDelta'] = TestPatternColumnDelta
    
    DetectorHorizontalFlip = fileobj.read(2)
    DetectorHorizontalFlip = struct.unpack("=H",DetectorHorizontalFlip)[0]
    header['DetectorHorizontalFlip'] = DetectorHorizontalFlip
    
    DetectorVerticalFlip = fileobj.read(2)
    DetectorVerticalFlip = struct.unpack("=H",DetectorVerticalFlip)[0]
    header['DetectorVerticalFlip'] = DetectorVerticalFlip
    
    DFNAutoScrubOnOff = fileobj.read(2)
    DFNAutoScrubOnOff = struct.unpack("=H",DFNAutoScrubOnOff)[0]
    header['DFNAutoScrubOnOff'] = DFNAutoScrubOnOff
    
    FiberChannelTimeOutInMicrosecs = fileobj.read(4)
    FiberChannelTimeOutInMicrosecs = struct.unpack("=L",FiberChannelTimeOutInMicrosecs)[0]
    header['FiberChannelTimeOutInMicrosecs'] = FiberChannelTimeOutInMicrosecs
    
    DFNAutoScrubDelayInMicrosecs = fileobj.read(4)
    DFNAutoScrubDelayInMicrosecs = struct.unpack("=L",DFNAutoScrubDelayInMicrosecs)[0]
    header['DFNAutoScrubDelayInMicrosecs'] = DFNAutoScrubDelayInMicrosecs
    
    StoreAECROI = fileobj.read(2)
    StoreAECROI = struct.unpack("=H",StoreAECROI)[0]
    header['StoreAECROI'] = StoreAECROI
    
    TestPatternSaturationValue = fileobj.read(2)
    TestPatternSaturationValue = struct.unpack("=H",TestPatternSaturationValue)[0]
    header['TestPatternSaturationValue'] = TestPatternSaturationValue
    
    TestPatternSeed = fileobj.read(4)
    TestPatternSeed = struct.unpack("=L",TestPatternSeed)[0]
    header['TestPatternSeed'] = TestPatternSeed
            
    ExposureTimeInMillisecs = fileobj.read(4) 
    ExposureTimeInMillisecs = struct.unpack("=f",ExposureTimeInMillisecs)[0]
    header['ExposureTimeInMillisecs'] = ExposureTimeInMillisecs
    
    FrameRateInFps = fileobj.read(4) 
    FrameRateInFps = struct.unpack("=f",FrameRateInFps)[0]
    header['FrameRateInFps'] = FrameRateInFps
    
    kVp = fileobj.read(4) 
    kVp = struct.unpack("=f",kVp)[0]
    header['kVp'] = kVp
    
    mA = fileobj.read(4) 
    mA = struct.unpack("=f",mA)[0]
    header['mA'] = mA
    
    mAs = fileobj.read(4) 
    mAs = struct.unpack("=f",mAs)[0]
    header['mAs'] = mAs
    
    FocalSpotInMM = fileobj.read(4) 
    FocalSpotInMM = struct.unpack("=f",FocalSpotInMM)[0]
    header['FocalSpotInMM'] = FocalSpotInMM
    
    GeneratorType = fileobj.read(20)
    header['GeneratorType'] = GeneratorType
    
    StrobeIntensityInFtL = fileobj.read(4) 
    StrobeIntensityInFtL = struct.unpack("=f",StrobeIntensityInFtL)[0]
    header['StrobeIntensityInFtL'] = StrobeIntensityInFtL
    
    NDFilterSelection = fileobj.read(2) 
    NDFilterSelection = struct.unpack("=H",NDFilterSelection)[0]
    header['NDFilterSelection'] = NDFilterSelection
    
    RefRegTemp1 = fileobj.read(8) 
    RefRegTemp1 = struct.unpack("=d",RefRegTemp1)[0]
    header['RefRegTemp1'] = RefRegTemp1
    
    RefRegTemp2 = fileobj.read(8) 
    RefRegTemp2 = struct.unpack("=d",RefRegTemp2)[0]
    header['RefRegTemp2'] = RefRegTemp2
    
    RefRegTemp3 = fileobj.read(8) 
    RefRegTemp3 = struct.unpack("=d",RefRegTemp3)[0]
    header['RefRegTemp3'] = RefRegTemp3
    
    Humidity1 = fileobj.read(4) 
    Humidity1 = struct.unpack("=f",Humidity1)[0]
    header['Humidity1'] = Humidity1
    
    Humidity2 = fileobj.read(4) 
    Humidity2 = struct.unpack("=f",Humidity2)[0]
    header['Humidity2'] = Humidity2
    
    DetectorControlTemp = fileobj.read(8) 
    DetectorControlTemp = struct.unpack("=d",DetectorControlTemp)[0]
    header['DetectorControlTemp'] = DetectorControlTemp
    
    DoseValueInmR = fileobj.read(8) 
    DoseValueInmR = struct.unpack("=d",DoseValueInmR)[0]
    header['DoseValueInmR'] = DoseValueInmR
    
    TargetLevelROIRow0 = fileobj.read(2)
    TargetLevelROIRow0 = struct.unpack("=H",TargetLevelROIRow0)[0]
    header['TargetLevelROIRow0'] = TargetLevelROIRow0
    
    TargetLevelROICol0 = fileobj.read(2)
    TargetLevelROICol0 = struct.unpack("=H",TargetLevelROICol0)[0]
    header['TargetLevelROICol0'] = TargetLevelROICol0
    
    TargetLevelROIRow1 = fileobj.read(2)
    TargetLevelROIRow1 = struct.unpack("=H",TargetLevelROIRow1)[0]
    header['TargetLevelROIRow1'] = TargetLevelROIRow1
    
    TargetLevelROICol1 = fileobj.read(2)
    TargetLevelROICol1 = struct.unpack("=H",TargetLevelROICol1)[0]
    header['TargetLevelROICol1'] = TargetLevelROICol1
    
    FrameNumberForTargetLevelROI = fileobj.read(2)
    FrameNumberForTargetLevelROI = struct.unpack("=H",FrameNumberForTargetLevelROI)[0]
    header['FrameNumberForTargetLevelROI'] = FrameNumberForTargetLevelROI
    
    PercentRangeForTargetLevel = fileobj.read(2)
    PercentRangeForTargetLevel = struct.unpack("=H",PercentRangeForTargetLevel)[0]
    header['PercentRangeForTargetLevel'] = PercentRangeForTargetLevel
    
    TargetValue = fileobj.read(2)
    TargetValue = struct.unpack("=H",TargetValue)[0]
    header['TargetValue'] = TargetValue
    
    ComputedMedianValue = fileobj.read(2)
    ComputedMedianValue = struct.unpack("=H",ComputedMedianValue)[0]
    header['ComputedMedianValue'] = ComputedMedianValue
    
    LoadZero = fileobj.read(2)
    LoadZero = struct.unpack("=H",LoadZero)[0]
    header['LoadZero'] = LoadZero
    
    MaxLUTOut = fileobj.read(2)
    MaxLUTOut = struct.unpack("=H",MaxLUTOut)[0]
    header['MaxLUTOut'] = MaxLUTOut
    
    MinLUTOut = fileobj.read(2)
    MinLUTOut = struct.unpack("=H",MinLUTOut)[0]
    header['MinLUTOut'] = MinLUTOut
    
    MaxLinear = fileobj.read(2)
    MaxLinear = struct.unpack("=H",MaxLinear)[0]
    header['MaxLinear'] = MaxLinear
    
    Reserved = fileobj.read(2)
    Reserved = struct.unpack("=H",Reserved)[0]
    header['Reserved'] = Reserved
    
    ElectronsPerCount = fileobj.read(2)
    ElectronsPerCount = struct.unpack("=H",ElectronsPerCount)[0]
    header['ElectronsPerCount'] = ElectronsPerCount
    
    ModeGain = fileobj.read(2)
    ModeGain = struct.unpack("=H",ModeGain)[0]
    header['ModeGain'] = ModeGain
    
    TemperatureInDegC = fileobj.read(8)
    TemperatureInDegC = struct.unpack("=d",TemperatureInDegC)[0]
    header['TemperatureInDegC'] = TemperatureInDegC
    
    LineRepaired = fileobj.read(2)
    LineRepaired = struct.unpack("=H",LineRepaired)[0]
    header['LineRepaired'] = LineRepaired
    
    LineRepairFileName = fileobj.read(100)
    header['LineRepairFileName'] = LineRepairFileName
            
    CurrentLongitudinalInMM = fileobj.read(4)
    CurrentLongitudinalInMM = struct.unpack("=f",CurrentLongitudinalInMM)[0]
    header['CurrentLongitudinalInMM'] = CurrentLongitudinalInMM
    
    CurrentTransverseInMM = fileobj.read(4)
    CurrentTransverseInMM = struct.unpack("=f",CurrentTransverseInMM)[0]
    header['CurrentTransverseInMM'] = CurrentTransverseInMM
    
    CurrentCircularInMM = fileobj.read(4)
    CurrentCircularInMM = struct.unpack("=f",CurrentCircularInMM)[0]
    header['CurrentCircularInMM'] = CurrentCircularInMM
    
    CurrentFilterSelection = fileobj.read(4)
    CurrentFilterSelection = struct.unpack("=L",CurrentFilterSelection)[0]
    header['CurrentFilterSelection'] = CurrentFilterSelection
    
    DisableScrubAck = fileobj.read(2)
    DisableScrubAck = struct.unpack("=H",DisableScrubAck)[0]
    header['DisableScrubAck'] = DisableScrubAck
    
    ScanModeSelect = fileobj.read(2)
    ScanModeSelect = struct.unpack("=H",ScanModeSelect)[0]
    header['ScanModeSelect'] = ScanModeSelect
    
    DetectorAppSwVersion = fileobj.read(20)	
    header['DetectorAppSwVersion'] = DetectorAppSwVersion
    
    DetectorNIOSVersion = fileobj.read(20)	
    header['DetectorNIOSVersion'] = DetectorNIOSVersion
    
    DetectorPeripheralSetVersion = fileobj.read(20)	
    header['DetectorPeripheralSetVersion'] = DetectorPeripheralSetVersion
    
    DetectorPhysicalAddress	 = fileobj.read(20)
    header['DetectorPhysicalAddress'] = DetectorPhysicalAddress
    
    PowerDown = fileobj.read(2)
    PowerDown = struct.unpack("=H",PowerDown)[0]
    header['PowerDown'] = PowerDown
    
    InitialVoltageLevel_VCOMMON = fileobj.read(8)
    InitialVoltageLevel_VCOMMON = struct.unpack("=d",InitialVoltageLevel_VCOMMON)[0]
    header['InitialVoltageLevel_VCOMMON'] = InitialVoltageLevel_VCOMMON
    
    FinalVoltageLevel_VCOMMON = fileobj.read(8)
    FinalVoltageLevel_VCOMMON = struct.unpack("=d",FinalVoltageLevel_VCOMMON)[0]
    header['FinalVoltageLevel_VCOMMON'] = FinalVoltageLevel_VCOMMON
    
    DmrCollimatorSpotSize	 = fileobj.read(10)
    header['DmrCollimatorSpotSize'] = DmrCollimatorSpotSize
    
    DmrTrack	 = fileobj.read(5)
    header['DmrTrack'] = DmrTrack
    
    DmrFilter	 = fileobj.read(5)
    header['DmrFilter'] = DmrFilter
    
    FilterCarousel = fileobj.read(2)
    FilterCarousel = struct.unpack("=H",FilterCarousel)[0]
    header['FilterCarousel'] = FilterCarousel
    
    Phantom	 = fileobj.read(20)
    header['Phantom'] = Phantom
    
    SetEnableHighTime = fileobj.read(2)
    SetEnableHighTime = struct.unpack("=H",SetEnableHighTime)[0]
    header['SetEnableHighTime'] = SetEnableHighTime
    
    SetEnableLowTime = fileobj.read(2)
    SetEnableLowTime = struct.unpack("=H",SetEnableLowTime)[0]
    header['SetEnableLowTime'] = SetEnableLowTime
    
    SetCompHighTime = fileobj.read(2)
    SetCompHighTime = struct.unpack("=H",SetCompHighTime)[0]
    header['SetCompHighTime'] = SetCompHighTime
    
    SetCompLowTime = fileobj.read(2)
    SetCompLowTime = struct.unpack("=H",SetCompLowTime)[0]
    header['SetCompLowTime'] = SetCompLowTime
    
    SetSyncLowTime = fileobj.read(2)
    SetSyncLowTime = struct.unpack("=H",SetSyncLowTime)[0]
    header['SetSyncLowTime'] = SetSyncLowTime
    
    SetConvertLowTime = fileobj.read(2)
    SetConvertLowTime = struct.unpack("=H",SetConvertLowTime)[0]
    header['SetConvertLowTime'] = SetConvertLowTime
    
    SetSyncHighTime = fileobj.read(2)
    SetSyncHighTime = struct.unpack("=H",SetSyncHighTime)[0]
    header['SetSyncHighTime'] = SetSyncHighTime
    
    SetEOLTime = fileobj.read(2)
    SetEOLTime = struct.unpack("=H",SetEOLTime)[0]
    header['SetEOLTime'] = SetEOLTime
    
    SetRampOffsetTime = fileobj.read(2)
    SetRampOffsetTime = struct.unpack("=H",SetRampOffsetTime)[0]
    header['SetRampOffsetTime'] = SetRampOffsetTime
            
    FOVStartingValue = fileobj.read(2)
    FOVStartingValue = struct.unpack("=H",FOVStartingValue)[0]
    header['FOVStartingValue'] = FOVStartingValue
    
    ColumnBinning = fileobj.read(2)
    ColumnBinning = struct.unpack("=H",ColumnBinning)[0]
    header['ColumnBinning'] = ColumnBinning
    
    RowBinning = fileobj.read(2)
    RowBinning = struct.unpack("=H",RowBinning)[0]
    header['RowBinning'] = RowBinning
    
    BorderColumns64 = fileobj.read(2)
    BorderColumns64 = struct.unpack("=H",BorderColumns64)[0]
    header['BorderColumns64'] = BorderColumns64
    
    BorderRows64 = fileobj.read(2)
    BorderRows64 = struct.unpack("=H",BorderRows64)[0]
    header['BorderRows64'] = BorderRows64
    
    FETOffRows64 = fileobj.read(2)
    FETOffRows64 = struct.unpack("=H",FETOffRows64)[0]
    header['FETOffRows64'] = FETOffRows64
    
    FOVStartColumn128 = fileobj.read(2)
    FOVStartColumn128 = struct.unpack("=H",FOVStartColumn128)[0]
    header['FOVStartColumn128'] = FOVStartColumn128
    
    FOVStartRow128 = fileobj.read(2)
    FOVStartRow128 = struct.unpack("=H",FOVStartRow128)[0]
    header['FOVStartRow128'] = FOVStartRow128
    
    NumberOfColumns128 = fileobj.read(2)
    NumberOfColumns128 = struct.unpack("=H",NumberOfColumns128)[0]
    header['NumberOfColumns128'] = NumberOfColumns128
    
    NumberOfRows128 = fileobj.read(2)
    NumberOfRows128 = struct.unpack("=H",NumberOfRows128)[0]
    header['NumberOfRows128'] = NumberOfRows128
        
    VFPAquisition	 = fileobj.read(2000)
    header['VFPAquisition'] = VFPAquisition
    
    Comment	 = fileobj.read(200)
    header['Comment'] = Comment
    
    fileobj.close()    
    return header

def NreadGE(filename, frameno):
    # NreadGE - read GE file from fastsweep image stack
    #
    #   INPUT:
    #
    #   filename
    #       name of the GE image stack file name
    #
    #   frameno
    #       frame to load
    #
    #   OUTPUT:
    #
    #   imdata
    #       image data in a [2048 x 2048] matrix
    #
    #   NOTE:
    #   1. if the image size changes, this file needs to be updated.
    #   2. if the buffer contains useful information, this file needs to read
    #   it in.
    import sys
    import os
    import numpy
    
    GE_buffer = 8192
    num_X = 2048
    num_Y = 2048
    
    filesize = os.path.getsize(filename)
    nFrames = (filesize - GE_buffer) / (2 * num_X * num_Y)
    
    with open(filename, mode='rb') as fileobj:
        if frameno > nFrames:
            print '\nthere are only ' + str(nFrames) + ' frames in ' + filename + '\n'
            sys.exit()
        else:
            offset = GE_buffer + (frameno - 1) * num_X * num_Y * 2
            fileobj.seek(offset)
            imdata = numpy.fromfile(fileobj, numpy.uint16, num_X * num_Y).astype('uint16')
    fileobj.close()
    
    return imdata

def NwriteGE(filename, imdata):
    # NwriteGE - write GE image stack file
    #
    #   INPUT:
    #
    #   filename
    #       name of the GE image stack file name
    #
    #   imdata
    #       image data to write
    #
    #   OUTPUT:
    #
    #   none
    #
    import sys
    import os
    import numpy
    
    GE_buffer = 8192
    
    fileobj = open(filename, mode='wb')
    fileobj.seek(GE_buffer)
    numpy.uint16(imdata).tofile(fileobj)
    fileobj.close()