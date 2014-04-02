#!/usr/bin/env python

import re,string,os,sys,Numeric,struct,scipy,mmap
from math import *

import Image

class read_tiff:
    def __init__(self,image_filename):
        self.image_filename = image_filename
        try:
            self.image = Image.open(self.image_filename)
            (self.size_x, self.size_y) = self.image.size
            self.mode = self.image.mode
            # print self.mode
        except IOError, (errno, strerror):
            print "I/O error(%s): %s" % (errno, strerror)
            print "Error in opening file: ", self.image_filename
            raise

    def load_image(self):
        # Return a Numeric array with the data.....
        image_tmp = self.image.getdata()
        image_tmp = Numeric.array(image_tmp)
        return(image_tmp)
        

if __name__ == '__main__':


    if len(sys.argv)<2:
        print "USAGE: read_tiff.py <GEaSi_tiff_single_image>"
        sys.exit()
        
        
    image_file = sys.argv[1]
    print image_file
    image1 = read_tiff(image_file)    
    data1 = image1.load_image()

    #im = Image.open(image_file)
    #pix = im.load()
    #print pix[0,0]
    #sys.exit()
    
    data1 = [float(x) for x in data1]

    print image1.size_x, image1.size_y, image1.mode
    print len(data1), data1[0], data1[1], data1[2]

    
    #try:
    #    im = Image.open(infile)
    #    print infile, im.format, "%d x %d"%im.size, im.mode
    #except IOError:
    #    pass
    #print im.read(1)
    
    
    print "Median = ",
    print scipy.median(data1)
    print "Mean = ",
    print scipy.mean(data1)
    print "Std = ",
    print scipy.std(data1)
    print "\n"

