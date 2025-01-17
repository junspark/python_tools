#!/usr/bin/env python


'''Test of spec module used by another module'''


########### SVN repository information ###################
# $Date: 2013-04-24 18:41:03 -0500 (Wed, 24 Apr 2013) $
# $Author: jemian $
# $Revision: 1281 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/branches/1id_afrl/src/testing/test_spec_macro.py $
# $Id: test_spec_macro.py 1281 2013-04-24 23:41:03Z jemian $
########### SVN repository information ###################


import APSpy.spec
import epics as PyEpics
import logging
from pprint import pprint


MOTOR_CONFIGURATION = '''
  samX   como:m1     sample X position (mm) + outboard
  samZ   como:m2     sample Z position (mm) + up
  phi    como:m3     sample rotation (deg)
  j1     como:m4     sample table N jack
  j2     como:m5     sample table SE jack
  j3     como:m6     sample table SW jack
'''

alldone = PyEpics.PV('como:alldone')

def wait_motors():
    while not alldone.get():
        APSpy.spec.sleep(1)
    logging.info("keep waiting for motor(s) to stop? " + str(alldone.get() != 1) )

def ImportMotorSymbols():
    exec( APSpy.spec.DefineMotorSymbols(APSpy.spec.mtrDB, make_global=True) )


def print_title(title):
    logging.info( 70*'=' )
    logging.info( title )
    logging.info( 70*'=' )


def setup():
    """exercise the definition routines"""
    print_title('setup')
    logging.info("*** define the motors we will use")
    #APSpy.spec.DEBUG = True
     
    # test applies when using development IOC *only*
    motors = MOTOR_CONFIGURATION.strip().splitlines()
    for row in motors:
        items = row.split()
        mne  = items[0]
        pv   = items[1]
        desc = ' '.join(items[2:])
        item = APSpy.spec.DefineMtr(mne, pv, desc)
        #print item, mne, pv, APSpy.spec.mtrDB[item], mne in APSpy.spec.mtrDB, mne in APSpy.spec.__dict__
     
    APSpy.spec.DefinePseudoMtr({
        # define pseudo motor position
        'jack': '(A[j1] + A[j2] + A[j3])/3.',
        # define motor movements in terms of pseudo motor target position
        'j1': 'A[j1] + T[jack] - A[jack]',
        'j2': 'A[j2] + T[jack] - A[jack]',
        'j3': 'A[j3] + T[jack] - ((A[j1] + A[j2] + A[j3])/3)',
        },'composite motion for j1,j2 & j3')
    APSpy.spec.DefinePseudoMtr({
        # define pseudo motor positions
        'samLX': 'cosd(A[phi])*A[samX] + sind(A[phi])*A[samZ]',
        'samLZ': '-sind(A[phi])*A[samX] + cosd(A[phi])*A[samZ]',
        # define motor movements in terms of pseudo motor target position
        'samX' : 'cosd(A[phi])*T[samLX] - sind(A[phi]) * T[samLZ]',
        'samZ' : 'sind(A[phi])*T[samLX] + cosd(A[phi]) * T[samLZ]',
        },' sample displacement in difractometer axes')
    
    ImportMotorSymbols()

    logging.info('*** ListMtrs()')
    logging.info(APSpy.spec.ListMtrs())

    import rst_table
    t = rst_table.Table()
    for mne in APSpy.spec.ListMtrs():
        logging.info('*** GetMtrInfo(%s)' % mne)
        info = APSpy.spec.GetMtrInfo(APSpy.spec.Sym2MtrVal(mne))
        if len(t.labels) == 0:
            t.labels = info.keys()
        t.rows.append([str(info[item]).strip() for item in t.labels])
    print t.reST(add_tabularcolumns=False)


def test_motors():
    """exercise some motor movement routines"""
    print_title('test_motors')
    
    logging.info("move all motors to 0")
    for mne in APSpy.spec.ListMtrs():
        mtr = APSpy.spec.Sym2MtrVal(mne)
        APSpy.spec.mv(mtr, 0.0)
    wait_motors()
    
    logging.info("*** perform some moves")
    logging.info("moving samX to 2.0");    APSpy.spec.umv( samX,   2.)
    logging.info("moving samZ to 0.5");    APSpy.spec.umv( samZ,   0.5)
    wait_motors()
    logging.info("moving samX by -1.0");   APSpy.spec.umvr(samX,  -1.)
    logging.info("moving j1   to 2.05");   APSpy.spec.umv( j1,     2.05)
    logging.info("moving j2   to 2.11");   APSpy.spec.umv( j2,     2.11)
    logging.info("moving j3   to 2.2");    APSpy.spec.umv( j3,     2.2)
    logging.info("moving phi  to 30.0");   APSpy.spec.umv( phi,    30.0)
    
    logging.info('Before move of jack')
    for mtr in 'j1','j2','j3','jack':
        print('  ', mtr, APSpy.spec.ReadMtr(APSpy.spec.Sym2MtrVal(mtr)))
    APSpy.spec.umv(jack,3.12)
    wait_motors()
    logging.info('After move of jack')
    for mtr in 'j1','j2','j3','jack':
        print '  ', mtr, APSpy.spec.ReadMtr(APSpy.spec.Sym2MtrVal(mtr))

    logging.info('\n\nX,Z = ' + str(APSpy.spec.wm(samX))) 
    logging.info(APSpy.spec.wm(samZ)) 
    print 'sq', APSpy.spec.wm(samX)**2 + APSpy.spec.wm(samZ)**2
    for ang in (0, 30, 45, 90, 180, 270, -30):
        APSpy.spec.mv(phi, ang)
        wait_motors()
    logging.info('ang, LX,LZ = ' + str(ang)) 
    logging.info( str(APSpy.spec.wm(samLX)) + '  ' + str(APSpy.spec.wm(samLZ)) )
    logging.info('sq ' + str((APSpy.spec.wm(samLX) **2 + APSpy.spec.wm(samLZ)**2)) )
    APSpy.spec.sleep(1)

    logging.info('*** move jack, samLX & samLZ together')
    APSpy.spec.mmv([
              [jack,  0], 
              [samLX, 0], 
              [samLZ, 0]],)
    
    logging.info('*** move back in samLX & samLZ together in 5 steps')
    APSpy.spec.MoveMultipleMtr([
                          [samLX, 0.616025403784], 
                          [samLZ, 0.933012701892]], 
                         5)
    
    logging.info("move all motors back to 0")
    wait_motors()
    # refer to motor names in spec module namespace
    APSpy.spec.mmv([
              [samX, 0], 
              [samZ, 0],
              [phi,  0],
              [j1,   0],
              [j2,   0],
              [j3,   0],
              ],)
    wait_motors()


def show_motors():
    """exercise motor introspection routines"""
    print_title('show_motors')

    logging.info('*** ExplainMtr() by string') 
    for mne in APSpy.spec.ListMtrs():
        mtr = APSpy.spec.Sym2MtrVal(mne)
        logging.info( '\t'.join([mne,  str(APSpy.spec.wm(mtr)),  APSpy.spec.ExplainMtr(mtr)]) )
    logging.info('*** ExplainMtr() by reference') 
    logging.info(str(samX)+'\t' + APSpy.spec.ExplainMtr(samX))
    logging.info('*** wm(samX,samZ):')
    logging.info(APSpy.spec.wm(samX, samZ))
    logging.info('*** wa()')
    APSpy.spec.wa()
    logging.info('*** wa() long form')
    APSpy.spec.wa(True)


def test_scalers():
    """exercise scaler routines"""
    print_title('test_scalers')
    APSpy.spec.DefineScaler('ioc:scaler1', 16)
    APSpy.spec.DefineScaler('ioc:scaler2', 8, index=1)
    logging.info("Count on default scaler, default count time")
    print APSpy.spec.ct()
    print "Count on scaler 1, count time=2.5"
    print APSpy.spec.ct(2.5, index=1)
    print "Start async count on scaler 1, count time=5 sec"
    APSpy.spec.count_em(5, index=1)
    print "read immediately"
    print APSpy.spec.get_counts()
    sleep(1)
    print "after a second"
    print APSpy.spec.get_counts()
    APSpy.spec.wait_count()
    logging.info("after a  wait_count()")
    logging.info(APSpy.spec.get_counts())


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s',
                        level=logging.INFO)
    APSpy.spec.EnableEPICS()
    setup()
    
    test_motors()
    show_motors()
    #test_scalers()
    logging.info("wait for all motors to complete their moves")
    wait_motors()
    print_title("all tests complete")
