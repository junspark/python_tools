#!/usr/bin/python
def NreadGE(filename, frameno):
    # NreadGE - read GE file from fastsweep image stack
    #
    #   INPUT:
    #
    #   filename
    #       name of the GE image stack file name
    #
    #   frameno
    #       frame to load
    #
    #   OUTPUT:
    #
    #   imdata
    #       image data in a [2048 x 2048] matrix
    #
    #   NOTE:
    #   1. if the image size changes, this file needs to be updated.
    #   2. if the buffer contains useful information, this file needs to read
    #   it in.
    import sys
    import os
    import numpy
    
    GE_buffer = 8192
    num_X = 2048
    num_Y = 2048
    with open(filename, mode='rb') as fileobj:
        statinfo = os.stat(filename)
        nFrames = (statinfo.st_size - GE_buffer) / (2 * num_X * num_Y)
        if frameno > nFrames:
            print '\nthere are only ' + str(nFrames) + ' frames in ' + filename + '\n'
            sys.exit()
        else:
            offset = GE_buffer + (frameno - 1) * num_X * num_Y * 2
            fileobj.seek(offset)
            imdata = numpy.fromfile(fileobj, numpy.uint16, num_X * num_Y).astype('uint16')
    fileobj.close()
    
    return imdata

def NwriteGE(filename, imdata):
    # NwriteGE - write GE image stack file
    #
    #   INPUT:
    #
    #   filename
    #       name of the GE image stack file name
    #
    #   imdata
    #       image data to write
    #
    #   OUTPUT:
    #
    #   none
    #
    import sys
    import os
    import numpy
    
    GE_buffer = 8192
    
    fileobj = open(filename, mode='wb')
    fileobj.seek(GE_buffer)
    numpy.uint16(imdata).tofile(fileobj)
    fileobj.close()