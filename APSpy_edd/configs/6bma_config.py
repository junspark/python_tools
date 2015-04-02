### alldone = PyEpics.PV('1edd:alldone') ### IS THERE SOMETHING EQUIVALENT?

### SCALARS
scaler_name = '6bma2:scaler1'
spec.DefineScaler(scaler_name,3)

### MOTORS
# spec.DefineMtr('VPtop', '1edd:m3', 'VPtop (mm)')    ## COLOR CODED
# spec.DefineMtr('VPbot', '1edd:m4', 'VPbot (mm)')    ## COLOR CODED
# spec.DefineMtr('VPob',  '1edd:m5', 'VPob (mm)')    ## COLOR CODED
# spec.DefineMtr('VPib',  '1edd:m6', 'VPib (mm)')    ## COLOR CODED
# spec.DefineMtr('VPth',  '1edd:m16', 'VPtheta (deg)')        ## ELCO CABLE 1
# spec.DefineMtr('HPtop', '1edd:m8', 'HPtop (mm)')        ## PRINTER CABLE 14
# spec.DefineMtr('HPbot', '1edd:m7', 'HPbot (mm)')        ## PRINTER CABLE 17
# spec.DefineMtr('HPob',  '1edd:m2', 'HPob (mm)')        ## PRINTER CABLE 15
# spec.DefineMtr('HPib',  '1edd:m1', 'HPib (mm)')        ## PRINTER CABLE 16
# spec.DefineMtr('HPth',  '1edd:m9', 'HPtheta (deg)')     ## ELCO CABLE 7
# spec.DefineMtr('samX',  '1edd:m11', 'samX (mm)')        ## ELCO CABLE 3
# spec.DefineMtr('samY',  '1idc:m72', 'samY (mm)')        ## MOVOACT FROM C HUTCH ==> CHECK WHICH MOTOR IS ACTUALLY MOVING
# spec.DefineMtr('samY2',  '1edd:m14', 'samY2 (mm)')        ## ELCO CABLE 6
# spec.DefineMtr('samZ',  '1edd:m10', 'samZ (mm)')        ## ELCO CABLE 2

### BEAMLINE SPECIFIC PV NAMES
epoch_time_pv ='6bma1:GTIM_TIME'
shutter_state = PyEpics.PV('PA:06BM:STA_A_FES_OPEN_PL.VAL')
# shutter_control = PyEpics.PV('1bma:rShtrA:Open.PROC')

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




