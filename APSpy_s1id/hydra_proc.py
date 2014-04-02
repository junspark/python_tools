'''This is a data collection module that collects a grid scan moving three motors
'''

import AD
import spec
import macros

# define some globals
det = (AD.ScintX,AD.GE1,AD.GE2,AD.GE3,AD.GE4) # default detectors to use
logfile = 'test.par'                          # default par file name
userlist = ('almer@aps.anl.gov',)             # default user to tell of crashes
motor1 = spec.samY                            # default motors to scan (slowest scanned)
motor2 = spec.phi                             # default motors to scan (2nd slowest scanned)
motor3 = spec.samX3                           # default motors to scan (fastest scanned)

def setup_logging():
    '''Defines the parameters to be recorded during the scan'''
    macros.init_logging()
    macros.add_logging_PV('filename', 'GE1:cam1:FileName_RBV',as_string=True)
    macros.add_logging_PV('ge1_num','GE1:cam1:FileNumber')
#macros.add_logging_PV('ge2_num','GE2:cam1:FileNumber')
    macros.add_logging_PV('ScintX','ScintX:TIFF1:FileNumber')
    macros.add_logging_PV('ge3_num','GE3:cam1:FileNumber')
    macros.add_logging_PV('ge4_num','GE4:cam1:FileNumber')
    macros.add_logging_PV('ge1_time','GE1:cam1:AcquireTime_RBV')
    macros.add_logging_PV('ge1_frames','GE1:cam1:NumImages_RBV')
    for i in (0,1,2,8,11,12,13):
        macros.add_logging_scaler(i)
    macros.add_logging_motor(spec.JJHAp)
    macros.add_logging_motor(spec.JJVAp)
    macros.add_logging_PV('Iring',"BL01:srCurrent")
    macros.add_logging_PV('energy',"1id:userTran3.A")
    macros.add_logging_PV('energy',"1id:userTran3.A") # want cal
    macros.add_logging_PV('preamp1',"1idc:A3sens_num.VAL")
    macros.add_logging_PV('preamp2',"1idc:A4sens_num.VAL")
    macros.add_logging_motor(spec.samX)
    macros.add_logging_motor(motor1)
    macros.add_logging_motor(spec.samZ)
    macros.add_logging_motor(motor3)
    macros.add_logging_motor(spec.hydraZ)
    macros.add_logging_motor(motor2)
    macros.add_logging_PV('keyence1',"1id:Keyence:1:ch1.VAL")
    macros.add_logging_PV('keyence2',"1id:Keyence:1:ch2.VAL")
    macros.add_logging_PV('cross',"1id:D2Ch1_calc.VAL")
    macros.add_logging_PV('load',"1id:D2Ch2_calc.VAL")
    macros.add_logging_PV('mts3',"1id:D2Ch3_calc.VAL")
    macros.add_logging_PV('mts4',"1id:D2Ch4_calc.VAL")
    macros.add_logging_PV('temp1',"1id:ET_RI:Temp1")
    macros.add_logging_PV('temp2',"1id:ET_RI:Temp2")
    macros.add_logging_PV('temp3',"1id:ET_RI:Temp3")
    macros.add_logging_PV('tempX',"1id:ET_RI:Temp3") 


def collect(*args):
    if len(args) == 0:
        print "Motors are listed with the innermost loop first."
        print "Press ^D (control D) to abort input\n"
        print ("Fastest moving motor (X0) is "+str(spec.GetMtrInfo(motor3)['symbol']))
        X0 = macros.UserIn("X0",spec.wm(motor3),float)
        DX = macros.UserIn("DX",0.1,float)
        NX = macros.UserIn("NX",1,int)

        print ("Next fastest moving motor (PHI0) is "+str(spec.GetMtrInfo(motor2)['symbol']))
        PHI0 = macros.UserIn("PHI0",spec.wm(motor2),float)
        DPHI = macros.UserIn("DPHI",0.1,float)
        NPHI = macros.UserIn("NPHI",1,int)

        print ("Slowest moving motor (Y0) is "+str(spec.GetMtrInfo(motor1)['symbol']))
        Y0 = macros.UserIn("Y0",spec.wm(motor1),float)
        DY = macros.UserIn("DY",0.1,float)
        NY = macros.UserIn("NY",1,int)

        Count = macros.UserIn("count",1.0,float)
        frames = macros.UserIn("frames",1,int)
        filename = macros.UserIn("filename",None,str)
    elif len(args) == 12:
        X0, DX, NX, PHI0, DPHI, NPHI, Y0, DY, NY, Count, frames, filename = args
    else:
        print 'Wrong number of arguments'
        print '  collect(X0, DX, NX, PHI0, DPHI, NPHI, Y0, DY, NY, Count, frames, filename)'
        return

#    print 'NX = ', NX, ', NPH1 = ', NPHI, ', X0 = ', X0, ', DX = ', DX, ', PHI0 = ', PHI0, ', DPH1 = ', DPHI, ', File Name = ', filename, ', Time Per Frame = ', Count, ', Number of Frames = ', frames

    macros.write_logging_header(logfile)

    try: 
        for IY in range(NY):
            Y = Y0 + (IY*DY)
            spec.umv(motor1,Y)
            for IPHI in range(NPHI):
                PHI = PHI0 + (IPHI*DPHI)
                spec.umv(motor2,PHI)
                for IX in range(NX):
                    X = X0 + (IX*DX)
                    spec.umv(motor3,X)                
                    macros.Copen()
                    spec.count_em(Count*frames)
                    AD.AD_acquire(det,filename,Count,frames,wait=True)
                    spec.wait_count()
                    spec.get_counts()
                    macros.Cclose()
                    macros.write_logging_parameters(logfile)
    except Exception,err:
        import traceback
        msg = "An error occurred at " + macros.specdate()
        msg += " in file " + __file__ + "\\n\\n"
        msg += str(traceback.format_exc())
        macros.SendTextEmail(userlist, msg, '1-ID Beamline specpy Abort')
        print 'Error=',err
        print str(traceback.format_exc())
        

    
