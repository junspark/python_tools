#!/usr/bin/env python


'''Test of spec module used by an interactive session'''


########### SVN repository information ###################
# $Date: 2013-04-24 18:41:03 -0500 (Wed, 24 Apr 2013) $
# $Author: jemian $
# $Revision: 1281 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/branches/1id_afrl/src/testing/test_spec_session.py $
# $Id: test_spec_session.py 1281 2013-04-24 23:41:03Z jemian $
########### SVN repository information ###################


from APSpy.spec import *
import epics as PyEpics
import logging
from pprint import pprint


def wait_motors():
    '''this is useful but specific to the development IOC'''
    while not alldone.get():
        sleep(1)

alldone = PyEpics.PV('como:alldone')


EnableEPICS()
DefineMtr('samX', 'como:m1',  'sample X position (mm) + outboard')
DefineMtr('samZ', 'como:m2',  'sample Z position (mm) + up')
DefineMtr('phi',  'como:m3',  'sample rotation (deg)')
DefineMtr('j1',   'como:m4',  'sample table N jack')
DefineMtr('j2',   'como:m5',  'sample table SE jack')
DefineMtr('j3',   'como:m6',  'sample table SW jack')

m = motors.get_keys_enum()
print 'samX', m.samX, wm(m.samX)
print 'phi',  m.phi,  wm(m.phi)
print 'phi',  m.phi,  wm('phi')
try:
    # this should fail since 'phi' is not a 
    # known symbol in our namespace
    print 'phi',  m.phi,  wm(phi)
except NameError, s:
    print s
exec( DefineMotorSymbols(mtrDB) )
print 'phi',  m.phi,  wm(phi)
print
wa()
print '\n again \n'
wa(True)

print "j2 motor's dictionary:"
pprint(GetMtrInfo( m.j2 ))

DefinePseudoMtr({
    # define pseudo motor position
    'jack': '(A[j1] + A[j2] + A[j3])/3.',
    # define motor movements in terms of pseudo motor target position
    'j1': 'A[j1] + T[jack] - A[jack]',
    'j2': 'A[j2] + T[jack] - A[jack]',
    'j3': 'A[j3] + T[jack] - ((A[j1] + A[j2] + A[j3])/3)',
    },'composite motion including j1,j2 & j3')
DefinePseudoMtr({
    # define pseudo motor positions
    'samLX': 'cosd(A[phi])*A[samX] + sind(A[phi])*A[samZ]',
    'samLZ': '-sind(A[phi])*A[samX] + cosd(A[phi])*A[samZ]',
    # define motor movements in terms of pseudo motor target position
    'samX' : 'cosd(A[phi])*T[samLX] - sind(A[phi]) * T[samLZ]',
    'samZ' : 'sind(A[phi])*T[samLX] + cosd(A[phi]) * T[samLZ]',
    },'sample displacement in diffractometer axes')

wa(True)

mmv([(m.samX,0),(m.samZ,0),(m.phi,0),(m.j1,0),(m.j2,0),(m.j3,0)])
wait_motors()

print "moving samX to 2.0";    umv( m.samX,   2.)
print "moving samZ to 0.5";    umv( m.samZ,   0.5)
wait_motors()
print "moving samX by -1.0";   umvr(m.samX,  -1.)
print "moving j1   to 2.05";   umv( m.j1,     2.05)
print "moving j2   to 2.11";   umv( m.j2,     2.11)
print "moving j3   to 2.2";    umv( m.j3,     2.2)
print "moving phi  to 30.0";   umv( m.phi,    30.0)
wait_motors()
wa(True)



print 'done'

