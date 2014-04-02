###########################################################################
# DIC
###########################################################################
import epics as ep
import APSpy.AD as AD
import APSpy.macros as mac
import APSpy.spec as spec

import APSpy.macros_1id as mac1id
    
def DICSetup(det, pathname = None, filename = None, filenameformat = None, filenum = None):
    if pathname is None:
        print 'path name missing.'
        pathname = raw_input('enter path name (e.g. W:/park_Sep13/) : ')

    if filename is None:
        print 'file name missing.'
        filename = raw_input('enter file name : ')

    if filenameformat is None:
        print 'file name format missing.'
        filenameformat = raw_input('enter file name format (e.g. %s%s_%5.5d.tif) : ')

    if filenum is None:
        filenum = int(AD.AD_get(det, 'filenumber'))
    print 'next file number is ' + str(filenum)
    
    AD.AD_set(det, 'filepath', pathname)
    AD.AD_set(det, 'filename', filename)
    AD.AD_set(det, 'filetemplate', filenameformat)
    AD.AD_set(det, 'filenumber', filenum)
    AD.AD_set(det, 'array_callback', 1)
    
    return

def DICTakeImage(det, HutchLetter = None, expTime = None):
    if HutchLetter is None:
        print 'hutch letter missing.'
        print 'e: 1-id-e'
        HutchLetter = raw_input('enter hutch letter : ')

    ## LIGHT CONTROL
    if HutchLetter is 'e':
        # DIODE FOR OVERHEAD LIGHTS
        pvname = '1ide1:IPC1:ch3'
#        while mac1id.IsLightOn(pvname):
#            spec.sleep(0.5)

        # PULIZZI LIGHT SWITCH
        pv_indicator = '1ide1:IPC1:ch3'
        pv_on_switch = '1ide1:IPC1:on_ch3.PROC'
        pv_off_switch = '1ide1:IPC1:off_ch3.PROC'
        if ep.caget(pv_indicator) is False:
            print 'pulizzi dic light is off'
            while ep.caget(pv_indicator) is False:
                ep.caput(pv_on_switch, 1)
                spec.sleep(0.25)
            print 'pulizzi dic light is on'
    else:
        print 'no photo diodes / dic lights implemented'
    
    AD.AD_set(det, 'image_mode', 0)
    AD.AD_set(det, 'autosave', 1)
    AD.AD_set(det, 'acquire_time', expTime)
    AD.AD_set(det, 'acquire', 1)
    
    while AD.AD_get(det, 'state'):
        spec.sleep(0.25)

    AD.AD_set(det, 'autosave', 0)
    
    filenum = AD.AD_get(det, 'filenumber') - 1
    print 'last image number is ' + str(filenum)

def DICLiveImage(det, HutchLetter = None, expTime = None):
    if HutchLetter is None:
        print 'hutch letter missing.'
        print 'e: 1-id-e'
        HutchLetter = raw_input('enter hutch letter : ')

    ## LIGHT CONTROL
    if HutchLetter is 'e':
        # DIODE FOR OVERHEAD LIGHTS
        pvname = '1ide1:IPC1:ch3'
#        while mac1id.IsLightOn(pvname):
#            spec.sleep(0.5)

        # PULIZZI LIGHT SWITCH
        pv_indicator = '1ide1:IPC1:ch3'
        pv_on_switch = '1ide1:IPC1:on_ch3.PROC'
        pv_off_switch = '1ide1:IPC1:off_ch3.PROC'
        if ep.caget(pv_indicator) is False:
            print 'pulizzi dic light is off'
            while ep.caget(pv_indicator) is False:
                ep.caput(pv_on_switch, 1)
                spec.sleep(0.25)
            print 'pulizzi dic light is on'
    else:
        print 'no photo diodes / dic lights implemented'

    AD.AD_set(det, 'image_mode', 2)
    AD.AD_set(det, 'autosave', 0)
    AD.AD_set(det, 'acquire_time', expTime)
    print 'python console control returned'
    print 'press STOP button to finish live dic feed'
    AD.AD_set(det, 'acquire', 1)
