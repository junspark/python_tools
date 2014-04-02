'''
**GE Image processing module**

*Module GE: GE Image processing*
================================

This is a module for reading files and quick processing of data from the GE angiography detector
in use at sector 1. It requires the NumPy package. It does not require the PyEpics package. 
Most functions in this module work directly with data files created by the GE detectors,
with the exceptions of :func:`PlotGEimage` and :func:`PlotROIsums`, which plot images and
ROI values, respectively, from other functions in this module. 

*Summary*
----------

======================  ===========================================================
Routines		Description
======================  ===========================================================
:func:`Count_Frames`    Determine the number of frames in a GE image file
:func:`getGEimage`      Read a single entire GE image file
:func:`getGE_ROI`       Read a section (region of interest) of a GE image file
:func:`PlotGEimage`     Plot an image or ROI  
:func:`sumGE_ROIs`      Report the average intensity for ROIs in a GE image frame
:func:`sumAllGE_ROIs`   Reports the average intensity for ROIs for all frames in a file
:func:`PlotROIsums`     Plots the ROIs values from :func:`sumAllGE_ROIs`   
======================  ===========================================================


*Complete Function Descriptions*
-----------------------------------

The functions available in this module are listed below.

'''


########### SVN repository information ###################
# $Date: 2013-09-04 15:17:08 -0500 (Wed, 04 Sep 2013) $
# $Author: parkjs $
# $Revision: 1433 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/branches/1id_afrl/src/APSpy/GE.py $
# $Id: GE.py 1433 2013-09-04 20:17:08Z parkjs $
########### SVN repository information ###################


import numpy
import os

# Globals
HEADER = 8192 # bytes to skip in GE header
IMGSIZE = 2048 # assume we are always reading full-density images

def Count_Frames(filename):
    '''Determine the number of frames in a GE file by looking at the file size.

    :param str filename: The filename containing the as-recorded GE images
    :returns: the number of frames (int).
    
    Example:

    >>> ifil = '/Users/toby/software/work/1ID/data/AZ91_01306.ge2'
    >>> GE.Count_Frames(ifil)
    220

    '''
    return int((os.stat(filename).st_size-HEADER)/(2.*IMGSIZE*IMGSIZE))

def getGEimage(filename,frame):
    '''Read a single entire GE image from a file
    
    :param str filename: The filename containing as-recorded GE images
    :param int frame: the image number on the file, counted starting at 1
      An exception is raised if frame is greater than the number of frames in the file.

    :returns: An image as a 2048x2048 numpy array of intensities

    Example:

    >>> ifil = '/Users/toby/software/work/1ID/data/AZ91_01306.ge2'
    >>> GE.getGEimage(ifil,2)
    array([[1699, 1713, 1713, ..., 1701, 1697, 1695],
       [1708, 1717, 1717, ..., 1708, 1703, 1705],
       [1715, 1719, 1719, ..., 1708, 1707, 1707],
       ..., 
       [1714, 1720, 1714, ..., 1698, 1702, 1697],
       [1714, 1718, 1716, ..., 1702, 1703, 1702],
       [1701, 1704, 1697, ..., 1684, 1685, 1687]], dtype=uint16)

    '''    
    if frame > Count_Frames(filename):
        raise Exception("Frame number "+str(frame)+" is out of range for file "+filename)
    fp = open(filename,'rb')
    fp.seek(HEADER + (frame-1) * 2 * IMGSIZE**2) # 2 bytes * # pixels
    img = numpy.fromfile(fp,dtype=numpy.uint16,count=IMGSIZE*IMGSIZE).reshape(IMGSIZE,IMGSIZE)
    fp.close()
    return img

def getGE_ROI(filename,frame,region):
    '''Read a section (region of interest) of a GE image from a file. This is usually
    faster than reading an entire image.
    
    :param str filename: The filename containing as-recorded GE images
    :param int frame: the image number on the file, counted starting at 1
    :param list region: describes the region to be extracted

      ===========  ======  ================================
       element #   label   description
      ===========  ======  ================================
         0          xmid   x value for central pixel   
         1          ymid   y value for central pixel   
         2          xwid   half-width of ROI in pixels
         3          ywid   half-width of ROI in pixels
      ===========  ======  ================================
      
      The extracted ROI will be pixels img[ymid-ywid:ymid+ywid,xmid-xwid:xmid+xwid]
      where img is the full image.
      
    :returns: An image as a (2*ywid)x(2*xwid) numpy memmap (behaves like an array) of intensities

    Example:

    >>> ifil = '/Users/toby/software/work/1ID/data/AZ91_01306.ge2'
    >>> GE.getGE_ROI(ifil,2,(100,200,4,6))
    memmap([[1755, 1762, 1763, 1761, 1766, 1762, 1761, 1756],
       [1761, 1763, 1760, 1764, 1765, 1769, 1755, 1758],
       [1762, 1762, 1763, 1758, 1769, 1769, 1757, 1756],
       [1760, 1767, 1764, 1763, 1763, 1765, 1762, 1756],
       [1760, 1764, 1760, 1763, 1763, 1762, 1758, 1758],
       [1761, 1760, 1766, 1762, 1761, 1767, 1761, 1761],
       [1754, 1761, 1765, 1754, 1760, 1768, 1760, 1759],
       [1763, 1764, 1764, 1763, 1766, 1762, 1765, 1761],
       [1760, 1757, 1761, 1765, 1766, 1766, 1761, 1759],
       [1761, 1761, 1761, 1761, 1761, 1763, 1757, 1758],
       [1757, 1765, 1760, 1767, 1764, 1768, 1758, 1760],
       [1762, 1765, 1764, 1760, 1764, 1766, 1761, 1761]], dtype=uint16)

    '''
    xmid,ymid,xwid,ywid = region
    return numpy.memmap(filename,
                     dtype=numpy.uint16,
                     offset=HEADER + (frame-1) * 2 * IMGSIZE**2, 
                     shape=(IMGSIZE,IMGSIZE)
                     )[ymid-ywid:ymid+ywid,xmid-xwid:xmid+xwid]

def _PylabPlotGEimage(img,imin,imax,region=None):
    '''Plots a an image using pylab. Primarily for code development and testing.
    '''
    import pylab as pl
    pl.figure().clear()
    if region is None:
        extent = 0,img.shape[0],img.shape[1],0,
    else:
        xmid,ymid,xwid,ywid = region
        extent = xmid-xwid,xmid+xwid,ymid+ywid,ymid-ywid,
    pl.imshow(img,cmap=pl.cm.spectral,vmin=imin,vmax=imax,interpolation="nearest",
              extent=extent)
    pl.colorbar()
    pl.show()

class _ImagePlot(object):
    '''An object to hold info about image plots
    '''
    def __init__(self,image,page,region=None):
        import matplotlib as mpl
        if region is None:
            self.extent = 0,image.shape[0],image.shape[1],0,
        else:
            xmid,ymid,xwid,ywid = region
            self.extent = xmid-xwid,xmid+xwid,ymid+ywid,ymid-ywid,
        self.image = image
        self.colormap = mpl.cm.spectral
        self.imin = self.image.min()
        self.imax = self.image.max()
        self.page = page
    def plot(self):
        import plotnotebook
        import matplotlib as mpl
        self.page.figure.clear()
        self.page.figure.subplots_adjust(left=0.15, bottom=0.15)
        self.imgplt = self.page.figure.gca().imshow(
            self.image,cmap=self.colormap,vmin=self.imin,vmax=self.imax,
            interpolation="nearest",
            extent=self.extent)
        self.page.figure.colorbar(self.imgplt)
        axcolor = 'lightgoldenrodyellow'
        axmin = self.page.figure.add_axes([0.08, 0.02, 0.6, 0.03], axisbg=axcolor)
        axmax  = self.page.figure.add_axes([0.08, 0.07, 0.6, 0.03], axisbg=axcolor)
        self.smin = mpl.widgets.Slider(axmin, 'Min', 0, self.image.max(), valinit=self.imin)
        self.smax = mpl.widgets.Slider(axmax, 'Max', 0, self.image.max(), valinit=self.imax)
        self.smin.on_changed(self.sliderupdate)
        self.smax.on_changed(self.sliderupdate)
        self.page.figure.canvas.draw()
        plotnotebook.UpdatePlots()
    def sliderupdate(self,val):
        if self.smin.val == self.smax.val:
            return
        elif self.smin.val >= self.smax.val: 
            self.imgplt.set_clim([self.smax.val,self.smin.val])
            self.imin,self.imax = [self.smax.val,self.smin.val]
        else:
            self.imgplt.set_clim([self.smin.val,self.smax.val])
            self.imin,self.imax = [self.smin.val,self.smax.val]
        self.page.figure.canvas.draw()
       
def PlotGEimage(img,title,tablbl,plotlist,region=None,size=(700,700),imgwin=None):
    '''Create a plot of an image in tabbed window

    :param array img: An image, as a numpy array or matplotlib compatible object. Usually
      this will be created by :func:`getGEimage` or :func:`getGE_ROI`.
    :param str title: A string with a title for the window
    :param str tablbl: A string with the title for the new tab (should be short)
    :param list plotlist: A list of _ImagePlot objects. As new plots are created in this routine
      they are added to this list. The list is used to assign color maps. 
    :param list region: A list for four numbers which describes the ROI
      location for use in adding offsets for the plot axes labeling. The numbers are:

      ===========  ======  ================================
       element #   label   description
      ===========  ======  ================================
         0          xmid   x value for central pixel   
         1          ymid   y value for central pixel   
         2          xwid   half-width of ROI in pixels
         3          ywid   half-width of ROI in pixels
      ===========  ======  ================================
      
      The default is to label the pixels starting from zero.
      
    :param list size: A list, tuple or wx.size object with the size of the window
      to be created in pixels. The default is (700,700)
    :param object imgwin: A plotnotebook object that has been created using
      :func:`plotnotebook.MakePlotWindow`, usually in a prior call to :func:`PlotGEimage`. A
      value of None (default) causes a new frame (window) to be created.
    :returns: A reference to the plot window (a plotnotebook object), which will be either imgwin or
      the new one created in :func:`plotnotebook.MakePlotWindow`.

    Examples:

    >>> import plotnotebook
    >>> import GE
    >>> plotlist = []
    >>> ifil = '/Users/toby/software/work/1ID/data/AZ91_01306.ge2'
    >>> img = GE.getGEimage(ifil,2)
    >>> imgwin = GE.PlotGEimage(img,'image window','full image',plotlist)
    >>> plotnotebook.ShowPlots()

    >>> import plotnotebook
    >>> import GE
    >>> plotlist = []
    >>> ifil = '/Users/toby/software/work/1ID/data/AZ91_01306.ge2'
    >>> ROI = GE.getGE_ROI(ifil,2,(100,200,5,7))
    >>> imgwin = GE.PlotGEimage(ROI ,'','ROI',plotlist, (100,200,4,6))
    >>> plotnotebook.ShowPlots()
     
    '''
    import plotnotebook
    import wx
    import matplotlib as mpl
    colorList = sorted([m for m in mpl.cm.datad.keys() if not m.endswith("_r")],key=str.lower)
    def OnNewColorBar(event):
        for img in plotlist:
            try:
                img.colormap = mpl.cm.get_cmap(colorList[event.GetSelection()])
                img.plot()
            except:
                pass
    def makeCBsel(page):
        colSel = wx.ComboBox(parent=page,value='spectral',choices=colorList,
            style=wx.CB_READONLY|wx.CB_DROPDOWN)
        colSel.Bind(wx.EVT_COMBOBOX, OnNewColorBar)
        page.topsizer.Add((-1,1), 1, wx.RIGHT, 1)
        page.topsizer.Add(
            wx.StaticText(parent=page,label=' Color bar '), 0, wx.RIGHT, 0)
        page.topsizer.Add(colSel, 0, wx.RIGHT, 0)

    # make a plotting window, if not already created
    try:
        imgwin.Parent.SetTitle(title)
    except:
        imgwin = plotnotebook.MakePlotWindow(size=size, DisableDelete=False)
        imgwin.Parent.SetTitle(title)
        makeCBsel(imgwin)
        imgwin.frame.Show(True)
    # add a new tab to the window
    page = imgwin.AddPlotTab(tablbl) # add a tab and add it to the list
    imgwin.RaisePlotTab(tablbl) # show new tab
    # create the image plot object and save it
    imgplt = _ImagePlot(img,page,region)
    plotlist.append(imgplt)
    imgplt.plot()
    page.canvas.draw()
    plotnotebook.UpdatePlots()
    # return the name of the window
    return imgwin


class ROI_rect:
    '''Defines the rectangle of a region of interest (ROI) by midpoint and width
    
      Each ROI region consists of 4 elements:
      
      ===========  ======  ================================
       element #   label   description
      ===========  ======  ================================
         0          xmid   x value for central pixel   
         1          ymid   y value for central pixel   
         2          xwid   half-width of ROI in pixels
         3          ywid   half-width of ROI in pixels
      ===========  ======  ================================
    '''
    
    def __init__(self, xmid, ymid, xwid, ywid):
        self.xmid = xmid
        self.ymid = ymid
        self.xwid = xwid
        self.ywid = ywid
    
    def get_bounds(self):
        '''return the boundaries (start and end) of an ROI'''
        ystart = self.ymid-self.ywid
        yend = self.ymid+self.ywid
        xstart = self.xmid-self.xwid
        xend = self.xmid+self.xwid
        return ystart, yend, xstart, xend
    

def sumGE_ROIs(filename,frame,regionlist):
    '''Reads a frame from a raw GE image file and returns a list of the average intensity for
    each ROI specified in the regionlist.

    :param str filename: The filename containing as-recorded GE images
    :param int frame: the image number on the file, counted starting at 1
    :param [ROI_rect] regionlist: A list of ROI_rect objects

    :returns: a list of N average intensity values, one for each ROI region in
      regionlist.

    Example:

    >>> ifil = '/Users/toby/software/work/1ID/data/AZ91_01306.ge2'
    >>> regionlist = [ROI_rect(1335,1525,50,50),ROI_rect(1435,1525,50,50),]
    >>> GE.sumGE_ROIs(ifil,2,regionlist)
    [1792.6894, 1780.4342]
    
    '''
    ROIsumList = []
    for roi in regionlist:
        ystart, yend, xstart, xend = roi.get_bounds()
        ROI = numpy.memmap(filename,
                        dtype=numpy.uint16,
                        offset=HEADER + (frame-1) * 2 * IMGSIZE**2, 
                        shape=(IMGSIZE,IMGSIZE)
                        )[ystart:yend, xstart:xend]
        ROIsumList.append(float(ROI.sum(dtype=float))/ROI.size)
    return ROIsumList

def sumGE_ROIs_wrapper(args):
    '''Provides an interface to :func:`sumGE_ROIs` that allows it to be called with a
    single argument. This is needed for use with the multiprocessing module and :func:`sumAllGE_ROIs`
    
    :param tuple args: A tuple or list containing a filename, frame, and regionlist,
      as defined in :func:`sumGE_ROIs`.

    :returns: a list of N average intensity values, one for each ROI region in
      regionlist.

    '''
    return sumGE_ROIs(*args)

def sumAllGE_ROIs(filename,regionlist,processes=1):
    '''Computes the average intensity for each ROI specified in the regionlist for every
    frame in a raw GE image file.
    
    :param str filename: The filename containing as-recorded GE images
    :param [ROI_rect] regionlist: A list of ROI_rect objects
      
    :param int processes: specifies the number of simultaneous processes that can be used to
      perform ROI integration using the Python `multiprocessing` module. The default, 1, will not
      use this module and all computations are done in the current thread. Values >1 can show significant
      gains in speed on multicore/multicpu computers. 
      
    :returns: a list of MxN array of average intensity values, where M is the number of frames and
      N is the number of ROI region(s) in regionlist.
      
    Examples:

    >>> ifil = '/Users/toby/software/work/1ID/data/AZ91_01306.ge2'
    >>> GE.sumAllGE_ROIs(ifil, [(100,200,4,6), (1335,1525,50,50)])
    array([[ 1794.57291667,  1801.2036    ],
       [ 1761.80208333,  1792.6894    ],
       [ 1760.5       ,  1791.7353    ],
       [ 1760.36458333,  1791.4961    ],
       [ 1760.03125   ,  1791.6162    ],
       ...
       [ 1760.0625    ,  1779.0867    ],
       [ 1759.72916667,  1779.1182    ],
       [ 1759.5       ,  1779.2508    ]])

    In the example above, two ROIs are integrated for all frames in a file in the
    current Python interpreter.
    
    >>> import GE
    >>> import numpy as numpy
    >>> import time
    >>> imgfile = '/tmp/AZ91_01306'
    >>> regionlist = [ROI_rect(1335,1525,50,50),ROI_rect(1435,1525,50,50),
    ...    ROI_rect(335,1525,50,50),ROI_rect(1935,1525,50,50)]
    >>> nframe = GE.Count_Frames(imgfile)
    >>> l = {}
    >>> for proc in range(10):
    ...    st = time.time()
    ...    l[proc] = GE.sumAllGE_ROIs(imgfile,regionlist, proc)
    ...    print 'sec per frame, processors=',proc,(time.time()-st)/float(nframe)
    ...    assert(numpy.allclose(l[0],l[proc]))

    The example above integrates 4 ROIs and compares running with all computations
    in the current Python thread (processes=0 and 1) 
    with running with up to 9 concurrent processes. Usually one sees a speed-up with ~1.5 times
    the actual number of cores for multiprocessing. The assert is used to confirm the computation
    returns the same results independent of the number of processes.

    '''
    
    nframes = Count_Frames(filename)
    #reslts = npzeros
    if processes <= 1:
        return numpy.array([sumGE_ROIs(filename,frame,regionlist) for frame in range(1,nframes+1)])
    import multiprocessing
    arglist = [(filename,frame,regionlist) for frame in range(1,nframes+1)]
    mpPool = multiprocessing.Pool(processes)
    return numpy.array(mpPool.map(sumGE_ROIs_wrapper,arglist))

def PlotROIsums(datarray, tablbl='ROIs', title='', captions=None, size=(700,700), imgwin=None):
    '''Plots a series of ROIs

    :param array datarray: a list of MxN array of average intensity values,
      as returned by :func:`sumAllGE_ROIs`,
      where M is the number of frames and N is the number of ROI region(s).
    :param str tablbl: A string with the title for the new tab. (Should be short; default is "ROIs".)
    :param str title: A string with a title for the window. Defaults to blank.
    :param list captions: A list of N strings, where each string specifies a legend caption
      for each of the N ROI regions. (Default is "ROI #".)
    :param list size: A list, tuple or wx.size object with the size of the window
      to be created in pixels. The default is (700,700)
    :param object imgwin: A plotnotebook object that has been created using
      :func:`plotnotebook.MakePlotWindow`, usually in a prior call to :func:`PlotGEimage`. A
      value of None (default) causes a new frame (window) to be created.
    :returns: A reference to the plot window (a plotnotebook object), which will be either imgwin or
      the new one created in :func:`plotnotebook.MakePlotWindow`.
      
    Example:
    
    >>> regionlist = [ROI_rect(1335,1525,50,50),ROI_rect(1435,1525,50,50),
    ...               ROI_rect(335,1525,50,50),ROI_rect(1935,1525,50,50)]
    >>> caps = [str(i[0])+','+str(i[1]) for i in regionlist]
    >>> ROIarr = GE.sumAllGE_ROIs(imgfile,regionlist)
    >>> GE.PlotROIsums(ROIarr, captions=caps)
    >>> import plotnotebook
    >>> plotnotebook.ShowPlots()

    '''
    import plotnotebook
    # make a plotting window, if not already created
    global page
    try:
        imgwin.Parent.SetTitle(title)
        page = imgwin.ReusePlotTab(tablbl)
        page.figure.clear()
        imgwin.RaisePlotTab(tablbl)
    except:
        imgwin = plotnotebook.MakePlotWindow(size=size, DisableDelete=False)
        imgwin.Parent.SetTitle(title)
        page = imgwin.AddPlotTab(tablbl)
        imgwin.RaisePlotTab(tablbl)
        imgwin.frame.Show(True)
    page.figure.gca().set_xlabel('Frame number')
    page.figure.gca().set_ylabel('Average pixel intensity')
    for i in range(datarray.shape[1]):
        try:
            lbl = str(captions[i])
        except:
            lbl = 'ROI '+str(i+1)
        page.figure.gca().plot(range(1,datarray.shape[0]+1),
                               datarray[:,i],
                               label=lbl)
    if datarray.shape[1] > 1 and page.figure.gca().get_legend() is None:
        page.figure.gca().legend()
    page.figure.canvas.draw()

    # return the name of the window
    return imgwin

def _test1(imgfile,frame):
    plotlist = []
    img = getGEimage(imgfile,frame)
    title = 'image plot'
    imgwin = PlotGEimage(img,title,'full image',plotlist)
    regionlist = [ROI_rect(1335,1525,50,50),ROI_rect(1435,1525,50,50)]
    for region in regionlist:
        img = getGE_ROI(imgfile,frame,region)
        PlotGEimage(img, 'multiple images','subregion',plotlist,region,imgwin=imgwin)

def _test2(imgfile,frame):
    regionlist = [ROI_rect(1335,1525,50,50),ROI_rect(1435,1525,50,50),
                  ROI_rect(335,1525,50,50),ROI_rect(1935,1525,50,50)]
    print sumGE_ROIs(imgfile,frame,regionlist)
    return sumAllGE_ROIs(imgfile,regionlist)

def _test3(imgfile,frame):
    regionlist = [ROI_rect(1335,1525,50,50),ROI_rect(1435,1525,50,50),
                  ROI_rect(335,1525,50,50),ROI_rect(1935,1525,50,50)]
    print len(regionlist),' ROIs per frame'
    nframe = Count_Frames(imgfile)
    l = {}
    for proc in range(10):
        st = time.time()
        l[proc] = sumAllGE_ROIs(imgfile,regionlist, proc)
        print 'sec per frame, processors=',proc,(time.time()-st)/float(nframe)
        assert(numpy.allclose(l[0],l[proc]))
    return l[0]

def _test4(imgfile,frame):
    regionlist = [ROI_rect(1335,1525,50,50),ROI_rect(1435,1525,50,50),
                  ROI_rect(335,1525,50,50),ROI_rect(1935,1525,50,50)]
    caps = [str(i[0])+','+str(i[1]) for i in regionlist]
    PlotROIsums(sumAllGE_ROIs(imgfile,regionlist),
                'ROIs',
                captions=caps)

if __name__ == "__main__":
    import time
    frame = 2
    import os.path
    fl = '~/software/work/1ID/data/AZ91_01306.ge2'
    rfl = os.path.expanduser(fl)
    #rfl = "/home/beams/S1IDUSER/mnt/HEDM/Beaudoin_June12/GE1/AZ91_01306"
    _test1(rfl,frame)
    _test2(rfl,frame)
    _test3(rfl,frame)
    _test4(rfl,frame)
    import plotnotebook
    plotnotebook.ShowPlots()
