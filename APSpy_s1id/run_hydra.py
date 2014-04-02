# take care of imports, assuming this script is run directly from python
import sys,os.path
if '~/specpy/1ID' not in sys.path:
    sys.path.append(os.path.expanduser('~/specpy/1ID'))
if '~/specpy/src' not in sys.path:
    sys.path.append(os.path.expanduser('~/specpy/src'))
import mtrsetup
import spec
import AD

# pull in the procedure and override parameters in the procedure
import hydra_proc as hy
hy.userlist = ('toby@anl.gov',)
#hy.userlist += ('s-stock@northwestern.edu', 'leemreize@hotmail.com')
hy.det = (AD.ScintX,AD.GE1)
hy.logfile = 'mytest1.par'
hy.motor1 = spec.samY
hy.motor2 = spec.phi
hy.motor3 = spec.samX3

hy.setup_logging()
hy.collect()
#            motor3        motor2             motor1
#hy.collect(X0, DX, NX,  PHI0, DPHI, NPHI,  Y0, DY, NY,   Count, frames, filename)
#hy.collect(1, .1, 2,      0., .01,  4,       2, .1, 3,     2, 1, 'test1')


