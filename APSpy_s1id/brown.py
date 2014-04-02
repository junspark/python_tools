import time
import datetime as dt
import epics as ep  #from epics import PV
import spec
import macros as mac
PV = ep.PV

###############################################################################################################################
# misc beamline macros
#PV Objects
spec.EnableEPICS()
spec.DefineMtr('mts_x2','1idc:m4','MTS_X2')
spec.DefineMtr('mts_y','1idc:m6','MTS_Y')
spec.DefineScaler('1id:scaler1',16)

GE_prefix = 'GE2:cam1:'
#GE_fnum = ep.PV(GE_prefix+"FileNumber")
GE_fname = ep.PV(GE_prefix+"FileName")
GE_tframe = ep.PV(GE_prefix+"AcquireTime")
GE_Nframe = ep.PV(GE_prefix+'NumImages')
GE_Acquire = ep.PV(GE_prefix+'Acquire')
GE_address = ep.PV(GE_prefix+'DetectorState_RBV')

def sleep(timesec):
    time.sleep(timesec)
    

###############################################################################################################

mac.init_logging()
mac.add_logging_PV('GE_fname',GE_prefix+"FileName",as_string=True)
mac.add_logging_PV('GE_fnum',GE_prefix+"FileNumber")
mac.add_logging_PV('GE_tframe', GE_prefix+"AcquireTime")
mac.add_logging_PV('GE_Nframe',GE_prefix+'NumImages')
mac.add_logging_Global('S0','spec.S[0]')
mac.add_logging_Global('S1','spec.S[1]')
mac.add_logging_Global('S2','spec.S[2]')
mac.add_logging_Global('S8','spec.S[8]')
mac.add_logging_Global('S9','spec.S[9]')
mac.add_logging_Global('S10','spec.S[10]')
mac.add_logging_Global('S11','spec.S[11]')    
mac.add_logging_PV('p1Hs',"1idc:m62.RBV")
mac.add_logging_PV('p1Vs',"1idc:m64.RBV")
mac.add_logging_PV('Iring',"BL01:srCurrent")
mac.add_logging_PV('energy',"1id:userTran3.A") 
#mac.add_logging_PV('energy_cal',"1id:userTran3.A") 
mac.add_logging_PV('preamp1',"1idc:A3sens_num.VAL") 
mac.add_logging_PV('preamp2',"1idc:A4sens_num.VAL") 
mac.add_logging_motor(spec.mts_x2)
mac.add_logging_motor(spec.mts_y)
#mac.add_logging_motor() # sammy_z,sammy_x2,sammy_z2,sammy_phi
mac.add_logging_PV('keyence1',"1id:Keyence:1:ch1.VAL") 
mac.add_logging_PV('keyence2',"1id:Keyence:1:ch2.VAL") 
mac.add_logging_PV('cross',"1id:D2Ch1_calc.VAL") 
mac.add_logging_PV('load',"1id:D2Ch2_calc.VAL") 
mac.add_logging_PV('mts3',"1id:D2Ch3_calc.VAL") 
mac.add_logging_PV('mts4',"1id:D2Ch4_calc.VAL") 
mac.add_logging_PV('temp1',"1id:ET_RI:Temp1") 
mac.add_logging_PV('temp2',"1id:ET_RI:Temp2") 
mac.add_logging_PV('temp3',"1id:ET_RI:Temp3") 

def scan_xyN (fname, Nframe, tframe, stX, nX, dX, stY, nY, dY, nLoop, logname):
    ''' Usage: scan_xyN [fname] [Nframe] [tframe] [x0] [Nx] [dx] [y0] [Ny] [dy] [nLoop] [logname]
    '''
    # define PVs to be recorded

#p date(),GE_fname,GE_fnum,GE_tframe,GE_Nframe,S[0],S[1],S[2],S[8],S[9],S[10],S[11],
#   p1Hs,p1Vs,Iring,energy,energy_cal,preamp1,preamp2,
#    sammy_x,sammy_y,sammy_z,sammy_x2,sammy_z2,sammy_phi,
#    keyence1,keyence2,cross,load,mts3,mts4,temp1,temp2,temp3,temp4

    mac.write_logging_header(logname)
    for iLoop in range(nLoop):
        spec.umv(spec.mts_y,stY) 
        for yLoop in range(nY):
            spec.umv(spec.mts_x2,stX) 
            for xLoop in range(nX): 
                GE_expose(fname, Nframe, tframe)
                #record beamline and exposure data in parameter file after exposure
                mac.write_logging_parameters(logname)
                spec.umvr(spec.mts_x2,dX) 
            spec.umvr(spec.mts_y,dY) 
    mac.beep_dac()

    
def GE_expose(fname, Nframe, tframe):
    """Collect data with a GE detector, defined by PV objects, GE_fname, GE_tframe and GE_Nframe.
    This checks the shutters are open for A & C and closes the fast shutter and puts it 
    under remote control. The GE is loaded with the function's parameters and is started.
    While the GE collects data, the default scaler is counted. When the GE indicates it is done
    the fast shutter is taken out of remote control mode.
    
    :param str fname: Defines the file name used by the GE for data collection
    :param int Nframe: Defines the number of frames that will be collected
    :param float tframe: Defines the time per frame (sec)
    """

    delt=0.05 #wait time between epics commands
    mac.Cclose() #arm shutters
    mac.check_beam_shutterA()
    mac.check_beam_shutterC() #arm shutters  
    mac.shutter_sweep() #shutter will be controlled remotely (by GE TTL)

    # set GE collection params                 
    GE_fname.put(fname)
    GE_tframe.put(tframe)
    GE_Nframe.put(Nframe)
    sleep(delt)

    # start collection
    GE_Acquire.put(1)
    sleep(delt) # probably serves no purpose, may as well start count immediately
    # start a count on scaler to last while GE collects data plus one second
    spec.ct(Nframe*tframe+1)  #count scalers for absorption/i0 info
 
    GE_wait_for_idle() #return prompt once GE is idle
    mac.shutter_manual() #reset to allow Copen/Cclose shutter commands

def GE_wait_for_idle(wait=250):
    '''check if GE is idle by checking the Epics PV driven by the Area Detector Control application
    checks every 0.1 sec (set by poll_time) up to wait seconds. If the wait is exceeded, the
    GE is assumed to be hung up and a Exception is triggered.

    :param int wait: time to wait before triggering an Exception. Defaults to 250 sec.
    ''' 
    
    poll_time=0.1
    Ncheck_max= wait/poll_time
    icheck=0
    sleep(poll_time)

    while GE_address.get() !=  0: # value of 0 = idle
        icheck += 1
        if icheck > Ncheck_max:
            raise Exception,"waited too long for GE - check detector computer and restart programs / reboot as needed"
        sleep(poll_time) #extra safety factor
