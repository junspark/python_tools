def WriteParFile():
    return
#def write_parfile(detname,imgnr,imgprefix,motname,startpos,endpos) '{
#	#takes: detector name, img number, img prefix
#	#       motor name, startpos, endpos 
#	#detname = "$1"
#	#imgnr = $2
#	#imgprefix=$3
#	#motname = $4
#	#startpos = $5
#	#endpos = $6
#
#	get_angles
#
#	#read out intensity loggin to readable names
#	
#	#print to the par file.
#       
#	on(parfile);offt
#
#	# CMU Nov 2008
#	p date(),detname,A[samXb],A[samYb],A[samZb],motname,startpos,endpos,OSC["exposure_time"],img#prefix,imgnr,S[ic7b],S[ic1b]
#	ont;off(parfile)
#     
#	 
#
#}'

## CHECK THIS - THERE ARE TWO sweep_header DEFINED
def SweepHeader():
    return
#def sweep_header '{
#    if(IS_SWEEPSCAN) {
#       local x[]
#       printf("#C osi_N speed shutter_open shutter_close scaler1  scaler2  det\n")
#       printf("#C osi_V %g %g %g %g %g %s\n",OSC["speed"],OSC["shutteropen_delay"],OSC["shutterclose_delay"],OSC["scaler1"],OSC["scaler2"],OSC["detector"])
#       printf("#C SWP_N imgprefix ic1g ic1u ic2g ic2u hrmg hrmu jjuh jjuv jjdi jjdo jjdt jjdb HRdetY\n")
#       x[0] = OSC["imgprefix"]
#       x[1]= epics_get("1idc:A1sens_num.VAL") 
#       x[2]= epics_get("1idc:A1sens_unit.VAL")
#       x[3]= epics_get("1idc:A2sens_num.VAL") 
#       x[4]= epics_get("1idc:A2sens_unit.VAL") 
#       x[5]= epics_get("1id:A5sens_num.VAL")	 
#       x[6]= epics_get("1id:A5sens_unit.VAL")
#	#Upstreem slit setting
#	x[7]=epics_get("1idc:m62.RBV")
#	x[8]=epics_get("1idc:m64.RBV")
#	
#	#downstreem slit setting
#	x[9] =epics_get("1idc:m44.RBV")
#	x[10]=epics_get("1idc:m43.RBV")
#	x[11]=epics_get("1idc:m41.RBV")
#	x[12]=epics_get("1idc:m42.RBV")

#	#high res detector vertical pos
#	x[13]=epics_get("1idc:m45.RBV")
#        printf("#C SWP_V %s %g %g %g %g %g %g %g %g %g %g %g %g %g\n",x[0],x[1],x[2],x[3],x[4],x[5],x[6],x[7],x[8],x[9],x[10],x[11],x[12],x[13])
#   }      
#}'

##Redefine Header in .spe datafile. Different to omega and phi sweep
#def sweep_header '{
#    if(IS_SWEEPSCAN) {
#       local x[]
#        
#          printf("#C OSC_N speed shutter_open shutter_close  det\n")
#          printf("#C OSC_V %g %g %g %s\n",OSC["speed"],OSC["shutteropen_delay"],OSC["shutterclose_delay"],OSC["detector"])
#          printf("#C SWP_N imgprefix ic7g ic7u ic8g ic8u jjbot jjtop jjin jjout \n")
#          x[0] = OSC["imgprefix"]
#          x[1]= epics_get("1id:A7sens_num.VAL") 
#          x[2]= epics_get("1id:A7sens_unit.VAL")
#          x[3]= epics_get("1id:A8sens_num.VAL") 
#          x[4]= epics_get("1id:A8sens_unit.VAL") 
#         
#	   #Slits
#    	   x[5]=epics_get("1idb:m21.RBV")
#  	   x[6]=epics_get("1idb:m22.RBV")
#	   x[7] =epics_get("1idb:m23.RBV")
#	   x[8]=epics_get("1idb:m24.RBV")
#           printf("#C SWP_V %s %g %g %g %g %g %g %g %g\n",x[0],x[1],x[2],x[3],x[4],x[5],x[6],x[7],x[8])
#           
#   }      
##}'

## CHECK THIS - THERE ARE TWO sweep_fprnt_label DEFINED
def SweepFprintLabel():
    return
#def sweep_fprnt_label '{
#    FPRNT=sprintf("start  end  imgn  samY_enc  ome_enc  tension  load  strain1  ")
#    PPRNT=sprintf("%9.9s %9.9s %9.9s %9.9s %9.9s %9.9s %9.9s %9.9s ","start","end","imgn","samY_enc","ome_enc","tension","load","strain1")
#    VPRNT=PPRNT 
#    _cols+=8;
#}'

#def sweep_fprnt_label '{
#    
#    FPRNT=sprintf("start  end  imgn  ")
#    PPRNT=sprintf("%9.9s %9.9s %9.9s ","start","end","imgn")
#    VPRNT=PPRNT 
#    _cols+=3;
#    
#}'

## CHECK THIS - THERE ARE TWO sweep_fprnt_label DEFINED
def SweepFprintValue():
 return
#def sweep_fprnt_value '{
#    local imgn samY_enc ome_enc tension load strain1
#    if(OSC["detector"] == "bruker") {
#          imgn=(++BRUKERFILE["index"])
#    } else {
#          imgn = (detget_seqNumber-1);
#    }
#    samY_enc = epics_get("1id:AD4enc1:count")
#    ome_enc = epics_get("1id:Fed:s1:probe_5")
#    tension =  epics_get("1idc:m33.RBV")
#    load =  epics_get("1id:D1Ch2_raw.VAL")
#    strain1 = epics_get("1id:D1Ch4_raw.VAL")

#    FPRNT = sprintf("%.8g %.8g %.8g %.8g %.8g %.8g %.8g %.8g ",_start,_stop,imgn,samY_enc,ome_enc,tension,load,strain1);
#    PPRNT = sprintf("%9.4f %9.4f %.8g %9.4f %9.4f %9.4f %9.4f %9.4f ",_start,_stop,imgn,samY_enc,ome_enc,tension,load,strain1);
#    VPRNT=PPRNT
#    if(SOFTIOC_USE ) {
#      local t
#      if(MATLAB_OK) {
#        while(epics_get(sprintf("%sBusy",SOFTIOC_PV),"short")==1) {
#          if(t>20) {
#          printf("\nWaited too long, forced to unlock with matlab.\n")
#          epics_put(sprintf("%sBusy",SOFTIOC_PV),0)
#          MATLAB_OK = 0
#          break;
#          }
#          sleep(0.5)
#          t++
#        }
#      }
#      
#      epics_put(sprintf("%simgn",SOFTIOC_PV),imgn)
#      if(epics_get(sprintf("%sscantype",SOFTIOC_PV)) == "supersweep") {
#         epics_put(sprintf("%sstart",SOFTIOC_PV),$1)
#         epics_put(sprintf("%send",SOFTIOC_PV),$1)
#      } else {
#         epics_put(sprintf("%sstart",SOFTIOC_PV),_start)
#         epics_put(sprintf("%send",SOFTIOC_PV),_stop) # replaced _end
#      }   
#      epics_put(sprintf("%sNPTS",SOFTIOC_PV),NPTS+1)
#      epics_put(sprintf("%sBusy",SOFTIOC_PV),1)
#      
#    }  
#    write_parfile(OSC["detector"], imgn, OSC["imgprefix"],  OSC["motor"], _start, _stop )
#}'
