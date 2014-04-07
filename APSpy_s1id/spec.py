"""
**SPEC Simulation module**

*Module spec: SPEC-like emulation*
===================================

The Python functions in this module are designed to emulate similar
commands/macros in SPEC or provide similar functionality. They require the
PyEpics [#]_ package. 

.. [#] PyEpics: http://cars9.uchicago.edu/software/python/pyepics3/

*Motor interface routines*
--------------------------

===============================  ==============  ==============
Description                      Relative        Absolute
===============================  ==============  ==============
move motor                       :func:`mvr`	    :func:`mv`
move motor with wait             :func:`umvr`    :func:`umv`
move multiple motors [#C]_       ..              :func:`mmv`
move multiple w/wait [#C]_       ..              :func:`ummv`
where is this motor?             ..              :func:`wm`
where are all motors?            ..              :func:`wa`
===============================  ==============  ==============

.. [#C] These commands implement capabilities not present in SPEC. 

*Scaler routines*
-----------------

===========================================	====================
description                                	command
===========================================	====================
start and readout scaler after completion  	:func:`ct`
start scaler and return                    	:func:`count_em`
wait for scaler to complete                	:func:`wait_count`
read scaler                                	:func:`get_counts`
===========================================	====================

*More spec-like capabilities*
-----------------------------

=============================  =================
description                    command
=============================  =================
Turn simulation mode on        :func:`onsim()`
Turn simulation mode off       :func:`offsim()`
array of motor positions       :ref:`A-sec`
array of last count values     :ref:`S-sec`
=============================  =================

*Routines not in spec*
-------------------------------

===========================  ============================================================
Routine                      Description
===========================  ============================================================
:func:`sleep`                Delay for a specified amount of time
:func:`EnableEPICS`          Turns simulation mode on or off
:func:`UseEPICS`             Show if EPICS should be accessed
:func:`DefineMtr`            Define a motor to be accessed
:func:`DefinePseudoMtr`      Define pseudo motors from previously defined motors
:func:`GetMtrInfo`           Retrieves all motor info from a key
:func:`DefineMotorSymbols`   Used to define motor symbols in caller's namespace
:func:`DefineScaler`	     Define a scaler to be accessed
:func:`GetScalerInfo`	     Retrieves all scaler info from an index
:func:`ListMtrs`             Returns a list of motor symbols
:func:`Sym2MtrVal`           Retrieves the motor entry key from a symbol
:func:`ExplainMtr`           Retrieves the motor description from a key or symbol
:func:`ReadMtr`              Returns the motor position from a key
:func:`PositionMtr`          Moves a motor
:func:`MoveMultipleMtr`      Move several motors together
:func:`GetScalerLastCount`   Returns the last set of counts that have been read for a scaler
:func:`GetScalerLastTime`    Returns the counting time for the last use of a scaler
:func:`GetScalerLabels`      Returns the labels that have been retrieved for a scaler
:func:`SetMon`               Set the monitor channel for the scaler
:func:`GetMon`               Return the monitor channel for the scaler
:func:`SetDet`               Set the main detector channel for the scaler
:func:`GetDet`               Return the main detector channel for the scaler
:func:`setCOUNT`             Sets the default counting time
:func:`initElapsed`          Initialize the elapsed time counter
:func:`setElapsed`           Update the elapsed time counter
:func:`setRETRIES`           Sets the maximum number of EPICS retries
:func:`setDEBUG`             Sets debugging mode (printing lots of stuff) on or off
===========================  ============================================================


.. _Globals:

*Global variables*
------------------

As described below, these variables can be read from outside of the package,
but should be set with care. 

.. index:: COUNT

:COUNT: defines the default counting time (sec) when ct is called without an argument. Defaults to 1 sec. Use
  :func:`setCOUNT` to set this when using ``from APSpy.spec import *``, as setting the variable directly has problems:

   This will sort-of work:
      >>>  from APSpy.spec import *
      >>>  import APSpy.spec
      >>>  APSpy.spec.COUNT=3
      
      however, COUNT in the local namespace will still have the old value.

   but this will not work:
      >>>  from APSpy.spec import *
      >>>  COUNT=3
      
      This fails because the local copy of COUNT gets replaced, but the copy of COUNT actually
      in the spec module is left unchanged.

----------------

.. index:: MAX_RETRIES

:MAX_RETRIES:
   Number of times to retry an EPICS operation (that are nominally 
   expected to work on the first try) before generating an exception. 
   Use :func:`setRETRIES` to set this or care when changing 
   this (see comment on :data:`COUNT`, in this section.)

----------------

.. index:: DEBUG

:DEBUG:
   When set to True lots of print statements to be executed. Use for code development/testing.
   Use :func:`setDEBUG` to set this or care when changing this (see comment on :data:`COUNT`, above
   in this section.)

.. index:: ELAPSED

:ELAPSED:
   Contains the time that has elapsed between when the spec module was loaded
   (or :func:`initElapsed` was called) and when :func:`setElapsed` was last called,
   which happens when motors are moved or counting is done or :func:`sleep` is called.

.. index:: SIMSPEED

.. _SIMSPEED-sec:

:SIMSPEED:
  When in simulation mode, scripts are sped up by decreasing delays (calls to :func:`spec.sleep`)
  by a factor of ``SIMSPEED``. Be sure to change ``spec.SIMSPEED`` if you want to change this.

.. index:: A (motor array)

.. _A-sec:

A[]
-----

:A:
  As in spec, A[mtr1] provides the current position of mtr1. A is not actually implemented as
  a global array, but can be indexed as one. 

.. index:: S (scaler array)

.. _S-sec:

S[]
-----

:S:
  As in spec, S[`i`] provides the last read intensity from scaler channel `i`. This is a
  python list and is thus indexed starting at 0. The first channel, ``S[0]``, is expected to be
  configured as the count-time reference channel. 


*Complete Function Descriptions*
-----------------------------------

The functions available in this module are listed below.

"""


########### SVN repository information ###################
# $Date: 2013-04-24 18:41:03 -0500 (Wed, 24 Apr 2013) $
# $Author: jemian $
# $Revision: 1281 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/trunk/src/APSpy/spec.py $
# $Id: spec.py 1281 2013-04-24 23:41:03Z jemian $
########### SVN repository information ###################


import time
import os
import atexit
import numpy
import numpy as np
# define shortcuts for commonly used math routines
import math
from math import sqrt, exp
from math import fabs as abs
import motor
import cross_ref
import rst_table


EPICS = False
try:
    import epics as ep  #from epics import PV
    import epics.devices as edev  #from epics import PV
    EPICS = True
except:
    print 'Note, PyEPICS was not found'


# create a table of motor info
mtrDB = {} 


#############################################################################
# unique exceptions for use with this module
#############################################################################
 

class APSpyException(Exception):
    '''any exception from this module'''
    pass

class APSpyMotorException(APSpyException):
    '''any motor exception'''
    pass

class APSpyUndefinedMotorException(APSpyMotorException):
    '''requested a mne or mtrsym that was not defined'''
    pass

class APSpyScalerException(APSpyException):
    '''any scaler exception'''
    pass

class APSpyUndefinedScalerException(APSpyScalerException):
    '''(one instance occurs) - needs work to demonstrate usage'''
    pass


#############################################################################
# internal support
#############################################################################


def _cleanup_globals():
    ' cleanup old globals if this is a reload; for internal use only'
    if 'mtrDB' in globals():
        global mtrDB
        for sym in mtrDB:
            del globals()[mtrDB[sym].symbol]
        mtrDB = {} # initialize table of motor info
    # reset globals used for scalers
    global _lastCountTime, _lastScalerIndex, _startTime_lastcount
    global simLowerLimits, simUpperLimits, _ScalerDict, S
    _lastCountTime = 0      # count time from last call to count_em
    _lastScalerIndex = None # save index from last call to count_em
    _startTime_lastcount = None
    simLowerLimits = {}
    simUpperLimits = {}
    _ScalerDict = {}
    S = []
    
    # global motors, scalers
    # # crossref motor key = mnemonic symbol ('phi') with value = mtrsym ('mtr1002')
    # # TODO: 2013-04 plan: motors will replace mtrDB
    # motors = cross_ref.CrossReference("MotorMneList")       # key = symbol ('phi'), value = mtrsym ('mtr1002')
    # # crossref scaler ? with ?
    # # TODO: 2013-04 plan: scalers will replace _ScalerDict
    # scalers = cross_ref.CrossReference("ScalerMneList")


#############################################################################
# general
#############################################################################


#abs = math.fabs
def sind(deg): return math.sin(math.radians(deg))
def cosd(deg): return math.cos(math.radians(deg))
def tand(deg): return math.tan(math.radians(deg))
def asind(val): return math.degrees(math.asin(val))
def acosd(val): return math.degrees(math.acos(val))
def atand(val): return math.degrees(math.atan(val))


#############################################################################
# motor-related methods
#############################################################################


def get_mtrsym(key):
    '''return motor mtrsym given either mtrsym or mne
    
    .. index:: ! mne
    
    **mne**: motor menmonic symbol, such as `phi`
    
    .. index:: ! mtrsym
    
    **mtrsym**: motor symbol, such as `mtr1002`. 
    `mtrsym` is the key used to index mtrDB
    
    :param str key: either a motor mne or a mtrsym
    :returns str: a motor key
    :raises: APSpyUndefinedMotorException if mtrsym is not found
    '''
    #if key in mtrDB: return key    # original plan
    # 2013-04 plan
    if key in motors.get_keys():
        key = motors.get(key)                # translates key (as `mne`) into mtrsym
    if key in motors.get_values():
        return key                           # return mtrsym, as given
    raise APSpyUndefinedMotorException(str(key))


def _loadlimits():
    'Load a file of soft limits'
    global simLowerLimits, simUpperLimits
    # put something into the limit arrays
    simLowerLimits['Null'] = 0
    simUpperLimits['Null'] = 0
    search_path = ( # look for MOTORLIMITS_FILENAME in these places
        # directory containing this module
        os.path.abspath(os.path.split(__file__)[0]),
        
        # user's current working directory
        os.getcwd(),
    )
    for path in search_path:
        filename = os.path.join(path, MOTORLIMITS_FILENAME)
        if os.path.exists(filename):
            for line in open(filename, 'r').readlines():
                try:
                    parts = line.split()
                    if len(parts) == 3:
                        key, mmin, mmax = parts
                        simLowerLimits[key] = float(mmin)
                        simUpperLimits[key] = float(mmax)
                except:
                    pass    # we give up _very_ easily here


def sleep(sec):
    '''Causes the script to delay for `sec` seconds. 
    
    This method is replaced when plotting is loaded by 
    an alternate method (see :func:`sleepWithYield` in
    :func:`macros._makePlotWin`). 

    :param float sec: time to delay in seconds
    '''
    if UseEPICS():
        time.sleep(sec)
    else: # simulation
        time.sleep(sec/SIMSPEED)
    setElapsed()


def EnableEPICS(state=True):
    '''
    Call to enable communication with EPICS. 
    
    This must be called to enable communication with EPICS before initializing motors.
    If not called then APSpy will function in simulation mode only.
    If the PyEpics module cannot be loaded, then this function has no effect. 
    
    :param bool state: if False is specified, then EPICS communication is disabled
      (default value, True).
    '''
    global _ENABLE, mtrDB, _ScalerDict
    if len(mtrDB) > 0 or len(_ScalerDict):
        print("EnableEPICS called with motors or scalers defined, initializing!")
        _cleanup_globals()

    _ENABLE = state and EPICS
    if state and not EPICS:
        print "pyEpics is not available. Motors access will be simulated"
        return
    global _lastScalerIndex
    _lastScalerIndex = None


def onsim():
    '''Turns simulation mode on. Note that unlike :func:`EnableEPICS`,
    :func:`onsim` and :func:`offsim` can be used at any time. 
    '''
    global _SIMULATE
    if not _SIMULATE: print("Simulation mode turned on")
    _SIMULATE = True


def offsim():
    '''Turns simulation mode off. Note that unlike :func:`EnableEPICS`,
    :func:`onsim` and :func:`offsim` can be used at any time. 
    '''
    global _SIMULATE
    if _SIMULATE: print("Simulation mode turned off")
    _SIMULATE = False


def initElapsed():
    '''Initialize the elapsed time counter'''
    global _StartTime, ELAPSED
    _StartTime = time.time()
    ELAPSED = 0.0


def setElapsed():
    '''Measure time from the last call to  :func:`initElapsed`. 
    
    Global variable :data:`ELAPSED` is 
    set to this value. This is called after motors are moved and when counting is done with scalers or
    :func:`sleep` is called.
    
    :returns: the elapsed time in sec (float)
    '''

    global _StartTime, ELAPSED
    ELAPSED = time.time() - _StartTime
    return ELAPSED


def UseEPICS():
    '''Show if use of EPICS is allowed or disabled, see :func:`EnableEPICS`,
    :func:`onsim` and :func:`offsim`.
    
    :returns: True if PyEpics has been loaded and enabled (see :func:`EnableEPICS`)
      and simulate mode is False (see :func:`onsim` and :func:`offsim`),
      False otherwise.
    
    '''
    return _ENABLE and not _SIMULATE


def DefineMtr(symbol, prefix, comment=''):
    """Define a motor for use in this module. Adds a motor to the motor table.

    :param string symbol: a symbolic name for the motor. A global variable is
      defined in this module's name space with this name, This must be unique; 
      Exception ``APSpyException``  is raised if a name is reused.
    :param string prefix: the prefix for the motor PV (``ioc:mnnn``). 
      Omit the motor record field name (``.VAL``, etc.).
    :param string comment: a human-readable text field that describes the motor. 
      Suggestion: include units and define the motion direction.
    :returns: key of entry created in motor table (str).

    If you will use the `` from APSpy.spec import * `` python command to 
    import these routines into the current
    module's name space, it is necessary to repeat this command after 
    :func:`DefineMtr()` to import the globals
    defined within in the top namespace:
    
    Example (recommended for interactive use):
      >>>  from spec import *
      >>>  EnableEPICS()
      >>>  DefineMtr('mtrXX1','ioc1:mtr98','Example motor #1')
      >>>  DefineMtr('mtrXX2','ioc1:mtr99','Example motor #2')
      >>>  from spec import *
      >>>  mv(mtrXX1, 0.123)
      
    Note that if the second ``from ... import *`` command is not used, 
    the variables ``*mtrXX1*`` and ``*mtrXX2*`` 
    cannot be accessed and the final command will fail.

    Alternate example (this is a cleaner way to code scripts, since namespaces are not mixed):
      >>>  import APSpy.spec
      >>>  APSpy.spec.EnableEPICS()
      >>>  APSpy.spec.DefineMtr('mtrXX1','ioc1:mtr98','Example motor #1')
      >>>  APSpy.spec.DefineMtr('mtrXX2','ioc1:mtr99','Example motor #2')
      >>>  APSpy.spec.mv(spec.mtrXX1, 0.123)

    It is also possible to mix the two styles:
      >>>  import APSpy.spec
      >>>  APSpy.spec.EnableEPICS()
      >>>  APSpy.spec.DefineMtr('mtrXX1','ioc1:mtr98','Example motor #1')
      >>>  APSpy.spec.DefineMtr('mtrXX2','ioc1:mtr99','Example motor #2')
      >>>  from APSpy.spec import *
      >>>  mv(mtrXX1, 0.123)

    """
    if DEBUG: print("Defining "+str(symbol)+" with PV="+str(prefix))
    # is symbol in use as a global? If not, create a global for it
    if symbol not in globals():
        mtrcntr = len(mtrDB) + MTRDB_OFFSET # this defines an arbitrary index for the table
        # start at a large value to help prevent accidental access
        mtrsym = 'mtr'+str(mtrcntr)
        globals()[symbol] = mtrsym      # original plan
        global motors
        motors.add(symbol, mtrsym)      # 2013-04 plan
    else:
        raise APSpyMotorException('Variable '+str(symbol)+' is in use')
    # prepare a record for simulation 
    mtrDB[mtrsym] = motor.MotorObject(symbol, prefix, info=comment, tolerance=0.0)
    if not _ENABLE: return mtrsym
    
    # create Motor object
    mtrObj = ep.Motor(prefix)

    # get deadband from .RDBD or abs(.UREV/.SREV), which ever is larger
    # retry steps were omitted from this, defer that to PyEpics
    rdbd = mtrObj.retry_deadband
    urev = mtrObj.u_revolutions
    srev = mtrObj.s_revolutions
    deadVal = 1.5 * max(  abs(float(urev / srev)),  abs(rdbd), )
    if deadVal == 0: deadVal = 0.0001

    # add info to motor table
    mtrDB[mtrsym].mtr_pv = mtrObj
    mtrDB[mtrsym].tolerance = deadVal
    return mtrsym


def DefinePseudoMtr(inpdict, comment=''):
    """Define one or more pseudo motors in terms of previously defined motors. Adds the new pseudo
    motor definition(s) to the motor table.

    :param dict inpdict: defines a dictionary that defines pseudo motor postions in terms of real motor
      positions and maps pseudo-motor target positions into real motor target positions. Dictionary
      entries that do not correspond to previously defined motors are used to define new pseudo-motors.     
    :param string comment: a human-readable text field that describes the motor. Suggestion: include units and
      define the motion direction.
    :returns: key of entry created in motor table (str).

    For computations in the dictionary, motor positions may be referenced in one of two ways, A[mtr] or
    T[mtr]. A[mtr] provides the actual position of the motor while T[mtr] provides the target position
    for the move, i.e., the value of the motor or pseudo-motor after the move, if it will be changed.
    For definitions of pseudo motors, use of A[] is usually correct, but for 
    entries that compute target positions of real motors, one almost always wishes to use T[] to compute
    from target positions (this is most important for use with :func:`MoveMultipleMtr`, where multiple
    target positions are updated prior to any motor movement.). See the examples, below. Note also
    that these expressions are computed in the spec namespace, so the prefix 'spec.' on motor names (etc.)
    is not needed.

    Note that all the routines in math and numpy are available for use in these calculations (but must
    be prefixed by math or numpy or np (such as :func:`math.log10` or :func:`np.exp2` or :func:`numpy.exp2` or
    constant :data:`math.pi`).
    In addition, for convenience the following functions are also defined
    without a prefix:
    :func:`sind` (sine of angle in degrees),
    :func:`cosd` (cosine of angle in degrees),
    :func:`tand` (tangent of angle in degrees),
    :func:`asind` (inverse sine, returns angle in degrees),
    :func:`acosd` (inverse cosine, returns angle in degrees),
    :func:`atand` (inverse tangent, returns angle in degrees),
    :func:`abs`, :func:`sqrt` and :func:`exp`.

    Examples:
    
    >>>  DefineMtr('j1','1idc:j1','sample table N jack')
    >>>  DefineMtr('j2','1idc:j2','sample table SE jack')
    >>>  DefineMtr('j3','1idc:j3','sample table SW jack')
    >>>  APSpy.spec.DefinePseudoMtr({
    ...      # define pseudo motor position
    ...      'jack': '(A[j1] + A[j2] + A[j3])/3.',
    ...      # map motor movements in terms of pseudo motor target position
    ...      'j1': 'A[j1] + T[jack] - A[jack]',
    ...      'j2': 'A[j2] + T[jack] - A[jack]',
    ...      'j3': 'A[j3] + T[jack] - ((A[j1] + A[j2] + A[j3])/3)',
    ...      })

    The above definition a new pseudo motor, `jack` is defined in terms of three motors that
    are already defined, `j1`, `j2`, and `j3`. Note that 'T[jack] - A[jack]' (or equivalently
    'T[jack] - ((A[j1] + A[j2] + A[j3])/3)', both are used here as a pedagogical example)
    computes the difference between the target position for jack    
    and its current position and then adds that difference to the positions for `j1`, `j2`, and `j3`,
    thus, the motors move relative to their initial positions. Note that the comments placed in the
    input are only a guide to the reader, the fact that 'jack' is new and  `j1`, `j2`, and `j3` are
    defined indicates that `jack` is to be defined.

    >>>  DefineMtr('samX','1idc:m77','sample X position (mm) + outboard')
    >>>  DefineMtr('samZ','1idc:m78','sample Z position (mm) + up')
    >>>  DefineMtr('phi','1idc:mphi','sample rotation (deg)')
    >>>  APSpy.spec.DefinePseudoMtr({
    ...      # define pseudo motor positions
    ...      'samLX': 'cosd(A[phi])*A[samX] + sind(A[phi])*A[samZ]',
    ...      'samLZ': '-sind(A[phi])*A[samX] + cosd(A[phi])*A[samZ]',
    ...      # define motor movements in terms of pseudo motor target position
    ...      'samX' : 'cosd(T[phi])*T[samLX] - sind(T[phi]) * T[samLZ]',
    ...      'samZ' : 'sind(T[phi])*T[samLX] + cosd(T[phi]) * T[samLZ]',
    ...      })

    In the above definition two new pseudo motors, `samLX` and `samLZ` are defined in terms of
    three motors that are already defined, `samX`, `samZ`, and `phi`. This maps the axes defined by
    the sample translations `samX`, `samZ` which are rotated by motor `phi` relative to the
    diffractometer coordinate system into a static frame of reference. Note that use of
    T[samLX] and T[samLY] is necessary in the latter expressions, but A[phi] could be
    used in place of T[phi] as long as one does not try to move phi along with `samLX` and/or `samLY`
    in a single call to :func:`MoveMultipleMtr`.

    As described for :func:`DefineMtr()`, if you will use the `` from APSpy.spec import * `` python
    command to import these routines into the current
    module's name space, it is necessary to repeat this import command after defining all
    motors and pseudo motors to import the newly defined global symbols into the top namespace.
    """
    
    mapdict = {} # mapping relationships to compute real motor positions from pseudo motor(s)
    dfndict = {} # mapping relationships to compute pseudo motor(s) positions from real motors
    for key, val in inpdict.items():
        if key in globals():    # TODO: use "motors" instead!
            key = globals()[key]
        if key in mtrDB:
            mapdict[key] = val # motor exists, this should process target positions
        else:
            dfndict[key] = val # defines a new pseudo-motor
            # do some error checking, can the definition be interpreted? 
            try:
                eval(val)
            except Exception, err:
                print('Unable to interpret relationship for '+str(key)+':\n\t'+
                      str(val)+'\nError message: '+str(err)+'\n')
                raise APSpyMotorException('Error in pseudo motor definition')
    for key in dfndict:
        if DEBUG: print 'define motor ',key,'using',dfndict[key]
        if key not in globals():
            mtrcntr = len(mtrDB) + MTRDB_OFFSET # this defines a arbitrary index for the table
            # start at a large value to help prevent accidental access
            mtrsym = 'mtr'+str(mtrcntr)
            globals()[key] = mtrsym      # original plan
            global motors
            motors.add(key, mtrsym)      # 2013-04 plan
        else:
            raise APSpyMotorException('Variable '+str(key)+' is in use')
        if DEBUG:
            print("Defining " + str(key) + " as motor " + str(mtrsym))
        mtrdict={'_PMdef':dfndict[key]}
        mtrdict.update(mapdict)
        # define a pseudo-motor, note that the PV prefix is a dict
        mtrDB[mtrsym] = motor.MotorObject(key, mtrdict, info=comment, tolerance=0.0)

    # now that all pseudo-motors are defined, check that the other definitions also work
    for key in mapdict:
        T = A # use current value as target
        try:
            eval(mapdict[key])
        except Exception, err:
            msg = 'Unable to interpret mapping relationship for ' 
            msg += mtrDB[key].symbol + ':\n\t' + str(mapdict[key]) 
            msg += '\nError message: ' + str(err) + '\n'
            print(msg)
            raise APSpyMotorException('Error in pseudo motor mapping')


# TODO: move this class to motor.py
class _MTRpos(object):
    '''Defines an interface to the current motor values, similar to spec so that 
    A[mtr1] returns the current position of motor mtr1
    '''
    def __getitem__(self, key):
        return ReadMtr(key)         # 2013-04 plan


# TODO: move this class to motor.py
class _MTRtarget(object):
    '''Defines an interface that provides the target values for intended moves of motors. If no
    target has been set, the current motor position is returned.
    Method keys returns the list of motors where a target has been defined.
    '''
    def __init__(self):
        self.targets = {}

    def __getitem__(self, key):
        if key in self.targets: 
            return self.targets[key]
        return ReadMtr(key)         # 2013-04 plan

    def __setitem__(self, key, value):
        self.targets[key] = value
        return ReadMtr(key)         # 2013-04 plan

    def keys(self):
        return self.targets.keys()


def DefineMotorSymbols(db=mtrDB, make_global=False):
    '''
    make definitions of the motor symbolic names
    
    Returns a string listing the motor symbols and values.
    This string can be executed in the local namespace
    (by :func:`exec`) to define (or redefine) these names 
    locally for convenience.  This is recommended for 
    interactive (command-line session) use only.
        
    >>> from spec import *
    >>> DefineMtr('samX', 'como:m1',  'sample X position (mm) + outboard')
    >>> DefineMtr('samZ', 'como:m2',  'sample Z position (mm) + up')
    >>> samX
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    NameError: name 'samX' is not defined
    >>> exec( DefineMotorSymbols(mtrDB) )
    >>> samX
    'mtr1000'
    >>>
    
    .. note:: Using :func:`exec` is the only known and reliable way to 
        import the motor symbol definitions into the local namespace.
    
    To import the motor symbols into a module's *global* namespace,
    (non-interactive, as used in a script or macro file)
    one way would be to include the following function in the module::
    
 	import spec
 	# ...
 	def ImportMotorSymbols():
 	    exec( spec.DefineMotorSymbols(spec.mtrDB, make_global=True) )
 	# ...
 	ImportMotorSymbols()

    '''
    if make_global:
        return '\n'.join(['global %s; %s = "%s"' % (v.symbol, v.symbol, k) for k, v in db.items()])
    else:
        return '\n'.join(['%s = "%s"' % (v.symbol, k) for k, v in db.items()])


def ListMtrs():
    '''Returns a list of the variables defined as motor symbols.
    
    :returns: a python list of defined motor symbols (list of str values).
    '''
    #return sorted([mtrDB[i].symbol for i in mtrDB.keys()])    # original plan
    return sorted(motors.get_keys())        # 2013-04 plan


def Sym2MtrVal(mtrsym):
    '''Converts a motor symbol (as a string) to the motor value (key) 
    as assigned in :func:`DefineMtr()`

    :param str mtrsym: a motor symbol (such as 'phi')
    :returns str: motor value (such as `mtr1002`)
    :raises: `APSpyException` if the value does not correspond to a motor entry.
    '''
    #if mtrsym in globals():            # original plan
    #    return globals()[mtrsym]
    return get_mtrsym(mtrsym)


def ExplainMtr(mtr):
    '''
    Show the description for a motor, as defined in :func:`DefineMtr()`
    
    :param various mtr: symbolic name for the motor, can take two forms:
       a motor key or a motor symbol.
        
    :returns: motor description (str) or '?' if not defined
    
    .. returns the description related to a motor or ?
       if the motor is not defined

        mtr can be a str in which case it is looked up as a global or
        it can be the value associated with that motor symbol
    '''
    try:
        return mtrDB[get_mtrsym(mtr)].info
    except APSpyUndefinedMotorException:
        return '?'


def GetMtrInfo(mtr):
    '''Return a dictionary with motor information.

    :param str mtr: a key corresponding to an entry in the motor table. If the value
      does not correspond to a motor entry, an exception is raised.
    :returns: dictionary with motor information

    '''
    return mtrDB[get_mtrsym(mtr)].get_dict()


def ReadMtr(mtr):
    '''Return the motor position associated with the passed motor value.

    :param int mtr: a key corresponding to an entry in the motor table. If the value
      does not correspond to a motor entry, an exception is raised.
    :returns: motor position (float).

    '''
    # - - - - - - - - - - - - - - - - - - - - - 
    def do_retries(pv):
        for i in range(MAX_RETRIES):
            pos = pv.get('RBV') # get mtr position
            if pos is not None:
                return pos
            if DEBUG:
                print 'repeat read of mtr: ' + str(mtr) + ' ' + mtrDB[mtr].symbol
            if (i+1) < MAX_RETRIES:
                sleep(RETRY_INTERVAL_S)
        msg = 'Failed to read mtr: ' + str(mtr) + ' ' + \
                mtrDB[mtr].symbol + ' in '+str(MAX_RETRIES)+' tries'
        raise APSpyMotorException(msg)
    # - - - - - - - - - - - - - - - - - - - - -
    mtr = get_mtrsym(mtr)       # translate only once
    pv = mtrDB[mtr].mtr_pv
    if isinstance(pv, dict):
        try:    # try pv as a pseudomotor
            return eval(pv['_PMdef'])
        except Exception,err:
            msg = 'Error evaluating Pseudo-motor ' + mtrDB[mtr].symbol
            msg +=' position from definition\n\t'
            msg += pv['_PMdef'] + '\nError message: ' + str(err)
            raise APSpyMotorException(msg)
    if not UseEPICS(): # simulation
        return mtrDB[mtr].simpos
    return do_retries(pv)

def _ExpandPseudoMove(mtr, pos, T):
    '''Take a pseudo-motor move as input and return target positions for all motors
    that are moved by this pseudo-motor
    '''
    mtr = get_mtrsym(mtr)       # translate only once
    pv = mtrDB[mtr].mtr_pv
    if not isinstance(pv, dict):
        # not a pseudo motor, no problem
        return (mtr,pos)
    T[mtr] = pos # define the target
    tlist = []
    for key in pv:
        if key == '_PMdef': continue # skip over the Pseudo Motor definition
        tlist.append((key,eval(pv[key])))
    return tlist
                    
                     
def PositionMtr(mtr, pos, wait=True):
    '''Move a motor
    
    Position a motor associated with ``mtr`` to position ``pos``,
    wait for the move to complete if wait is True, or else return immediately. 
    The function attempts to verify the move command has been acted upon.

    :param int mtr: a value corresponding to an entry in the motor table, 
      as defined in :func:`DefineMtr()`.
      If the value does not correspond to a motor entry, an exception is raised.
    :param float pos: a value to position the motor. If the value is invalid or outside
      the limits an exception occurs (are hard limits checked?).
    :param bool wait: a flag that specifies if the move should be completed before the
      function returns. If False, the function returns immediately.

    '''
    mtr = get_mtrsym(mtr)       # translate only once
    # is this a pseudo motor? If so expand to the real motor positions
    pv = mtrDB[mtr].mtr_pv
    if isinstance(pv, dict):
        T = _MTRtarget() # holding point for move targets
        movelist = _ExpandPseudoMove(mtr, pos, T)
        # start all the motors moving just about the same time
        for m,p in movelist:
            PositionMtr(m, p, wait=False)
        if wait: # if requested, wait for each to get to the assigned position
            for m,p in movelist:
                PositionMtr(m, p, wait=True)
        return
    else:
        movelist = (mtr, pos)
    mtrDB[mtr].simpos = pos
    if not UseEPICS(): # simulation
        # if this is the first simulation event, try to read in the motor limits
        if len(simLowerLimits) == 0: _loadlimits()
        print 'Simulate move of '+mtrDB[mtr].symbol+' to '+str(pos),' wait=',wait
        key = pv
        if simLowerLimits.get(key):
            if pos < simLowerLimits[key]:
                msg = 'Move outside lower soft limit: ' +mtrDB[mtr].symbol+' to '+str(pos)
                raise APSpyMotorException(msg)
        if simUpperLimits.get(key):
            if pos > simUpperLimits[key]:
                msg = 'Move outside upper soft limit: ' +mtrDB[mtr].symbol+' to '+str(pos)
                raise APSpyMotorException(msg)
        setElapsed()
        return
    if pv.disabled:
        msg = 'Disabled motor: '+mtrDB[mtr].symbol+' ('+str(mtr)+ ') Unable to position to '+str(pos)
        raise APSpyMotorException(msg) 
    mvval = pv.move(pos,wait=wait) # reposition the motor, wait if needed
    if mvval < 0:
        msg = 'Invalid move for motor '+mtrDB[mtr].symbol+' ('+str(mtr)+ ') to position '+str(pos)
        raise APSpyMotorException(msg)
    if mvval > 1:
        msg = 'Limit on move for motor '+mtrDB[mtr].symbol+' ('+str(mtr)+ ') to position '+str(pos)
        raise APSpyMotorException(msg)
    if wait:
        movetype = 'move'
        field = 'RBV'
    else:
        movetype = 'set'
        field = 'VAL'
    # make sure the motor really got message (move complete if wait True)
    i = 0
    sleep(DELAY_FOR_MOVE_TO_START_S)
    while True:
        i += 1
        if i > MAX_RETRIES:
            msg = 'Failed to '+movetype+' motor '+mtrDB[mtr].symbol+' ('+str(mtr)+') in '+str(MAX_RETRIES)+' tries'
            raise APSpyMotorException(msg)
        curpos = pv.get(pv)
        if curpos is None:
            if DEBUG: print 'motor read failed!'
            sleep(MOTOR_READ_FAILED_SLEEP_S)
            continue
        if abs(curpos-pos) < mtrDB[mtr].tolerance: # close enough?
            break
        if DEBUG: print 'repeating '+movetype+' command!'
        if pv.get('LVIO') != 0:
            msg = 'Hit EPICS limit for motor '+mtrDB[mtr].symbol+' ('+str(mtr)+ ') on move to position '+str(pos)
            raise APSpyMotorException(msg)
        mvval = pv.move(pos,wait=wait) 
        if mvval < 0:
            msg = 'Invalid move for motor '+mtrDB[mtr].symbol+' ('+str(mtr)+ ') to position '+str(pos)
            raise APSpyMotorException(msg)
        if mvval > 1:
            msg = 'Limit on move for motor '+mtrDB[mtr].symbol+' ('+str(mtr)+ ') to position '+str(pos)
            raise APSpyMotorException(msg)
        sleep(MOVING_POLL_INTERVAL_S)
    setElapsed()


def mmv(mtrposlist, nsteps=1, wait=False):
    '''Launch movement of several motors together. By default, does not wait
    for all motion to complete.
    See the equivalent function, :func:`MoveMultipleMtr`, for a complete description. 

    :param list mtrposlist: A list of pairs of motor keys and target positions
    :param int nsteps: the number of steps to be used to break down the requested move. The default, 1,
      means that all motors are launched at the same time for the entire requested movement range,
      but a value of 2 indicates that all motors will launched to the mid-point of the requested
      movement range and only after all motors have reached that point, will the subsequent set
      of moves be started. 
    :param bool wait: When `wait` is False, moves are started, but the routine returns immediately,
       but `wait` is True, the routine returns after all motors have stopped moving.
       the default is to not wait.
       Note that if 
       `nsteps` is greater than 1, this parameter is ignored and the routine returns only 
       after all requested moves are completed. 

    Example:
    
    >>>  mmv([(samLX,1.1),(samLZ,0.25)])

    '''
    return MoveMultipleMtr(mtrposlist, nsteps, wait)


def ummv(mtrposlist, nsteps=1, wait=True):
    '''Launch movement of several motors together. By default, waits for all motion to complete.
    See the equivalent function, :func:`MoveMultipleMtr`, for a complete description. 

    :param list mtrposlist: A list of pairs of motor keys and target positions
    :param int nsteps: the number of steps to be used to break down the requested move. The default, 1,
      means that all motors are launched at the same time for the entire requested movement range,
      but a value of 2 indicates that all motors will launched to the mid-point of the requested
      movement range and only after all motors have reached that point, will the subsequent set
      of moves be started. 
    :param bool wait: When `wait` is False, moves are started, but the routine returns immediately,
      but `wait` is True (default), the routine returns after all motors have stopped moving. If
      `nsteps` is greater than 1, this parameter is ignored and the routine returns only 
      after all requested moves are completed. 

    Example:
    
    >>>  ummv([(samLX,1.1),(samLZ,0.25)])

    '''
    return MoveMultipleMtr(mtrposlist, nsteps, wait)

    
def MoveMultipleMtr(mtrposlist, nsteps=1, wait=True):
    '''Launch movement of several motors together.
    If a motor would be moved more than one time (for example because it is referenced in more than
    on pseudo-motor), only the last move is actually performed. 
    The target for each motor is included in subsequent computations, so that when motor positions
    are computed from postions of more than one pseudo-motor, the performed move will represent the
    positions from the cummulative move of all previous motors. To deal with the case where motor speeds
    or movements are unequal, the requested moves can be broken down into a series of ``nsteps`` steps,
    where each motor will be moved an increment of 1/``nsteps`` times the total requested change in
    position. This will not keep the movement on exactly the requested trajectory, but it will stay
    close. 

    :param list mtrposlist: A list of motor keys and target positions, for example
      [(samLX,1.1),(samLZ,0.25)]
    :param int nsteps: the number of steps to be used to break down the requested move. The default, 1,
      means that all motors are launched at the same time for the entire requested movement range,
      but a value of 2 indicates that all motors will launched to the mid-point of the requested
      movement range and only after all motors have reached that point, will the subsequent set
      of moves be started. 
    :param bool wait: When `wait` is False, moves are started, but the routine returns immediately,
      but `wait` is True (default), the routine returns after all motors have stopped moving. If
      :`nsteps` is greater than 1, this parameter is ignored and the routine returns only 
      after all requested moves are completed. 

    Example:

    >>>  MoveMultipleMtr([(samLX,1.1),(samLZ,0.25)],5,wait=True)

    ''' 
    T = _MTRtarget() # holding point for move targets
    movetargets = {}
    for mtr, pos in mtrposlist:
        if DEBUG: 
            print 'MoveMultipleMtr move', mtr, mtrDB[mtr].symbol, ' to ', pos
        mtr = get_mtrsym(mtr)
        pv = mtrDB[mtr].mtr_pv
        if isinstance(pv, dict):
            movelist = _ExpandPseudoMove(mtr,pos,T)
            for m,p in movelist:
                movetargets[m] = p
        else:
            movetargets[mtr] = pos
    if DEBUG:
        print 'MoveMultipleMtr pseudo-motors'
        for i in T.keys(): 
            print i, mtrDB[i].symbol, 'from', A[i], 'to', T[i]
        print 'MoveMultipleMtr real motors'
        for i in movetargets.keys(): 
            print i, mtrDB[i].symbol, 'from',A[i],'to', movetargets[i]

    if nsteps > 1:
        steplist = {}
        # compute range to move for each motor
        for i in movetargets.keys():
            steplist[i] = list(np.linspace(A[i], movetargets[i] ,nsteps+1)[1:])
        while len(steplist[i]) > 0:
            # launch motors
            for i in movetargets.keys():
                PositionMtr(i, steplist[i][0], wait=False)
            # wait for each to stop
            for i in movetargets.keys():
                PositionMtr(i, steplist[i].pop(0), wait=True)
        return
    else:
        for i in movetargets.keys():        # start them moving
            PositionMtr(i, movetargets[i], wait=False)
        if not wait: return
        for i in movetargets.keys():        # wait for motion to stop
            PositionMtr(i, movetargets[i], wait=True)


# define Spec look-alikes
def umv(mtr, pos):
    '''Move motor with wait.

    If the move cannot be completed, an exception is raised.
    
    :param int mtr: a value corresponding to an entry in the motor table, as defined in :func:`DefineMtr()`.
      If the value
      does not correspond to a motor entry, an exception is raised.
    :param float pos: a value to position the motor. If the value is invalid or outside
      the limits, an exception occurs.
      
    **Example:**
      >>> umv(samX,0.1)
    '''
    PositionMtr(mtr, pos, wait=True)
            
            
def mv(mtr,pos):
    '''Move motor without wait
    
    If the move cannot be made, an exception is raised.
    
    :param int mtr: a value corresponding to an entry in the motor table, as defined in :func:`DefineMtr()`.
      If the value
      does not correspond to a motor entry, an exception is raised.
    :param float pos: a value to position the motor. If the value is invalid or outside
      the limits, an exception occurs.

    **Example:**
      >>> mv(samX,0.1)
    '''
    PositionMtr(mtr, pos, wait=False)


def umvr(mtr,delta):
    '''Move motor relative to current position with wait.
    
    If the move cannot be completed, an exception is raised.
    
    :param int mtr: a value corresponding to an entry in the motor table, as defined in :func:`DefineMtr()`.
      If the value
      does not correspond to a motor entry, an exception is raised.
    :param float delta: a value to offset the motor. If the resulting value is invalid or outside
      the limits, an exception occurs.

    **Example:**
      >>> umvr(samX,0.1)
    '''
    pos = ReadMtr(mtr)         # 2013-04 plan
    PositionMtr(mtr, pos+delta, wait=True)


def mvr(mtr,delta):
    '''Move motor relative to current position without wait.
    
    If the move cannot be made, an exception is raised.
    
    :param int mtr: a value corresponding to an entry in the motor table, as defined in :func:`DefineMtr()`.
      If the value
      does not correspond to a motor entry, an exception is raised.
    :param float delta: a value to offset the motor. If the resulting value is invalid or outside
      the limits, an exception occurs.

    **Example:**
      >>> mvr(samX,0.1)
      
    '''
    pos = ReadMtr(mtr)
    PositionMtr(mtr, pos+delta, wait=False)


def wm(*mtrs):
    '''Read out specified motor(s).
    
    :arguments:
      one or more motor table entries that are  defined in :func:`DefineMtr()`.

    :returns: a single float if a single argument is passed to wm. Returns a list of
      floats if more than one argument is passed.

    **Example:**
      >>> wm(samX,samZ)
      [1.0, 0.0]
      
    '''
    
    if len(mtrs) == 1:
        return ReadMtr(mtrs[0])
    else:
        return [ReadMtr(mtr) for mtr in mtrs]


def wa(label=False):
    '''Print positions of all motors defined using :func:`DefineMtr()`.

    :param bool label: a flag that specifies if the list should include the motor descriptions.
       If omitted or False, the descriptions are not included. 

    **Example:**
        >>> wa()
        ===== ========
        motor position
        ===== ========
        samX  1.0     
        samZ  0.5  
        ===== ========   
        >>> wa(True)
        ===== ======== =================================
        motor position description                      
        ===== ======== =================================
        samX  1.0      sample X position (mm) + outboard
        samZ  0.5      sample Z position (mm) + up      
        ===== ======== =================================
    '''
    t = rst_table.Table()
    lbl = ['motor', 'position', ]
    if label:
        lbl.append('description')
    t.labels = lbl
    keys = sorted(motors.get_values())
    values = [mtrDB[key].symbol for key in keys]
    # rst_table
    for key in sorted(motors.get_values()):
        row = [ mtrDB[key].symbol, str(wm(key)), ]
        if label:
            row.append( ExplainMtr(key).strip() )
        t.rows.append(row)
    print t.reST(add_tabularcolumns=False)

#======================================================================
# scaler (counter) access routines
#======================================================================


def DefineScaler(prefix,channels=8,index=0):
    '''Defines a scaler to be used for this module

    :param string prefix: the prefix for the scaler PV (ioc:mnnn). Omit the scaler record field name (.CNT, etc.)

    :param int channels: the number of channels associated with the scaler. Defaults to 8.

    :param int index: an index for the scaler, if more than one will be defined. The default (0) is used to
       define the scaler that will be used when :func:`ct` is called with one or no arguments.

    Example (recommended for interactive use):
      >>>  from APSpy.spec import *
      >>>  EnableEPICS()
      >>>  DefineScaler('id1:scaler1',16)
      >>>  DefineScaler('id1:scaler2',index=1)
      >>>  ct()
      [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

    Alternate example (preferred for use in code):
      >>>  import APSpy.spec as s
      >>>  s.EnableEPICS()
      >>>  s.DefineScaler('ioc1:3820:scaler1',16)
      >>>  s.DefineScaler('ioc1:3820:scaler2',index=1)
      >>>  s.ct()
      [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
      >>>  s.ct(index=1)
      [1, 2, 3, 4, 5, 6, 7, 8]

    
    '''
    global S
    S[:] = channels*[0,]
    defaultLbls = ['S[%d]' % i for i in range(channels)]
    global _ScalerDict
    # define DB entry
    _ScalerDict[index] = {'channels':channels, 'MON':None, 'DET':None, 'labels':defaultLbls,
                          'lastcount':S, 'lastctime':0}
    _ScalerDict[index]['pvname'] = prefix
    if not _ENABLE:
        # prepare an entry for simulation 
        _ScalerDict[index]['pv'] = prefix
        print '*** Simulating a Scaler on PV '+str(prefix)+' with '+str(channels)+' channels'
        return
    # set up the scaler object
    _ScalerDict[index]['pv'] = edev.Scaler(prefix,channels)

    # for now, assume that the first channel is the clock
    # set the gate on the clock and turn off all others
    for ch in range(channels):
        if ch==0:
            setval = 1
        else:
            setval = 0
        _setGate(index,ch,setval)
    # get labels from Scaler
    for i in range(0,channels):
        _ScalerDict[index]['labels'][i] = _ScalerDict[index]['pv'].get('NM'+str(i+1))


def GetScalerInfo(index=0):
    '''returns information about a scaler based on the index

    :param int index: an index for the scaler, if more than one is be defined
      (see :func:`DefineScaler`). 
      The default (0) is used if not specified.

    :returns: a dictionary with information on the scaler
    
    '''
    return _ScalerDict[index]


def GetScalerLastCount(index=0):
    '''returns the last set of counts that have been read for a scaler

    :param int index: an index for the scaler, if more than one is be defined
      (see :func:`DefineScaler`). 
      The default (0) is used if not specified.

    :returns: a list of the last counts
    
    '''
    return _ScalerDict[index]['lastcount']


def GetScalerLastTime(index=0):
    '''returns the count time for the last read from a scaler

    :param int index: an index for the scaler, if more than one is be defined
      (see :func:`DefineScaler`). 
      The default (0) is used if not specified.

    :returns: a single float with the last elapsed time for that scaler (initialized at 0) of the last counts
    
    '''
    return _ScalerDict[index]['lastctime']


def GetScalerLabels(index=0):
    '''returns the labels that have been retrieved for a scaler

    :param int index: an index for the scaler, if more than one is be defined
      (see :func:`DefineScaler`). 
      The default (0) is used if not specified.

    :returns: a list of labels
    
    '''
    return _ScalerDict[index]['labels']


def _setGate(index, ch, setval):
    '''Set the gate setting for channel #ch of scaler index to setval

    :param int ch: channel number, which must be in the range of 0 to the number of channels-1
    '''
    i = 0
    while _ScalerDict[index]['pv'].get('G'+str(ch+1)) != setval:
        i += 1
        _ScalerDict[index]['pv'].put('G'+str(ch+1), setval)
        sleep(0.1)
        if DEBUG: print 'setting scaler channel',ch,'to',setval
        if i > MAX_RETRIES:
            # TODO: FIXME: variable "prefix" is undefined at this point (part of the PV left of the ".")
            msg = ['In ', str(MAX_RETRIES), ' attempts, ',
                   'unable to set ', prefix, ' gate for channel', str(ch)]
            raise APSpyUndefinedScalerException(''.join(msg))


def SetMon(Monitor=None,index=0):
    '''Set the monitor channel for the scaler. The default is to restore this to the initial
      setting, where this is undefined. This is needed for counting on the Monitor.

    :param int Monitor: channel number. If omitted the Monitor is set as undefined. The
      valid range for this parameter is 0 through one less than the number of channels.

    :param int index: an index for the scaler, if more than one will be defined
      (see :func:`DefineScaler`). 
      The default (0) is used if not specified.
    '''
    if Monitor is None:
        _ScalerDict[index]['MON'] = None
        return
    if Monitor >= _ScalerDict[index]['channels'] or Monitor < 0:
        raise APSpyMotorException('Monitor channel #'+str(Monitor)+
                                   ' is invalid ')
    _ScalerDict[index]['MON'] = Monitor


def GetMon(index=0):
    '''Return the monitor channel for the scaler or none if not defined. (See :func:`SetMon`)
    This is used for counting on the Monitor.

    :param int index: an index for the scaler, if more than one will be defined (see :func:`DefineScaler`).
       The default (0) is used if not specified.

    :returns: the channel number of the Monitor 
    '''
    return _ScalerDict[index]['MON']


def SetDet(Detector=None,index=0):
    '''Set the main detector channel for the scaler. 
    
    The default is to restore this to the initial setting, 
    where this is undefined. This is used for ASCAN, etc.

    :param int Detector: channel number. 
      If omitted the Detector is set as undefined. 
      The valid range for this parameter is 0 through 
      one less than the number of channels.

    :param int index: an index for the scaler,
      if more than one will be defined 
      (see :func:`DefineScaler`). 
      The default (0) is used if not specified.
    
    '''
    if Detector is None:
        _ScalerDict[index]['DET'] = None
        return
    if Detector >= _ScalerDict[index]['channels'] or Detector < 0:
        raise APSpyScalerException('Detector channel #'+str(Detector)+
                                   ' is invalid ')
    _ScalerDict[index]['DET'] = Detector


def GetDet(index=0):
    '''Return the main detector channel for the scaler or none if not defined. (See :func:`SetDet`)
    This is used for ASCAN, etc.

    :param int index: an index for the scaler, if more than one will be defined (see :func:`DefineScaler`).
       The default (0) is used if not specified.

    :returns: the channel number of the Detector
    
    '''
    return _ScalerDict[index]['DET']


def ct(count=None, index=0, label=False):
    '''
    Cause scaler to count for specified period or to a specified number of counts
    on a prespecified channel (see :func:`SetMon`)
    
    Counting is on time if count is 0 or positive; Counting is on monitor if count < 0

    Global variable ``S`` is set to the count values for the n channels 
    (set in :func:`DefineScaler`) to
    provide functionality similar to *SPEC*. 

    :param float count: time (sec) to count, if omitted :data:`COUNT` is used 
        (see :ref:`Globals` section)

    :param int index: an index for the scaler, if more than one is defined 
       (see :func:`DefineScaler`).
       The default (0) is used if not specified.

    :param bool label: indicates if counts should be printed along with their labels
       The default (False) is to not print counts

    :returns: count values for the channels (see :func:`DefineScaler`)


    Example:
    
    >>>  ct()
    [10000000.0, 505219.0, 359.0, 499.0, 389.0, 356.0, 114.0, 53.0]
    >>>  SetMon(3)
    >>>  ct(-1000)
    [20085739.0, 1011505.0, 719.0, 1000.0, 781.0, 715.0, 226.0, 105.0]
    '''
    global S,_ScalerDict
    # default count if not specified as first arg
    if count is None:
        count=COUNT
    if index not in _ScalerDict:
        raise APSpyScalerException('Error Scaler index '+str(index)+
                                   ' is not defined')
    if count < 0 and _ScalerDict[index]['MON'] is None:
        raise APSpyScalerException('Attempt to count on Monitor without defining a Monitor channel.'+
                            ' Use APSpy.spec.SetMon() first')

    global _lastScalerIndex
    _lastScalerIndex = None
    if not UseEPICS(): # simulation
        # simulate a count
        global simulationcount
        simulationcount += 1
        mult = 10-abs(10-(simulationcount % 20))
        prefix = _ScalerDict[index]['pv']
        n = _ScalerDict[index]['channels']
        print '*** Simulate Scaler count on PV '+str(prefix)+' with '+str(n)+' channels'
        S[:] = [ ]
        if count >= 0:
            for i in range(1,n+1):
                S.append(i*count*mult)
            _ScalerDict[index]['lastctime'] = float(count)
            sleep(count)            
        else:
            for i in range(n):
                if i == _ScalerDict[index]['MON']:
                    S.append(-count)
                else:
                    S.append(-(i+1)*count)
            _ScalerDict[index]['lastctime'] = float(-count/1000.)
        _ScalerDict[index]['lastcount'] = S[:]
        if label:
            for i,j in zip(_ScalerDict[index]['lastcount'],
	                   _ScalerDict[index]['labels']):
                print str(i)+'\t'+str(j)
        setElapsed()
        return S

    if count >= 0:
        # set to count on time
        _setGate(index,0,1)
        if _ScalerDict[index]['MON'] is not None:
            _setGate(index,_ScalerDict[index]['MON'],0)
        # start the count and put the results into the S array
        _ScalerDict[index]['pv'].Count(count,wait=True)
    else:
        # set to count on monitor
        _setGate(index,0,0)
        ch = _ScalerDict[index]['MON']
        _setGate(index,ch,1)
        # load the monitor preset
        _ScalerDict[index]['pv'].put('PR'+str(ch),-count)
        # start the count, wait for it to finish (modeled on Scaler class)
        _ScalerDict[index]['pv'].put('CNT', 1, wait=True)
        ep.ca.poll()
    sleep(0.05)
    S[:] = _ScalerDict[index]['pv'].Read(use_calc=False)
    _ScalerDict[index]['lastcount'] = S[:]
    _ScalerDict[index]['lastctime'] = _ScalerDict[index]['pv'].get('T')
    if label:
        for i,j in zip(_ScalerDict[index]['lastcount'],_ScalerDict[index]['labels']):
            print str(i)+'\t'+str(j)
    setElapsed()
    return S


def count_em(count=None, index=0):
    ''' Cause scaler to start counting for specified period, but return immediately. On the first use,
    this will take the scaler out of autocount mode and put it into one-shot mode (this is because if one
    does not read the scaler shortly after a count when in autocount mode, the scaler returns to autocount
    and the values are lost.) If put in one-shot mode, then autocount will be restored when the python
    interpreter is exited.
    
    Counting is on time if count is 0 or positive; Counting is on monitor if count < 0

    :param float count: time (sec) to count, if omitted :data:`COUNT` is used (see :ref:`Globals` section)

    :param int index: an index for the scaler, if more than one will be defined (see :func:`DefineScaler`).
       The default (0) is used if not specified.

    :returns: None

    Example:
      >>>  count_em()
      >>>  # do other commands
      >>>  wait_count()
      >>>  get_counts()

    '''
    # default count if not specified as first arg
    if count is None:
        count=COUNT
    if index not in _ScalerDict:
        raise APSpyScalerException('Error Scaler index '+str(index)+
                                   ' is not defined')
    if count < 0 and _ScalerDict[index]['MON'] is None:
        raise APSpyScalerException('Attempt to count on Monitor without defining a Monitor channel.'+
                            ' Use APSpy.spec.SetMon() first')
    global _lastCountTime
    _lastCountTime = count
    global _lastScalerIndex
    _lastScalerIndex = index
    if not UseEPICS(): # simulation
        # simulate a count
        prefix = _ScalerDict[index]['pvname']
        print '*** Simulate Scaler start on PV '+str(prefix)+' for '+str(count)+' sec'
        global _startTime_lastcount
        _startTime_lastcount = time.time()
        setElapsed()
        return

    # first use, test if the scaler in autocount mode?
    global _autocountMode
    i = 0
    while _autocountMode is None:
        if i != 0: sleep(0.1)
        _autocountMode = _ScalerDict[index]['pv'].get('CONT')
        i += 1
        if i > MAX_RETRIES:
            raise APSpyScalerException('In '+str(MAX_RETRIES)+
                               ' attempts, unable to read '
                                   +prefix+'.CONT')
        if _autocountMode == 1: # autocount, set to one shot and set up an exit handler to return
                               # to autocount when python exits
            mode = None
            i = 0
            while mode is None:
                if i != 0: sleep(0.1)
                _ScalerDict[index]['pv'].OneShotMode()
                sleep(0.01)
                mode = _ScalerDict[index]['pv'].get('CONT')
                i += 1
                if i > MAX_RETRIES:
                    raise APSpyScalerException('In '+str(MAX_RETRIES)+
                                        ' attempts, unable to set '
                                        +prefix+'.CONT')
            atexit.register(_ScalerDict[index]['pv'].AutoCountMode)

    if count >= 0:
        # set to count on time
        _setGate(index,0,1)
        if _ScalerDict[index]['MON'] is not None:
            _setGate(index,_ScalerDict[index]['MON'],0)
        # start the count and return
        _ScalerDict[index]['pv'].Count(count,wait=False)
    else:
        # set to count on monitor
        _setGate(index,0,0)
        ch = _ScalerDict[index]['MON']
        _setGate(index,ch,1)
        # load the monitor preset
        _ScalerDict[index]['pv'].put('PR'+str(ch),-count)
        # start the count, and return
        _ScalerDict[index]['pv'].put('CNT', 1, wait=False)
    setElapsed()
    return


def wait_count():
    ''' Wait for scaler to finish, must follow count_em

    :returns: None

    Example:
      >>>  wait_count()
    
    '''
    if _lastScalerIndex is None:
        raise APSpyScalerException('Error: last access was not count_em')
    index = _lastScalerIndex
    if index not in _ScalerDict:
        raise APSpyScalerException('Error Scaler index '+str(index)+
                                   ' is not defined')
    if not UseEPICS(): # simulation
        print '*** Simulate Scaler wait on PV '+str(_ScalerDict[index]['pvname'])
        if _lastCountTime < 0:         # simulate a delay
            sleep(max(0.1,-_lastCountTime/1000))
        else:
            sleep(_lastCountTime)
        setElapsed()
        return 
    # wait for count to end, if requested
    i = 0
    sleep(DELAY_FOR_COUNT_TO_START_S) # delay a bit so that the change to .CNT in count_em registers
    while _ScalerDict[0]['pv'].get('CNT') != 0:
        if i > _lastCountTime*4 and _lastCountTime >= 0: # we have waited too long by a factor of 4
            raise APSpyScalerException(
                "Count delay too long. Waited "+str(i)+
                ' sec for '+
                str(_lastCountTime)+' count event')
        i += 0.1
        sleep(0.1)
    setElapsed()
    return


def get_counts(wait=False):
    ''' Read scaler with optional delay, must follow count_em

    reads count values for the channels (see :func:`DefineScaler`)

    :param bool wait: True causes the routine to wait for
           the scaler to complete;
           False (default) will read the scaler instananeously

    :returns: a list of channels values

    Example:
      >>>  get_counts()
      [1, 2, 3, 4, 5, 6, 7, 8]
    
    '''
    global S,_ScalerDict
    if _lastScalerIndex is None:
        raise APSpyScalerException('Error: last access was not count_em')
    index = _lastScalerIndex
    if index not in _ScalerDict:
        raise APSpyScalerException('Error Scaler index '+str(index)+
                                   ' is not defined')
    if not UseEPICS(): # simulation
        # simulate a count
        prefix = _ScalerDict[index]['pvname']
        n = _ScalerDict[index]['channels']
        if _lastCountTime < 0:
            elapsed = time.time() - _startTime_lastcount
        else:
            elapsed = min(time.time() - _startTime_lastcount,_lastCountTime)
        print '*** Simulate Scaler read on PV '+str(prefix)+' with '+str(n)+' channels after '+str(elapsed)+' sec'
        S[:] = [ ]
        for i in range(1,n+1):
            S.append(int(1000.*i*elapsed))
        _ScalerDict[index]['lastcount'] = S[:]
        _ScalerDict[index]['lastctime'] = elapsed
        return S
    # wait for count to end, if requested
    if wait: wait_count
    i = 0
    while wait and (_ScalerDict[index]['pv'].get('CNT') != 0):
        if i > _lastCountTime*4 and _lastCountTime >= 0: # we have waited too long by a factor of 4
            raise APSpyScalerException(
                "Count delay too long. Waited "+str(i)+
                ' sec for '+
                str(_lastCountTime)+' count event')
        i += 0.1
        sleep(0.1)
    S[:] = _ScalerDict[index]['pv'].Read(use_calc=False)
    _ScalerDict[index]['lastcount'] = S[:]
    _ScalerDict[index]['lastctime'] = _ScalerDict[index]['pv'].get('T')
    setElapsed()
    return S


def setCOUNT(count):
    '''Sets the default counting time, see global variable :data:`COUNT` (see :ref:`Globals` section).
    Used in :func:`ct`.

    :param float count: default time (sec) to count.
    '''
    global COUNT
    COUNT = count


def setRETRIES(count=20):
    '''Sets the maximum number of times to retry an EPICS operation (that would nominally be
    expected to work on the first try) before generating an exception.
    See global variable :data:`MAX_RETRIES` (in :ref:`Globals` section)

    :param float count: maximum number of times to retry an EPICS operation. Defaults to 20.
    '''
    global MAX_RETRIES
    MAX_RETRIES = count


def setDEBUG(state=True):
    '''Sets the debug state on or off, see global variable :data:`DEBUG` (see :ref:`Globals` section)

    :param bool state: DEBUG is initialized as False, but the default effect of `setDEBUG`, if no parameter is
      specified is to turn the debug state on.
    '''
    global DEBUG
    DEBUG = state





# initialize the motors table, cleaning up any 
# previously defined motor/scaler globals
_cleanup_globals()

# Initialize the elapsed time counter
initElapsed()


#############################################################################
# define various globals
#############################################################################

# number of times to retry an EPICS operation 
# (that should work on the first or at least second try) 
# before generating an exception
MAX_RETRIES = 20

# seconds to sleep between PV connection retries
RETRY_INTERVAL_S = 1.0 

# delay a bit so that motion can start 
DELAY_FOR_MOVE_TO_START_S = 0.01

# a sleep after reporting that a motor read has failed
# presumably, this is to allow a human sufficient time to see the message
MOTOR_READ_FAILED_SLEEP_S = 1.0

# how long to wait while motor is moving 
# before checking if move is complete
MOVING_POLL_INTERVAL_S = 0.1

# delay a bit so that the change to .CNT in count_em registers 
DELAY_FOR_COUNT_TO_START_S = 0.05  

# _ENABLE (bool)
# Initialized as False, which indicates that indicates that EPICS PV access
# should not be be allowed. 
# (also allows module to be imported for documentation generation, etc. without importing
# PyEpics). Use function EnableEPICS() to set _ENABLE to True.
_ENABLE = False 

# _SIMULATE (bool)
# Initialized as False, which indicates that indicates that
# EPICS PV access should be access, if allowed by _ENABLE.
# When on, turns on simulation mode
# functions onsim() and offsim() to change _SIMULATE
_SIMULATE = False

# shows extra print messages when turned on
DEBUG = False

# create a table of motor info
mtrDB = {} 
simLowerLimits = {}
simUpperLimits = {}

# array of motor positions
A = _MTRpos()

# starting number for autonumbered motors (arbitrary, but known)
MTRDB_OFFSET = 1000

# in simulation mode, this file defines the soft limits for each motor
MOTORLIMITS_FILENAME = 'motorlimits.dat'

# key = symbol ('phi'), value = mtrsym ('mtr1002')
motors = cross_ref.CrossReference("MotorMneList")

# key = ?, value = ?
scalers = cross_ref.CrossReference("ScalerMneList")


COUNT = 1  # default counting time
_lastCountTime = 0      # count time from last call to count_em
_lastScalerIndex = None # saves scaler index from last call to count_em
_startTime_lastcount = None   # time when the last count with count_em was started

# set in count_em when initial autocountmode is checked, 
# so that this is only checked on the first count_em() use
_autocountMode = None   


_ScalerDict = {}
S = []

# used to show changes happening in simulated counting
simulationcount = 0

# speed-up ratio in simulation mode, 
# counts will wait 1/SIMSPEED as long as requested
SIMSPEED = 20. 

if __name__ == '__main__':
    pass

