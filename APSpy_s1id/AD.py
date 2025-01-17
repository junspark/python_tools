"""
**Area Detector Implementation Module**

*Module AD: Area-Detector access*
===================================

These routines provide a general framework for control of Area Detectors (AD). Also
included is a specific implementation for the commonly-used area detectors in 1-ID,
which are summarized in :ref:`commands_section`, below.

Kludged: \0 is added to all string caput calls (in :func:`AD_set`)

*Detector Access Routines*
--------------------------

These routines are used to change or read parameters for detectors, or to show
information about how these commands have been configured. 

======================  ============================================================
Access routines 	Description
======================  ============================================================
:func:`AD_get`	        Read an area detector parameter
:func:`AD_set`	        Set an area detector parameter
:func:`AD_acquire`      Set the filename, count time and frames and collect
:func:`AD_done`         Test if the detector(s) have completed data collection
:func:`AD_show`         Shows commands options for :func:`AD_get` and :func:`AD_set`
:func:`AD_cmds`         Returns but does not print commands options for
                        :func:`AD_get` and :func:`AD_set`
======================  ============================================================

*Detector Setup Routines*
-------------------------

These routines are used inside the module and are likely only changed by beamline staff. 

===========================  =====================================================
Setup routines               Description	 
===========================  =====================================================
:func:`DefineAreaDetector`   Define an area detector for later use
:func:`defADcmd`	     Define parameters to set up an area detector command
===========================  =====================================================

.. include:: ../AD_commands.txt

*Complete Function Descriptions*
--------------------------------

The functions available in this module are listed below.

"""


########### SVN repository information ###################
# $Date: 2013-04-24 18:41:03 -0500 (Wed, 24 Apr 2013) $
# $Author: jemian $
# $Revision: 1281 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/trunk/src/APSpy/AD.py $
# $Id: AD.py 1281 2013-04-24 23:41:03Z jemian $
########### SVN repository information ###################


EPICS = False
import spec
import numpy as np
import rst_table
DEBUG=spec.DEBUG
#DEBUG=True
try:
    import epics as ep  #from epics import PV
    EPICS = True
except:
    #print 'Note, PyEPICS was not found' # already printed in spec module
    pass

# list of defined detector types
#detectorTypeList = ('GE','ScintX','Retiga','Other')
detectorTypeList = []

def _cleanup_globals():
    ' cleanup old globals if this is a reload; for internal use only'
    if globals().get('DetectorList'):
        if DEBUG: print('cleaning up previous detector list')
        for obj in DetectorList:
            del globals()[obj.symbol]

# Define list of defined Detectors after deleting any defined detector globals
_cleanup_globals()
DetectorList = []
CommandDict={}
pvSim= {} # used for simulation only

def defADcmd(command, setsuffix, readsuffix, comment='', valtyp=int, 
                   det=None, enum=None):
    '''This is called to create a table of actions to be used for writing to detectors. This
    will normally only be used by beamline staff and only inside this routine. Define detector-specific
    commands first, if they should take precedence over generic ones.

    :param str command: A string to be used in :func:`AD_get` and :func:`AD_set` to
       be used to read or set an area detector parameter
    :param str setsuffix: The PV suffix to be used to set the parameter. This is appended to the end of
       controlprefix (if setsuffix begins with one % sign) or imageprefix (if setsuffix begins with twp % signs).
       If this is blank, the PV cannot be set. 
    :param str readsuffix: The PV suffix to be used to read the parameter. This is appended to the end of
       controlprefix (if readsuffix begins with one % sign) or imageprefix (if readsuffix begins with twp % signs).
       If this is blank, the PV cannot be read. 
    :param string comment: a optional human-readable text field that describes the command.
    :param type valtyp: a data type for the PV. Should be str, float or int (default)
    :param str detectortype: The type of the detector, if the command is not generic. The default is to
       define a command that can be used with all area detectors.
    :param str enum: A list of allowed values for the command, or a statement that must evaluate as True for the
      value to be accepted, typically a logical test on variable val. The default is allow all values.
      
      enum examples:
      
         ``enum=(0,1,2)``              -- defines three specific allowed values (0, 1 and 2). No others are valid.

         ``enum='val > 0'``            -- requires that the value must be greater than 0.0

         ``enum='0 <= val <= 10'``     -- requires the value be 0 or 10 or any value in between

    Examples:

    >>> # GE detector specific			
    >>> defADcmd('trigger_mode', '%TriggerMode', '%TriggerMode_RBV',
    ...    'Triggering: Angio=0, Rad=1, UserSingle=2, MultiDet=3',
    ...    det='GE', enum=(0,1,2,3))
    >>> defADcmd('state', '', '%DetectorState_RBV', 'Data collection state', det='GE')
    >>> defADcmd('autostore', '%%AutoStore', '%%AutoStore_RBV', 'Save images to file: No=0, Yes=1',
    ...    det='GE', enum=(0,1)) # overrides generic, below
    >>> defADcmd('autosave', '%%AutoStore', '%%AutoStore_RBV', 'Save images to file: No=0, Yes=1',
    ...    det='GE', enum=(0,1))		
    >>> #ScintX detector specific			
    >>> defADcmd('trigger_mode', '%TriggerMode', '%TriggerMode_RBV',
    ...    'Triggering mode: Internal=0, External=1',
    ...    det='ScintX', enum=(0,1))
    >>> defADcmd('video_mode', '%CCDVideoMode', '%CCDVideoMode_RBV',
    ...    'Format: 0=4024x2680, 2=2012x1340', det='ScintX',enum=(0,2))
    >>> #Retiga detector specific			
    >>> defADcmd('transfer', '%qInitialize', '', 'Transfer EPICS values to FPGA', det='Retiga', enum=(1,))
    >>> defADcmd('trigger_mode', '%TriggerMode', '%TriggerMode_RBV',
    ...     'Triggering: free=0, edge: Hi=1, low=2, Pulse: Hi=3, low=5, soft=5, Strobe: Hi=6, low=7, last=8',
    ...     det='Retiga', enum='0 <= val <= 8')
    >>> # Generic
    >>> defADcmd('acquire', '%Acquire', '', 'Trigger Data coll.',enum=(1,))
    >>> defADcmd('acquire_time', '%AcquireTime', '%AcquireTime_RBV', 'Data coll. time (sec)', float, enum='val > 0')
    >>> defADcmd('frames', '%NumImages', '%NumImages_RBV', 'number of frames (int)', enum='0 < val < 300')
    >>> defADcmd('filename', '%%FileName', '%%FileName_RBV', 'Set data filename', str)
    >>> defADcmd('filenumber', '%%FileNumber', '%%FileNumber_RBV', 'Next file number', int)
    >>> defADcmd('autoincrement', '%%AutoIncrement', '%%AutoIncrement_RBV',
    ...   'Overwrite current file or increment filenumber', int, enum=(0,1))
    >>> defADcmd('filepath', '%%FilePath', '%%FilePath_RBV', 'Full path for data file',str)


    '''
    class cmdobj(object):
        def __init__(self, setstr, readstr, useImagePrefix, valtyp, detectortype, enum, comment):
            self.setstr = setstr
            self.readstr = readstr
            self.useImagePrefix = useImagePrefix
            self.valtyp = valtyp
            self.detectortype = detectortype
            self.enum = enum
            self.comment = comment
                     
    Slist = setsuffix.strip().split('%')
    Rlist = readsuffix.strip().split('%')
    if len(Slist) > 1 and len(Rlist) > 1 and len(Slist) != len(Rlist):
        print('Warning for '+command+
              '. Prefixes do not agree:\n\tset='+setsuffix+
              '\n\tread='+readsuffix)
    if len(Slist) > 2:
        useImagePrefix = True
    else:
        useImagePrefix = False
    if len(Slist) > 0:
        setS = Slist[-1]
    else:
        setS = ""
    if len(Rlist) > 0:
        readS = Rlist[-1]
    else:
        readS = ""
    global CommandDict
    if CommandDict.get(command):
        CommandDict[command].append(cmdobj(setS, readS, useImagePrefix, valtyp, det, enum, comment))
    else:
        CommandDict[command] = [cmdobj(setS, readS, useImagePrefix, valtyp, det, enum, comment),]

def AD_show(detsym=None,allowprint=True):
    '''Shows all the commands defined for a particular detector, or with any detector.

    :param object detsym: An area detector variable (or name as a string), as defined in
      :func:`DefineAreaDetector`. Default is to only list commands that can be used
      with all detectors.
    :param bool allowprint: If True (default) prints a list of the allowed commands
    :returns: a list of allowed commands

    '''
    if detsym is None:
        detTyp = None
        if allowprint: print("Defined AD_get() & AD_set() commands for all Area Detectors")
    else:
        detObj = globals().get(detsym)
        if detObj is None: detObj = detsym
        if not isinstance(detObj,_ADobject):
            raise spec.specException('AD_show error: detsym '+str(detsym)+' is not defined in DefineAreaDetector')
        detTyp = detObj.detectortype
        if allowprint: print('Defined AD_get() & AD_set() commands for "'+str(detTyp)+'" Area Detectors')

    cmdlist = []
    for cmd in sorted(CommandDict):
        for cmdObj in CommandDict[cmd]:
            if cmdObj.detectortype == detTyp or cmdObj.detectortype is None:
                if allowprint: print('  '+("%-14s" % cmd)+'\t'+str(cmdObj.comment))
                cmdlist.append(cmd)
                break
    return cmdlist

def AD_cmds(detsym=None):
    '''Returns all the commands defined for a particular detector, or with any detector. Does not print.

    :param object detsym: An area detector variable (or name as a string), as defined in
      :func:`DefineAreaDetector`. Default is to only list commands that can be used
      with all detectors.
    :returns: a list of allowed commands

    '''
    return AD_show(detsym,allowprint=False)


def AD_get(detsyms,cmd,ignoreOK=False):
    '''Read a parameter from an area detector

    :param object detsyms: An area detector variable (or name as a string), as defined in
      :func:`DefineAreaDetector` or a list of area detector variables or strings.
      If a list (or tuple) of detectors is used, the function may
      return a list of values (but only if they differ.)
    :param str cmd: a command string that has been defined using :func:`defADcmd`
    :param bool ignoreOK: if ignoreOK is False (default) an exception will be raised if command
      cmd is not defined for a detector. If True, the command will be ignored

    :returns: the as-read parameter. The type will be determined by the PV associated with the command. If
      detsyms is a list and the read values differ, then a list of values is returned. Otherwise, only
      the (common) value is return.
    
    Examples:

    >>> AD.DefineAreaDetector('GE1', 'GE', 'GE1:cam1')
    >>> val = AD.AD_get(AD.GE1,'acquire_time')

    or 
    
    >>> val = AD.AD_get('GE1','acquire_time')

    also

    >>> hydra = (AD.GE1,AD.GE2,AD.GE3,AD.GE4)
    >>> val =  AD.AD_get(hydra,'trigger_mode')
    >>> try:
    >>>     if len(val) == 4 and not isinstance(val,str):
    >>>         print 'values disagree'
    >>> except TypeError:
    >>>     pass
    
    '''
    valList = []
    if cmd not in CommandDict:
        raise spec.specException('AD_get error: command '+str(cmd)+' is not defined')
    # is the detector specified as a string? 
    if isinstance(detsyms,str): detsyms = tuple((detsyms,))
    # is there a list of detectors?
    try:
        symList = tuple(detsyms)
    except TypeError:
        symList = tuple((detsyms,))
    for sym in symList:
        detObj = globals().get(sym)
        if detObj is None: detObj = sym
        if not isinstance(detObj,_ADobject):
            raise spec.specException('AD_get error: detsyms '+str(sym)+' is not defined in DefineAreaDetector')
        # get cmdObj of correct type for the current detector ==============================
        for cmdObj in CommandDict[cmd]:
            if cmdObj.detectortype is None: break #  this a generic command
            if cmdObj.detectortype == detObj.detectortype: break # matches selected device
        else:
            if ignoreOK: continue
            raise spec.specException('AD_get error: no match for command '+str(cmd)+
                                     ' and detector type '+detObj.detectortype)
        if cmdObj.readstr == "": 
            raise spec.specException('No AD_get "'+str(cmd)+'" read command')
        if cmdObj.useImagePrefix:
            PV = detObj.imageprefix + cmdObj.readstr
        else:
            PV = detObj.controlprefix + cmdObj.readstr
        if not (EPICS and spec.UseEPICS()): # in simulation
            val = pvSim.get(PV)
            if cmd == 'state': val = 0
            print("For "+detObj.symbol+" reading PV="+str(PV)+' value= '+str(val))
            valList.append(val)
            continue
        valList.append( ep.caget(PV,as_string=(cmdObj.valtyp==str)) )
    if len(valList) == 0:
        raise spec.specException('AD_get error: no detectors specified in '+str(detsyms))
    # return a single value or a list if they don't agree
    val = valList[0]
    for v in valList:
        if v != val:
            return valList
    return valList

def AD_set(detsyms,cmd,value,ignoreOK=False):
    '''Set a parameter for an area detector. *This routine has been patched to add a \0 to
    strings, to fix a problem in EPICS.*

    :param object detsyms: An area detector variable (or name as a string), as defined in
      :func:`DefineAreaDetector`. Alternately, a list of area detectors variable or names
      (as strings) can be supplied.
      The command (``cmd``) must be defined for all supplied detectors, or an exception occurs. 
    :param str cmd: a command that has been defined using :func:`defADcmd`
    :param str value: The value to set the parameter. This value will be set to the type defined for the
      command from :func:`defADcmd` if possible and will be checked against the enumeration range,
      if one is supplied. If the type conversion fails or the check fails, an exception is raised.

    :param bool ignoreOK: if ignoreOK is False (default) an exception will be raised if command
      cmd is not defined for a detector. If True, the command will be ignored
    :returns: the as-read parameter. The type will be determined by the PV associated with the command.
    
    Examples:

    >>> AD.DefineAreaDetector('GE1', 'GE', 'GE1:cam1')
    >>> val = AD.AD_set(AD.GE1,'acquire_time',3)

    or 
    
    >>> val = AD.AD_set('GE1','acquire_time',3)

    also

    >>> hydra = (AD.GE1,AD.GE2,AD.GE3,AD.GE4)
    >>> val =  AD.AD_set(hydra,'trigger_mode',0)

    '''

    if cmd not in CommandDict:
        raise spec.specException('AD_set error: command '+str(cmd)+' is not defined')
    # is the detector specified as a string? 
    if isinstance(detsyms,str): detsyms = tuple((detsyms,))
    # is there a list of detectors?
    try:
        symList = tuple(detsyms)
    except TypeError:
        symList = tuple((detsyms,))
    for sym in symList:
        detObj = globals().get(sym)
        if detObj is None: detObj = sym
        if not isinstance(detObj,_ADobject):
            raise spec.specException('AD_set error: detsyms '+str(sym)+' is not defined in DefineAreaDetector')
        # get cmdObj of correct type for the current detector ==============================
        for cmdObj in CommandDict[cmd]:
            if cmdObj.detectortype is None: break #  this a generic command
            if cmdObj.detectortype == detObj.detectortype: break # matches selected device
        else:
            if ignoreOK: continue
            raise spec.specException('AD_set error: no match for command '+str(cmd)+
                                     ' and detector type '+detObj.detectortype)
        if cmdObj.setstr == "": 
            raise spec.specException('No AD_set "'+str(cmd)+'" set command')
        # validate the supplied value =========================================================
        if cmdObj.enum is not None and not isinstance(cmdObj.enum,str):
            if value in cmdObj.enum:
                val = value
            else:
                raise spec.specException('AD_set error: value '+str(value)+
                                         ' is not in allowed list: '+str(cmdObj.enum))
        else:
            try:
                val = cmdObj.valtyp(value)
            except Exception, err:
                raise spec.specException('AD_set error: value '+str(value)+' is not of correct type')
        if isinstance(cmdObj.enum,str):
            try:
                tst = eval(cmdObj.enum)
            except Exception, err:
                tst = True
                print("AD_set: Error evaluating expression "+cmdObj.enum)
                print err
            if not tst:
                raise spec.specException('AD_set error: value '+str(value)+' is outside allowed range: '+cmdObj.enum)
        # set the PV as requested
        if cmdObj.useImagePrefix:
            PV = detObj.imageprefix +  cmdObj.setstr
        else:
            PV = detObj.controlprefix + cmdObj.setstr
        if cmdObj.readstr == "":
            rPV = ""
        elif cmdObj.useImagePrefix:
            rPV = detObj.imageprefix +  cmdObj.readstr
        else:
            rPV = detObj.controlprefix + cmdObj.readstr

        if not (EPICS and spec.UseEPICS()): # in simulation
            print("For "+detObj.symbol+", setting PV="+str(PV)+' to '+str(val))
            global pvSim
            pvSim[PV] = val
            pvSim[PV+'_RBV'] = val
            continue
        if isinstance(val,str):
            # add a \0 to the string, since EPICS does not seem to handle 
            # this correctly otherwise for some clients
            ep.caput(PV,val + '\0')
        else:
            ep.caput(PV,val)
        # now validate that the setting has been completed
        if cmdObj.valtyp == float and rPV != "":
            spec.sleep(0.05)
            setVal = ep.caget(rPV)
            i = 0
            while not np.allclose(setVal,val):
                i += 1
                if i > spec.MAX_RETRIES:
                    print("Warning: For "+detObj.symbol+", unable to set PV="+str(PV)+' to '+str(val))
                    break
                spec.sleep(0.1)
                setVal = ep.caget(rPV)
        elif  cmdObj.valtyp == str and rPV != "":
            setVal = None
            i = 0
            while setVal != val:
                if i > spec.MAX_RETRIES:
                    print("Warning: For "+detObj.symbol+", unable to set PV="+str(PV)+' to '+str(val))
                    break
                spec.sleep(0.05)
                setVal = ep.caget(rPV,as_string=True)
                if DEBUG: print setVal
                i += 1
        elif rPV != "":
            setVal = None
            i = 0
            while setVal != val:
                if i > spec.MAX_RETRIES:
                    print("Warning: For "+detObj.symbol+", unable to set PV="+str(PV)+' to '+str(val))
                    break
                spec.sleep(0.05)
                setVal = ep.caget(rPV)
                if DEBUG: print setVal
                i += 1

def AD_acquire(detsyms, filename, counttime, frames=1, wait=False):
    """Set parameters for an area detector and collect image(s)
    
    :param object detsyms: An area detector variable (or name as a string), as defined in
      :func:`DefineAreaDetector`. Alternately, a list of area detectors variable or names
      (as strings) can be supplied.
    :param str filename: The name of the data file to be used
    :param float counttime: The data collection pre frame time to be used (sec)
    :param int frames: The number of images to be recorded
    :param bool wait: If False (default) return immediately; if True, return after
      waiting the appropriate amount of time and 
      when the ``state`` command (if defined) indicates the data collection is done.
      
    """
    # set the PV's
    AD_set(detsyms,'filename',filename)
    AD_set(detsyms,'acquire_time',counttime)
    AD_set(detsyms,'frames',frames)
    spec.sleep(0.01)
    # for Retiga, transfer the values from EPICS to the device, for others this will be ignored
    AD_set(detsyms,'transfer',1,ignoreOK=True)
    spec.sleep(0.01)
    # start the acquisition
    AD_set(detsyms,'acquire',1)
    if not wait: return
    # wait for the detectors to finish
    AD_done(detsyms,wait=True)

def AD_done(detsyms,wait=True):
    """Test and optionally wait for the detector(s) have completed data collection

    :param object detsyms: An area detector variable (or name as a string), as defined in
      :func:`DefineAreaDetector`. Alternately, a list of area detectors variable or names
      (as strings) can be supplied.
    :param bool wait: If False test and return immediately; if True (default), return
      after the ``state`` command (if defined) indicates the data collection is done
      for each detector.

    :returns: True if all detector(s) are done; False is wait is False and any detectors are
      not done; or None if after 30 seconds, any detector is not complete
    """
    # is the detector specified as a string? 
    if isinstance(detsyms,str): detsyms = tuple((detsyms,))
    # is there a list of detectors?
    try:
        symList = tuple(detsyms)
    except TypeError:
        symList = tuple((detsyms,))
    alldone = True
    sleeptime = 0.0
    for sym in symList:
        detObj = globals().get(sym)
        if detObj is None: detObj = sym
        if not isinstance(detObj,_ADobject):
            raise spec.specException('AD_done error: detsyms '+str(sym)+' is not defined in DefineAreaDetector')
        # get cmdObj of correct type for the current detector ==============================
        for cmdObj in CommandDict['state']:
            if cmdObj.detectortype is None: break #  this a generic command
            if cmdObj.detectortype == detObj.detectortype: break # matches selected device
        else:
            continue
        if cmdObj.readstr == "": continue
        if cmdObj.useImagePrefix:
            PV = detObj.imageprefix + cmdObj.readstr
        else:
            PV = detObj.controlprefix + cmdObj.readstr
        if not (EPICS and spec.UseEPICS()): # in simulation
            print("Confirming detector "+detObj.symbol+" is done with collection")
            continue
        else:
            val = ep.caget(PV)
            if val == 0: continue # detector has completed
            if not wait: return False
            # detector is not done and a wait is requested
            while val != 0:
                if sleeptime > 30.0:
                    print('AD_done wait exceeded count*frames+30 seconds for'+detObj.symbol+', continuing with script')
                    return
                spec.sleep(0.1)
                sleeptime += 0.1
                val = ep.caget(PV)
    # all detector(s) have signed off as done
    return True
    
class _ADobject(object):
    """Defines an area detector instance
    """
    def __init__(self, detsym, detectortype, controlprefix, imageprefix, comment):
        if DEBUG: print("Defining "+str(detsym)+" with PVs="+str(controlprefix)+
                        ' and '+str(imageprefix))
        if globals().get(detsym) is None:
            globals()[detsym] = self
        else:
            raise spec.specException('Variable '+str(detsym)+' is in use')

        global detectorTypeList
        if detectortype not in detectorTypeList:
            detectorTypeList.append(detectortype)
        self.detectortype = detectortype
        #else:
        #    raise spec.specException('Type '+str(detectortype)+'for detector '+str(detsym)+
        #                             ' is not defined,\n  allowed choices are: '+str(detectorTypeList))
        self.symbol = detsym
        if controlprefix[-1] == ":":
            self.controlprefix = controlprefix
        else:
            self.controlprefix = controlprefix + ':'
        if imageprefix[-1] == ":":
            self.imageprefix = imageprefix
        else:
            self.imageprefix = imageprefix + ':'
        self.comment = comment

def DefineAreaDetector(detsym, detectortype, controlprefix, imageprefix=None, comment=''):
    """Define an area detector for use in this module
    
    :param str detsym: a symbolic name for the detector. A global variable is
      defined in this module's name space with this name, This must be unique;
      exception specException is raised if a name is reused.
    :param str detectortype: the type of the detector. This must match one of the entries in
      global variable detectorTypeList (case sensitive). 
    :param str controlprefix: the prefix for the detector PV (dev:camN).
      Omit the detector record field names (.NumImages, etc.).
      Inclusion of a final colon (':') is optional.
    :param str imageprefix: the prefix for the detector PV (dev:fmt).
      Omit the detector record field names (.FileNumber, etc.).
      Inclusion of a final colon (':') is optional.
      If not specified, defaults to the value for controlprefix
    :param string comment: a optional human-readable text field that describes the detector.

    :returns: detector object created for the detector

    Example: 

    >>> DefineAreaDetector('GE1', 'GE', 'GE1:cam1', comment='bottom')
    >>> DefineAreaDetector('GE2', 'GE', 'GE2:cam1', comment='left')
    >>> DefineAreaDetector('GE3', 'GE', 'GE3:cam1', comment='top')
    >>> DefineAreaDetector('GE4', 'GE', 'GE4:cam1', comment='right')
    >>> DefineAreaDetector('ScintX', 'ScintX', 'ScintX:cam1', 'ScintX:TIFF1:')
    >>> DefineAreaDetector('Retiga1', 'Retiga', 'QIMAGE1:cam1:', 'QIMAGE1:TIFF1:')
    >>> DefineAreaDetector('Retiga2', 'Retiga', 'QIMAGE2:cam1:', 'QIMAGE2:TIFF1:')

    """
    
    if imageprefix==None:
        imageprefix = controlprefix
        
    try: 
        obj = _ADobject(detsym, detectortype, controlprefix, imageprefix, comment)
    except spec.specException,err:
        print('Error in creating detector '+str(detsym)+'\n  '+str(err))
        raise spec.specException('Error defining Area Detector '+str(detsym))
        
    global DetectorList
    DetectorList.append(obj)
    return obj

#GE detector specific
defADcmd('trigger_mode', '%TriggerMode', '%TriggerMode_RBV',
         'Triggering: Angio=0, Rad=1, MULTI_DET SW=2, MULTI_DET Edge=3, MULTI_DET Pulse=4, MULTI_DET Custom=5',
         det='GE', enum=(0,1,2,3,4,5))
defADcmd('state', '', '%DetectorState_RBV', 'Data collection state',
         det='GE')
defADcmd('autostore', '%%AutoStore', '%%AutoStore_RBV',
         'Save images to file: No=0, Yes=1',
         det='GE', enum=(0,1)) # overrides generic, below
defADcmd('autosave', '%%AutoStore', '%%AutoStore_RBV',
         'Save images to file: No=0, Yes=1',
         det='GE', enum=(0,1))
defADcmd('buffersize1', '%%BufferSize1', '%%BufferSize1_RBV',
         'Buffer size', int, enum='0 < val < 290')
defADcmd('windowlevel', '%%WindowValueDesired', '%%WindowValueDesired_RBV',
         'Window value', int, enum='val > 0')
defADcmd('levelvalue', '%%LevelValueDesired', '%%LevelValueDesired_RBV',
         'Level value', int, enum='val > 0')
#ScintX detector specific			
defADcmd('trigger_mode', '%TriggerMode', '%TriggerMode_RBV',
         'Triggering mode: Internal=0, External=1',
         det='ScintX', enum=(0,1))
defADcmd('video_mode', '%CCDVideoMode', '%CCDVideoMode_RBV',
         'Format: 0=4024x2680, 2=2012x1340',
         det='ScintX',enum=(0,2))
defADcmd('state', '', '%Acquire', 'Data collection state',
         det='ScintX')
#Retiga detector specific			
defADcmd('transfer', '%qInitialize', '', 'Transfer EPICS values to FPGA',
         det='Retiga', enum=(1,))
defADcmd('trigger_mode', '%TriggerMode', '%TriggerMode_RBV',
         'Triggering: free=0, edge: Hi=1, low=2, Pulse: Hi=3, low=5, soft=5, Strobe: Hi=6, low=7, last=8',
         det='Retiga', enum='0 <= val <= 8')
# Generic
defADcmd('acquire', '%Acquire', '', 'Trigger Data collection: Stop=0, Acquire=1', enum=(0,1))
defADcmd('acquire_time', '%AcquireTime', '%AcquireTime_RBV',
         'Data collection time/frame (sec)', float, enum='val > 0')
defADcmd('frames', '%NumImages', '%NumImages_RBV',
         'number of frames', int, enum='0 < val < 300')
defADcmd('autostore', '%%AutoSave', '%%AutoSave_RBV',
         'Save images to file: No=0, Yes=1', enum=(0,1))
defADcmd('autosave', '%%AutoSave', '%%AutoSave_RBV',
         'Save images to file: No=0, Yes=1',enum=(0,1))
defADcmd('filename', '%%FileName', '%%FileName_RBV',
         'Set image filename', str)
defADcmd('filenumber', '%%FileNumber', '%%FileNumber_RBV',
         'Next file number', enum='val > 0')
defADcmd('filetemplate', '%%FileTemplate', '%%FileTemplate_RBV',
         'Set image filename template', str)
defADcmd('autoincrement', '%%AutoIncrement', '%%AutoIncrement_RBV',
         'Overwrite current file or increment filenumber', int, enum=(0,1))
defADcmd('filepath', '%%FilePath', '%%FilePath_RBV', 'Full path for data file',str)
defADcmd('lastfilename', '', '%%FullFileName_RBV', 'Full path of the last saved file',str)
# define the area detectors used at 1-ID
DefineAreaDetector('GE1', 'GE', 'GE1:cam1', comment='')
DefineAreaDetector('GE2', 'GE', 'GE2:cam1', comment='')
DefineAreaDetector('GE3', 'GE', 'GE3:cam1', comment='')
DefineAreaDetector('GE4', 'GE', 'GE4:cam1', comment='')
DefineAreaDetector('ScintX', 'ScintX', 'ScintX:cam1', 'ScintX:TIFF1:', comment='')
DefineAreaDetector('Retiga1', 'Retiga', 'QIMAGE1:cam1:', 'QIMAGE1:TIFF1:', comment='')
DefineAreaDetector('Retiga2', 'Retiga', 'QIMAGE2:cam1:', 'QIMAGE2:TIFF1:', comment='')

def _cmds_reST():
    '''Shows all the commands defined for all detector types in reStructure Text
    :returns: a big reST string

    '''
    def header():
        st = 20*'='
        st += "  "
        st += 60*'='
        st += "  "
        st += 15*'='
        st += "  "
        st += 20*'='
        st += "\n"
        return st
    def fmtline(a,b,c,d):
        st = ""
        for v,l in (a,20),(b,60),(c,15),(d,20):
            fmt = "%-"+str(l)+"s"
            st += (fmt % v)[:l]
            st += "  "
        st += "\n"
        return st
    types = {str:'str',int:'int',float:'float'}
    st =  "\n\n"
    det_list = []
    for detTyp in sorted(detectorTypeList):
        det_list.append( ":ref:`" + str(detTyp) + "<" + str(detTyp) + " detector commands>`" )
    st += "Below are lists of the commands that can be used in "
    st += ":func:`AD_get` and :func:`AD_set`, for each detector ("
    st += ", ".join(det_list) + "):\n\n"

    for detTyp in sorted(detectorTypeList):
        st += "\n.. index::\n"
        st += "   Detector-specific commands; " + str(detTyp) + "\n"
        st += "   " + str(detTyp) + " detector commands\n"
        st += "\n.. _" + str(detTyp) + " detector commands:\n"
        st += "\n*Defined commands for " + str(detTyp) + " detectors*\n"
        t = rst_table.Table()
        t.labels = ("command", "Explanation", "data type", "validator")
        for cmd in sorted(CommandDict):
            for cmdObj in CommandDict[cmd]:
                if cmdObj.detectortype == detTyp or cmdObj.detectortype is None:
                    explanation = cmdObj.comment
                    data_type = types.get(cmdObj.valtyp,'?')
                    validator = str(cmdObj.enum)
                    t.rows.append( [cmd, explanation, data_type, validator] )
            st += '\n' + t.reST() + '\n'
    return st

# If sphinx is loaded, we are probably running inside it: create a reST file with the currently defined commands in it
import sys
comment = r'''.. DO NOT EDIT THIS FILE!
  - - - - - - - - - - - - - - - - - - - - - - - -
  This file is automatically updated during a 
  (re)build of the Sphinx-based documentation from 
  code in the file AD.py.  Look in that file
  for this text to modify this comment.

.. _commands_section:

*Defined Commands*
------------------

'''
if 'sphinx' in sys.modules:
    print("Building the command listing file (AD_commands.txt)")
    try:
        fp = open("AD_commands.txt","w")
        fp.write(comment)
        fp.write(_cmds_reST())
        fp.close()
    except:
        pass

def _test1():
    print 70*'='
    for det in ('GE1',Retiga2,'ScintX',):
        AD_set(det,'acquire_time',3)
        val = AD_get(det,'acquire_time')
        print 'read=',val
        AD_set(det,'frames',3)
        val = AD_get(det,'frames')
        print 'read=',val
        AD_set(det,'filename','myfile.xxx')
        val = AD_get(det,'filename')
        print 'read=',val
        #AD_set(det,'autostore',3) # invalid value
        AD_set(det,'autostore',1)
        val = AD_get(det,'autostore')
        print 'read=',val

    hydra = (GE1,GE2,GE3,GE4)
    AD_set(hydra,'filename','myfile.xxx')
    val = AD_get(hydra,'filename')
    print 'read=',val
    AD_set(hydra,'trigger_mode',0)
    val = AD_get(hydra,'trigger_mode')
    print 'read=',val
    #AD_set(hydra,'state','myfile.xxx') # error
    val = AD_get(hydra,'state')
    print 'read=',val

    AD_set(ScintX,'trigger_mode',0)
    val = AD_get(ScintX,'trigger_mode')
    print 'read=',val


if __name__ == '__main__':
    _test1()
