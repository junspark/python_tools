
# $Id: getinfo.py 1281 2013-04-24 23:41:03Z jemian $

'''Quick routine to grab motor limits'''
import epics as ep  #from epics import PV
for i in range(1,97):
    ioc = '1idc:m%d' % i
    print ioc,ep.caget(ioc+'.LLM'),ep.caget(ioc+'.HLM')
