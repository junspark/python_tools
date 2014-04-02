#!/usr/bin/env python

import re,string,os,sys
import Numeric
import Image
import scipy

sys.path.append("/home/oxygen/AMICELI/python/GEaSi")

import read_tiff


file1 = sys.argv[1]
file2 = sys.argv[2]

diff_filename = file1 + "_subtracted.tiff"

img1 = read_tiff.read_tiff(file1)
img1_data = img1.load_image()
img1_data = Numeric.array(img1_data)

img2 = read_tiff.read_tiff(file2)
img2_data = img2.load_image()
img2_data = Numeric.array(img2_data)


image_diff = img1_data - img2_data
image_diff2d = Numeric.reshape(image_diff,(img1.size_y,img1.size_x))


#I --> (32-bit signed integer pixels) Is this deep enough
out_im = Image.new('I', (img1.size_x,img1.size_y))

for x in range(img1.size_x):
    for y in range(img1.size_y):
        out_im.putpixel((x,y),image_diff2d[y][x])
        

print diff_filename
out_im.save(diff_filename,'TIFF')

