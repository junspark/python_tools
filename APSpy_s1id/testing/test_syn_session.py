#!/usr/bin/env python


'''Test of spec module used by an interactive session'''


########### SVN repository information ###################
# $Date: 2013-04-24 18:41:03 -0500 (Wed, 24 Apr 2013) $
# $Author: jemian $
# $Revision: 1281 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/branches/1id_afrl/src/testing/test_syn_session.py $
# $Id: test_syn_session.py 1281 2013-04-24 23:41:03Z jemian $
########### SVN repository information ###################


from APSpy.spec import *
import epics as PyEpics
import logging
from pprint import pprint


def wait_motors():
    '''this is useful but specific to the development IOC'''
    while not alldone.get():
        sleep(1)
	print 'keep waiting?', alldone.get() != 1

alldone = PyEpics.PV('syn:alldone')


EnableEPICS()
DefineMtr('samX', 'syn:m1',  'sample X position (mm) + outboard')
DefineMtr('samZ', 'syn:m2',  'sample Z position (mm) + up')
DefineMtr('phi',  'syn:m3',  'sample rotation (deg)')
DefineMtr('j1',   'syn:m4',  'sample table N jack')
DefineMtr('j2',   'syn:m5',  'sample table SE jack')
DefineMtr('j3',   'syn:m6',  'sample table SW jack')

exec( DefineMotorSymbols(mtrDB) )

print 'samX', samX, wm(samX)
print 'phi',  phi,  wm(phi)
print 'phi',  phi,  wm('phi')
print
wa()
print '\n again \n'
wa(True)

print "j2 motor's dictionary:"
pprint(GetMtrInfo( j2 ))

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


exec( DefineMotorSymbols(mtrDB) )
wa(True)

mmv([(samX,0),(samZ,0),(phi,0),(j1,0),(j2,0),(j3,0)])
wait_motors()

print "moving samX to 2.0";    umv( samX,   2.0)
print "moving samZ to 0.5";    umv( samZ,   0.5)
wait_motors()
print "moving samX by -1.0";   umvr(samX,  -1.0)
print "moving j1   to 2.05";   umv( j1,     2.05)
print "moving j2   to 2.11";   umv( j2,     2.11)
print "moving j3   to 2.2";    umv( j3,     2.2)
print "moving phi  to 30.0";   umv( phi,    30.0)
wait_motors()
wa(True)

print "moving motors to default locations"
mmv([(samX,1.1),(samZ,-1.2),(phi,1.3),(j1,-1.4),(j2,1.5),(j3,-1.6)])
wait_motors()

print 'done'

