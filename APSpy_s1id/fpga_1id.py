import epics as ep

def SignalsInput_1id():             # _signals_input_1id
    '''
    _signals_input_1id
    '''
    ep.caput('1id:softGlue:FI1_Signal','Sweep',wait=True)
    ep.caput('1id:softGlue:FI2_Signal','RetExp',wait=True)
    ep.caput('1id:softGlue:FI13_Signal','GE2tot',wait=True)
    ep.caput('1id:softGlue:FI14_Signal','GE2SE',wait=True)
    ep.caput('1id:softGlue:FI12_Signal','UserTTL1',wait=True)
    return
    
def SignalsInput_1ide():            # _signals_input_1ide
    '''
    _signals_input_1ide
    '''
    ep.caput('1ide:sg:FI15_Signal','NFExp',wait=True)
    ep.caput('1ide:sg:FI16_Signal','TomoExp',wait=True)
    return

def SelectTomoDetector():           # TomoDet_select
    '''
    TomoDet_select
    '''
    SignalsInput_1ide()
    ep.caput('1ide:sg:FO24_Signal','TomoExp',wait=True) # RetExp signal to 1id
    return
    
def SelectNFDetector():             # NFDet_select
    '''
    NFDet_select
    '''
    SignalsInput_1ide()
    ep.caput('1ide:sg:FO24_Signal','NFExp',wait=True) # RetExp signal to 1id
    return

def FS_SweepControl():              # FS_Sweep_control
    '''
    FS_Sweep_control
    '''
    SignalsInput_1id()
    ep.caput('1id:softGlue:FO24_Signal','Sweep',wait=True) # to fast shutter
    return

def FS_RetigaControl():             # FS_Retiga_control
    '''
    FS_Retiga_control
    '''
    SignalsInput_1id()
    ep.caput('1id:softGlue:FO24_Signal','RetExp',wait=True) # to fast shutter
    return

def FS_GE2SEControl():              # FS_GE2SE_control
    '''
    FS_GE2SE_control
    '''
    SignalsInput_1id()
    ep.caput('1id:softGlue:FO24_Signal', 'GE2SE', wait=True) # to fast shutter
    ep.caput('1id:softGlue:FO18_Signal', 'GE2SE', wait=True)
    ep.caput('1id:softGlue:FO19_Signal','GE2tot', wait=True)
    return

def FS_GE2TOTControl():             # FS_GE2tot_control
    '''
    FS_GE2tot_control
    '''
    SignalsInput_1id()
    ep.caput('1id:softGlue:FO24_Signal','GE2tot', wait=True) # to fast shutter
    ep.caput('1id:softGlue:FO18_Signal', 'GE2SE', wait=True)
    ep.caput('1id:softGlue:FO19_Signal','GE2tot', wait=True)
    return

def FS_UserTTL1Control():           # FS_UserTTL1_control
    '''
    FS_UserTTL1_control
    '''
    SignalsInput_1id()
    ep.caput('1id:softGlue:FO24_Signal','UserTTL1', wait=True) # to fast shutter
    ep.caput('1id:softGlue:FO23_Signal','UserTTL1', wait=True) # to fast shutter
    return
