### alldone = PyEpics.PV('1edd:alldone') ### IS THERE SOMETHING EQUIVALENT?
alldone = PyEpics.PV('1edd:alldone')

### SCALARS - NEED TO CHECK THESE
scaler_name = '6bma2:scaler1'
spec.DefineScaler(scaler_name,3)

## MOTORS
spec.DefineMtr('sl1r', '6bma1:m1', 'sl1r (mm)')
spec.DefineMtr('sl1l', '6bma1:m2', 'sl1l (mm)')
spec.DefineMtr('sl1t', '6bma1:m3', 'sl1t (mm)')
spec.DefineMtr('sl1b', '6bma1:m4', 'sl1b (mm)')
spec.DefineMtr('sl2r', '6bma1:m5', 'sl2r (mm)')
spec.DefineMtr('sl2l', '6bma1:m6', 'sl2l (mm)')
spec.DefineMtr('sl2t', '6bma1:m7', 'sl2t (mm)')
spec.DefineMtr('sl2b', '6bma1:m8', 'sl2b (mm)')
spec.DefineMtr('sl3r', '6bma1:m9', 'sl3r (mm)')
spec.DefineMtr('sl3l', '6bma1:m10', 'sl3l (mm)')
spec.DefineMtr('sl3t', '6bma1:m11', 'sl3t (mm)')
spec.DefineMtr('sl3b', '6bma1:m12', 'sl3b (mm)')
spec.DefineMtr('sl4r', '6bma1:m13', 'sl4r (mm)')
spec.DefineMtr('sl4l', '6bma1:m14', 'sl4l (mm)')
spec.DefineMtr('sl4t', '6bma1:m15', 'sl4t (mm)')
spec.DefineMtr('sl4b', '6bma1:m16', 'sl4b (mm)')
spec.DefineMtr('xr', '6bma1:m17', 'xr (mm)')
spec.DefineMtr('yr', '6bma1:m18', 'yr (mm)')
spec.DefineMtr('zr', '6bma1:m19', 'zr (mm)')
spec.DefineMtr('ytth', '6bma1:m20', 'ytth (deg)')
spec.DefineMtr('rotx', '6bma1:m21', 'rotx (deg)')
spec.DefineMtr('rotz', '6bma1:m22', 'rotz (deg)')

### BEAMLINE SPECIFIC PV NAMES
epoch_time_pv ='6bma1:GTIM_TIME'
shutter_state = PyEpics.PV('PA:06BM:STA_A_FES_OPEN_PL.VAL')

### PV HOLDING DUMMY VARIABLES FOR METADATA PADDING
dummy_num_pv = '6bma2:userStringCalc10.H';
dummy_str_pv = '6bma2:userStringCalc10.HH'
dummy_h1_num_pv = '6bma2:userStringCalc10.I';
dummy_h1_str_pv = '6bma2:userStringCalc10.II';
dummy_v1_num_pv = '6bma2:userStringCalc10.J';
dummy_v1_str_pv = '6bma2:userStringCalc10.JJ';
dummy_h2_num_pv = '6bma2:userStringCalc10.K';
dummy_h2_str_pv = '6bma2:userStringCalc10.KK';
dummy_v2_num_pv = '6bma2:userStringCalc10.L';
dummy_v2_str_pv = '6bma2:userStringCalc10.LL';

### DETECTOR PREFIXES
# horz_prefix = 'dp_vortex_xrd76:mca1'
# vert_prefix = 'dp_vortex_xrd73:mca1'

## DATA FILE NAMES / NUMBERS ARE STORED INTO THE FOLLOWING PV
## AS THE DATA ARE COLLECTED
h_det_fname_pv = '6bma2:userStringCalc10.AA';
h_det_fnum_pv = '6bma2:userStringCalc10.A';

v_det_fname_pv = '6bma2:userStringCalc10.BB';
v_det_fnum_pv = '6bma2:userStringCalc10.B';

iter_number_pv = '6bma2:userCalc10.A';
pos_number_pv = '6bma2:userCalc10.B';
fid_number_pv = '6bma2:userCalc10.C';

### PREAMP PV
# ic0_preamp_sens_pv = '1edd:A3sens_num.VAL';
# ic0_preamp_unit_pv = '1edd:A3sens_unit.VAL';
ic0_preamp_sens_nA_pv = '6bma2:userCalc10.D';

# ic1_preamp_sens_pv = '1edd:A2sens_num.VAL';
# ic1_preamp_unit_pv = '1edd:A2sens_unit.VAL';
ic1_preamp_sens_nA_pv = '6bma2:userCalc10.E';
