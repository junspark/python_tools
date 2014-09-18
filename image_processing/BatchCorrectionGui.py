#import tkFileDialog
#dirname = tkFileDialog.askdirectory(initialdir="/", title='Please select a directory')
## test
#print dirname


import os
import wx
import wx.lib.agw.multidirdialog as MDD
 
wildcard = "Python source (*.py)|*.py|" \
            "All files (*.*)|*.*"
 
########################################################################
class MyForm(wx.Frame):
 
    #----------------------------------------------------------------------
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY,
                          "File and Folder Dialogs Tutorial")
        panel = wx.Panel(self, wx.ID_ANY)
        self.currentDirectory = os.getcwd()
 
        # create the buttons and bindings
#        openFileDlgBtn = wx.Button(panel, label="Show OPEN FileDialog")
#        openFileDlgBtn.Bind(wx.EVT_BUTTON, self.onOpenFile)
 
#        saveFileDlgBtn = wx.Button(panel, label="Show SAVE FileDialog")
#        saveFileDlgBtn.Bind(wx.EVT_BUTTON, self.onSaveFile)
 
        dirDlgBtn = wx.Button(panel, label="Show DirDialog")
        dirDlgBtn.Bind(wx.EVT_BUTTON, self.onDir)
 
#        multiDirDlgBtn = wx.Button(panel, label="Show MultiDirDialog")
#        multiDirDlgBtn.Bind(wx.EVT_BUTTON, self.onMultiDir)
 
        # put the buttons in a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
#        sizer.Add(openFileDlgBtn, 0, wx.ALL|wx.CENTER, 5)
#        sizer.Add(saveFileDlgBtn, 0, wx.ALL|wx.CENTER, 5)
        sizer.Add(dirDlgBtn, 0, wx.ALL|wx.CENTER, 5)
#        sizer.Add(multiDirDlgBtn, 0, wx.ALL|wx.CENTER, 5)
        panel.SetSizer(sizer)
 
    #----------------------------------------------------------------------
    def onDir(self, event):
        """
        Show the DirDialog and print the user's choice to stdout
        """
        dlg = wx.DirDialog(self, "Choose a directory:",
                           style=wx.DD_DEFAULT_STYLE
                           #| wx.DD_DIR_MUST_EXIST
                           #| wx.DD_CHANGE_DIR
                           )
        if dlg.ShowModal() == wx.ID_OK:
            print "You chose %s" % dlg.GetPath()
            DataDir = dlg.GetPath()
        dlg.Destroy()

        return DataDir
 
    #----------------------------------------------------------------------
#    def onMultiDir(self, event):
#        """
#        Create and show the MultiDirDialog
#        """
#        dlg = MDD.MultiDirDialog(self, title="Choose a directory:",
#                                 defaultPath=self.currentDirectory,
#                                 agwStyle=0)
#        if dlg.ShowModal() == wx.ID_OK:
#            paths = dlg.GetPaths()
#            print "You chose the following file(s):"
#            for path in paths:
#                print path
#        dlg.Destroy()
 
    #----------------------------------------------------------------------
#    def onOpenFile(self, event):
#        """
#        Create and show the Open FileDialog
#        """
#        dlg = wx.FileDialog(
#            self, message="Choose a file",
#            defaultDir=self.currentDirectory, 
#            defaultFile="",
#            wildcard=wildcard,
#            style=wx.OPEN | wx.MULTIPLE | wx.CHANGE_DIR
#            )
#        if dlg.ShowModal() == wx.ID_OK:
#            paths = dlg.GetPaths()
#            print "You chose the following file(s):"
#            for path in paths:
#                print path
#        dlg.Destroy()
 
    #----------------------------------------------------------------------
#    def onSaveFile(self, event):
#        """
#        Create and show the Save FileDialog
#        """
#        dlg = wx.FileDialog(
#            self, message="Save file as ...", 
#            defaultDir=self.currentDirectory, 
#            defaultFile="", wildcard=wildcard, style=wx.SAVE
#            )
#        if dlg.ShowModal() == wx.ID_OK:
#            path = dlg.GetPath()
#            print "You chose the following filename: %s" % path
#        dlg.Destroy()
 
#----------------------------------------------------------------------
# Run the program
if __name__ == "__main__":
    app = wx.App(False)
    frame = MyForm()
    frame.Show()
    app.MainLoop()
