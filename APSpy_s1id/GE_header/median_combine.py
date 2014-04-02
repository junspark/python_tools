#!/usr/bin/env python

# Median combines images in GE sequence file. The GE header is stripped and median file is
# saved as a TIFF file (mode = I (32-bit signed integer pixels)). 

import re,string,os,sys
import numarray.image
import Image

sys.path.append("/home/oxygen/AMICELI/python/GEaSi")

import read_GEaSi_data

if len(sys.argv)<2:
    print "USAGE:  median_combine.py <GE_sequence_file> "
    sys.exit()

file = sys.argv[1]
print file

tiff_out_file = file + '_median.tiff'

img_list = []

# Calculate the mean image
image_seq = read_GEaSi_data.read_GEaSi_data(file)

for i in range(image_seq.NumberOfFrames):
    i = i + 1
    img_list.append(numarray.array(image_seq.load_image_from_seq(i)))
    print i

image_seq.close()

print img_list[0][0]
print img_list[1][0]

print img_list[0][1]
print img_list[1][1]

print img_list[0][2]
print img_list[1][2]

print len(img_list)


print "Now median combining..."
median_img = numarray.image.median(img_list,outtype=numarray.Int32)

print len(median_img)

print "reshaping..."

median_img = numarray.reshape(median_img,(image_seq.NumberOfRowsInFrame,image_seq.NumberOfColsInFrame))

print len(median_img)

out_im = Image.new('I', (image_seq.NumberOfRowsInFrame,image_seq.NumberOfColsInFrame)) 

for x in range(image_seq.NumberOfRowsInFrame):
    for y in range(image_seq.NumberOfColsInFrame):
        out_im.putpixel((x,y),median_img[y][x])

out_im.save(tiff_out_file,'TIFF')

print tiff_out_file
im = Image.open(tiff_out_file)
print im.mode

