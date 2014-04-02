clear all
close all
clc

pname   = 'W:\park_apr2013b';
fname   = 'vff_00013.ge2';
pfname  = fullfile(pname, fname);

% a = char(a)
buffer  = 8192;

fp      = fopen(pfname,'r','n');

Header.ImageFormat                  = fread(fp, 10, '*char')';
Header.VersionOfStandardHeader      = fread(fp, 1, '*ushort')';
Header.StandardHeaderSizeInBytes    = fread(fp, 1, '*ulong')';
Header.VersionOfUserHeader          = fread(fp, 1, '*ushort')';
Header.UserHeaderSizeInBytes        = fread(fp, 1, '*ulong')';
Header.NumberOfFrames               = fread(fp, 1, '*ushort')';
Header.NumberOfRowsInFrame          = fread(fp, 1, '*ushort')';
Header.NumberOfColsInFrame          = fread(fp, 1, '*ushort')';
Header.ImageDepthInBits             = fread(fp, 1, '*ushort')';
Header.AcquisitionDate              = fread(fp, 20, '*char')';
Header.AcquisitionTime              = fread(fp, 20, '*char')';
Header.DUTID                        = fread(fp, 20, '*char')';
Header.Operator                     = fread(fp, 50, '*char')';
Header.DetectorSignature            = fread(fp, 20, '*char')';
Header.TestSystemName               = fread(fp, 20, '*char')';
Header.TestStationRevision          = fread(fp, 20, '*char')';
Header.CoreBundleRevision           = fread(fp, 20, '*char')';
Header.AcquisitionName              = fread(fp, 40, '*char')';
Header.AcquisitionParameterRevision = fread(fp, 20, '*char')';
Header.OriginalNumberOfRows         = fread(fp, 1, '*ushort')';
Header.OriginalNumberOfColumns      = fread(fp, 1, '*ushort')';

Header.RowNumberUpperLeftPointArchiveROI    = fread(fp, 1, '*ushort')';
Header.ColNumberUpperLeftPointArchiveROI    = fread(fp, 1, '*ushort')';

Header.Swapped      = fread(fp, 1, '*ushort')';
Header.Reordered    = fread(fp, 1, '*ushort')';

Header.HorizontalFlipped    = fread(fp, 1, '*ushort')';
Header.VerticalFlipped      = fread(fp, 1, '*ushort')';
Header.WindowValueDesired   = fread(fp, 1, '*ushort')';
Header.LevelValueDesired    = fread(fp, 1, '*ushort')';
Header.AcquisitionMode      = fread(fp, 1, '*ushort')';
Header.AcquisitionType      = fread(fp, 1, '*ushort')';

Header.UserAcquisitionCoffFileName1 = fread(fp, 100, '*char')';
Header.UserAcquisitionCoffFileName2 = fread(fp, 100, '*char')';

Header.FramesBeforeExpose   = fread(fp, 1, '*ushort')';
Header.FramesDuringExpose   = fread(fp, 1, '*ushort')';
Header.FramesAfterExpose    = fread(fp, 1, '*ushort')';

Header.IntervalBetweenFrames        = fread(fp, 1, '*ushort')';
Header.ExposeTimeDelayInMicrosecs   = fread(fp, 1, '*double')';
Header.TimeBetweenFramesInMicrosecs = fread(fp, 1, '*double')';

Header.FramesToSkipExpose	= fread(fp, 1, '*ushort')';

% # Rad --> ExposureMode = 1
Header.ExposureMode	= fread(fp, 1, '*ushort')';

Header.PrepPresetTimeInMicrosecs    = fread(fp, 1, '*double')';
Header.ExposePresetTimeInMicrosecs  = fread(fp, 1, '*double')';
Header.AcquisitionFrameRateInFps    = fread(fp, 1, '*float')';

Header.FOVSelect    = fread(fp, 1, '*ushort')';
Header.ExpertMode   = fread(fp, 1, '*ushort')';

Header.SetVCommon1  = fread(fp, 1, '*double')';
Header.SetVCommon2  = fread(fp, 1, '*double')';
Header.SetAREF      = fread(fp, 1, '*double')';
Header.SetAREFTrim  = fread(fp, 1, '*ulong')';

Header.SetSpareVoltageSource        = fread(fp, 1, '*double')';
Header.SetCompensationVoltageSource = fread(fp, 1, '*double')';

Header.SetRowOffVoltage = fread(fp, 1, '*double')';
Header.SetRowOnVoltage  = fread(fp, 1, '*double')';

Header.StoreCompensationVoltage = fread(fp, 1, '*ulong')';

Header.RampSelection    = fread(fp, 1, '*ushort')';
Header.TimingMode       = fread(fp, 1, '*ushort')';
Header.Bandwidth        = fread(fp, 1, '*ushort')';
Header.ARCIntegrator    = fread(fp, 1, '*ushort')';

Header.ARCPostIntegrator    = fread(fp, 1, '*ushort')';
Header.NumberOfRows         = fread(fp, 1, '*ulong')';
Header.RowEnable            = fread(fp, 1, '*ushort')';
Header.EnableStretch        = fread(fp, 1, '*ushort')';
Header.CompEnable           = fread(fp, 1, '*ushort')';
Header.CompStretch          = fread(fp, 1, '*ushort')';
Header.LeftEvenTristate     = fread(fp, 1, '*ushort')';

Header.RightOddTristate = fread(fp, 1, '*ushort')';
Header.TestModeSelect   = fread(fp, 1, '*ulong')';
Header.VCommonSelect    = fread(fp, 1, '*ulong')';
Header.DRCColumnSum     = fread(fp, 1, '*ulong')';

Header.TestPatternFrameDelta    = fread(fp, 1, '*ulong')';
Header.TestPatternRowDelta      = fread(fp, 1, '*ulong')';
Header.TestPatternColumnDelta   = fread(fp, 1, '*ulong')';
Header.DetectorHorizontalFlip   = fread(fp, 1, '*ushort')';
Header.DetectorVerticalFlip     = fread(fp, 1, '*ushort')';
Header.DFNAutoScrubOnOff        = fread(fp, 1, '*ushort')';
fread(fp, 1, '*ulong')';

Header.FiberChannelTimeOutInMicrosecs   = fread(fp, 1, '*ulong')';
Header.DFNAutoScrubDelayInMicrosecs     = fread(fp, 1, '*ulong')'
return

Header.StoreAECROI                  = fread(fp, 1, '*ushort')';
Header.TestPatternSaturationValue   = fread(fp, 1, '*ushort')';

Header.TestPatternSeed          = fread(fp, 1, '*ulong')';
Header.ExposureTimeInMillisecs  = fread(fp, 1, '*float')';
Header.FrameRateInFps           = fread(fp, 1, '*float')';

Header.kVp	= fread(fp, 1, '*float')';
Header.mA   = fread(fp, 1, '*float')';
Header.mAs  = fread(fp, 1, '*float')';

Header.FocalSpotInMM    = fread(fp, 1, '*float')';
Header.GeneratorType    = fread(fp, 20, '*char')';

Header.StrobeIntensityInFtL = fread(fp, 1, '*float')';
Header.NDFilterSelection    = fread(fp, 1, '*ushort')';

Header.RefRegTemp1	= fread(fp, 1, '*double')';
Header.RefRegTemp2  = fread(fp, 1, '*double')';
Header.RefRegTemp3  = fread(fp, 1, '*double')';
Header.Humidity1    = fread(fp, 1, '*float')';
Header.Humidity2    = fread(fp, 1, '*float')';

Header.DetectorControlTemp  = fread(fp, 1, '*double')';
Header.DoseValueInmR        = fread(fp, 1, '*double')';
Header.TargetLevelROIRow0   = fread(fp, 1, '*ushort')';
Header.TargetLevelROICol0   = fread(fp, 1, '*ushort')';
Header.TargetLevelROIRow1   = fread(fp, 1, '*ushort')';
Header.TargetLevelROICol1   = fread(fp, 1, '*ushort')';

Header.FrameNumberForTargetLevelROI = fread(fp, 1, '*ushort')';
Header.PercentRangeForTargetLevel   = fread(fp, 1, '*ushort')';

Header.TargetValue          = fread(fp, 1, '*ushort')';
Header.ComputedMedianValue  = fread(fp, 1, '*ushort')'

% Header.LoadZero     = fread(fp, 1, '*ushort')';
% Header.MaxLUTOut    = fread(fp, 1, '*ushort')';
% Header.MinLUTOut    = fread(fp, 1, '*ushort')';
% Header.MaxLinear    = fread(fp, 1, '*ushort')';
% Header.Reserved     = fread(fp, 1, '*ushort')'
% 
% Header.ElectronsPerCount    = fread(fp, 1, '*ushort')';
% Header.ModeGain             = fread(fp, 1, '*ushort')';
% Header.TemperatureInDegC    = fread(fp, 1, '*double')'

% TemperatureInDegC = fp.read(8)
% TemperatureInDegC = struct.unpack("=d",TemperatureInDegC)[0]
% #print "TemperatureInDegC \t",
% #print TemperatureInDegC
% 
% LineRepaired = fp.read(2)
% LineRepaired = struct.unpack("=H",LineRepaired)[0]
% #print "LineRepaired \t",
% #print LineRepaired
% 
% LineRepairFileName = fp.read(100)
% #print "LineRepairFileNam \t",
% #print LineRepairFileName
% 
% 
% CurrentLongitudinalInMM = fp.read(4)
% CurrentLongitudinalInMM = struct.unpack("=f",CurrentLongitudinalInMM)[0]
% #print "CurrentLongitudinalInMM \t",
% #print CurrentLongitudinalInMM
% 
% CurrentTransverseInMM = fp.read(4)
% CurrentTransverseInMM = struct.unpack("=f",CurrentTransverseInMM)[0]
% #print "CurrentTransverseInMM \t",
% #print CurrentTransverseInMM
% 
% CurrentCircularInMM = fp.read(4)
% CurrentCircularInMM = struct.unpack("=f",CurrentCircularInMM)[0]
% #print "CurrentCircularInMM \t",
% #print CurrentCircularInMM
% 
% CurrentFilterSelection = fp.read(4)
% CurrentFilterSelection = struct.unpack("=L",CurrentFilterSelection)[0]
% #print "CurrentFilterSelection \t",
% #print CurrentFilterSelection
% 
% DisableScrubAck = fp.read(2)
% DisableScrubAck = struct.unpack("=H",DisableScrubAck)[0]
% #print "DisableScrubAck \t",
% #print DisableScrubAck
% 
% ScanModeSelect = fp.read(2)
% ScanModeSelect = struct.unpack("=H",ScanModeSelect)[0]
% #print "ScanModeSelect \t",
% #print ScanModeSelect
% 
% DetectorAppSwVersion = fp.read(20)	
% #print "DetectorAppSwVersion \t",
% #print DetectorAppSwVersion
% 
% DetectorNIOSVersion = fp.read(20)	
% #print "DetectorNIOSVersion \t",
% #print DetectorNIOSVersion
% 
% DetectorPeripheralSetVersion = fp.read(20)	
% #print "DetectorPeripheralSetVersion \t"
% #print DetectorPeripheralSetVersion
% 
% DetectorPhysicalAddress	 = fp.read(20)
% #print "DetectorPhysicalAddress \t",
% #print DetectorPhysicalAddress
% 
% PowerDown = fp.read(2)
% PowerDown = struct.unpack("=H",PowerDown)[0]
% #print "PowerDown \t",
% #print PowerDown
% 
% InitialVoltageLevel_VCOMMON = fp.read(8)
% InitialVoltageLevel_VCOMMON = struct.unpack("=d",InitialVoltageLevel_VCOMMON)[0]
% #print "InitialVoltageLevel_VCOMMON \t",
% #print InitialVoltageLevel_VCOMMON
% 
% FinalVoltageLevel_VCOMMON = fp.read(8)
% FinalVoltageLevel_VCOMMON = struct.unpack("=d",FinalVoltageLevel_VCOMMON)[0]
% #print "FinalVoltageLevel_VCOMMON \t",
% #print FinalVoltageLevel_VCOMMON
% 
% DmrCollimatorSpotSize	 = fp.read(10)
% #print "DmrCollimatorSpotSize \t",
% #print DmrCollimatorSpotSize
% 
% DmrTrack	 = fp.read(5)
% #print "DmrTrack \t",
% #print DmrTrack
% 
% DmrFilter	 = fp.read(5)
% #print "DmrFilter \t",
% #print DmrFilter
% 
% FilterCarousel = fp.read(2)
% FilterCarousel = struct.unpack("=H",FilterCarousel)[0]
% #print "FilterCarousel \t",
% #print FilterCarousel
% 
% Phantom	 = fp.read(20)
% #print "Phantom \t",
% #print Phantom
% 
% SetEnableHighTime = fp.read(2)
% SetEnableHighTime = struct.unpack("=H",SetEnableHighTime)[0]
% #print "SetEnableHighTime \t",
% #print SetEnableHighTime
% 
% SetEnableLowTime = fp.read(2)
% SetEnableLowTime = struct.unpack("=H",SetEnableLowTime)[0]
% #print "SetEnableLowTime \t",
% #print SetEnableLowTime
% 
% SetCompHighTime = fp.read(2)
% SetCompHighTime = struct.unpack("=H",SetCompHighTime)[0]
% #print "SetCompHighTime \t",
% #print SetCompHighTime
% 
% SetCompLowTime = fp.read(2)
% SetCompLowTime = struct.unpack("=H",SetCompLowTime)[0]
% #print "SetCompLowTime \t",
% #print SetCompLowTime
% 
% SetSyncLowTime = fp.read(2)
% SetSyncLowTime = struct.unpack("=H",SetSyncLowTime)[0]
% #print "SetSyncLowTime \t",
% #print SetSyncLowTime
% 
% SetConvertLowTime = fp.read(2)
% SetConvertLowTime = struct.unpack("=H",SetConvertLowTime)[0]
% #print "SetConvertLowTime \t",
% #print SetConvertLowTime
% 
% SetSyncHighTime = fp.read(2)
% SetSyncHighTime = struct.unpack("=H",SetSyncHighTime)[0]
% #print "SetSyncHighTime \t",
% #print SetSyncHighTime
% 
% SetEOLTime = fp.read(2)
% SetEOLTime = struct.unpack("=H",SetEOLTime)[0]
% #print "SetEOLTime \t",
% #print SetEOLTime
% 
% SetRampOffsetTime = fp.read(2)
% SetRampOffsetTime = struct.unpack("=H",SetRampOffsetTime)[0]
% #print "SetRampOffsetTime \t",
% #print SetRampOffsetTime
% 
% 
% FOVStartingValue = fp.read(2)
% FOVStartingValue = struct.unpack("=H",FOVStartingValue)[0]
% #print "FOVStartingValue \t",
% #print FOVStartingValue
% 
% ColumnBinning = fp.read(2)
% ColumnBinning = struct.unpack("=H",ColumnBinning)[0]
% #print "ColumnBinning \t",
% #print ColumnBinning
% 
% RowBinning = fp.read(2)
% RowBinning = struct.unpack("=H",RowBinning)[0]
% #print "RowBinning \t",
% #print RowBinning
% 
% BorderColumns64 = fp.read(2)
% BorderColumns64 = struct.unpack("=H",BorderColumns64)[0]
% #print "BorderColumns64 \t",
% #print BorderColumns64
% 
% BorderRows64 = fp.read(2)
% BorderRows64 = struct.unpack("=H",BorderRows64)[0]
% #print "BorderRows64 \t",
% #print BorderRows64
% 
% FETOffRows64 = fp.read(2)
% FETOffRows64 = struct.unpack("=H",FETOffRows64)[0]
% #print "FETOffRows64 \t",
% #print FETOffRows64
% 
% FOVStartColumn128 = fp.read(2)
% FOVStartColumn128 = struct.unpack("=H",FOVStartColumn128)[0]
% #print "FOVStartColumn128 \t",
% #print FOVStartColumn128
% 
% FOVStartRow128 = fp.read(2)
% FOVStartRow128 = struct.unpack("=H",FOVStartRow128)[0]
% #print "FOVStartRow128 \t",
% #print FOVStartRow128
% 
% NumberOfColumns128 = fp.read(2)
% NumberOfColumns128 = struct.unpack("=H",NumberOfColumns128)[0]
% #print "NumberOfColumns128 \t",
% #print NumberOfColumns128
% 
% NumberOfRows128 = fp.read(2)
% NumberOfRows128 = struct.unpack("=H",NumberOfRows128)[0]
% #print "NumberOfRows128 \t",
% #print NumberOfRows128
% 
% #print fp.tell()
% 
% VFPAquisition	 = fp.read(2000)
% #print "VFPAquisition \t",
% #print VFPAquisition
% 
% Comment	 = fp.read(200)
% #print "Comment \t",
% #print Comment
% 
% #print fp.tell()
% #fp.seek(8192)


% offset  = buffer + (frameno-1)*2048*2048*2;
% fseek(fp,offset,'bof');

img     = fread(fp,[2048 2048],'uint16');

fclose(fp);
