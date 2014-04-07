
'''motor support classes'''


########### SVN repository information ###################
# $Date: 2013-04-24 18:41:03 -0500 (Wed, 24 Apr 2013) $
# $Author: jemian $
# $Revision: 1281 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/trunk/src/APSpy/motor.py $
# $Id: motor.py 1281 2013-04-24 23:41:03Z jemian $
########### SVN repository information ###################


# TODO: move these definitions to this module from spec.py
#     class _MTRpos(object):
#     class _MTRtarget(object):
# The challenge is to resolve how mtrDB is identified uniquely


class MotorObject(object):
    '''internal data structure with configuration of an EPICS motor'''
    
    def __init__(self, symbol, mtrpv, info, tolerance):
        self.symbol = symbol         # name of motor symbol
        self.info = info             # info string about motor
        self.mtr_pv = mtrpv          # PV to access motor device
        self.tolerance = tolerance   # tolerance to ignore in motor positioning
        self.simpos = 0              # position used for simulation
    
    def get_dict(self):
        '''Return a dictionary with motor information.'''
        value = dict(symbol    = self.symbol,
                     info      = self.info,
                     PV        = None,
                     tolerance = self.tolerance,
                     dict      = None,
                     )
        if isinstance(self.mtr_pv,dict):
            value['dict'] = self.mtr_pv
        else:
            value['PV'] = self.mtr_pv
        return value
