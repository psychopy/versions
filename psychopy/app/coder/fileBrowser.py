#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Classes and functions for the coder file browser pane."""

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

from __future__ import absolute_import, print_function

import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

try:
    from wx import aui
except Exception:
    import wx.lib.agw.aui as aui  # some versions of phoenix

import os
import time
import collections

# enums for file types
FOLDER_TYPE_NORMAL = 0
FOLDER_TYPE_NAV = 1
FOLDER_TYPE_NO_ACCESS = 2

# IDs for menu events
ID_GOTO_BROWSE = wx.NewId()
ID_GOTO_CWD = wx.NewId()
ID_GOTO_FILE = wx.NewId()


def convertBytes(nbytes):
    """Convert a size in bytes to a string."""
    if nbytes >= 1e9:
        return '{:.1f} GB'.format(nbytes / 1e9)
    elif nbytes >= 1e6:
        return '{:.1f} MB'.format(nbytes / 1e6)
    elif nbytes >= 1e3:
        return '{:.1f} KB'.format(nbytes / 1e3)
    else:
        return '{:.1f} B'.format(nbytes)


FolderItemData = collections.namedtuple(
    'FolderItemData',
    field_names=['name', 'abspath', 'basename'])

FileItemData = collections.namedtuple(
    'FileItemData',
    field_names=['name', 'abspath', 'basename', 'fsize', 'mod'])



class FileBrowserListCtrl(ListCtrlAutoWidthMixin, wx.ListCtrl):
    """Custom list control for the file browser."""

    def __init__(self, parent, id, pos, size, style):
        wx.ListCtrl.__init__(self,
                             parent,
                             id,
                             pos,
                             size,
                             style=style)
        ListCtrlAutoWidthMixin.__init__(self)


class FileBrowserPanel(wx.Panel):
    """Panel for a file browser.
    """
    def __init__(self, parent, frame):
        wx.Panel.__init__(self, parent, -1)
        self.parent = parent
        self.coder = frame
        self.currentPath = None
        self.selectedItem = None
        self.isSubDir = False
        self.pathData = {}

        # get graphics for toolbars and tree items
        rc = self.coder.paths['resources']
        join = os.path.join

        # handles for icon graphics in the image list
        tsize = (16, 16)
        self.fileImgList = wx.ImageList(tsize[0], tsize[1])
        self.gotoParentBmp = self.fileImgList.Add(
            wx.ArtProvider.GetBitmap(
                wx.ART_GO_TO_PARENT, wx.ART_TOOLBAR, tsize))
        self.folderBmp = self.fileImgList.Add(
            wx.ArtProvider.GetBitmap(
                wx.ART_FOLDER, wx.ART_TOOLBAR, tsize))
        self.fileBmp = self.fileImgList.Add(
            wx.ArtProvider.GetBitmap(
                wx.ART_NORMAL_FILE, wx.ART_TOOLBAR, tsize))

        # icons for toolbars
        gotoBmp =  wx.ArtProvider.GetBitmap(
            wx.ART_GO_FORWARD, wx.ART_TOOLBAR, tsize)
        newFolder = wx.ArtProvider.GetBitmap(
            wx.ART_NEW_DIR, wx.ART_TOOLBAR, tsize)
        # copyBmp = wx.ArtProvider.GetBitmap(
        #     wx.ART_COPY, wx.ART_TOOLBAR, tsize)
        deleteBmp = wx.ArtProvider.GetBitmap(
            wx.ART_DELETE, wx.ART_TOOLBAR, tsize)
        renameBmp = wx.Bitmap(join(rc, 'rename16.png'), wx.BITMAP_TYPE_PNG)

        # self.SetDoubleBuffered(True)

        # create the toolbar
        szrToolbar = wx.BoxSizer(wx.HORIZONTAL)

        self.toolBar = wx.aui.AuiToolBar(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
            aui.AUI_TB_HORZ_LAYOUT | aui.AUI_TB_HORZ_TEXT)
        self.toolBar.SetToolBitmapSize((16, 16))
        self.gotoTool = self.toolBar.AddTool(
            wx.ID_ANY,
            'Goto',
            gotoBmp,
            "Jump to another folder",
            wx.ITEM_NORMAL)
        self.toolBar.AddSeparator()
        self.newFolderTool = self.toolBar.AddTool(
            wx.ID_ANY,
            'New Folder',
            newFolder,
            "Create a new folder in the current folder",
            wx.ITEM_NORMAL)
        self.toolBar.AddSeparator()
        self.renameTool = self.toolBar.AddTool(
            wx.ID_ANY,
            'Rename',
            renameBmp,
            "Rename the selected folder or file",
            wx.ITEM_NORMAL)
        # self.copyTool = self.toolBar.AddTool(
        #     wx.ID_ANY,
        #     'Copy',
        #     copyBmp,
        #     "Create a copy of the selected file.",
        #     wx.ITEM_NORMAL)
        self.deleteTool = self.toolBar.AddTool(
            wx.ID_ANY,
            'Delete',
            deleteBmp,
            "Delete the selected folder or file",
            wx.ITEM_NORMAL)

        self.toolBar.SetToolDropDown(self.gotoTool.GetId(), True)
        self.toolBar.Realize()

        self.Bind(wx.EVT_TOOL, self.OnBrowse, self.gotoTool)
        self.Bind(aui.EVT_AUITOOLBAR_TOOL_DROPDOWN, self.OnGotoMenu, self.gotoTool)
        self.Bind(wx.EVT_TOOL, self.OnNewFolderTool, self.newFolderTool)
        self.Bind(wx.EVT_TOOL, self.OnDeleteTool, self.deleteTool)
        # self.Bind(wx.EVT_TOOL, self.OnCopyTool, self.copyTool)
        self.Bind(wx.EVT_TOOL, self.OnRenameTool, self.renameTool)
        self.Bind(wx.EVT_MENU, self.OnBrowse, id=ID_GOTO_BROWSE)
        self.Bind(wx.EVT_MENU, self.OnGotoCWD, id=ID_GOTO_CWD)
        self.Bind(wx.EVT_MENU, self.OnGotoFileLocation, id=ID_GOTO_FILE)

        szrToolbar.Add(self.toolBar, 1, flag=wx.ALL | wx.EXPAND)

        # create an address bar
        self.lblDir = wx.StaticText(self, label="Directory:")
        self.txtAddr = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)

        # create the source tree control
        self.flId = wx.NewIdRef()
        self.fileList = FileBrowserListCtrl(
            self,
            self.flId,
            pos=(0, 0),
            size=wx.Size(300, 300),
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.fileList.SetImageList(self.fileImgList, wx.IMAGE_LIST_SMALL)

        # bind events for list control
        self.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.fileList)
        self.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated, self.fileList)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.OnAddrEnter, self.txtAddr)

        # do layout
        szrAddr = wx.BoxSizer(wx.HORIZONTAL)
        szrAddr.Add(
            self.lblDir, 0, flag=wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, border=5)
        szrAddr.Add(self.txtAddr, 1, flag=wx.ALIGN_CENTRE_VERTICAL)
        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(szrToolbar, 0, flag=wx.EXPAND | wx.ALL)
        szr.Add(szrAddr, 0, flag=wx.EXPAND | wx.ALL, border=5)
        szr.Add(self.fileList, 1, flag=wx.EXPAND)
        self.SetSizer(szr)

        # create the dropdown menu for goto
        self.gotoMenu = wx.Menu()
        item = self.gotoMenu.Append(
            wx.ID_ANY,
            "Browse ...",
            "Browse the file system for a directory to open")
        self.Bind(wx.EVT_MENU, self.OnBrowse, id=item.GetId())
        self.gotoMenu.AppendSeparator()
        item = self.gotoMenu.Append(
            wx.ID_ANY,
            "Current working directory",
            "Open the current working directory")
        self.Bind(wx.EVT_MENU, self.OnGotoCWD, id=item.GetId())
        item = self.gotoMenu.Append(
            wx.ID_ANY,
            "Editor file location",
            "Open the directory the current editor file is located")
        self.Bind(wx.EVT_MENU, self.OnGotoFileLocation, id=item.GetId())
        #self.toolBar.SetDropdownMenu(self.gotoTool.GetId(), self.gotoMenu)

        # add columns
        self.fileList.InsertColumn(0, "Name")
        self.fileList.InsertColumn(1, "Size", wx.LIST_FORMAT_LEFT)
        #self.fileList.InsertColumn(2, "Modified")
        self.fileList.SetColumnWidth(0, 280)
        self.fileList.SetColumnWidth(1, 80)
        #self.fileList.SetColumnWidth(2, 100)

        self.gotoDir(os.getcwd())

    def OnGotoFileLocation(self, evt):
        """Goto the currently opened file location."""
        filename = self.coder.currentDoc.filename
        filedir = os.path.split(filename)[0]
        if os.path.isabs(filedir):
            self.gotoDir(filedir)

            # select the file in the browser
            for idx, item in enumerate(self.dirData):
                if item.abspath == filename:
                    self.fileList.Select(idx, True)
                    self.fileList.EnsureVisible(idx)
                    self.selectedItem = self.dirData[idx]
                    self.fileList.SetFocus()
                    break
        else:
            dlg = wx.MessageDialog(
                self,
                "Cannot change working directory to location of file `{}`. It"
                " needs to be saved first.".format(filename),
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            evt.Skip()

    def OnGotoMenu(self, event):
        mnuGoto = wx.Menu()
        mnuGoto.Append(
            ID_GOTO_BROWSE,
            "Browse ...",
            "Browse the file system for a directory to open")
        mnuGoto.AppendSeparator()
        mnuGoto.Append(
            ID_GOTO_CWD,
            "Current working directory",
            "Open the current working directory")
        mnuGoto.Append(
            ID_GOTO_FILE,
            "Editor file location",
            "Open the directory the current editor file is located")

        self.PopupMenu(mnuGoto)
        mnuGoto.Destroy()

        #event.Skip()

    def OnBrowse(self, event=None):
        dlg = wx.DirDialog(self, "Choose directory ...", "",
                           wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.gotoDir(dlg.GetPath())

        dlg.Destroy()

    def OnNewFolderTool(self, event):
        """When the new folder tool is clicked."""

        # ask for the name of the folder
        dlg = wx.TextEntryDialog(self, 'Enter folder name:', 'New folder', '')

        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Destroy()
            event.Skip()
            return

        folderName = dlg.GetValue()
        if folderName == '':
            dlg = wx.MessageDialog(
                self,
                "Folder name cannot be empty.".format(folderName),
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            event.Skip()
            return

        abspath = os.path.join(self.currentPath, folderName)

        if os.path.isdir(abspath):  # folder exists, warn and exit
            dlg = wx.MessageDialog(
                self,
                "Cannot create folder `{}`, already exists.".format(folderName),
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            event.Skip()
            return

        # try to create the folder
        try:
            os.mkdir(abspath)
        except OSError:
            dlg = wx.MessageDialog(
                self,
                "Cannot create folder `{}`, permission denied.".format(folderName),
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            event.Skip()
            return

        # open the folder we just created
        self.gotoDir(abspath)

    def OnDeleteTool(self, event=None):
        """Activated when the delete tool is pressed."""
        if self.selectedItem is not None:
            if isinstance(self.selectedItem, FolderItemData):
                if self.selectedItem.name == '..':
                    return  # is a sub directory marker

            self.delete()

    def OnRenameTool(self, event):
        """Activated when the rename tool is pressed."""
        if self.selectedItem is not None:
            if isinstance(self.selectedItem, FolderItemData):
                if self.selectedItem.name == '..':
                    return  # is a sub directory marker
            self.rename()

    def OnGotoCWD(self, event):
        """Activated when the goto CWD menu item is clicked."""
        cwdpath = os.getcwd()
        if os.getcwd() != '':
            self.gotoDir(cwdpath)
    #
    # def OnCopyTool(self, event=None):
    #     """Activated when the copy tool is pressed."""
    #     pass  # mdc - will add this in a later version

    def rename(self):
        """Rename a file or directory."""
        if os.path.isdir(self.selectedItem.abspath):  # rename a directory
            dlg = wx.TextEntryDialog(
                self, 'Rename folder `{}` to:'.format(self.selectedItem.name),
                'Rename Folder', self.selectedItem.name)

            if dlg.ShowModal() == wx.ID_OK:
                newName = dlg.GetValue()
                try:
                    os.rename(self.selectedItem.abspath,
                              os.path.join(self.selectedItem.basename, newName))
                except OSError:
                    dlg2 = wx.MessageDialog(
                        self,
                        "Cannot rename `{}` to `{}`.".format(
                            self.selectedItem.name, newName),
                        style=wx.ICON_ERROR | wx.OK)
                    dlg2.ShowModal()
                    dlg2.Destroy()
                    dlg.Destroy()
                    return

                self.gotoDir(self.currentPath)  # refresh

                for idx, item in enumerate(self.dirData):
                    abspath = os.path.join(self.currentPath, newName)
                    if item.abspath == abspath:
                        self.fileList.Select(idx, True)
                        self.fileList.EnsureVisible(idx)
                        self.selectedItem = self.dirData[idx]
                        self.fileList.SetFocus()
                        break

            dlg.Destroy()
        elif os.path.isfile(self.selectedItem.abspath):  # rename a directory
            dlg = wx.TextEntryDialog(
                self, 'Rename file `{}` to:'.format(self.selectedItem.name),
                'Rename file', self.selectedItem.name)

            if dlg.ShowModal() == wx.ID_OK:
                newName = dlg.GetValue()

                try:
                    newPath = os.path.join(self.selectedItem.basename, newName)
                    os.rename(self.selectedItem.abspath,
                              newPath)
                except OSError:
                    dlgError = wx.MessageDialog(
                        self,
                        "Cannot rename `{}` to `{}`.".format(
                            self.selectedItem.name, newName),
                        style=wx.ICON_ERROR | wx.OK)
                    dlgError.ShowModal()
                    dlgError.Destroy()
                    dlg.Destroy()
                    return

                self.gotoDir(self.currentPath)  # refresh

                for idx, item in enumerate(self.dirData):
                    abspath = os.path.join(self.currentPath, newName)
                    if newPath == item.abspath:
                        self.fileList.Select(idx, True)
                        self.fileList.EnsureVisible(idx)
                        self.selectedItem = self.dirData[idx]
                        self.fileList.SetFocus()
                        break

            dlg.Destroy()

    def delete(self):
        """Delete a file or directory."""
        if os.path.isdir(self.selectedItem.abspath):  # delete a directory
            dlg = wx.MessageDialog(
                self, "Are you sure you want to PERMANENTLY delete folder "
                      "`{}`?".format(self.selectedItem.name),
                'Confirm delete', style=wx.YES_NO | wx.NO_DEFAULT |
                                        wx.ICON_WARNING)

            if dlg.ShowModal() == wx.ID_YES:
                try:
                    os.rmdir(self.selectedItem.abspath)
                except FileNotFoundError:  # file was removed
                    dlgError = wx.MessageDialog(
                        self, "Cannot delete folder `{}`, directory does not "
                              "exist.".format(self.selectedItem.name),
                        'Error', style=wx.OK | wx.ICON_ERROR)
                    dlgError.ShowModal()
                    dlgError.Destroy()
                except OSError:  # permission or directory not empty error
                    dlgError = wx.MessageDialog(
                        self, "Cannot delete folder `{}`, directory is not "
                              "empty or permission denied.".format(
                            self.selectedItem.name),
                        'Error', style=wx.OK | wx.ICON_ERROR)
                    dlgError.ShowModal()
                    dlgError.Destroy()

                self.gotoDir(self.currentPath)

            dlg.Destroy()
        elif os.path.isfile(self.selectedItem.abspath):  # delete a file
            dlg = wx.MessageDialog(
                self, "Are you sure you want to PERMANENTLY delete file "
                      "`{}`?".format(self.selectedItem.name),
                'Confirm delete', style=wx.YES_NO | wx.NO_DEFAULT |
                                        wx.ICON_WARNING)

            if dlg.ShowModal() == wx.ID_YES:
                try:
                    os.remove(self.selectedItem.abspath)
                except FileNotFoundError:
                    dlgError = wx.MessageDialog(
                        self, "Cannot delete folder `{}`, file does not "
                              "exist.".format(self.selectedItem.name),
                        'Error', style=wx.OK | wx.ICON_ERROR)
                    dlgError.ShowModal()
                    dlgError.Destroy()
                except OSError:
                    dlgError = wx.MessageDialog(
                        self, "Cannot delete file `{}`, permission "
                              "denied.".format(self.selectedItem.name),
                        'Error', style=wx.OK | wx.ICON_ERROR)
                    dlgError.ShowModal()
                    dlgError.Destroy()

                self.gotoDir(self.currentPath)

            dlg.Destroy()

    def open(self):
        if self.selectedItem is not None:
            self.selectedItem.open()

    def OnAddrEnter(self, evt=None):
        """When enter is pressed."""
        path = self.txtAddr.GetValue()
        if path == self.currentPath:
            return

        if os.path.isdir(path):
            self.gotoDir(path)
        else:
            dlg = wx.MessageDialog(
                self,
                "Specified path `{}` is not a directory.".format(path),
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            self.txtAddr.SetValue(self.currentPath)

    def OnItemActivated(self, evt):
        if self.selectedItem is not None:
            if isinstance(self.selectedItem, FolderItemData):
                self.gotoDir(self.selectedItem.abspath)
            elif isinstance(self.selectedItem, FileItemData):
                self.coder.fileOpen(None, self.selectedItem.abspath)

    def OnItemSelected(self, evt=None):
        itemIdx = self.fileList.GetFirstSelected()
        if itemIdx >= 0:
            self.selectedItem = self.dirData[itemIdx]

    def scanDir(self, path):
        """Scan a directory and update file and folder items."""
        self.dirData = []

        # are we in a sub directory?
        upPath = os.path.abspath(os.path.join(path, '..'))
        if upPath != path:  # add special item that goes up a directory
            self.dirData.append(FolderItemData('..', upPath, None))

        # scan the directory and create item objects
        try:
            contents = os.listdir(path)
            for f in contents:
                absPath = os.path.join(path, f)
                if os.path.isdir(absPath):
                    self.dirData.append(FolderItemData(f, absPath, path))
            for f in contents:
                absPath = os.path.join(path, f)
                if os.path.isfile(absPath):
                    fsize = convertBytes(os.stat(absPath).st_size)
                    modTime = time.ctime(os.path.getmtime(absPath))
                    modTime = time.strftime(
                        "%b %d, %Y, %I:%M %p",
                        time.strptime(modTime, "%a %b %d %H:%M:%S %Y"))
                    self.dirData.append(
                        FileItemData(f, absPath, path, fsize, modTime))
        except OSError:
            dlg = wx.MessageDialog(
                self,
                "Cannot access directory `{}`, permission denied.".format(path),
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False

        return True

    def updateFileBrowser(self):
        """Update the contents of the file browser.
        """
        # start off with adding folders to the list
        self.fileList.DeleteAllItems()
        for obj in self.dirData:
            if isinstance(obj, FolderItemData):
                if not obj.name == '..':
                    img = 1
                else:
                    img = 0

                index = self.fileList.InsertItem(
                    self.fileList.GetItemCount(), obj.name, img)
            elif isinstance(obj, FileItemData):
                index = self.fileList.InsertItem(
                    self.fileList.GetItemCount(),
                    obj.name,
                    2)
                self.fileList.SetItem(index, 1, obj.fsize)
                #self.fileList.SetItem(index, 2, obj.mod)

    def addItem(self, name, absPath):
        """Add an item to the directory browser."""
        pass

    def gotoDir(self, path):
        """Set the file browser to a directory."""
        # check if a directory
        if not os.path.isdir(path):
            dlg = wx.MessageDialog(
                self,
                "Cannot access directory `{}`, not a directory.".format(path),
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # check if we have access
        # if not os.access(path, os.R_OK):
        #     dlg = wx.MessageDialog(
        #         self,
        #         "Cannot access directory `{}`, permission denied.".format(path),
        #         style=wx.ICON_ERROR | wx.OK)
        #     dlg.ShowModal()
        #     return

        # update files and folders
        if not self.scanDir(path):  # if failed, return the current directory
            self.gotoDir(self.currentPath)
            return

        # change the current path
        self.currentPath = path
        self.txtAddr.SetValue(self.currentPath)
        self.updateFileBrowser()

