# -*- coding: utf-8 -*-
'''
*Module G2img_1ID_32bit_TIFsum.py: 1ID summed 32bit Dexela TIF for rapid access measurement*
--------------------------------------------------
Originally written by Connor Horn 2018 using G2img_1TIF.py revision 3323
Updates by Jun-Sang Park
'''

from __future__ import division, print_function
import struct as st
import GSASIIobj as G2obj
import GSASIIpath
import GSASIIfiles as G2fil
import numpy as np
import time
DEBUG = False
GSASIIpath.SetVersionNumber("$Revision: 1 $")
class TIF_ReaderClass(G2obj.ImportImage):
    '''Reads TIF files using a routine (:func:`GetTifData`) that looks
    for files that can be identified from known instruments and will
    correct for slightly incorrect TIF usage. If that routine fails,
    it will be read with a standard TIF reader, which can handle compression
    and other things less commonly used at beamlines. 
    '''
    def __init__(self):
        super(self.__class__,self).__init__( # fancy way to self-reference
            extensionlist=('.sum.tif','.sum.tiff','.ave.tif','.ave.tiff'),
            strictExtension=True,
            # formatName = '1ID summed 32bit Dexela TIF',
            formatName = '1ID summed 16bit Dexela TIF',
            # longFormatName = '1ID summed 32bit Dexela TIF for rapid access measurement'
            longFormatName = '1ID summed 16bit Dexela TIF for rapid access measurement'
            )
        self.scriptable = True

    def ContentsValidator(self, filename):
        '''Does the header match the required TIF header?
        '''
        fp = open(filename,'rb')
        tag = fp.read(2)
        if 'bytes' in str(type(tag)):
            tag = tag.decode('latin-1')
        if tag == 'II' and int(st.unpack('<h',fp.read(2))[0]) == 42: #little endian
            pass
        elif tag == 'MM' and int(st.unpack('>h',fp.read(2))[0]) == 42: #big endian
            pass
        else:
            return False # header not found; not valid TIF
            fp.close()
        fp.close()
        return True
    
    def Reader(self,filename, ParentFrame=None, **unused):
        '''Read the TIF file using :func:`GetTifData`. If that fails,
        use :func:`scipy.misc.imread` and give the user a chance to
        edit the likely wrong default image parameters. 
        '''
        self.Comments,self.Data,self.Npix,self.Image = GetTifData(filename)
        if self.Npix == 0:
            G2fil.G2Print("GetTifData failed to read "+str(filename)+" Trying PIL")
            import PIL.Image as PI
            self.Image = PI.open(filename,mode='r')
            self.Npix = self.Image.size
            if ParentFrame:
                self.SciPy = True
                self.Comments = ['no metadata']
                self.Data = {'wavelength': 0.172973, 'pixelSize': [74.8, 74.8], 'distance': 500.0}
                
                self.Data['size'] = list(self.Image.size)
                self.Data['center'] = [int(i/2) for i in self.Image.size]
        if self.Npix == 0:
            return False
        self.LoadImage(ParentFrame,filename)
        return True

def GetTifData(filename):
    '''Confirm that the file is in fact a 16bit tiff image with the correct
    parameters. Will nearly always throw an error unless used with the 1ID
    GSASII workflow, which assigns the proper tags and converts the Dexela
    tiff images into the 16bit format with a different buffer in order to hold
    the larger amount of data in each pixel.
    '''
    
    import struct as st
    # import array as ar
    # import ReadMarCCDFrame as rmf
    image = None
    File = open(filename,'rb')
    dataType = 5
    center = [None,None]
    wavelength = None
    distance = None
    polarization = None
    try:
        Meta = open(filename+'.metadata','Ur')
        head = Meta.readlines()
        for line in head:
            line = line.strip()
            try:
                if '=' not in line: continue
                keyword = line.split('=')[0].strip()
                if 'dataType' == keyword:
                    dataType = int(line.split('=')[1])
                elif 'wavelength' == keyword.lower():
                    wavelength = float(line.split('=')[1])
                elif 'distance' == keyword.lower():
                    distance = float(line.split('=')[1])
                elif 'polarization' == keyword.lower():
                    polarization = float(line.split('=')[1])
            except:
                G2fil.G2Print('error reading metadata: '+line)
        Meta.close()
    except IOError:
        G2fil.G2Print ('no metadata file found - will try to read file anyway')
        head = ['no metadata file found',]
        
    tag = File.read(2);
    if 'bytes' in str(type(tag)):
        tag = tag.decode('latin-1')
    byteOrd = '<'
    if tag == 'II' and int(st.unpack('<h',File.read(2))[0]) == 42:     #little endian
        IFD = int(st.unpack(byteOrd+'i',File.read(4))[0])
    elif tag == 'MM' and int(st.unpack('>h',File.read(2))[0]) == 42:   #big endian
        byteOrd = '>'
        IFD = int(st.unpack(byteOrd+'i',File.read(4))[0])        
    else:
        # print (tag)
        lines = ['not a detector tiff file',]
        return lines,0,0,0
    File.seek(IFD)                                                  #get number of directory entries
    NED = int(st.unpack(byteOrd+'h',File.read(2))[0])
    IFD = {}
    nSlice = 1
    if DEBUG: print('byteorder:',byteOrd)
    for ied in range(NED):
        Tag,Type = st.unpack(byteOrd+'Hh',File.read(4))
        nVal = st.unpack(byteOrd+'i',File.read(4))[0]
        if DEBUG: print ('Try:',Tag,Type,nVal)
        if Type == 1:
            Value = st.unpack(byteOrd+nVal*'b',File.read(nVal))
        elif Type == 2:
            Value = st.unpack(byteOrd+'i',File.read(4))
        elif Type == 3:
            Value = st.unpack(byteOrd+nVal*'h',File.read(nVal*2))
            st.unpack(byteOrd+nVal*'h',File.read(nVal*2))
        elif Type == 4:
            if Tag in [273,279]:
                nSlice = nVal
                nVal = 1
            Value = st.unpack(byteOrd+nVal*'i',File.read(nVal*4))
        elif Type == 5:
            Value = st.unpack(byteOrd+nVal*'i',File.read(nVal*4))
        elif Type == 11:
            Value = st.unpack(byteOrd+nVal*'f',File.read(nVal*4))
        IFD[Tag] = [Type,nVal,Value]
        if DEBUG: print (Tag,IFD[Tag])
    sizexy = [IFD[256][2][0],IFD[257][2][0]]
    [nx,ny] = sizexy
    Npix = nx*ny
    time0 = time.time()


    print(IFD) #prints the tiff tags, good for making sure the format is good
    '''This is the code that was changed from the original GSASII tiff reading
    script, only populates the image variable if certain parameters are met
    '''
    # if IFD[258][2][0] == 32:                                                #summed files are 32 bit to hold the required amount of data
    if IFD[258][2][0] == 16:                                                #summed files are 32 bit to hold the required amount of data
        print(sizexy)
        if sizexy == [3888, 3072] or sizexy == [3072, 3888]:                  #confirms that it has the proper size
            # tifType = '1ID summed 32bit Dexela'
            tifType = '1ID summed 16bit Dexela'
            pixy = [74.8,74.8]                                                      #sets the pixel size
            # print ('Read 1ID summed 32bit Dexela tiff file: '+filename)
            print ('Read 1ID summed 16bit Dexela tiff file: '+filename)
            # File.seek(134)                                                  #using image.save() with python PIL to save these summed files creates a buffer of 134
            File.seek(0)
            # image = np.array(np.frombuffer(File.read(4*Npix),dtype=np.int32),dtype=np.int32) #trial and error showed that this formula properly reads the image, see G2img_1TIF.py
            image = np.array(np.frombuffer(File.read(2*Npix),dtype=np.int16),dtype=np.int16) #trial and error showed that this formula properly reads the image, see G2img_1TIF.py
    if image is None:
        print('Image is improperly formatted in some way, confirm that this tiff file is being uses properly with the 1ID workflow.')
        lines = ['Image is improperly formatted in some way.',]
        return lines,0,0,0
        
    if sizexy[1]*sizexy[0] != image.size: # test is resize is allowed
        print(image.size)
        print('Image size is not consistent with the expected 3888 by 3072')
        lines = ['Unexpected image size, not 3888 by 3072',]
        return lines,0,0,0
    print ('image read time: %.3f'%(time.time()-time0))
    image = np.reshape(image,(sizexy[1],sizexy[0]))
    center = (not center[0]) and [pixy[0]*sizexy[0]/2000,pixy[1]*sizexy[1]/2000] or center
    wavelength = (not wavelength) and 0.10 or wavelength
    distance = (not distance) and 100.0 or distance
    polarization = (not polarization) and 0.99 or polarization
    data = {'pixelSize':pixy,'wavelength':wavelength,'distance':distance,'center':center,'size':sizexy,
            'setdist':distance,'PolaVal':[polarization,False]}
    File.close()
    return head,data,Npix,image
