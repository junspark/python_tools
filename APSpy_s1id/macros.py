"""
**SPEC Simulation: Macros module**

*Module macros: Additional SPEC-like emulation*
===============================================

Python functions listed below are designed to implement functionality for data collection
similar to that available in spec. Routines are divided into sections, :ref:`General-sec`, 
:ref:`Logging-sec`, :ref:`Plotting-sec`, :ref:`Monitoring-sec` and :ref:`1-ID-sec`

.. _General-sec:

*General Purpose Routines*
--------------------------

Note that the :func:`ascan` and :func:`dscan` are affected by what is used in
:func:`~spec.SetDet` and possibly :func:`spec.SetMon` as well as the :ref:`Logging-sec`
configuration. 

========================  ============================================================
General routines	  Description
========================  ============================================================
:func:`specdate`          Returns the date/time formated like Spec
:func:`SetScanFile`       Open a file for scan output
:func:`ascan`             Scan a single motor on a fixed range
:func:`dscan`             Scan a single motor on a range relative to current position
:func:`RefitLastScan`     Fit a user-supplied function to a user-supplied function
:func:`SendTextEmail`     Sends an e-mail message to one or more addresses
:func:`UserIn`            Prompts a user for input
========================  ============================================================

.. _Logging-sec:

*Logging*
---------

An important set of configuration parameters is that which determine what values are
recorded. During data collection, for example, after each :func:`ascan` or 
:func:`dscan` data point. Also, for use in defining macros,
the values can also be saved to a log file using :func:`write_logging_parameters`.

================================  ===============================================================
Logging routines		  Description
================================  ===============================================================
:func:`init_logging`              Initializes the list of items to be reported
:func:`show_logging`              Displays a list of the items that will be logged
:func:`make_log_obj_PV`           Define Logging Object that records a PV value
:func:`make_log_obj_Global`       Define Logging Object that records a global variable
:func:`make_log_obj_PVobj`        Define Logging Object that records a value from a PVobj object
:func:`make_log_obj_motor`        Define Logging Object that records a motor position. 
:func:`make_log_obj_scaler`       Define Logging Object that records a scaler channel value.
:func:`log_it`                    Adds a Logging Object to the list of items to be reported
:func:`add_logging_PV`            Adds a PV to the list of items to be reported
:func:`add_logging_Global`        Adds a Global variable to the list of items to be reported
:func:`add_logging_PVobj`         Adds a PV object to the list of items to be reported
:func:`add_logging_motor`         Adds a motor reference to the list of items to be reported
:func:`add_logging_scaler`        Adds a scaler channel to the list of items to be reported
:func:`write_logging_header`      Writes a header line with labels for each logged item
:func:`write_logging_parameters`  Write the current value of each logged variable
================================  ===============================================================

Two examples for setting up logging (new method):

>>> import macros
>>> macros.init_logging()
>>> GE_prefix = 'GE2:cam1:'
>>> macros.log_it(macros.make_log_obj_PV('GE_fname',GE_prefix+"FileName",as_string=True))
>>> macros.log_it(macros.make_log_obj_PV('GE_fnum',GE_prefix+"FileNumber"))
>>> macros.log_it(macros.make_log_obj_motor(spec.samX))
>>> macros.log_it(macros.make_log_obj_scaler(9))
>>> macros.log_it(macros.make_log_obj_Global('var S9','spec.S[9]'))
>>> macros.log_it(macros.make_log_obj_PV('p1Vs',"1idc:m64.RBV"))

Note that the `make_log_obj_scaler` and `make_log_obj_Global` calls above will record the same
value (though with different headings), but the `make_log_obj_scaler` is a better choice as
the second option could produce the wrong value if use of a second scaler is later
added to a script.

Old method (does the same as the previous) is:

>>> import macros
>>> macros.init_logging()
>>> GE_prefix = 'GE2:cam1:'
>>> macros.add_logging_PV('GE_fname',GE_prefix+"FileName",as_string=True)
>>> macros.add_logging_PV('GE_fnum',GE_prefix+"FileNumber")
>>> macros.add_logging_motor(spec.samX)
>>> macros.add_logging_scaler(9)
>>> macros.add_logging_Global('var S9','spec.S[9]')
>>> macros.add_logging_PV('p1Vs',"1idc:m64.RBV")


Example for use of logging in a script:

>>> mac.write_logging_header(logname)
>>> spec.umv(spec.mts_y,stY) 
>>> for iLoop in range(nLoop):
>>>     spec.umvr(spec.mts_y,dY) 
>>>     count_em(Nframe*tframe)
>>>     GE_expose(fname, Nframe, tframe)
>>>     wait_count()
>>>     get_counts()
>>>     mac.write_logging_parameters(logname)
>>> mac.beep_dac()

This code step-scans motor `mts_y`. It writes a header to the log file at the beginning
of the operation and then logs parameters after each measurement. Measurements are done
in :meth:`GE_expose` and the default scaler, which are run at the same time. 

Note that it can be useful to put differing sets of logging configurations into
files where they can
be invoked as needed using ``execfile(xxx.py)`` [where ``xxx.py`` is the name of the file to be read].
Do not use import for this task because import will process the file when it is referenced first,
but will not do anything if one attempts to import the file again (to reset values back after
a different setting has been used). One must use reload to force that. 

.. _Plotting-sec:

*Plotting*
----------

Similar to logging, it is also possible to designate that values can be plotted as part of a
script. A Logging Object (from the ``make_log_obj_...`` routines) is needed for each
item that will be plotted. 

============================  ============================================================
Plotting routines	      Description
============================  ============================================================
:func:`make_log_obj_PV`       Define Logging Object that records a PV value
:func:`make_log_obj_Global`   Define Logging Object that records a global variable
:func:`make_log_obj_PVobj`    Define Logging Object that records a value from a PVobj object
:func:`make_log_obj_motor`    Define Logging Object that records a motor position. 
:func:`make_log_obj_scaler`   Define Logging Object that records a scaler channel value.
:func:`DefineLoggingPlot`     Creates a plot (if needed) or tab on tab to display values
                             	      and register items to be plotted. 
:func:`UpdateLoggingPlots`    Read and display all parameters added to plot in 
                             	      :func:`DefineLoggingPlot`.
:func:`InitLoggingPlot`       Clear out plotting definitions from previous calls to
                             	      :func:`DefineLoggingPlot`.
============================  ============================================================

Examples:

>>> macros.DefineLoggingPlot(
...     'I vs pos',
...     macros.make_log_obj_motor(spec.samX),
...     macros.make_log_obj_scaler(2),
...     )
>>> spec.umv(spec.samX,2) 
>>> for iLoop in range(30):
...    spec.umvr(spec.samX,0.05)
...    spec.ct(1)
...    macros.UpdateLoggingPlots()

In the above example, a scaler channel is read and plotted against a motor position.

>>> macros.DefineLoggingPlot(
...     'I vs time',
...     macros.make_log_obj_Global('time (sec)','spec.ELAPSED'),
...     macros.make_log_obj_scaler(2),
...     macros.make_log_obj_scaler(3),
...     )
>>> spec.initElapsed()
>>> for iLoop in range(30):
...    spec.ct(1)
...    macros.UpdateLoggingPlots()

In the above example, two scaler channels are plotted against elapsed time. 


.. _Monitoring-sec:

*Monitoring*
------------

Monitoring of PVs is used to record values of selected PVs when any designated PV changes. 
Optionally, only when that PV changes to a specific value or the recording can be 
limited to not occur more than a maximum frequency. It may be best to perform monitoring 
in a process separate from the one making changes to EPICS PVs.


===========================  =================================
Monitoring routines	     Description
===========================  =================================
:func:`DefMonitor`           Set up a PV to be monitored
:func:`StartAllMonitors`     Start the monitoring operation
===========================  =================================

Monitor definition examples:

>>> spec.EnableEPICS()
>>> macros.DefMonitor('/tmp/tst','1ide1:m1.VAL',
...               ('1id:scaler1.S2','1id:scaler1.S3','1ide1:m1.RBV','1ide1:m1.VAL')
...               )
>>> macros.StartAllMonitors()

This will report the values of four PVs every time that PV 1ide1:m1.VAL is changed.


>>> macros.DefMonitor('/tmp/tst','1ide1:m1.RBV',
...               ('1id:scaler1.S3','1ide1:m1.RBV','1ide1:m1.VAL'),
...               pvvalue=0.0)
>>> macros.StartAllMonitors()

This will report three PVs, but only when PV 1ide1:m1.RBV is changed to 0.0 (within 0.00001)

>>> macros.DefMonitor('/tmp/tst','1ide1:m1.RBV',
...              ('1id:scaler1.S2','1id:scaler1.S3','1ide1:m1.RBV','1ide1:m1.VAL'),
...               delay=1.0)
>>> macros.StartAllMonitors()

This will report three PVs, every time that PV 1ide1:m1.RBV is changed, but only a maximum
of one change will be reported each second. 

.. _1-ID-sec:

*Macros specific to 1-ID*
-------------------------

These macros reference 1-ID PV's or are customized for 1-ID in some other manner.

===============================   ============================================================
1-ID specific routines            Description	      
===============================   ============================================================
:func:`beep_dac`                  Causes a beep to sound
:func:`Cclose`                    Close 1-ID fast shutter in B hutch
:func:`Copen`                     Open 1-ID fast shutter in B hutch
:func:`shutter_sweep`             Set 1-ID fast shutter to external control
:func:`shutter_manual`            Set 1-ID fast shutter to manually control
:func:`check_beam_shutterA`       Open 1-ID Safety shutter to bring beam into 1-ID-A
:func:`check_beam_shutterC`       Open 1-ID Safety shutter to bring beam into 1-ID-C
:func:`Sopen`                     Same as :func:`check_beam_shutterC`, bring beam into 1-ID-C
:func:`MakeMtrDefaults`           Create a file with default motor assignments
:func:`SaveMotorLimits`           Create a file with soft limits for off-line simulations
===============================   ============================================================

*Complete Function Descriptions*
--------------------------------

The functions available in this module are listed below.

"""


########### SVN repository information ###################
# $Date: 2013-04-24 18:41:03 -0500 (Wed, 24 Apr 2013) $
# $Author: jemian $
# $Revision: 1281 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/trunk/src/APSpy/macros.py $
# $Id: macros.py 1281 2013-04-24 23:41:03Z jemian $
########### SVN repository information ###################


EPICS = False
import spec
try:
    import epics as ep  #from epics import PV
    EPICS = True
except:
    #print 'Note, PyEPICS was not found' # already printed in spec module
    pass
import sys
import os.path
import time
import datetime as dt
import numpy as np

# define monitoring variables
monobjlist = []
monfiledict = {}
PVmondict = {}


def specdate():
    '''format current date/time as produced in Spec

    :returns: the current date/time as a string, formatted like "Thu Oct 04 18:24:14 2012"

    Example:
      >>> macros.specdate()
      'Thu Oct 11 16:16:39 2012'

    '''
    return dt.datetime.now().strftime("%a %b %d %H:%M:%S %Y")

################################################################################################
# define code for logging of misc PV's during a scan
class _LogObject:
    """data structure to define an entry to log"""
    def __init__(self, label, PV=None, var=None, PVobj=None, mtr=None, scaler=None,
                 as_string=False):
        self.label = label          # label for entry
        self.PV = PV                 # EPICS PV to be reported
        self.var = var               # global variable to be reported
        self.PVobj = PVobj              # a PyEpics PV object connected to a PV to be reported
        self.mtr = mtr               # a motor reference to be reported
        self.scaler = scaler         # a scaler channel to be recorded
        self.as_string = as_string   # forces PVs to be read as a string
    def GetValue(self):
        if self.PV is not None:
            if not (EPICS and spec.UseEPICS()): # in simulation
                return str(simulation_values[self.PV])
            else:
                return str(ep.caget(self.PV,as_string=self.as_string))
        elif self.var is not None:
            return str(eval(self.var))
        elif self.PVobj is not None:
            if not (EPICS and spec.UseEPICS()): # in simulation
                return str(simulation_values[self.PVobj])
            else:
                return str(self.PVobj.get(as_string=self.as_string))
        elif self.mtr is not None:
            return str(spec.ReadMtr(self.mtr))
        elif self.scaler is not None:
            det,index = self.scaler
            return str(spec.GetScalerLastCount(index)[det])
        else:
            return '?'
    def GetInfo(self):
        txt = self.label
        val = ''
        if self.PV is not None:
            typ = 'PV'
            val = 'pv='+self.PV
        elif self.var is not None:
            typ = 'Global'
            val = 'var='+self.var
        elif self.PVobj is not None:
            typ = 'PVobj'
            if not (EPICS and spec.UseEPICS()): # in simulation
                pv = self.PVobj
            else:
                pv = self.PVobj.pvname
        elif self.mtr is not None:
            typ = 'motor'
            if not (EPICS and spec.UseEPICS()): # in simulation
                pv = spec.GetMtrInfo(self.mtr)['PV']
            else:
                pv = spec.GetMtrInfo(self.mtr)['PV']._prefix
            val = pv + ' ' + spec.GetMtrInfo(self.mtr)['info']
        elif self.scaler is not None:
            typ = 'scaler'
            det,index = self.scaler
            if not (EPICS and spec.UseEPICS()): # in simulation
                pv = spec.GetScalerInfo(index)['pv']
            else:
                pv = spec.GetScalerInfo(index)['pv']._prefix
            val = pv + ' channel '+str(det)
        else:
            typ = 'Error!'
            txt = ''
        return (typ,txt,val)

def init_logging():
    '''Initialize the list of data items to be logged

    see :ref:`Logging-sec` for an example of use.
    '''
    global monitor_list, simulation_values
    monitor_list = []
    simulation_values = {}

init_logging()

def log_it(LogObj):
    '''Add a Logging Object into list to be recorded when :func:`write_logging_parameters`
    is called.

    :param object LogObj: a reference to a Logging Object created by
      :func:`make_log_obj_PV`, :func:`make_log_obj_Global`,
      :func:`make_log_obj_PVobj`, :func:`make_log_obj_motor`
      or :func:`make_log_obj_scaler`
    '''
    if not isinstance(LogObj,_LogObject):
        raise spec.specException('Attempt to log parameter not created in make_log_obj_...()')
    monitor_list.append(LogObj)

def make_log_obj_PV(txt,PV,as_string=False):
    '''Define Logging Object that records a PV value

    :param str txt: defines a text string, preferably short, to be used 
       when :func:`write_logging_header` is called as a header for the item to be logged.

    :param str PV: defines an EPICS Process Variable that will be read and logged each time
       :func:`write_logging_parameters` is called.

    :param bool as_string: if True, the PV will be translated to a string. When False (default)
       the native data type will be used. Use of True is of greatest for waveform records that
       are used to store character strings as a series of integers. 

    see :ref:`Logging-sec` for an example of use.
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        simulation_values[PV] = len(simulation_values)+1
    return _LogObject(str(txt),PV=PV,as_string=as_string)

def add_logging_PV(txt,PV,as_string=False):
    '''Define a PV to be recorded when :func:`write_logging_parameters` is called.

    :param str txt: defines a text string, preferably short, to be used 
       when :func:`write_logging_header` is called as a header for the item to be logged.

    :param str PV: defines an EPICS Process Variable that will be read and logged each time
       :func:`write_logging_parameters` is called.

    :param bool as_string: if True, the PV will be translated to a string. When False (default)
       the native data type will be used. Use of True is of greatest for waveform records that
       are used to store character strings as a series of integers. 

    see :ref:`Logging-sec` for an example of use.
    '''
    log_it(
        make_log_obj_PV(txt,PV,as_string)
        )

def make_log_obj_Global(txt,var):
    '''Define Logging Object that records a global variable

    :param str txt: defines a text string, preferably short, to be used 
       when :func:`write_logging_header` is called as a header for the item to be logged.

    :param str var: defines a Python variable that will be logged each time
       :func:`write_logging_parameters` is called. Note that this is read inside the macros
       module so the variable must be defined inside that module or must be prefixed by
       a reference to a module referenced in that module, e.g. spec.S[0]

    see :ref:`Logging-sec` for an example of use.
    '''
    return _LogObject(str(txt),var=var)

def add_logging_Global(txt,var):
    '''Define a global variable to be recorded when :func:`write_logging_parameters` is called.

    :param str txt: defines a text string, preferably short, to be used 
       when :func:`write_logging_header` is called as a header for the item to be logged.

    :param str var: defines a Python variable that will be logged each time
       :func:`write_logging_parameters` is called. Note that this is read inside the macros
       module so the variable must be defined inside that module or must be prefixed by
       a reference to a module referenced in that module, e.g. spec.S[0]

    see :ref:`Logging-sec` for an example of use.
    '''
    log_it(
        make_log_obj_Global(txt,var)
        )
  
def make_log_obj_PVobj(txt,PVobj,as_string=False):
    '''Define Logging Object that records a value from a PVobj object

    :param str txt: defines a text string, preferably short, to be used 
       when :func:`write_logging_header` is called as a header for the item to be logged.

    :param epics.PV PV: defines a PyEpics PV object that is connected to an EPICS Process Variable.
       The PV method .get() will be used to read that PV to log it each time
       :func:`write_logging_parameters` is called.

    :param bool as_string: if True, the PV value will be translated to a string. When False (default)
       the native data type will be used. Use of True is of greatest for waveform records that
       are used to store character strings as a series of integers. 

    see :ref:`Logging-sec` for an example of use.
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        simulation_values[PVobj] = len(simulation_values)+1
    return _LogObject(str(txt),PVobj=PVobj,as_string=as_string)

def add_logging_PVobj(txt,PVobj,as_string=False):
    '''Define a PVobj to be recorded when :func:`write_logging_parameters` is called.

    :param str txt: defines a text string, preferably short, to be used 
       when :func:`write_logging_header` is called as a header for the item to be logged.

    :param epics.PV PV: defines a PyEpics PV object that is connected to an EPICS Process Variable.
       The PV method .get() will be used to read that PV to log it each time
       :func:`write_logging_parameters` is called.

    :param bool as_string: if True, the PV value will be translated to a string. When False (default)
       the native data type will be used. Use of True is of greatest for waveform records that
       are used to store character strings as a series of integers. 

    see :ref:`Logging-sec` for an example of use.
    '''
    log_it(
        make_log_obj_PVobj(txt,PVobj,as_string)
        )


def make_log_obj_motor(mtr):
    """Define Logging Object that records a motor position. 
    Note that the heading text string is defined as the motor's symbol (see :func:`spec.DefineMtr`).

    :param str mtr: a reference to a motor object, returned by :func:`spec.DefineMtr` or defined
      in the motor symbol. The position of the motor will be read and logged each time
      :func:`write_logging_parameters` is called.

    see :ref:`Logging-sec` for an example of use.
    """
    mtrdict = spec.GetMtrInfo(mtr)
    return _LogObject(str(mtrdict['symbol']),mtr=mtr)

def add_logging_motor(mtr):
    """Define a motor object to be recorded when :func:`write_logging_parameters` is called.
    Note that the heading text string is defined as the motor's symbol (see :func:`spec.DefineMtr`).

    :param str mtr: a reference to a motor object, returned by :func:`spec.DefineMtr` or defined
      in the motor symbol. The position of the motor will be read and logged each time
      :func:`write_logging_parameters` is called.

    see :ref:`Logging-sec` for an example of use.
    """
    log_it(
        make_log_obj_motor(mtr)
        )

def make_log_obj_scaler(channel,index=0):
    """Define Logging Object that records a scaler channel value.
    Note that the heading text string is defined as the scaler's label (which is read from
    the scaler when :func:`spec.DefineScaler` is run).

    :param str channel: a channel number for a scaler, which can be any value between 0
      and one less than the number of channels. The last-read value of that scaler
      logged each time :func:`write_logging_parameters` is called.

    :param int index: an index for the scaler, if more than one is be defined
      (see :func:`DefineScaler`). 
      The default (0) is used if not specified.
      
    see :ref:`Logging-sec` for an example of use.
    """
    lbl = spec.GetScalerLabels(index)[channel]
    return _LogObject(lbl,scaler=(channel,index))

def add_logging_scaler(channel,index=0):
    """Define a scaler channel to be recorded when :func:`write_logging_parameters` is called.
    Note that the heading text string is defined as the scaler's label (which is read from
    the scaler when :func:`spec.DefineScaler` is run).

    :param str channel: a channel number for a scaler, which can be any value between 0
      and one less than the number of channels. The last-read value of that scaler
      logged each time :func:`write_logging_parameters` is called.

    :param int index: an index for the scaler, if more than one is be defined
      (see :func:`DefineScaler`). 
      The default (0) is used if not specified.
      
    see :ref:`Logging-sec` for an example of use.
    """
    log_it(
        make_log_obj_scaler(channel,index)
        )

def show_logging():
    '''Show the user the current logged items
    '''
    for obj in monitor_list:
        (typ,txt,val) = obj.GetInfo()
        if len(txt) < 8: txt += '\t'
        print(typ+'\t'+txt+'\t'+val)

def write_logging_parameters (filename=""):
    '''Record the current value of all items tagged to be recorded in :func:`add_logging_PV`,
    :func:`add_logging_Global`, :func:`add_logging_PVobj`, :func:`add_logging_motor` or
    :func:`add_logging_scaler`.

    :param str filename: a filename to be be used for output. If not specified, the
      output is sent to the terminal window.

    see :ref:`Logging-sec` for an example of use.
    '''
    if filename == "":
        fp = sys.stdout
    else:
        fp = open(filename,'a')

    fp.write(specdate())
    fp.write(", ")
    fp.write(_write_logging_values(', '))
    fp.write("\n")
    if filename == "":
        fp.flush()
    else:
        fp.close()

def _write_logging_values(separator=' '):
    string = ''
    for obj in monitor_list:
        if string != "": string += separator
        string += obj.GetValue()
    return string
 
def write_logging_header(filename=""):
    '''Write a header for parameters recorded when :func:`write_logging_parameters` is called.

    :param str filename: a filename to be be used for output. If not specified, the
       output is sent to the terminal window.

    see :ref:`Logging-sec` for an example of use.

    '''
    if filename == "":
        fp = sys.stdout
    elif os.path.exists(filename):
        return
    else:
        fp = open(filename,'a')

    fp.write("Date, ")
    for obj in monitor_list:
        txt = obj.label
        fp.write(txt+", ")
    fp.write("\n")
    if filename == "":
        fp.flush()
    else:
        fp.close()

scanfile = None
scanFP = sys.stdout
scanNumber = 0
def SetScanFile(outfile=None):
    '''Set a file for output from ascan, etc. The output is intended to closely mimic
    what spec produces in ascan and dscan.

    :param str outfile: the file name to be opened. If not specified, output is sent to
      the terminal. If the file is new (or is the not specified) a header listing all motors,
      etc. is printed
    '''    
    global scanfile, scanFP, scanNumber
    newfile = True
    try:
        if outfile is not None:
            # file name specified
            if os.path.exists(outfile):
                # read the file and extract previous scan numbers
                fp = open(outfile,'r')
                for line in fp:
                    if line[:3] == '#S ':
                        try:
                            scanNumber = max(scanNumber, int(line.split()[1]))
                        except:
                            pass
                fp.close()
                fp = open(outfile,'a')
                newfile = False
            else:
                fp = open(outfile,'w')
            # close the previous file if not stdout
            if scanfile is not None: scanFP.close()
        else:
            # send output to terminal
            fp = sys.stdout
        scanFP = fp
        scanfile = outfile
    except IOError:
        raise IOError,'Error opening file '+str(outfile)+' for scan output'

    # when a file is created, give it a spec-like header
    if newfile:
        scanFP.write('#F '+str(outfile)+'\n')
        scanFP.write('#E '+str(int(time.time()))+'\n')
        scanFP.write('#D '+specdate()+'\n')
        scanFP.write('#C pySpec  User = '+str(os.getlogin())+'\n')
        i = 0
        j = 0
        for m in spec.ListMtrs():
            #  list motor names following Spec format
            if i == 0:
                scanFP.write('#O' + '%-2d' % j + ' %7s' % m)
                i = 1
            elif i == 7:
                scanFP.write('  %8s\n' % m)
                i = 0
                j += 1
            else:
                scanFP.write('  %8s' % m)
                i += 1
        if i != 0:
            scanFP.write('\n')
        scanFP.write('\n')
        scanFP.flush()

#======================================================================
# routines to plot Logging Objects

def InitLoggingPlot():
    '''Clear out plot definitions from previous calls to :func:`DefineLoggingPlot`.
    Prevents updates from occuring in :func:`UpdateLoggingPlot`, but does not
    delete any tabs or the window.
    '''
    global _LoggingPlotsList
    _LoggingPlotsList = []

InitLoggingPlot()

def DefineLoggingPlot(tablbl,Xvar,*args):
    '''Creates a plot window (if needed) or tab on plot to display values. Parameters include
    a label for the tab, a Logging Object that will be used as an x-value and as
    many Logging Object as desired (minimum 1) that will be define y-values.
    Each time this routine is called, a new plot tab is called. As many plot tabs can be created and
    populated as desired. 
    
    see :ref:`Plotting-sec` for an example of use.

    :param str tablbl: a label to place on the plot tab

    :param object Xvar: a reference to a Logging Object created by
      :func:`make_log_obj_PV`, :func:`make_log_obj_Global`,
      :func:`make_log_obj_PVobj`, :func:`make_log_obj_motor`
      or :func:`make_log_obj_scaler`

    :param object Yvar: a reference to a Logging Object created by
      :func:`make_log_obj_PV`, :func:`make_log_obj_Global`,
      :func:`make_log_obj_PVobj`, :func:`make_log_obj_motor`
      or :func:`make_log_obj_scaler`

    :param object Yvar1: a reference to a Logging Object created by
      :func:`make_log_obj_PV`, :func:`make_log_obj_Global`,
      :func:`make_log_obj_PVobj`, :func:`make_log_obj_motor`
      or :func:`make_log_obj_scaler`
    '''
    if not isinstance(Xvar,_LogObject):
        raise spec.specException('Attempt to log Xvar parameter not created in make_log_obj_...()')
    xs = Xvar.GetValue()
    try:
        x = float(xs)
    except:
        raise spec.specException('Value for Xvar,'+str(xs)+', parameter cannot be converted to a number')
    if len(args) < 1:
        raise spec.specException('No Yvar parameters were passed')  
    for i,Yvar in enumerate(args):
        if not isinstance(Yvar,_LogObject):
            raise spec.specException('Attempt to log Yvar parameter not created in make_log_obj_...()')
        ys = Yvar.GetValue()
        try:
            y = float(ys)
        except:
            raise spec.specException('Value for Yvar,'+str(ys)+', from Y parameter #'+str(i+1)+' cannot be converted to a number')
    
    # make a window, if needed
    _makePlotWin("Logging Plot",MakeStop=False)
    page = plotwin.AddPlotTab(tablbl) # add a tab and add it to the list
    global _LoggingPlotsList
    _LoggingPlotsList.append((tablbl,page,Xvar,args))
    plotwin.RaisePlotTab(tablbl) # show new tab
    plotwin.frame.Show(True)
    # label Y axis and if only 1 value, Y axis
    (typ,txt,val) = Xvar.GetInfo()
    page.figure.gca().set_xlabel(str(txt)+' ('+str(val)+')')
    if len(args) == 1:
        (typ,txt,val) = Yvar.GetInfo()
        page.figure.gca().set_ylabel(str(txt)+' ('+str(val)+')')
    # show what we have done
    page.canvas.draw()
    pnb.UpdatePlots()

def UpdateLoggingPlots():
    '''Read all current values in plot and display in plots

    see :ref:`Plotting-sec` for an example of use.    
    '''
    labels = ('vb','or','pg','*b','sr','Dg')
    for (tablbl,page,Xvar,Ylist) in _LoggingPlotsList:
        xs = Xvar.GetValue()
        try:
            x = float(xs)
        except:
            print('Value for Xvar,'+str(xs)+', parameter cannot be converted to a number')
            continue
        for i,Yvar in enumerate(Ylist):
            ys = Yvar.GetValue()
            try:
                y = float(ys)
            except:
                print('Value for Yvar,'+str(ys)+', parameter cannot be converted to a number')
                continue
            page.figure.gca().plot(x,y,labels[i % len(labels)],label=Yvar.label)
        if len(Ylist) > 1 and page.figure.gca().get_legend() is None:
            page.figure.gca().legend()
        page.canvas.draw()
        pnb.UpdatePlots()
        
plotwin = None
pnb = None
def _makePlotWin(title,DisableDelete=False,MakeStop=True,size=(700,700)):
    '''Make a window (frame) to plotting in. Creates a new sleep routine
    that replaces the one in module spec (:func:`spec.sleep`) that does periodic yields to wx for
    graphics updates.
    '''
    import plotnotebook
    import wx
    def sleepWithYield(seconds):
        '''Since wx has been loaded, define a new routine that does periodic screen updates
        '''
        if not spec.UseEPICS():
            seconds /= spec.SIMSPEED
        WaitTick = 0.1
        wait = 0
        wx.Yield()
        if seconds < WaitTick:
            time.sleep(seconds)
            wait = seconds
            wx.Yield()
        while wait < seconds:
            time.sleep(WaitTick)
            wait += WaitTick
            wx.Yield()
        spec.setElapsed()
        
    spec.sleep = sleepWithYield     # replace the sleep routine with the new one
    def OnStop(event):
        'Calback for stop button'
        global StopScan
        StopScan = True
    def makeStopButton():
        global plotwin,pnb
        btn = wx.Button(plotwin, -1, label='Stop Scan')
        btn.Bind(wx.EVT_BUTTON, OnStop)
        plotwin.bottomsizer.Add((-1,1), 1, wx.RIGHT, 1)
        plotwin.bottomsizer.Add(btn, 0, wx.RIGHT, 0)
    global plotwin,pnb
    pnb = plotnotebook
    global StopScan
    StopScan = False
    try:
        plotwin.Parent.SetTitle(title)
    except:
        plotwin = pnb.MakePlotWindow(size=size, DisableDelete=DisableDelete)
        if MakeStop: makeStopButton()
        plotwin.Parent.SetTitle(title)

def ShowPlots():
    '''Pause to show plot screens.
    Call this at the end of a script, if needed.
    '''
    pnb.ShowPlots()

# Fitting Equations
class FitClass(object):
    '''Defines a prototype class for deriving fitting class implementations.
    A fitting class should define at least two method: __init__ and Eval.

    __init__(x,y) computes a list of very approximate values for the fit parameters,
      good enough to be used as the starting values in the fit. The number of terms computed 
      determines the number of parameter values that will be fit.

    Eval(parms,x) provides the function to be fit.

    optionally, Format(parms) is used to return a nicely-formatted text string with
      the fitted parameters.
    '''
    def __init__(self,x,y):
        '''this defines a list of starting values to use for the initial parameters
        The number of items in the list determines the number of variables (refined
        parameters). Non-refineable parameters can also be included in the object,
        if desired.
        '''
        self.startVals = [sum(y)* 1./len(y)]
    def StartParms(self):
        '''Return the starting parameter values determined in __init__()
        '''
        return self.startVals[:]
    def Eval(self, parm, x):
        '''Evaluate the fitting function and return a "y" value computed for
        each value in x. Ideally this expression computes all values in a single
        NumPy expression, but looping is allowed. Both parameters should be
        lists, tuples or numpy arrays.

        :param list,tuple,etc. parm: parameters in the same order as returned by StartParms()
        
        :param list,tuple,etc. x: values of the independent parameter (scanned variable)
          for evaluation of the function.
        '''
        return np.array(len(x) * [parm[0],])
    def FormatNum(self,num):
        return '{:.5g}'.format(num)
    def Format(self,parm):
        '''This prints the parameters, potentially in a way that explains
        what they mean. If not overridden, one gets "Parameter values = <list>"

        :param list,tuple,etc. parm: parameters in the same order as returned by StartParms()
        '''
        s = ''
        for val in parm:
            if s: s += ', '
            s += self.FormatNum(val)
        return 'Parameter values ='+s

class FitGauss(FitClass):
    '''Define a function for fitting with a Gaussian.

    Parameters are defined as:
    
          =======  ================================================
          index     value
          =======  ================================================
             [0]   location of peak 
             [1]   function value at maximum, less parm[3]
             [2]   width as FWHM
             [3]   added to all points
          =======  ================================================

    '''
    def __init__(self,x,y):
        '''defines a list of starting values'''
        xp = x[0]
        yp = y[0]
        for xi,yi in zip(x,y):
            if yi > yp: yp = yi; xp = xi
        dl = 2.*abs(x[-1]-x[0])/len(x)
        self.startVals = [xp,yp,dl,0]
    def Eval(self, parm, x):
        '''Evaluate the Gaussian
        '''
        return parm[1]*np.exp(-4.0*np.log(2)*(np.array(x)-parm[0])**2/parm[2]**2) + parm[3]
    def Format(self, parm):
        '''Prints the parameters
        '''
        return ('Gaussian fit: peak = '+self.FormatNum(parm[1]+parm[2])+
                ' @ pos '+self.FormatNum(parm[0])+
                '; FWHM = '+self.FormatNum(parm[2])+
                '; Background  = '+self.FormatNum(parm[3])
                )

class FitSawtooth(FitClass):
    '''Define a function for fitting with a symmetric or asymmetric saw-tooth function.

    Parameters are defined as:
    
          =======  ================================================
          index     value
          =======  ================================================
             [0]   location of peak 
             [1]   function value at maximum
             [2]   added to all points
             [3]   asymmetric: slope on leading side of peak (+ is rising) 
                   symmetric: slope on both sides of peak
             [4]   asymmetric: slope on trailing side of peak (+ is falling)
          =======  ================================================

    :param bool Symmetric: determines if the SawTooth is symmetric (True) or asymmetric
      (False), meaning that the leading side and the trailing side of the peak
      can have different slopes.


    '''
    def __init__(self,x,y,Symmetric=True):
        '''defines a list of starting values
        also saves the mode for the computation (Symmetric/Asymmetric)
        '''
        self.Symmetric = Symmetric
        xp = x[0]
        yp = y[0]
        for xi,yi in zip(x,y):
            if yi > yp:
                yp = yi;
                xp = xi
        
        if self.Symmetric:
            self.startVals = [xp,yp,0,2./(x[-1]-x[0])]
        else:
            self.startVals = [xp,yp,0,2./(x[-1]-x[0]),2./(x[-1]-x[0])]
    def Eval(self, parm, x):
        '''Evaluate the sawtooth function
        '''
        if self.Symmetric:
            ms = parm[3]
        else:
            ms = parm[4]
        y = []
        for xi in x:
            yi = parm[2]
            if xi < parm[0]:
                dl = 1 - (parm[0] - xi)*parm[3]
                if dl > 0:
                    yi += parm[1] * dl
            else:
                dl = 1 - (xi - parm[0])*ms
                if dl > 0:
                    yi += parm[1] * dl
            y.append(yi)
        return np.array(y)

def dscan(mtr, start, finish, npts, count, index=0, settle=0.0):
    '''Relative scan of motor, see func:`ascan`,
    
    :param str mtr: a reference to a motor object, returned by :func:`spec.DefineMtr` or defined
      in the motor symbol.

    :param float start: starting position for scan, relative to current motor position
    
    :param float finish: ending position for scan, relative to current motor position

    :param int npts: number of points for scan

    :param float count: count time. 
       Counting is on time (sec) if count is 0 or positive; Counting is on monitor if count < 0

    :param int index: an index for the scaler, if more than one will be defined (see :func:`DefineScaler`).
       The default (0) is used if not specified.

    :param float settle: a time to wait (sec) after the motor has been moved before counting
       is starting. Default is 0.0 which means no delay

    Example:
      >>> spec.SetDet(2)
      >>> macros.dscan(spec.samX,-1,1,21,1,settle=.1)

    It is recommended that if dscan will be run in command line, where python commands are
      typed into a console window, that ipython be used in pylab mode (``ipython --pylab``).

    '''
    startpos = spec.wm(mtr)  # get starting position and validate the parameter
    ascan(mtr, startpos+start, startpos+finish, npts, count, index, settle,
          _func='dscan')

def ascan(mtr, start, finish, npts, count, index=0, settle=0.0, _func='ascan'):
    ''' Scan one motor and record parameters set with logging to the scanfile
    (see func:`SetScanFile`).

    :param str mtr: a reference to a motor object, returned by :func:`spec.DefineMtr` or defined
      in the motor symbol.

    :param float start: starting position for scan
    
    :param float finish: ending position for scan

    :param int npts: number of points for scan

    :param float count: count time. 
       Counting is on time (sec) if count is 0 or positive; Counting is on monitor if count < 0

    :param int index: an index for the scaler, if more than one will be defined (see :func:`DefineScaler`).
       The default (0) is used if not specified.

    :param float settle: a time to wait (sec) after the motor has been moved before counting
       is starting. Default is 0.0 which means no delay

    Example:
      >>> spec.SetDet(2)
      >>> macros.ascan(spec.samX,1,2,21,1,settle=.1)

    It is recommended that if ascan will be run in command line, where python commands are
      typed into a console window, that ipython be used in pylab mode (``ipython --pylab``).
    '''
    def specPrescanHeader():
        '''write spec headers
        '''
        scanFP.write('\n#S '+str(scanNumber)+'  '+str(_func)+'  '+str(mtrinfo['symbol'])+' '+
                     ' '+str(start)+' '+str(finish)+' '+str(npts)+' '+str(count)+'\n')
        scanFP.write('#D '+specdate()+'\n')
        if count < 0:
            lbl = spec.GetScalerLabels(index)[mon]
            scanFP.write('#M '+str(-count)+'  ('+str(mon)+':'+lbl+')\n')
        else:
            scanFP.write('#T '+str(count)+'  (Seconds)\n')
        scanFP.write('#G0 \n') # '0 0 0 0 0 1 0 0 0 0 0 0 50 0 0.1 0 68 68 50 -1 1 1 3.13542 3.13542 0 463.6 838.8'
        scanFP.write('#G1 \n') # '1.54 1.54 1.54 90 90 90 4.079990459 4.079990459 4.079990459 90 90 90 1 0 0 0 1 0 60 30 0 0 0 0 60 30 0 -90 0 0 1.54 1.54'
        scanFP.write('#G3 \n') # '4.079990459 -6.865325574e-16 -6.561207576e-16 -3.041179982e-17 -4.079990459 2.49819112e-16 0 0 -4.079990459'
        scanFP.write('#G4 \n') # '0 0 0 1.54 0 0 0 0 0 0 0 0 0 0 0 0 -180 -180 -180 -180 -180 -180 -180 -180 -180 0'
        scanFP.write('#Q 0 0 0\n')
        #  list all motor values
        i = 0
        j = 0
        for m in spec.ListMtrs():
            pos = spec.wm(spec.Sym2MtrVal(m))
            if abs(pos) < 1e-6: pos = 0.0
            if i == 0:
                scanFP.write('#P' + '%-2d' % j + ' %f' % pos)
                i = 1
            elif i == 7:
                scanFP.write(' %f\n' % pos)
                i = 0
                j += 1
            else:
                scanFP.write(' %f' % pos)
                i += 1
        if i != 0:
            scanFP.write('\n')
        scanFP.write('#U Beam Current: \n') # 102.3
        scanFP.write('#U Energy: \n') # 8.0509
        scanFP.write('#U Preamp Settings: \n') #  
        scanFP.write('#N 28\n') # 
        scanFP.flush()
    
    def specScanHeader():
        ''' write scan header
        '''
        scanFP.write('#L '+str(mtrinfo['symbol']))
        for txt in 'HKL':
            scanFP.write('  '+txt)
        for obj in monitor_list: 
            scanFP.write('  '+obj.label.strip().replace(' ','_'))
        if count < 0:
            # add time & Det
            lbl = spec.GetScalerLabels(index)[det]
            scanFP.write("  Seconds  "+lbl.strip().replace(' ','_'))
        else:
            # add Mon and Det
            if mon is not None:
                scanFP.write("  ")
                lbl = spec.GetScalerLabels(index)[mon]
                scanFP.write(lbl.strip().replace(' ','_'))
            scanFP.write("  ")
            lbl = spec.GetScalerLabels(index)[det]
            scanFP.write(lbl.strip().replace(' ','_'))
            scanFP.write('\n')
            scanFP.flush()
            
    def specScanList():
        '''write the current scan data point on a single line
        '''
        scanFP.write(str(pos))
        for txt in '000': scanFP.write(' '+txt)
        scanFP.write(' '+_write_logging_values())
        if count < 0:
            # add time & Det
            scanFP.write(" "+str(spec.GetScalerLastTime(index))+" "+
                         str(spec.GetScalerLastCount(index)[det]))
        else:
            # add Mon and Det
            if mon is not None:
                scanFP.write(" "+
                             str(spec.GetScalerLastCount(index)[mon]))
            scanFP.write(" "+
                         str(spec.GetScalerLastCount(index)[det]))
        scanFP.write('\n')
        scanFP.flush()

    def FitScan(positions,obs):
        '''Fit the scan results with Gaussian, if more than 10 points.
        If fit succeeds, label the plot and write results to scan file.
        '''
        FWHM = '?'
        fitpos = '?'
        lbl = ''
        COM = '?'
        if sumy != 0:
            COM = "%.3f" % (COMsum / sumy)
        if len(obs) > 10: 
            fitEq = FitGauss(positions,obs)
            pf = _eqfit(positions,obs,fitEq)
            if pf is not None:
                if abs(pf[0]-maxpos) < 0.5*pf[2]:
                    fitposa,fitmax,FWHMa,b = pf
                    FWHM = "%.4f" % FWHMa
                    fitpos = "%.4f" % fitposa
                    _eqshow(page,pf,positions,fitEq)
                    lbl = ('Max = '+str(ymax)+' @ '+str(maxpos)+
                           ' FWHM = '+str(FWHM)+' @ '+str(fitpos)+
                         ' COM: '+str(COM)+
                         ' SUM: '+str(sumy))            
                    scanFP.write('#R '+str(scanNumber)+'  Max: '+str(ymax)+'  at '+str(maxpos)+
                                 '   FWHM: '+str(FWHMa)+'  at '+str(fitposa)+
                                 '   COM: '+str(COM)+
                                 '   SUM: '+str(sumy)+'\n')
        if not lbl:
            lbl = ('Max = '+str(ymax)+' @ '+str(maxpos)+
                   '   COM: '+str(COM)+
                   '   SUM: '+str(sumy))
        page.figure.suptitle(lbl)    

    #======================================================================
    # start of actual ascan routine
    #startpos = spec.wm(mtr)  # get starting position and validate the parameter
    mtrinfo = spec.GetMtrInfo(mtr)
    det = spec.GetDet(index=index)
    mon = spec.GetMon(index=index)
    if det is None:
       raise spec.specException('Attempt to scan without defining a Det channel.'+
                            ' Use spec.SetDet() first')
 
    if count < 0 and mon is None:
        raise spec.specException('Attempt to count on Monitor without defining a Monitor channel.'+
                            ' Use spec.SetMon() first')        

    positions = np.linspace(start, finish, npts)
    global scanNumber
    scanNumber += 1
    spec.simulationcount = 0 # affects simulations only
    # prepare to plot
    _makePlotWin("ascan results")
    tablbl = 'Scan '+str(scanNumber)
    page = plotwin.AddPlotTab(tablbl)
    plotwin.RaisePlotTab(tablbl)
    plotwin.frame.Show(True)
    page.figure.gca().set_xlabel('Motor '+str(mtrinfo['symbol'])+' position')
    page.figure.gca().set_ylabel('Intensity')
    dl = (finish-start)/20. # 5% margin
    page.figure.gca().set_xlim(start-dl,finish+dl)
    specPrescanHeader()    # write spec headers
    specScanHeader()     # header for scan

    # perform the scan
    obs = []
    COMsum = 0.0
    try:
        i = 0
        sumy = 0.0
        ymax = None
        maxpos = None
        for pos in positions:
            i += 1
            spec.PositionMtr(mtr,pos,wait=True)
            if settle > 0: spec.sleep(settle)
            inten = spec.ct(count)[det]
            sumy += inten
            obs.append(inten)
            COMsum += inten*pos
            if ymax == None or ymax < inten:
                ymax,maxpos = inten,pos
            specScanList() # write the current scan data point
            # plot the current point
            page.figure.gca().plot(pos,inten,'+b')
            page.canvas.draw()
            pnb.UpdatePlots()
            if StopScan:
                raise KeyboardInterrupt
    except KeyboardInterrupt:
        print("Scan interrupted by Control-C after "+str(i)+" points")
        scanFP.write("#C "+specdate()+"  Scan aborted after after "+str(i)+" points.\n")
        scanFP.write("#C "+specdate()+"  do ?\n") # get top script name?
        #C Fri Jun 24 11:37:00 2011.  do wang_june11_macros.mac.
    else:
        FitScan(positions,obs) # Fit the scan results w/Gaussian, plot & label
    # expand scale slightly on y
    dl = (max(obs)-min(obs))/20. # 5% margin
    page.figure.gca().set_ylim(min(obs)-dl,max(obs)+dl)
    page.canvas.draw()
    pnb.UpdatePlots()
    global LastPlot
    LastPlot = [scanNumber,page,positions,obs,mtrinfo]
    scanFP.flush()


def _eqdiff(parm,x,y,FitObj):
    '''Fitting function, computes squared differences between obs and fitted intensities
    '''
    return (np.array(FitObj.Eval(parm,x))-y)**2

def _eqfit(x,y,FitObj):
    '''Fit parameters to using a fitting function and a starting parameter estimator
    '''
    import scipy.optimize as spo
    p = FitObj.StartParms()
    pf = spo.leastsq(_eqdiff,p,args=(x,y,FitObj))
    if pf[1] == 1: return pf[0]

def _eqshow(page,p,x,FitObj):
    '''Plot a fitting function as a line over a range of data
    '''
    xfit = np.linspace(x[0],x[-1],500)
    yfit = FitObj.Eval(p,xfit)
    page.figure.gca().plot((p[0],p[0]),(p[-1],p[-1]+p[1]),'-g')
    page.figure.gca().plot((xfit[0],xfit[-1]),(p[-1],p[-1]),'-g')
    page.figure.gca().plot(xfit,yfit,'-r')


def RefitLastScan(FitClass, **kwargs):
    '''Fit and plot an arbitrary equation to data from the last ascan
    
    :param class FitClass: a class that defines a minumum of two methods, one
      to define a fitting function and the other to determine rough starting values
      for the fitting function. See :class:`FitGauss` or :class:`FitSawtooth` for
      examples of Fitting classes.

    Optional: additional keyword parameters will be passed for the creation of a FitClass object.

    :returns: an optimized list of parameters or None if the fit fails

    Example:
      >>> macros.RefitLastScan(macros.FitSawtooth)
      Parameter values =1.45, 28.5, 1.5, 2.1053
      array([  1.44999999,  28.50005241,   1.4999749 ,   2.10525894])
    or
      >>> macros.RefitLastScan(macros.FitSawtooth, Symmetric=False)
      Parameter values =1.45, 28.5, 1.5, 2.1053, 2.1053
      array([  1.44999999,  28.5000524 ,   1.49997491,   2.10525896,   2.10525891])

    '''
    scannum,page,x,y,mtrinfo = LastPlot
    fitEq = FitClass(x,y,**kwargs)
    pf = _eqfit(x,y,fitEq)
    if pf is None:
        print "fit failed"
        return
    tablbl = 'Scan '+str(scannum)+' refit'
    page = plotwin.ReusePlotTab(tablbl)
    page.figure.clear()
    plotwin.RaisePlotTab(tablbl)
    page.figure.gca().set_xlabel('Motor '+str(mtrinfo['symbol'])+' position')
    page.figure.gca().set_ylabel('Intensity')
    page.figure.gca().plot(x,y,'+b')
    dl = (x[-1]-x[0])/20. # 5% margin
    page.figure.gca().set_xlim(x[0]-dl,x[-1]+dl)
    dl = (max(y)-min(y))/20. # 5% margin
    page.figure.gca().set_ylim(min(y)-dl,max(y)+dl)
    _eqshow(page,pf,x,fitEq)
    lbl = fitEq.Format(pf)

    page.figure.suptitle(lbl)
    page.canvas.draw()
    pnb.UpdatePlots()
    return pf

def SendTextEmail(recipientlist, msgtext,
                  subject = 'APSpy auto msg',
                  recipientname = None,
                  senderemail = '1ID@aps.anl.gov'):
    '''Send a short text string as an e-mail message. Uses the APS outgoing email
    server (apsmail.aps.anl.gov) to send the message via SMTP.
    
    :param str recipientlist: A string containing a single e-mail address or a list or tuple (etc.)
       containing a list of strings with e-mail addresses.
    :param str msgtext: a string containing the contents of the message to be sent.
    :param str subject: a subject to be included in the e-mail message; defaults to "APSpy auto msg".
    :param str recipientname: a string to be used for the recipient(s) of the message. If not specified,
       no "To:" header shows up in the e-mail. This should be an e-mail address or @aps.anl.gov
       is appended.
    :param str senderemail: a string with the e-mail address identified as the sender of the e-mail;
       defaults to "1ID@aps.anl.gov". This should be an e-mail address or @aps.anl.gov
       is appended.
       
    Examples:
      >>> msg = 'This is a very short e-mail'
      >>> macros.SendTextEmail(['toby@sigmaxi.net','brian.h.toby@gmail.com'],msg, subject='test')

    or with a single address:
      >>> msg = """Dear Brian,
      ...   How about a longer message?
      ... Thanks, Brian
      ... """
      >>> to = "toby@anl.gov"
      >>> macros.SendTextEmail(to,msg,recipientname='spamee@anl.gov',senderemail='spammer@anl.gov')

    A good way to use this routine is in a try/except block:
      >>> userlist = ['user@univ.edu','contact@anl.gov']
      >>> try:
      >>>     macros.write_logging_header(logname)
      >>>     spec.umv(spec.mts_y,stY) 
      >>>     for iLoop in range(nLoop):
      >>>         spec.umv(spec.mts_x2,stX) 
      >>>         for xLoop in range(nX): 
      >>>             GE_expose(fname, Nframe, tframe)
      >>>             macros.write_logging_parameters(logname)
      >>>             spec.umvr(spec.mts_x2,dX) 
      >>>         spec.umvr(spec.mts_y,dY) 
      >>>     macros.beep_dac()
      >>> except Exception:
      >>>     import traceback
      >>>     msg = "An error occurred at " + macros.specdate()
      >>>     msg += " in file " + __file__ + "\\n\\n"
      >>>     msg += str(traceback.format_exc())
      >>>     macros.SendTextEmail(userlist, msg, 'Beamline Abort')
    
    '''

    from email.Message import Message     # postpone imports until needed, since this routine is 
    import smtplib                        # not often called and a bit of a delayon 1st use is OK
    msg = Message()
    # create a recipient name string if none is specified
    if recipientname is not None:
        msg['To'] = recipientname
    msg['From'] = senderemail
    msg['Subject'] = subject
    msg.set_payload(msgtext)
    #if debug: print "sending e-mail message"
    server = smtplib.SMTP('apsmail.aps.anl.gov')
    #server.set_debuglevel(1)
    server.sendmail(senderemail, recipientlist,
                    str(msg))
    #server.quit()

def UserIn(parname,default,typ):
    '''Prompt a user for input.

    For reasons unclear, this is not raising an Exception on Control-C on Linux,
    but Control D does raise an exception, so use that.

    :param str parname: a string to be given to the user to tell them what to input
    :param (any) default: a default value, if no input is provided, use None to force user 
      input
    :param type typ: a data type, such as int, float, or str

    :returns: the value provided by the user in the selected type

    Examples:

    >>> UserIn('test',2.0,float)
    test (2.0): x
    Invalid, try again
    test (2.0): 3.1
    3.1

    >>> UserIn('test',None,float)
    test (None): 
    Invalid, try again
    test (None): 4
    4.0

    >>> UserIn('test',2,int)
    test (2): 2.0
    Invalid, try again
    test (2): 2
    2


    '''
    val = None
    while val is None:
        tmp = raw_input(parname + " ("+str(default)+"): ")
        if tmp.strip() == "": 
            if default is None: continue
            tmp = default
        try:
            val = typ(tmp)
        except:
            print "Invalid, try again"
            pass
    return val

################################################################################################
# PV monitoring utilities
class _MonitorCallback(object):
    '''Defines a class to be used to define a callback routine
    '''
    def __init__(self,fileprefix,pv,monitorlist,pvvalue,delay):
        self.monitorlist = monitorlist
        self.pvvalue = pvvalue
        self.delay = delay
        if delay is not None:
            self.lastread = time.time()-2*delay
        if monfiledict.get(fileprefix) is None:
            self.fp = open(fileprefix+time.strftime('%Y-%m-%d-%H%M')+'.log','w')
            self.fp.write('Monitor opened at '+time.asctime()+'\n')
        else:
            self.fp = monfiledict[fileprefix]
        self.monpv = pv # monitored PV
    def StartMonitor(self):
        'starts the monitoring'
        ep.camonitor(self.monpv,callback=self.CB)
    def StopMonitor(self):
        'stops the monitoring'
        ep.camonitor_clear(self.monpv)
    def CB(self,**kw):
        'call back routine'
        # test if value of PV is selected value (or for float close)
        if self.pvvalue is not None:
            if isinstance(kw['value'],float):
                if abs(kw['value']-self.pvvalue) > 1e-5: return
            elif self.pvvalue != kw['value']: 
                return
        if self.delay is not None:
            if self.lastread + self.delay > time.time(): return
            self.lastread = time.time()            
        self.fp.write(dt.datetime.today().strftime('%Y-%m-%d-%H:%M:%S.%f')+', ')
        for pv in self.monitorlist:
            val = PVmondict[pv].get()
            self.fp.write(pv + '=' + str(val) + ', ')
        self.fp.write('\n')
        self.fp.flush()
        
def DefMonitor(fileprefix,pv,monitorlist,pvvalue=None,delay=None):
    '''Write values of PVs in monitorlist each time that PV pv changes,
    values are written to a file named by fileprefix + timestamp
    optionally, values are written only if the PV is set to value pvvalue
    (if not None) and optionally only recording the first change in a period of delay
    seconds (if not None):

    Monitoring starts when :func:`StartAllMonitors` is called.

    :param str fileprefix: defines name of file to use
    :param str pv: PV to monitor
    :param list monitorlist: list of PVs to report
    :param ? pvvalue: report monitored PV only if this value is obtained
    :param float delay: do not log changes more frequently than this frequency in seconds

    see :ref:`Monitoring-sec` for an example of use.

    '''
    
    if not (EPICS and spec.UseEPICS()): # in simulation
        print 'Monitoring of PVs cannot be simulated'
        return

    # create callback object
    cbobj = _MonitorCallback(fileprefix,pv,monitorlist,pvvalue,delay)
    global monfiledict
    monfiledict[fileprefix] = cbobj.fp
    monobjlist.append(cbobj)


def StartAllMonitors(sleep=True):
    '''Start the monitoring defined in DefMonitor. Optionally delay until control-C is pressed.
    The control-C operation closes all files and clears the monitoring information.

    :param bool sleep: if True (default) start an infinite loop of one second delays

    see :ref:`Monitoring-sec` for an example of use.

    '''

    # compile a list of PVs to be monitored and create an object for each, but don't 
    # duplicate one if reused
    if not (EPICS and spec.UseEPICS()): # in simulation
        print 'Monitoring of PVs cannot be simulated'
        return

    global PVmondict
    global monfiledict
    global monobjlist
    if len(monobjlist) == 0:
        raise spec.specException('No PVs being logged')
    for obj in monobjlist:
        for pv in obj.monitorlist:
            if PVmondict.get(pv) is None:
                PVmondict[pv] = ep.PV(pv)
    # launch monitoring
    for obj in monobjlist:
        obj.StartMonitor()
    if not sleep: return

    # delay for control C
    while sleep:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print '\nEnded by control-c'
            break

    # stop monitoring, close files and clean up
    for obj in monobjlist:
        obj.StopMonitor()
    for obj in monobjlist:
        obj.fp.close()
    monobjlist = []
    monfiledict = {}
    PVmondict = {}


################################################################################################
# 1-ID specific code
if EPICS: 
    PV = ep.PV
    beeper = PV('1id:DAC1_8.VAL')
    shutterA_state = PV("PA:01ID:A_SHTRS_CLOSED")
    shutterA_openPV = "1id:rShtrA:Open.PROC"
    shutterC_state = PV('PA:01ID:C_SHTRS_CLOSED')
    shutterC_openPV = PV('1id:rShtrC:Open.PROC')

    fastshtr_man = PV('1id:9440:1:bo_3.VAL')
    fastshtr_remote = PV('1id:9440:1:bo_5.VAL')

def Cclose(): #arm shutters    
    '''Close 1-ID fast shutter in B hutch
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Closing Fast Shutter"
        return
    fastshtr_man.put(0)

def Copen(): #arm shutters    
    '''Open 1-ID fast shutter in B hutch
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Opening Fast Shutter"
        return
    fastshtr_man.put(1)
    
def shutter_sweep(): 
    ''' Set 1-ID fast shutter so that it will be controlled by an external electronic control
    (usually the GE TTL signal)
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Set Fast Shutter to sweep"
        return
    Cclose()  #p "Close shutter before changing"    
    fastshtr_remote.put(1)  # p "shutter to sweep mode"
    
def shutter_manual():    
    ''' Set 1-ID fast shutter so that it will not be controlled by the GE TTL signal
    and can be manually opened and closed with Copen() and Cclose()
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Set Fast Shutter to manual"
        return
    Cclose()  #p "Close the shutter, to be sure it is closed"
    fastshtr_remote.put(0)  # p "shutter to manual"

def check_beam_shutterC(): #arm shutters
    '''If not already open, open 1-ID-C Safety shutter to bring beam into 1-ID-C.
    Keep trying in an infinite loop until the shutter opens.
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Confirm C-Hutch Shutter is open"
        return
    while shutterC_state.get() != 0: #true if shutter is closed (0=Open)
        print "opening C shutter"
        shutterC_openPV.put(1)
        spec.sleep(6) #open the shutter & wait        
Sopen = check_beam_shutterC
    
def check_beam_shutterA():
    '''If not already open, open 1-ID-A Safety shutter to bring beam into 1-ID-A.
    Keep trying in an infinite loop until the shutter opens.
    '''
    if not (EPICS and spec.UseEPICS()): # in simulation
        print "Confirm A-Hutch Shutter is open"
        return
    i = 0
    while shutterA_state.get() != 0: # 1 is Closed
        print "sleeping due to beam dump"
        if i == 0: 
            p = PV(shutterA_openPV)
        i += 1
        p.put(1) # send a open command to PV in shutterA_openPV (1=Open)
        spec.sleep(10)

def MakeMtrDefaults(fil=None, out=None):
    '''Routine in Development:
    Creates an initialization file from a spreadsheet describing
    the 1-ID beamline motor assignments

    :param str fil: input file to read. By default opens file ../1ID/1ID_stages.csv relative to
       the location of the current file.   

    :param str out: output file to write. By default writes file ../1ID/mtrsetup.py.new
       Note that if the default file name is used, the output file must be
       renamed before use to mtrsetup.py
    '''
    import csv
    if fil is None:
        fil = os.path.join(
            os.path.split(os.path.split(os.path.abspath(__file__))[0])[0],
            '1ID',
            '1ID_stages.csv')
    print('reading file: '+str(fil))
    if out is None:
        out = os.path.join(
            os.path.split(os.path.split(os.path.abspath(__file__))[0])[0],
            '1ID',
           'mtrsetup.py.new')
    print('writing file: '+str(out))
    
    fo = open(out,'w')
    fo.write("# created " + specdate() + "\n")
    fo.write("import sys\n")
    fo.write('sys.path.append("'+os.path.split(os.path.abspath(__file__))[0]+'")\n')
    fo.write("import spec\n")
    fo.write("spec.EnableEPICS()\n")
    fo.write("spec.DefineScaler('1id:scaler1',16)\n")
    # define column number symbols (N.B. numbering starts with 0)
    mnenom = 1
    crate = 3
    num = 2
    comments = 7
    with open(fil, 'rUb') as fp:
        reader = csv.reader(fp)
        i = 0
        for row in reader:
            i += 1
            if i==1: continue # skip 1st row
            if row[mnenom].strip() == "": continue
            fo.write("spec.DefineMtr(" +
                     "'" + row[mnenom].strip() + "', " + 
                     "'" + row[crate].strip() + ':m' + row[num].strip() + "', " + 
                     "'" + row[comments].strip() + "') \t # " + str(i) + "\n")
    fp.close()
    fo.close()

def SaveMotorLimits(out=None):
    '''Routine in Development:
    Creates an initialization file for simulation use with the limits for
    every motor PV that is found in the current 1-ID beamline motor assignments.
    import mtrsetup.py or equivalent first. Scans each PV from 1 to the max number defined.

    :param str out: output file to write, writes file motorlimits.dat.new in the same
       directory as this file by default.
       Note that if the default file name is used, the output file must be
       renamed before use to motorlimits.dat
    '''
    if not EPICS:
        print 'This can only be run with EPICS on-line'
        return
    ioclist = []
    iocmax = {}
    for m in spec.ListMtrs():
        mtrdict = spec.GetMtrInfo(spec.Sym2MtrVal(m))
        try:
            ioc,mtr = mtrdict['PV'].split(':m')
            mtr = int(mtr)
        except Exception:
            break
        print m,spec.Sym2MtrVal(m),mtrdict['PV'].split(':m'),ioc,mtr
        if ioc not in ioclist: ioclist.append(ioc)
        if iocmax.get(ioc) == None: iocmax[ioc] = mtr
        if iocmax[ioc] < mtr: iocmax[ioc] = mtr

    if out is None:
        out = os.path.join(
            os.path.split(os.path.abspath(__file__))[0],
            'motorlimits.dat.new'
            )
    fo = open(out,'w')
    for ioc in ioclist:
        for i in range(1,iocmax[ioc]+1):
            PV = ioc + ':m' + str(i)
            #fo.write(PV)
            try:
                fo.write(
                    ioc+' '+str(ep.caget(PV+'.LLM'))+' '+str(ep.caget(PV+'.HLM'))
                )
                fo.write('\n')
            except:
                pass
    fo.close()

def beep_dac(beeptime=1.0):
    '''Set the 1-ID beeper on for a fixed period, which defaults to 1 second
    uses PV object beeper (defined as 1id:DAC1_8.VAL)
    makes sure that the beeper is actually turned on and off
    throws exception if beeper fails

    :param float beeptime: time to sound the beeper (sec), defaults to 1.0

    '''
    if not (EPICS and spec.UseEPICS()): # in simulation, use the terminal bell
        print('\a\a\a')
        return
    volume = 9 # beeper volume setting
    # part 1: set DAC to ON
    val = 0 # value of DAC (initialized)
    i = 0 # loop counter
    while abs(val-volume)>0.1: # within 0.1 V is OK by me
        if i > 10: # give up after 10 tries
            raise Exception,'Set Beep failed in 10 tries'
        i+=1
        beeper.put(volume, True, 10.) # set on
        val = beeper.get(use_monitor=False) # read value; force rereading of current value
        if val != volume: spec.sleep(0.01) # wait before trying again
        if val is None: val = 9999  # don't crash, even if beeper.get fails on read
    # part 2: delay while on
    spec.sleep(beeptime)
    # part 3: turn DAC OFF
    i = 0
    while abs(val)>0.1:
        if i > 10: 
            raise Exception,'Clear Beep failed in 10 tries'
        i += 1
        beeper.put(0, True, 10.)   # 0 is beeper off
        spec.sleep(0.001)
        val = beeper.get()
        if val is None: val = 9999  # don't crash, even if beeper.get fails on read
    # all done
    return

def _test1():
    '''Set up some motors and a scaler'''
    spec.DefineMtr('samX','1idc:m77','sample X position (mm) + outboard')
    spec.DefineMtr('samZ','1idc:m78','sample Z position (mm) + up')
    spec.DefineScaler('ioc:scaler1',16)

def _test2():
    '''Set up some items to log'''
    GE_prefix = 'GE2:cam1:'
    init_logging()
    log_it(make_log_obj_PV('GE_fname',GE_prefix+"FileName",as_string=True))
    log_it(make_log_obj_PV('GE_fnum',GE_prefix+"FileNumber"))
    log_it(make_log_obj_motor(spec.samX))
    log_it(make_log_obj_Global('var spec.S0','spec.S[0]'))
    log_it(make_log_obj_scaler(10))
    log_it(make_log_obj_Global('var S9','spec.S[9]'))
    log_it(make_log_obj_PV('p1Vs',"1idc:m64.RBV"))

def _test2_old():
    '''Set up some items to log'''
    # this uses old style parameter logging functions
    GE_prefix = 'GE2:cam1:'
    init_logging()
    add_logging_PV('GE_fname',GE_prefix+"FileName",as_string=True)
    add_logging_PV('GE_fnum',GE_prefix+"FileNumber")
    add_logging_motor(spec.samX)
    add_logging_Global('var spec.S0','spec.S[0]')
    add_logging_scaler(10)
    add_logging_Global('var S9','spec.S[9]')
    add_logging_PV('p1Vs',"1idc:m64.RBV")

def _test3():
    '''test logging'''
    spec.ct()
    write_logging_header()
    write_logging_parameters()
    spec.mv(spec.samX,1.34)
    spec.ct(2)
    write_logging_parameters()

def _test4():
    '''test ascan and fitting'''
    spec.SetDet(2)
    ascan(spec.samX,1,2,21,1,settle=.1)
    spec.sleep(3)
    RefitLastScan(FitSawtooth,Symmetric=False)

def _test5():
    '''Test LoggingPlot
    '''
    DefineLoggingPlot(
        'I vs pos',
        make_log_obj_motor(spec.samX),
        make_log_obj_scaler(2),
        )
    DefineLoggingPlot(
        'I vs time',
        make_log_obj_Global('time (sec)','spec.ELAPSED'),
        make_log_obj_scaler(2),
        make_log_obj_scaler(3),
        )
    spec.initElapsed()
    try:
        spec.umv(spec.samX,2) 
        for iLoop in range(30):
            spec.umvr(spec.samX,0.05)
            spec.sleep(0.5)
            spec.ct(1)
            UpdateLoggingPlots()
        beep_dac()
    except Exception,err:
        import traceback
        msg = "An error occurred at " + specdate()
        msg += " in file " + __file__ + "\n"
        msg += "Error message = " + str(err) + "\n\n"
        msg += str(traceback.format_exc())
        print msg
        #SendTextEmail(userlist, msg, 'Beamline Abort')

if __name__ == '__main__':
    _test1()
    _test2()
    #_test2_old()
    _test3()
    _test4()
    spec.sleep(5)
    _test5()
    ShowPlots()
    
