#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2009 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

from __future__ import absolute_import, print_function

# from future import standard_library
# standard_library.install_aliases()
import json
from past.builtins import unicode
from builtins import chr
from builtins import range
import wx
import wx.stc
import wx.richtext
from psychopy.app.themes._themes import ThemeSwitcher
from wx.html import HtmlEasyPrinting

import wx.lib.agw.aui as aui  # some versions of phoenix

import os
import sys
import glob
import io
import threading
import bdb
import pickle
import time
import textwrap

from . import psychoParser
from .. import stdOutRich, dialogs
from .. import pavlovia_ui
from psychopy import logging, prefs
from psychopy.localization import _translate
from ..utils import FileDropTarget, PsychopyToolbar, FrameSwitcher
from psychopy.projects import pavlovia
import psychopy.app.pavlovia_ui.menu
from psychopy.app.errorDlg import exceptionCallback
from psychopy.app.coder.codeEditorBase import BaseCodeEditor
from psychopy.app.coder.fileBrowser import FileBrowserPanel
from psychopy.app.coder.sourceTree import SourceTreePanel
from psychopy.app.themes import ThemeMixin
from psychopy.app.coder.folding import CodeEditorFoldingMixin
# from ..plugin_manager import PluginManagerFrame
from psychopy.app.errorDlg import ErrorMsgDialog

try:
    import jedi
    if jedi.__version__ < "0.15":
        logging.error(
                "Need a newer version of package `jedi`. Currently using {}"
                .format(jedi.__version__)
        )
    _hasJedi = True
except ImportError:
    logging.error(
        "Package `jedi` not installed, code auto-completion and calltips will "
        "not be available.")
    _hasJedi = False

# advanced prefs (not set in prefs files)
prefTestSubset = ""
analysisLevel = 1
analyseAuto = True
runScripts = 'process'

try:  # needed for wx.py shell
    import code
    haveCode = True
except Exception:
    haveCode = False

_localized = {'basic': _translate('basic'),
              'input': _translate('input'),
              'stimuli': _translate('stimuli'),
              'experiment control': _translate('exp control'),
              'iohub': 'ioHub',  # no translation
              'hardware': _translate('hardware'),
              'timing': _translate('timing'),
              'misc': _translate('misc')}

def toPickle(filename, data):
    """save data (of any sort) as a pickle file

    simple wrapper of the cPickle module in core python
    """
    with io.open(filename, 'wb') as f:
        pickle.dump(data, f)


def fromPickle(filename):
    """load data (of any sort) from a pickle file

    simple wrapper of the cPickle module in core python
    """
    with io.open(filename, 'rb') as f:
        contents = pickle.load(f)

    return contents


class PsychopyPyShell(wx.py.shell.Shell, ThemeMixin):
    """Simple class wrapper for Pyshell which uses the Psychopy ThemeMixin."""
    def __init__(self, coder):
        msg = _translate('PyShell in PsychoPy - type some commands!')
        wx.py.shell.Shell.__init__(
            self, coder.shelf, -1, introText=msg + '\n\n', style=wx.BORDER_NONE)
        self.prefs = coder.prefs
        self.paths = coder.paths
        self.app = coder.app

        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)

        # Set theme to match code editor
        self._applyAppTheme()

    def OnSetFocus(self, evt=None):
        """Called when the shell gets focus."""
        # Switch to the default callback when in console, prevents the PsychoPy
        # error dialog from opening.
        sys.excepthook = sys.__excepthook__

        if evt:
            evt.Skip()

    def OnKillFocus(self, evt=None):
        """Called when the shell loses focus."""
        # Set the callback to use the dialog when errors occur outside the
        # shell.
        sys.excepthook = exceptionCallback

        if evt:
            evt.Skip()

    def GetContextMenu(self):
        """Override original method (wx.py.shell.Shell.GetContextMenu)
        to localize context menu.  Simply added _translate() to
        original code.
        """
        menu = wx.Menu()
        menu.Append(self.ID_UNDO, _translate("Undo"))
        menu.Append(self.ID_REDO, _translate("Redo"))

        menu.AppendSeparator()

        menu.Append(self.ID_CUT, _translate("Cut"))
        menu.Append(self.ID_COPY, _translate("Copy"))
        menu.Append(wx.py.frame.ID_COPY_PLUS, _translate("Copy With Prompts"))
        menu.Append(self.ID_PASTE, _translate("Paste"))
        menu.Append(wx.py.frame.ID_PASTE_PLUS, _translate("Paste And Run"))
        menu.Append(self.ID_CLEAR, _translate("Clear"))

        menu.AppendSeparator()

        menu.Append(self.ID_SELECTALL, _translate("Select All"))
        return menu


class Printer(HtmlEasyPrinting):
    """bare-bones printing, no control over anything

    from http://wiki.wxpython.org/Printing
    """

    def __init__(self):
        HtmlEasyPrinting.__init__(self)

    def GetHtmlText(self, text):
        """Simple conversion of text."""

        text = text.replace('&', '&amp;')
        text = text.replace('<P>', '&#60;P&#62;')
        text = text.replace('<BR>', '&#60;BR&#62;')
        text = text.replace('<HR>', '&#60;HR&#62;')
        text = text.replace('<p>', '&#60;p&#62;')
        text = text.replace('<br>', '&#60;br&#62;')
        text = text.replace('<hr>', '&#60;hr&#62;')
        text = text.replace('\n\n', '<P>')
        text = text.replace('\t', '    ')  # tabs -> 4 spaces
        text = text.replace(' ', '&nbsp;')  # preserve indentation
        html_text = text.replace('\n', '<BR>')
        return html_text

    def Print(self, text, doc_name):
        self.SetStandardFonts(size=prefs.coder['codeFontSize'], normal_face="",
                              fixed_face=prefs.coder['codeFont'])

        _, fname = os.path.split(doc_name)
        self.SetHeader("Page @PAGENUM@ of @PAGESCNT@ - " + fname +
                       " (@DATE@ @TIME@)<HR>")
        # use <tt> tag since we're dealing with old school HTML here
        self.PrintText("<tt>" + self.GetHtmlText(text) + '</tt>', doc_name)


class ScriptThread(threading.Thread):
    """A subclass of threading.Thread, with a kill() method.
    """

    def __init__(self, target, gui):
        threading.Thread.__init__(self, target=target)
        self.killed = False
        self.gui = gui

    def start(self):
        """Start the thread.
        """
        self.__run_backup = self.run
        self.run = self.__run  # force the Thread to install our trace.
        threading.Thread.start(self)

    def __run(self):
        """Hacked run function, which installs the trace.
        """
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup
        # we're done - send the App a message
        self.gui.onProcessEnded(event=None)

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True


class PsychoDebugger(bdb.Bdb):
    # this is based on effbot: http://effbot.org/librarybook/bdb.htm

    def __init__(self):
        bdb.Bdb.__init__(self)
        self.starting = True

    def user_call(self, frame, args):
        name = frame.f_code.co_name or "<unknown>"
        self.set_continue()  # continue

    def user_line(self, frame):
        if self.starting:
            self.starting = False
            self.set_trace()  # start tracing
        else:
            # arrived at breakpoint
            name = frame.f_code.co_name or "<unknown>"
            filename = self.canonic(frame.f_code.co_filename)
            print("break at %s %i in %s" % (filename, frame.f_lineno, name))
        self.set_continue()  # continue to next breakpoint

    def user_return(self, frame, value):
        name = frame.f_code.co_name or "<unknown>"
        self.set_continue()  # continue

    def user_exception(self, frame, exception):
        name = frame.f_code.co_name or "<unknown>"
        self.set_continue()  # continue

    def quit(self):
        self._user_requested_quit = 1
        self.set_quit()
        return 1


class UnitTestFrame(wx.Frame):
    class _unitTestOutRich(stdOutRich.StdOutRich):
        """richTextCtrl window for unit test output"""

        def __init__(self, parent, style, size=None, **kwargs):
            stdOutRich.StdOutRich.__init__(self, parent=parent, style=style,
                                           size=size)
            self.bad = [150, 0, 0]
            self.good = [0, 150, 0]
            self.skip = [170, 170, 170]
            self.png = []

        def write(self, inStr):
            self.MoveEnd()  # always 'append' text rather than 'writing' it
            for thisLine in inStr.splitlines(True):
                if not isinstance(thisLine, unicode):
                    thisLine = unicode(thisLine)
                if thisLine.startswith('OK'):
                    self.BeginBold()
                    self.BeginTextColour(self.good)
                    self.WriteText("OK")
                    self.EndTextColour()
                    self.EndBold()
                    self.WriteText(thisLine[2:])  # for OK (SKIP=xx)
                    self.parent.status = 1
                elif thisLine.startswith('#####'):
                    self.BeginBold()
                    self.WriteText(thisLine)
                    self.EndBold()
                elif 'FAIL' in thisLine or 'ERROR' in thisLine:
                    self.BeginTextColour(self.bad)
                    self.WriteText(thisLine)
                    self.EndTextColour()
                    self.parent.status = -1
                elif thisLine.find('SKIP') > -1:
                    self.BeginTextColour(self.skip)
                    self.WriteText(thisLine.strip())
                    # show the new image, double size for easier viewing:
                    if thisLine.strip().endswith('.png'):
                        newImg = thisLine.split()[-1]
                        img = os.path.join(self.parent.paths['tests'],
                                           'data', newImg)
                        self.png.append(wx.Image(img, wx.BITMAP_TYPE_ANY))
                        self.MoveEnd()
                        self.WriteImage(self.png[-1])
                    self.MoveEnd()
                    self.WriteText('\n')
                    self.EndTextColour()
                else:  # line to write as simple text
                    self.WriteText(thisLine)
                if thisLine.find('Saved copy of actual frame') > -1:
                    # show the new images, double size for easier viewing:
                    newImg = [f for f in thisLine.split()
                              if f.find('_local.png') > -1]
                    newFile = newImg[0]
                    origFile = newFile.replace('_local.png', '.png')
                    img = os.path.join(self.parent.paths['tests'], origFile)
                    self.png.append(wx.Image(img, wx.BITMAP_TYPE_ANY))
                    self.MoveEnd()
                    self.WriteImage(self.png[-1])
                    self.MoveEnd()
                    self.WriteText('= ' + origFile + ';   ')
                    img = os.path.join(self.parent.paths['tests'], newFile)
                    self.png.append(wx.Image(img, wx.BITMAP_TYPE_ANY))
                    self.MoveEnd()
                    self.WriteImage(self.png[-1])
                    self.MoveEnd()
                    self.WriteText('= ' + newFile + '; ')

            self.MoveEnd()  # go to end of stdout so user can see updated text
            self.ShowPosition(self.GetLastPosition())

    def __init__(self, parent=None, ID=-1,
                 title=_translate('PsychoPy unit testing'),
                 files=(), app=None):
        self.app = app
        self.frameType = 'unittest'
        self.prefs = self.app.prefs
        self.paths = self.app.prefs.paths
        # deduce the script for running the tests
        try:
            import pytest
            havePytest = True
        except Exception:
            havePytest = False
        if havePytest:
            self.runpyPath = os.path.join(self.prefs.paths['tests'], 'run.py')
        else:
            # run the standalone version
            self.runpyPath = os.path.join(
                self.prefs.paths['tests'], 'runPytest.py')
        if sys.platform != 'win32':
            self.runpyPath = self.runpyPath.replace(' ', '\ ')
        # setup the frame
        self.IDs = self.app.IDs
        # to right, so Cancel button is clickable during a long test
        wx.Frame.__init__(self, parent, ID, title, pos=(450, 45))
        self.scriptProcess = None
        self.runAllText = 'all tests'
        border = 10
        # status = outcome of the last test run: -1 fail, 0 not run, +1 ok:
        self.status = 0

        # create menu items
        menuBar = wx.MenuBar()
        self.menuTests = wx.Menu()
        menuBar.Append(self.menuTests, _translate('&Tests'))
        _run = self.app.keys['runScript']
        self.menuTests.Append(wx.ID_APPLY,
                              _translate("&Run tests\t%s") % _run)
        self.Bind(wx.EVT_MENU, self.onRunTests, id=wx.ID_APPLY)
        self.menuTests.AppendSeparator()
        self.menuTests.Append(wx.ID_CLOSE, _translate(
            "&Close tests panel\t%s") % self.app.keys['close'])
        self.Bind(wx.EVT_MENU, self.onCloseTests, id=wx.ID_CLOSE)
        _switch = self.app.keys['switchToCoder']
        self.menuTests.Append(wx.ID_ANY,
                              _translate("Go to &Coder view\t%s") % _switch,
                              _translate("Go to the Coder view"))
        self.Bind(wx.EVT_MENU, self.app.showCoder)
        # -------------quit
        self.menuTests.AppendSeparator()
        _quit = self.app.keys['quit']
        self.menuTests.Append(wx.ID_EXIT,
                              _translate("&Quit\t%s") % _quit,
                              _translate("Terminate PsychoPy"))
        self.Bind(wx.EVT_MENU, self.app.quit, id=wx.ID_EXIT)
        item = self.menuTests.Append(
            wx.ID_PREFERENCES, _translate("&Preferences"))
        self.Bind(wx.EVT_MENU, self.app.showPrefs, item)
        self.SetMenuBar(menuBar)

        # create controls
        buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
        _style = wx.TE_MULTILINE | wx.TE_READONLY | wx.EXPAND | wx.GROW
        _font = self.prefs.coder['outputFont']
        _fsize = self.prefs.coder['outputFontSize']
        self.outputWindow = self._unitTestOutRich(self, style=_style,
                                                  size=wx.Size(750, 500),
                                                  font=_font, fontSize=_fsize)

        knownTests = glob.glob(os.path.join(self.paths['tests'], 'test*'))
        knownTestList = [t.split(os.sep)[-1] for t in knownTests
                         if t.endswith('.py') or os.path.isdir(t)]
        self.knownTestList = [self.runAllText] + knownTestList
        self.testSelect = wx.Choice(parent=self, id=-1, pos=(border, border),
                                    choices=self.knownTestList)
        tip = _translate(
            "Select the test(s) to run, from:\npsychopy/tests/test*")
        self.testSelect.SetToolTip(wx.ToolTip(tip))
        prefTestSubset = self.prefs.appData['testSubset']
        # preselect the testGroup in the drop-down menu for display:
        if prefTestSubset in self.knownTestList:
            self.testSelect.SetStringSelection(prefTestSubset)

        self.btnRun = wx.Button(parent=self, label=_translate("Run tests"))
        self.btnRun.Bind(wx.EVT_BUTTON, self.onRunTests)
        self.btnCancel = wx.Button(parent=self, label=_translate("Cancel"))
        self.btnCancel.Bind(wx.EVT_BUTTON, self.onCancelTests)
        self.btnCancel.Disable()
        self.Bind(wx.EVT_END_PROCESS, self.onTestsEnded)

        self.chkCoverage = wx.CheckBox(
            parent=self, label=_translate("Coverage Report"))
        _tip = _translate("Include coverage report (requires coverage module)")
        self.chkCoverage.SetToolTip(wx.ToolTip(_tip))
        self.chkCoverage.Disable()
        self.chkAllStdOut = wx.CheckBox(
            parent=self, label=_translate("ALL stdout"))
        _tip = _translate(
            "Report all printed output & show any new rms-test images")
        self.chkAllStdOut.SetToolTip(wx.ToolTip(_tip))
        self.chkAllStdOut.Disable()
        self.Bind(wx.EVT_IDLE, self.onIdle)
        self.SetDefaultItem(self.btnRun)

        # arrange controls
        buttonsSizer.Add(self.chkCoverage, 0, wx.LEFT |
                         wx.RIGHT | wx.TOP, border=border)
        buttonsSizer.Add(self.chkAllStdOut, 0, wx.LEFT |
                         wx.RIGHT | wx.TOP, border=border)
        buttonsSizer.Add(self.btnRun, 0, wx.LEFT |
                         wx.RIGHT | wx.TOP, border=border)
        buttonsSizer.Add(self.btnCancel, 0, wx.LEFT |
                         wx.RIGHT | wx.TOP, border=border)
        self.sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.sizer.Add(buttonsSizer, 0, wx.ALIGN_RIGHT)
        self.sizer.Add(self.outputWindow, 0, wx.ALL |
                       wx.EXPAND | wx.GROW, border=border)
        self.SetSizerAndFit(self.sizer)
        self.Show()

    def onRunTests(self, event=None):
        """Run the unit tests
        """
        self.status = 0

        # create process
        # self is the parent (which will receive an event when the process
        # ends)
        self.scriptProcess = wx.Process(self)
        self.scriptProcess.Redirect()  # catch the stdout/stdin
        # include coverage report?
        if self.chkCoverage.GetValue():
            coverage = ' cover'
        else:
            coverage = ''
        # printing ALL output?
        if self.chkAllStdOut.GetValue():
            allStdout = ' -s'
        else:
            allStdout = ''
        # what subset of tests? (all tests == '')
        tselect = self.knownTestList[self.testSelect.GetCurrentSelection()]
        if tselect == self.runAllText:
            tselect = ''
        testSubset = tselect
        # self.prefs.appData['testSubset'] = tselect # in onIdle

        # launch the tests using wx.Execute():
        self.btnRun.Disable()
        self.btnCancel.Enable()
        if sys.platform == 'win32':
            testSubset = ' ' + testSubset
            args = (sys.executable, self.runpyPath, coverage,
                    allStdout, testSubset)
            command = '"%s" -u "%s" %s%s%s' % args  # quotes handle spaces
            print(command)
            self.scriptProcessID = wx.Execute(
                command, wx.EXEC_ASYNC, self.scriptProcess)
            # self.scriptProcessID = wx.Execute(command,
            #    # wx.EXEC_ASYNC| wx.EXEC_NOHIDE, self.scriptProcess)
        else:
            testSubset = ' ' + testSubset.replace(' ', '\ ')  # protect spaces
            args = (sys.executable, self.runpyPath, coverage,
                    allStdout, testSubset)
            command = '%s -u %s%s%s%s' % args
            _opt = wx.EXEC_ASYNC | wx.EXEC_MAKE_GROUP_LEADER
            self.scriptProcessID = wx.Execute(command,
                                              _opt, self.scriptProcess)
        msg = "\n##### Testing: %s%s%s%s   #####\n\n" % (
            self.runpyPath, coverage, allStdout, testSubset)
        self.outputWindow.write(msg)
        _notNormUnits = self.app.prefs.general['units'] != 'norm'
        if _notNormUnits and 'testVisual' in testSubset:
            msg = "Note: default window units = '%s' (in prefs); for visual tests 'norm' is recommended.\n\n"
            self.outputWindow.write(msg % self.app.prefs.general['units'])

    def onCancelTests(self, event=None):
        if self.scriptProcess != None:
            self.scriptProcess.Kill(
                self.scriptProcessID, wx.SIGTERM, wx.SIGKILL)
        self.scriptProcess = None
        self.scriptProcessID = None
        self.outputWindow.write("\n --->> cancelled <<---\n\n")
        self.status = 0
        self.onTestsEnded()

    def onIdle(self, event=None):
        # auto-save last selected subset:
        self.prefs.appData['testSubset'] = self.knownTestList[
            self.testSelect.GetCurrentSelection()]
        if self.scriptProcess != None:
            if self.scriptProcess.IsInputAvailable():
                stream = self.scriptProcess.GetInputStream()
                text = stream.read()
                self.outputWindow.write(text)
            if self.scriptProcess.IsErrorAvailable():
                stream = self.scriptProcess.GetErrorStream()
                text = stream.read()
                self.outputWindow.write(text)

    def onTestsEnded(self, event=None):
        self.onIdle()  # so that any final stdout/err gets written
        self.outputWindow.flush()
        self.btnRun.Enable()
        self.btnCancel.Disable()

    def onURL(self, evt):
        """decompose the URL of a file and line number"""
        # "C:\Program Files\wxPython2.8 Docs and Demos\samples\hangman\hangman.py"
        tmpFilename, tmpLineNumber = evt.GetString().rsplit('", line ', 1)
        filename = tmpFilename.split('File "', 1)[1]
        try:
            lineNumber = int(tmpLineNumber.split(',')[0])
        except ValueError:
            lineNumber = int(tmpLineNumber.split()[0])
        self.app.coder.gotoLine(filename, lineNumber)

    def onCloseTests(self, evt):
        self.Destroy()


class CodeEditor(BaseCodeEditor, CodeEditorFoldingMixin, ThemeMixin):
    """Code editor class for the Coder GUI.
    """
    def __init__(self, parent, ID, frame,
                 # set the viewer to be small, then it will increase with aui
                 # control
                 pos=wx.DefaultPosition, size=wx.Size(100, 100),
                 style=wx.BORDER_NONE, readonly=False):
        BaseCodeEditor.__init__(self, parent, ID, pos, size, style)

        self.coder = frame
        self.prefs = self.coder.prefs
        self.paths = self.coder.paths
        self.app = self.coder.app
        self.SetViewWhiteSpace(self.coder.appData['showWhitespace'])
        self.SetViewEOL(self.coder.appData['showEOLs'])
        self.Bind(wx.EVT_DROP_FILES, self.coder.filesDropped)
        self.Bind(wx.stc.EVT_STC_MODIFIED, self.onModified)
        self.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyReleased)

        if hasattr(self, 'OnMarginClick'):
            self.Bind(wx.stc.EVT_STC_MARGINCLICK, self.OnMarginClick)

        # black-and-white text signals read-only file open in Coder window
        # if not readonly:
        #     self.setFonts()
        self.SetDropTarget(FileDropTarget(targetFrame=self.coder))

        # set to python syntax code coloring
        self.setLexerFromFileName()

        # Keep track of visual aspects of the source tree viewer when working
        # with this document. This makes sure the tree maintains it's state when
        # moving between documents.
        self.expandedItems = {}

        # show the long line edge guide, enabled if >0
        self.edgeGuideColumn = self.coder.prefs['edgeGuideColumn']
        self.edgeGuideVisible = self.edgeGuideColumn > 0

        # give a little space between the margin and text
        self.SetMarginLeft(4)

        # caret info, these are updated by calling updateCaretInfo()
        self.indentSize = self.GetIndent()
        self.caretCurrentPos = self.GetCurrentPos()
        self.caretVisible, caretColumn, caretLine = self.PositionToXY(
            self.caretCurrentPos)

        if self.caretVisible:
            self.caretColumn = caretColumn
            self.caretLine = caretLine
        else:
            self.caretLine = self.GetCurrentLine()
            self.caretColumn = self.GetLineLength(self.caretLine)

        # where does the line text start?
        self.caretLineIndentCol = \
            self.GetColumn(self.GetLineIndentPosition(self.caretLine))

        # what is the indent level of the line the caret is located
        self.caretLineIndentLevel = self.caretLineIndentCol / self.indentSize

        # is the caret at an indentation level?
        self.caretAtIndentLevel = \
            (self.caretLineIndentCol % self.indentSize) == 0

        # # should hitting backspace result in an untab?
        # self.shouldBackspaceUntab = \
        #     self.caretAtIndentLevel and \
        #     0 < self.caretColumn <= self.caretLineIndentCol
        self.SetBackSpaceUnIndents(True)

        # set the current line and column in the status bar
        self.coder.SetStatusText(
            'Line: {} Col: {}'.format(
                self.caretLine + 1, self.caretColumn + 1), 1)

        # calltips
        self.CallTipSetBackground(ThemeMixin.codeColors['base']['bg'])
        self.CallTipSetForeground(ThemeMixin.codeColors['base']['fg'])
        self.CallTipSetForegroundHighlight(ThemeMixin.codeColors['select']['fg'])
        self.AutoCompSetIgnoreCase(True)
        self.AutoCompSetAutoHide(True)
        self.AutoCompStops('. ')
        self.openBrackets = 0

        # better font rendering and less flicker on Windows by using Direct2D
        # for rendering instead of GDI
        if wx.Platform == '__WXMSW__':
            self.SetTechnology(3)

        # double buffered better rendering except if retina
        self.SetDoubleBuffered(self.coder.IsDoubleBuffered())

        self.theme = self.app.prefs.app['theme']

    def setFonts(self):
        """Make some styles,  The lexer defines what each style is used for,
        we just have to define what each style looks like.  This set is
        adapted from Scintilla sample property files."""

        if wx.Platform == '__WXMSW__':
            faces = {'size': 10}
        elif wx.Platform == '__WXMAC__':
            faces = {'size': 14}
        else:
            faces = {'size': 12}
        if self.coder.prefs['codeFontSize']:
            faces['size'] = int(self.coder.prefs['codeFontSize'])
        faces['small'] = faces['size'] - 2
        # Global default styles for all languages
        # ,'Arial']  # use arial as backup
        faces['code'] = self.coder.prefs['codeFont']
        # ,'Arial']  # use arial as backup
        faces['comment'] = self.coder.prefs['codeFont']

        # apply the theme to the lexer
        self.theme = self.coder.app.prefs.app['theme']

    def setLexerFromFileName(self):
        """Set the lexer to one that best matches the file name."""
        # best matching lexers for a given file type
        lexers = {'Python': 'python',
                  'HTML': 'html',
                  'C/C++': 'cpp',
                  'GLSL': 'cpp',
                  'Arduino': 'cpp',
                  'MATLAB': 'matlab',
                  'YAML': 'yaml',
                  'R': 'R',
                  'JavaScript': 'cpp',
                  'Plain Text': 'null'}

        self.setLexer(lexers[self.getFileType()])

    def getFileType(self):
        """Get the file type from the extension."""
        if os.path.isabs(self.filename):
            _, filen = os.path.split(self.filename)
        else:
            filen = self.filename

        # get the extension, if any
        fsplit = filen.split('.')
        if len(fsplit) > 1:   # has enough splits to have an extension
            ext = fsplit[-1]
        else:
            ext = 'txt'  # assume a text file if we're able to open it

        if ext in ('py', 'pyx', 'pxd', 'pxi',):  # python/cython files
            return 'Python'
        elif ext in ('html',):  # html file
            return 'HTML'
        elif ext in ('cpp', 'c', 'h', 'mex', 'hpp'):  # c-like file
            return 'C/C++'
        elif ext in ('glsl', 'vert', 'frag'):  # OpenGL shader program
            return 'GLSL'
        elif ext in ('m',):  # MATLAB
            return 'MATLAB'
        elif ext in ('ino',):  # Arduino
            return 'Arduino'
        elif ext in ('R',):  # R
            return 'R'
        elif ext in ('yaml',):  # R
            return 'YAML'
        elif ext in ('js',):  # R
            return 'JavaScript'
        else:
            return 'Plain Text'  # default

    def getTextUptoCaret(self):
        """Get the text upto the caret."""
        return self.GetTextRange(0, self.caretCurrentPos)

    def OnKeyReleased(self, event):
        """Called after a key is released."""

        if hasattr(self.coder, "useAutoComp"):
            keyCode = event.GetKeyCode()
            _mods = event.GetModifiers()
            if keyCode == ord('.'):
                if self.coder.useAutoComp:
                    # A dot was entered, get suggestions if part of a qualified name
                    wx.CallAfter(self.ShowAutoCompleteList)  # defer
                else:
                    self.coder.SetStatusText(
                        'Press Ctrl+Space to show code completions', 0)
            elif keyCode == ord('9') and wx.MOD_SHIFT == _mods:
                # A left bracket was entered, check if there is a calltip available
                if self.coder.useAutoComp:
                    if not self.CallTipActive():
                        wx.CallAfter(self.ShowCalltip)

                    self.openBrackets += 1
                else:
                    self.coder.SetStatusText(
                        'Press Ctrl+Space to show calltip', 0)
            elif keyCode == ord('0') and wx.MOD_SHIFT == _mods:  # close if brace matches
                if self.CallTipActive():
                    self.openBrackets -= 1
                    if self.openBrackets <= 0:
                        self.CallTipCancel()
                        self.openBrackets = 0
            else:
                self.coder.SetStatusText('', 0)

        event.Skip()

    def OnKeyPressed(self, event):
        """Called when a key is pressed."""
        # various stuff to handle code completion and tooltips
        # enable in the _-init__
        keyCode = event.GetKeyCode()
        _mods = event.GetModifiers()
        # handle some special keys
        if keyCode == ord('[') and wx.MOD_CONTROL == _mods:
            self.indentSelection(-4)
            # if there are no characters on the line then also move caret to
            # end of indentation
            txt, charPos = self.GetCurLine()
            if charPos == 0:
                # if caret is at start of line, move to start of text instead
                self.VCHome()
        elif keyCode == ord(']') and wx.MOD_CONTROL == _mods:
            self.indentSelection(4)
            # if there are no characters on the line then also move caret to
            # end of indentation
            txt, charPos = self.GetCurLine()
            if charPos == 0:
                # if caret is at start of line, move to start of text instead
                self.VCHome()

        elif keyCode == ord('/') and wx.MOD_CONTROL == _mods:
            self.commentLines()
        elif keyCode == ord('/') and wx.MOD_CONTROL | wx.MOD_SHIFT == _mods:
            self.uncommentLines()

        # show completions, very simple at this point
        elif keyCode == wx.WXK_SPACE and wx.MOD_CONTROL == _mods:
            self.ShowAutoCompleteList()

        # show a calltip with signiture
        elif keyCode == wx.WXK_SPACE and wx.MOD_CONTROL | wx.MOD_SHIFT == _mods:
            self.ShowCalltip()

        elif keyCode == wx.WXK_ESCAPE:  # close overlays
            if self.AutoCompActive():
                self.AutoCompCancel()  # close the auto completion list
            if self.CallTipActive():
                self.CallTipCancel()
                self.openBrackets = 0

        elif keyCode == wx.WXK_RETURN: # and not self.AutoCompActive():
            if not self.AutoCompActive():
                # process end of line and then do smart indentation
                event.Skip(False)
                self.CmdKeyExecute(wx.stc.STC_CMD_NEWLINE)
                self.smartIdentThisLine()
                self.analyseScript()
                return  # so that we don't reach the skip line at end

            if self.CallTipActive():
                self.CallTipCancel()
                self.openBrackets = 0

        # quote line
        elif keyCode == ord("'"):
            #raise RuntimeError
            start, end = self.GetSelection()
            if end - start > 0:
                txt = self.GetSelectedText()
                txt = "'" + txt.replace('\n', "'\n'") + "'"
                self.ReplaceSelection(txt)
                event.Skip(False)
                return

        event.Skip()

    def ShowAutoCompleteList(self):
        """Show autocomplete list at the current caret position."""
        if _hasJedi and self.getFileType() == 'Python':
            self.coder.SetStatusText(
                'Retrieving code completions, please wait ...', 0)
            # todo - create Script() periodically
            compList = [i.name for i in jedi.Script(
                self.getTextUptoCaret(),
                path=self.filename if os.path.isabs(self.filename) else
                None).completions(fuzzy=False)]
            # todo - check if have a perfect match and veto AC
            self.coder.SetStatusText('', 0)
            if compList:
                self.AutoCompShow(0, " ".join(compList))

    def ShowCalltip(self):
        """Show a calltip at the current caret position."""
        if _hasJedi and self.getFileType() == 'Python':
            self.coder.SetStatusText('Retrieving calltip, please wait ...', 0)
            thisObj = jedi.Script(self.getTextUptoCaret())
            if hasattr(thisObj, 'get_signatures'):
                foundRefs = thisObj.get_signatures()
            elif hasattr(thisObj, 'call_signatures'):
                # call_signatures deprecated in jedi 0.16.0 (2020)
                foundRefs = thisObj.call_signatures()
            else:
                foundRefs = None
            self.coder.SetStatusText('', 0)

            if foundRefs:
                # enable text wrapping
                calltipText = foundRefs[0].to_string()
                if calltipText:
                    calltipText = '\n    '.join(
                        textwrap.wrap(calltipText, 76))  # 80 cols after indent
                    y, x = foundRefs[0].bracket_start
                    self.CallTipShow(
                        self.XYToPosition(x + 1, y + 1), calltipText)

    def MacOpenFile(self, evt):
        logging.debug('PsychoPyCoder: got MacOpenFile event')

    def OnUpdateUI(self, evt):
        """Runs when the editor is changed in any way."""
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            styleBefore = self.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()":
            if styleBefore == wx.stc.STC_P_OPERATOR:
                braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)
            if charAfter and chr(charAfter) in "[]{}()":
                if styleAfter == wx.stc.STC_P_OPERATOR:
                    braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1 and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)

        # Update data about caret position, this can be done once per UI update
        # to eliminate the need to recalculate these values when needed
        # elsewhere.
        self.updateCaretInfo()

        # set the current line and column in the status bar
        self.coder.SetStatusText('Line: {} Col: {}'.format(
            self.caretLine + 1, self.caretColumn + 1), 1)

    def updateCaretInfo(self):
        """Update information related to the current caret position in the text.

        This is done once per UI update which reduces redundant calculations of
        these values.

        """
        self.indentSize = self.GetIndent()
        self.caretCurrentPos = self.GetCurrentPos()
        self.caretVisible, caretColumn, caretLine = self.PositionToXY(
            self.caretCurrentPos)

        if self.caretVisible:
            self.caretColumn = caretColumn
            self.caretLine = caretLine
        else:
            self.caretLine = self.GetCurrentLine()
            self.caretColumn = self.GetLineLength(self.caretLine)

        self.caretLineIndentCol = \
            self.GetColumn(self.GetLineIndentPosition(self.caretLine))
        self.caretLineIndentLevel = self.caretLineIndentCol / self.indentSize
        self.caretAtIndentLevel = \
            (self.caretLineIndentCol % self.indentSize) == 0
        # self.shouldBackspaceUntab = \
        #     self.caretAtIndentLevel and \
        #     0 < self.caretColumn <= self.caretLineIndentCol

    def commentLines(self):
        # used for the comment/uncomment machinery from ActiveGrid
        newText = ""
        for lineNo in self._GetSelectedLineNumbers():
            lineText = self.GetLine(lineNo)
            oneSharp = bool(len(lineText) > 1 and lineText[0] == '#')
            # todo: is twoSharp ever True when oneSharp is not?
            twoSharp = bool(len(lineText) > 2 and lineText[:2] == '##')
            lastLine = bool(lineNo == self.GetLineCount() - 1
                            and self.GetLineLength(lineNo) == 0)
            if oneSharp or twoSharp or lastLine:
                newText = newText + lineText
            else:
                newText = newText + "#" + lineText

        self._ReplaceSelectedLines(newText)

    def uncommentLines(self):
        # used for the comment/uncomment machinery from ActiveGrid
        newText = ""
        for lineNo in self._GetSelectedLineNumbers():
            lineText = self.GetLine(lineNo)
            # todo: is the next line ever True? seems like should be == '##'
            if len(lineText) >= 2 and lineText[:2] == "#":
                lineText = lineText[2:]
            elif len(lineText) >= 1 and lineText[:1] == "#":
                lineText = lineText[1:]
            newText = newText + lineText
        self._ReplaceSelectedLines(newText)

    def increaseFontSize(self):
        self.SetZoom(self.GetZoom() + 1)

    def decreaseFontSize(self):
        # Minimum zoom set to - 6
        if self.GetZoom() == -6:
            self.SetZoom(self.GetZoom())
        else:
            self.SetZoom(self.GetZoom() - 1)

    def resetFontSize(self):
        """Reset the zoom level."""
        self.SetZoom(0)

    # the Source Assistant and introspection functinos were broekn and removed frmo PsychoPy 1.90.0
    def analyseScript(self):
        """Parse the abstract syntax tree for the current document.

        This function gets a list of functions, classes and methods in the
        source code.

        """
        # scan the AST for objects we care about
        if hasattr(self.coder, 'structureWindow'):
            self.coder.structureWindow.refresh()

    def setLexer(self, lexer=None):
        """Lexer is a simple string (e.g. 'python', 'html')
        that will be converted to use the right STC_LEXER_XXXX value
        """
        lexer = 'null' if lexer is None else lexer
        try:
            lex = getattr(wx.stc, "STC_LEX_%s" % (lexer.upper()))
        except AttributeError:
            logging.warn("Unknown lexer %r. Using plain text." % lexer)
            lex = wx.stc.STC_LEX_NULL
            lexer = 'null'
        # then actually set it
        self.SetLexer(lex)
        self.setFonts()

        if lexer == 'python':
            self.SetIndentationGuides(self.coder.appData['showIndentGuides'])
            self.SetProperty("fold", "1")  # allow folding
            self.SetProperty("tab.timmy.whinge.level", "1")
        elif lexer.lower() == 'html':
            self.SetProperty("fold", "1")  # allow folding
            # 4 means 'tabs are bad'; 1 means 'flag inconsistency'
            self.SetProperty("tab.timmy.whinge.level", "1")
        elif lexer == 'cpp':  # JS, C/C++, GLSL, mex, arduino
            self.SetIndentationGuides(self.coder.appData['showIndentGuides'])
            self.SetProperty("fold", "1")
            self.SetProperty("tab.timmy.whinge.level", "1")
        elif lexer == 'R':
            # self.SetKeyWords(0, " ".join(['function']))
            self.SetIndentationGuides(self.coder.appData['showIndentGuides'])
            self.SetProperty("fold", "1")
            self.SetProperty("tab.timmy.whinge.level", "1")
        else:
            self.SetIndentationGuides(0)
            self.SetProperty("tab.timmy.whinge.level", "0")

        # keep text from being squashed and hard to read
        self.SetStyleBits(self.GetStyleBitsNeeded())
        spacing = self.coder.prefs['lineSpacing'] / 2.
        self.SetExtraAscent(int(spacing))
        self.SetExtraDescent(int(spacing))
        self.Colourise(0, -1)

    def onModified(self, event):
        # update the UNSAVED flag and the save icons
        #notebook = self.GetParent()
        #mainFrame = notebook.GetParent()
        self.coder.setFileModified(True)

    def DoFindNext(self, findData, findDlg=None):
        # this comes straight from wx.py.editwindow  (which is a subclass of
        # STC control)
        backward = not (findData.GetFlags() & wx.FR_DOWN)
        matchcase = (findData.GetFlags() & wx.FR_MATCHCASE) != 0
        end = self.GetLength()
        textstring = self.GetTextRange(0, end)
        findstring = findData.GetFindString()
        if not matchcase:
            textstring = textstring.lower()
            findstring = findstring.lower()
        if backward:
            start = self.GetSelection()[0]
            loc = textstring.rfind(findstring, 0, start)
        else:
            start = self.GetSelection()[1]
            loc = textstring.find(findstring, start)

        # if it wasn't found then restart at begining
        if loc == -1 and start != 0:
            if backward:
                start = end
                loc = textstring.rfind(findstring, 0, start)
            else:
                start = 0
                loc = textstring.find(findstring, start)

        # was it still not found?
        if loc == -1:
            dlg = dialogs.MessageDialog(self, message=_translate(
                'Unable to find "%s"') % findstring, type='Info')
            dlg.ShowModal()
            dlg.Destroy()
        else:
            # show and select the found text
            line = self.LineFromPosition(loc)
            # self.EnsureVisible(line)
            self.GotoLine(line)
            self.SetSelection(loc, loc + len(findstring))
        if findDlg:
            if loc == -1:
                wx.CallAfter(findDlg.SetFocus)
                return
            # else:
            #     findDlg.Close()


class CoderFrame(wx.Frame, ThemeMixin):

    def __init__(self, parent, ID, title, files=(), app=None):
        self.app = app  # type: PsychoPyApp
        self.frameType = 'coder'
        # things the user doesn't set like winsize etc
        self.appData = self.app.prefs.appData['coder']
        self.prefs = self.app.prefs.coder  # things about coder that get set
        self.appPrefs = self.app.prefs.app
        self.paths = self.app.prefs.paths
        self.IDs = self.app.IDs
        self.currentDoc = None
        self.project = None
        self.ignoreErrors = False
        self.fileStatusLastChecked = time.time()
        self.fileStatusCheckInterval = 5 * 60  # sec
        self.showingReloadDialog = False
        self.btnHandles = {}  # stores toolbar buttons so they can be altered

        # we didn't have the key or the win was minimized/invalid
        if self.appData['winH'] == 0 or self.appData['winW'] == 0:
            self.appData['winH'], self.appData['winW'] = wx.DefaultSize
            self.appData['winX'], self.appData['winY'] = wx.DefaultPosition
        if self.appData['winY'] < 20:
            self.appData['winY'] = 20
        # fix issue in Windows when frame was closed while iconized
        if self.appData['winX'] == -32000:
            self.appData['winX'], self.appData['winY'] = wx.DefaultPosition
            self.appData['winH'], self.appData['winW'] = wx.DefaultSize
        wx.Frame.__init__(self, parent, ID, title,
                          (self.appData['winX'], self.appData['winY']),
                          size=(self.appData['winW'], self.appData['winH']))

        # detect retina displays (then don't use double-buffering)
        self.isRetina = self.GetContentScaleFactor() != 1
        self.SetDoubleBuffered(not self.isRetina)

        # create a panel which the aui manager can hook onto
        szr = wx.BoxSizer(wx.VERTICAL)
        self.pnlMain = wx.Panel(self)
        szr.Add(self.pnlMain, flag=wx.EXPAND | wx.ALL, proportion=1)
        self.SetSizer(szr)

        # self.panel = wx.Panel(self)
        self.Hide()  # ugly to see it all initialise
        # create icon
        if sys.platform == 'darwin':
            pass  # doesn't work and not necessary - handled by app bundle
        else:
            iconFile = os.path.join(self.paths['resources'], 'coder.ico')
            if os.path.isfile(iconFile):
                self.SetIcon(wx.Icon(iconFile, wx.BITMAP_TYPE_ICO))
        # NB not the same as quit - just close the window
        self.Bind(wx.EVT_CLOSE, self.closeFrame)
        self.Bind(wx.EVT_IDLE, self.onIdle)

        if 'state' in self.appData and self.appData['state'] == 'maxim':
            self.Maximize()
        # initialise some attributes
        self.modulesLoaded = False  # goes true when loading thread completes
        self.findDlg = None
        self.findData = wx.FindReplaceData()
        self.findData.SetFlags(wx.FR_DOWN)
        self.importedScripts = {}
        self.scriptProcess = None
        self.scriptProcessID = None
        self.db = None  # debugger
        self._lastCaretPos = None

        # setup universal shortcuts
        accelTable = self.app.makeAccelTable()
        self.SetAcceleratorTable(accelTable)

        # Setup pane and art managers
        self.paneManager = aui.AuiManager(self.pnlMain, aui.AUI_MGR_DEFAULT | aui.AUI_MGR_RECTANGLE_HINT)
        # Create toolbar
        self.toolbar = PsychopyToolbar(self)
        self.SetToolBar(self.toolbar)
        # Create menus and status bar
        self.makeMenus()
        self.makeStatusBar()
        self.fileMenu = self.editMenu = self.viewMenu = None
        self.helpMenu = self.toolsMenu = None
        self.pavloviaMenu.syncBtn.Enable(bool(self.filename))
        self.pavloviaMenu.newBtn.Enable(bool(self.filename))

        # Create source assistant notebook
        self.sourceAsst = aui.AuiNotebook(
            self.pnlMain,
            wx.ID_ANY,
            size = wx.Size(350, 600),
            agwStyle=aui.AUI_NB_CLOSE_ON_ALL_TABS |
                     aui.AUI_NB_TAB_SPLIT |
                     aui.AUI_NB_TAB_MOVE)

        self.structureWindow = SourceTreePanel(self.sourceAsst, self)
        self.fileBrowserWindow = FileBrowserPanel(self.sourceAsst, self)
        # Add source assistant panel
        self.paneManager.AddPane(self.sourceAsst,
                                 aui.AuiPaneInfo().
                                 BestSize((350, 600)).
                                 FloatingSize((350, 600)).
                                 Floatable(False).
                                 BottomDockable(False).TopDockable(False).
                                 CloseButton(False).PaneBorder(False).
                                 Name("SourceAsst").
                                 Caption(_translate("Source Assistant")).
                                 Left())
        # Add structure page to source assistant
        self.structureWindow.SetName("Structure")
        self.sourceAsst.AddPage(self.structureWindow, "Structure")
        # Add file browser page to source assistant
        self.fileBrowserWindow.SetName("FileBrowser")
        self.sourceAsst.AddPage(self.fileBrowserWindow, "File Browser")

        # remove close buttons
        self.sourceAsst.SetCloseButton(0, False)
        self.sourceAsst.SetCloseButton(1, False)

        # Create editor notebook
        #todo: Why is editor default background not same as usual frame backgrounds?
        self.notebook = aui.AuiNotebook(
            self.pnlMain, -1, size=wx.Size(480, 600),
            agwStyle=aui.AUI_NB_TAB_MOVE | aui.AUI_NB_CLOSE_ON_ACTIVE_TAB)

        #self.notebook.SetArtProvider(PsychopyTabArt())
        # Add editor panel
        self.paneManager.AddPane(self.notebook, aui.AuiPaneInfo().
                                 Name("Editor").
                                 Caption(_translate("Editor")).
                                 BestSize((480, 600)).
                                 Floatable(False).
                                 Movable(False).
                                 Center().PaneBorder(False).  # 'center panes' expand
                                 CloseButton(False).
                                 MaximizeButton(True))
        self.notebook.SetFocus()
        # Link functions
        self.notebook.SetDropTarget(FileDropTarget(targetFrame=self.pnlMain))
        self.notebook.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.fileClose)
        self.notebook.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.pageChanged)
        self.SetDropTarget(FileDropTarget(targetFrame=self.pnlMain))
        self.Bind(wx.EVT_DROP_FILES, self.filesDropped)
        self.Bind(wx.EVT_FIND, self.OnFindNext)
        self.Bind(wx.EVT_FIND_NEXT, self.OnFindNext)
        #self.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)
        self.Bind(wx.EVT_END_PROCESS, self.onProcessEnded)

        # take files from arguments and append the previously opened files
        filename = ""
        if files not in [None, [], ()]:
            for filename in files:
                if not os.path.isfile(filename):
                    continue
                self.setCurrentDoc(filename, keepHidden=True)

        # Create shelf notebook
        self.shelf = aui.AuiNotebook(self.pnlMain, wx.ID_ANY, size=wx.Size(600, 600), agwStyle=aui.AUI_NB_CLOSE_ON_ALL_TABS)
        #self.shelf.SetArtProvider(PsychopyTabArt())
        # Create shell
        self._useShell = None
        if haveCode:
            useDefaultShell = True
            if self.prefs['preferredShell'].lower() == 'ipython':
                try:
                    # Try to use iPython
                    from IPython.gui.wx.ipython_view import IPShellWidget
                    self.shell = IPShellWidget(self)
                    useDefaultShell = False
                    self._useShell = 'ipython'
                except Exception:
                    msg = _translate('IPython failed as shell, using pyshell'
                                     ' (IPython v0.12 can fail on wx)')
                    logging.warn(msg)
            if useDefaultShell:
                # Default to Pyshell if iPython fails
                self.shell = PsychopyPyShell(self)
                self._useShell = 'pyshell'
            # Add shell to output pane
            self.shell.SetName("PythonShell")
            self.shelf.AddPage(self.shell, _translate('Shell'))
            # Hide close button
            for i in range(self.shelf.GetPageCount()):
                self.shelf.SetCloseButton(i, False)
        # Add shelf panel
        self.paneManager.AddPane(self.shelf,
                                 aui.AuiPaneInfo().
                                 Name("Shelf").
                                 Caption(_translate("Shelf")).
                                 BestSize((600, 250)).PaneBorder(False).
                                 Floatable(False).
                                 Movable(True).
                                 BottomDockable(True).TopDockable(True).
                                 CloseButton(False).
                                 Bottom())
        self._applyAppTheme()
        if 'pavloviaSync' in self.btnHandles:
            self.toolbar.EnableTool(self.btnHandles['pavloviaSync'].Id, bool(self.filename))
        self.unitTestFrame = None

        # Link to Runner output
        if self.app.runner is None:
            self.app.showRunner()
        self.outputWindow = self.app.runner.stdOut
        self.outputWindow.write(_translate('Welcome to PsychoPy3!') + '\n')
        self.outputWindow.write("v%s\n" % self.app.version)

        # Manage perspective
        if (self.appData['auiPerspective'] and
                'Shelf' in self.appData['auiPerspective']):
            self.paneManager.LoadPerspective(self.appData['auiPerspective'])
            self.paneManager.GetPane('SourceAsst').Caption(_translate("Source Assistant"))
            self.paneManager.GetPane('Editor').Caption(_translate("Editor"))
        else:
            self.SetMinSize(wx.Size(400, 600))  # min size for whole window
            self.Fit()
        # Update panes PsychopyToolbar
        isExp = filename.endswith(".py") or filename.endswith(".psyexp")

        # if the toolbar is done then adjust buttons
        if hasattr(self, 'cdrBtnRunner'):
            self.toolbar.EnableTool(self.cdrBtnRunner.Id, isExp)
            self.toolbar.EnableTool(self.cdrBtnRun.Id, isExp)
        # Hide panels as specified
        self.paneManager.GetPane("SourceAsst").Show(self.prefs['showSourceAsst'])
        self.paneManager.GetPane("Shelf").Show(self.prefs['showOutput'])
        self.paneManager.Update()
        #self.chkShowAutoComp.Check(self.prefs['autocomplete'])
        self.SendSizeEvent()
        self.app.trackFrame(self)

    @property
    def useAutoComp(self):
        """Show autocomplete while typing."""
        return self.prefs['autocomplete']

    def GetAuiManager(self):
        return self.paneManager

    def outputContextMenu(self, event):
        """Custom context menu for output window.

        Provides menu items to clear all, select all and copy selected text."""
        if not hasattr(self, "outputMenuID1"):
            self.outputMenuID1 = wx.NewId()
            self.outputMenuID2 = wx.NewId()
            self.outputMenuID3 = wx.NewId()

            self.Bind(wx.EVT_MENU, self.outputClear, id=self.outputMenuID1)
            self.Bind(wx.EVT_MENU, self.outputSelectAll, id=self.outputMenuID2)
            self.Bind(wx.EVT_MENU, self.outputCopy, id=self.outputMenuID3)

        menu = wx.Menu()
        itemClear = wx.MenuItem(menu, self.outputMenuID1, "Clear All")
        itemSelect = wx.MenuItem(menu, self.outputMenuID2, "Select All")
        itemCopy = wx.MenuItem(menu, self.outputMenuID3, "Copy")

        menu.Append(itemClear)
        menu.AppendSeparator()
        menu.Append(itemSelect)
        menu.Append(itemCopy)
        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self.PopupMenu(menu)
        menu.Destroy()

    def outputClear(self, event):
        """Clears the output window in Coder"""
        self.outputWindow.Clear()

    def outputSelectAll(self, event):
        """Selects all text from the output window in Coder"""
        self.outputWindow.SelectAll()

    def outputCopy(self, event):
        """Copies all text from the output window in Coder"""
        self.outputWindow.Copy()

    def makeMenus(self):
        # ---Menus---#000000#FFFFFF-------------------------------------------
        menuBar = wx.MenuBar()
        # ---_file---#000000#FFFFFF-------------------------------------------
        self.fileMenu = wx.Menu()
        menuBar.Append(self.fileMenu, _translate('&File'))

        # create a file history submenu
        self.fileHistory = wx.FileHistory(maxFiles=10)
        self.recentFilesMenu = wx.Menu()
        self.fileHistory.UseMenu(self.recentFilesMenu)
        for filename in self.appData['fileHistory']:
            self.fileHistory.AddFileToHistory(filename)
        self.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory,
                  id=wx.ID_FILE1, id2=wx.ID_FILE9)

        # add items to file menu
        keyCodes = self.app.keys
        menu = self.fileMenu
        menu.Append(wx.ID_NEW, _translate("&New\t%s") % keyCodes['new'])
        menu.Append(wx.ID_OPEN, _translate("&Open...\t%s") % keyCodes['open'])
        menu.AppendSubMenu(self.recentFilesMenu, _translate("Open &Recent"))
        menu.Append(wx.ID_SAVE,
                    _translate("&Save\t%s") % keyCodes['save'],
                    _translate("Save current file"))
        menu.Append(wx.ID_SAVEAS,
                    _translate("Save &as...\t%s") % keyCodes['saveAs'],
                    _translate("Save current python file as..."))
        menu.Append(wx.ID_CLOSE,
                    _translate("&Close file\t%s") % keyCodes['close'],
                    _translate("Close current file"))
        menu.Append(wx.ID_CLOSE_ALL,
                    _translate("Close all files"),
                    _translate("Close all files in the editor."))
        menu.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.fileNew, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.fileOpen, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.fileSave, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.fileSaveAs, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.fileClose, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.fileCloseAll, id=wx.ID_CLOSE_ALL)
        item = menu.Append(wx.ID_ANY,
                           _translate("Print\t%s") % keyCodes['print'])
        self.Bind(wx.EVT_MENU, self.filePrint, id=item.GetId())
        menu.AppendSeparator()
        msg = _translate("&Preferences\t%s")
        item = menu.Append(wx.ID_PREFERENCES,
                           msg % keyCodes['preferences'])
        self.Bind(wx.EVT_MENU, self.app.showPrefs, id=item.GetId())
        # item = menu.Append(wx.NewId(), "Plug&ins")
        # self.Bind(wx.EVT_MENU, self.pluginManager, id=item.GetId())
        # -------------Close coder frame
        menu.AppendSeparator()
        msg = _translate("Close PsychoPy Coder")
        item = menu.Append(wx.ID_ANY, msg)
        self.Bind(wx.EVT_MENU, self.closeFrame, id=item.GetId())
        # -------------quit
        menu.AppendSeparator()
        menu.Append(wx.ID_EXIT,
                    _translate("&Quit\t%s") % keyCodes['quit'],
                    _translate("Terminate the program"))
        self.Bind(wx.EVT_MENU, self.quit, id=wx.ID_EXIT)

        # ---_edit---#000000#FFFFFF-------------------------------------------
        self.editMenu = wx.Menu()
        menu = self.editMenu
        menuBar.Append(self.editMenu, _translate('&Edit'))
        menu.Append(wx.ID_CUT, _translate("Cu&t\t%s") % keyCodes['cut'])
        self.Bind(wx.EVT_MENU, self.cut, id=wx.ID_CUT)
        menu.Append(wx.ID_COPY, _translate("&Copy\t%s") % keyCodes['copy'])
        self.Bind(wx.EVT_MENU, self.copy, id=wx.ID_COPY)
        menu.Append(wx.ID_PASTE, _translate("&Paste\t%s") % keyCodes['paste'])
        self.Bind(wx.EVT_MENU, self.paste, id=wx.ID_PASTE)
        hnt = _translate("Duplicate the current line (or current selection)")
        menu.Append(wx.ID_DUPLICATE,
                    _translate("&Duplicate\t%s") % keyCodes['duplicate'],
                    hnt)
        self.Bind(wx.EVT_MENU, self.duplicateLine, id=wx.ID_DUPLICATE)

        menu.AppendSeparator()
        item = menu.Append(wx.ID_ANY,
                           _translate("&Find\t%s") % keyCodes['find'])
        self.Bind(wx.EVT_MENU, self.OnFindOpen, id=item.GetId())
        item = menu.Append(wx.ID_ANY,
                           _translate("Find &Next\t%s") % keyCodes['findAgain'])
        self.Bind(wx.EVT_MENU, self.OnFindNext, id=item.GetId())

        menu.AppendSeparator()
        item = menu.Append(wx.ID_ANY,
                           _translate("Comment\t%s") % keyCodes['comment'],
                           _translate("Comment selected lines"),
                           wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.commentSelected, id=item.GetId())
        item = menu.Append(wx.ID_ANY,
                           _translate("Uncomment\t%s") % keyCodes['uncomment'],
                           _translate("Un-comment selected lines"),
                           wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.uncommentSelected, id=item.GetId())

        item = menu.Append(wx.ID_ANY,
                           _translate("Toggle comment\t%s") % keyCodes['toggle comment'],
                           _translate("Toggle commenting of selected lines"),
                           wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.toggleComments, id=item.GetId())

        item = menu.Append(wx.ID_ANY,
                           _translate("Toggle fold\t%s") % keyCodes['fold'],
                           _translate("Toggle folding of top level"),
                           wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.foldAll, id=item.GetId())

        menu.AppendSeparator()
        item = menu.Append(wx.ID_ANY,
                           _translate("Indent selection\t%s") % keyCodes['indent'],
                           _translate("Increase indentation of current line"),
                           wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.indent, id=item.GetId())
        item = menu.Append(wx.ID_ANY,
                           _translate("Dedent selection\t%s") % keyCodes['dedent'],
                           _translate("Decrease indentation of current line"),
                           wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.dedent, id=item.GetId())
        hnt = _translate("Try to indent to the correct position w.r.t. "
                         "last line")
        item = menu.Append(wx.ID_ANY,
                           _translate("SmartIndent\t%s") % keyCodes['smartIndent'],
                           hnt,
                           wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.smartIndent, id=item.GetId())

        menu.AppendSeparator()
        menu.Append(wx.ID_UNDO,
                    _translate("Undo\t%s") % self.app.keys['undo'],
                    _translate("Undo last action"),
                    wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.undo, id=wx.ID_UNDO)
        menu.Append(wx.ID_REDO,
                    _translate("Redo\t%s") % self.app.keys['redo'],
                    _translate("Redo last action"),
                    wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.redo, id=wx.ID_REDO)

        menu.AppendSeparator()
        item = menu.Append(wx.ID_ANY,
                           _translate("Enlarge font\t%s") % self.app.keys['enlargeFont'],
                           _translate("Increase font size"),
                           wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.bigFont, id=item.GetId())
        item = menu.Append(wx.ID_ANY,
                           _translate("Shrink font\t%s") % self.app.keys['shrinkFont'],
                           _translate("Decrease font size"),
                           wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.smallFont, id=item.GetId())
        item = menu.Append(wx.ID_ANY,
                           _translate("Reset font"),
                           _translate("Return fonts to their original size."),
                           wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.resetFont, id=item.GetId())
        menu.AppendSeparator()

        # submenu for changing working directory
        sm = wx.Menu()
        item = sm.Append(
            wx.ID_ANY,
            _translate("Editor file location"),
            "",
            wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.onSetCWDFromEditor, id=item.GetId())
        item = sm.Append(
            wx.ID_ANY,
            _translate("File browser pane location"),
            "",
            wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.onSetCWDFromBrowserPane, id=item.GetId())
        sm.AppendSeparator()
        item = sm.Append(
            wx.ID_ANY,
            _translate("Choose directory ..."),
            "",
            wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.onSetCWDFromBrowse, id=item.GetId())
        menu.Append(wx.ID_ANY, _translate("Change working directory to ..."), sm)

        # ---_view---#000000#FFFFFF-------------------------------------------
        self.viewMenu = wx.Menu()
        menu = self.viewMenu
        menuBar.Append(self.viewMenu, _translate('&View'))

        # Frame switcher (legacy
        item = menu.Append(wx.ID_ANY,
                           _translate("Go to Builder view"),
                           _translate("Go to the Builder view"))
        self.Bind(wx.EVT_MENU, self.app.showBuilder, id=item.GetId())

        item = menu.Append(wx.ID_ANY,
                           _translate("Open Runner view"),
                           _translate("Open the Runner view"))
        self.Bind(wx.EVT_MENU, self.app.showRunner, item)
        menu.AppendSeparator()
        # Panel switcher
        self.panelsMenu = wx.Menu()
        menu.AppendSubMenu(self.panelsMenu,
                           _translate("Panels"))
        # output window
        key = keyCodes['toggleOutputPanel']
        hint = _translate("Shows the output and shell panes (and starts "
                          "capturing stdout)")
        self.outputChk = self.panelsMenu.AppendCheckItem(
            wx.ID_ANY, _translate("&Output/Shell\t%s") % key, hint)
        self.outputChk.Check(self.prefs['showOutput'])
        self.Bind(wx.EVT_MENU, self.setOutputWindow, id=self.outputChk.GetId())
        # source assistant
        hint = _translate("Hide/show the source assistant pane.")
        self.sourceAsstChk = self.panelsMenu.AppendCheckItem(wx.ID_ANY,
                                                  _translate("Source Assistant"),
                                                  hint)
        self.sourceAsstChk.Check(self.prefs['showSourceAsst'])
        self.Bind(wx.EVT_MENU, self.setSourceAsst,
                  id=self.sourceAsstChk.GetId())

        # indent guides
        key = keyCodes['toggleIndentGuides']
        hint = _translate("Shows guides in the editor for your "
                          "indentation level")
        self.indentGuideChk = menu.AppendCheckItem(wx.ID_ANY,
                                                   _translate("&Indentation guides\t%s") % key,
                                                   hint)
        self.indentGuideChk.Check(self.appData['showIndentGuides'])
        self.Bind(wx.EVT_MENU, self.setShowIndentGuides, self.indentGuideChk)
        # whitespace
        key = keyCodes['toggleWhitespace']
        hint = _translate("Show whitespace characters in the code")
        self.showWhitespaceChk = menu.AppendCheckItem(wx.ID_ANY,
                                                      _translate("&Whitespace\t%s") % key,
                                                      hint)
        self.showWhitespaceChk.Check(self.appData['showWhitespace'])
        self.Bind(wx.EVT_MENU, self.setShowWhitespace, self.showWhitespaceChk)
        # EOL markers
        key = keyCodes['toggleEOLs']
        hint = _translate("Show End Of Line markers in the code")
        self.showEOLsChk = menu.AppendCheckItem(
            wx.ID_ANY,
            _translate("Show &EOLs\t%s") % key,
            hint)
        self.showEOLsChk.Check(self.appData['showEOLs'])
        self.Bind(wx.EVT_MENU, self.setShowEOLs, id=self.showEOLsChk.GetId())
        menu.AppendSeparator()
        # Theme Switcher
        self.themesMenu = ThemeSwitcher(self)
        menu.AppendSubMenu(self.themesMenu,
                           _translate("Themes"))

        # menu.Append(ID_UNFOLDALL, "Unfold All\tF3",
        #   "Unfold all lines", wx.ITEM_NORMAL)
        # self.Bind(wx.EVT_MENU,  self.unfoldAll, id=ID_UNFOLDALL)
        # ---_tools---#000000#FFFFFF------------------------------------------
        self.toolsMenu = wx.Menu()
        menu = self.toolsMenu
        menuBar.Append(self.toolsMenu, _translate('&Tools'))
        item = menu.Append(wx.ID_ANY,
                           _translate("Monitor Center"),
                           _translate("To set information about your monitor"))
        self.Bind(wx.EVT_MENU, self.app.openMonitorCenter, id=item.GetId())
        # self.analyseAutoChk = self.toolsMenu.AppendCheckItem(self.IDs.analyzeAuto,
        #   "Analyse on file save/open",
        #   "Automatically analyse source (for autocomplete etc...).
        #   Can slow down the editor on a slow machine or with large files")
        # self.Bind(wx.EVT_MENU,  self.setAnalyseAuto, id=self.IDs.analyzeAuto)
        # self.analyseAutoChk.Check(self.prefs['analyseAuto'])
        # self.toolsMenu.Append(self.IDs.analyzeNow,
        #   "Analyse now\t%s" %self.app.keys['analyseCode'],
        #   "Force a reananalysis of the code now")
        # self.Bind(wx.EVT_MENU,  self.analyseCodeNow, id=self.IDs.analyzeNow)

        self.IDs.cdrRun = menu.Append(wx.ID_ANY,
                                      _translate("Run\t%s") % keyCodes['runScript'],
                                      _translate("Run the current script")).GetId()
        self.Bind(wx.EVT_MENU, self.runFile, id=self.IDs.cdrRun)
        item = menu.Append(wx.ID_ANY,
                                      _translate("Send to runner\t%s") % keyCodes['runnerScript'],
                                      _translate("Send current script to runner")).GetId()
        self.Bind(wx.EVT_MENU, self.runFile, id=item)

        menu.AppendSeparator()
        item = menu.Append(wx.ID_ANY,
                           _translate("PsychoPy updates..."),
                           _translate("Update PsychoPy to the latest, or a specific, version"))
        self.Bind(wx.EVT_MENU, self.app.openUpdater, id=item.GetId())
        item = menu.Append(wx.ID_ANY,
                           _translate("Benchmark wizard"),
                           _translate("Check software & hardware, generate report"))
        self.Bind(wx.EVT_MENU, self.app.benchmarkWizard, id=item.GetId())
        item = menu.Append(wx.ID_ANY,
                           _translate("csv from psydat"),
                           _translate("Create a .csv file from an existing .psydat file"))
        self.Bind(wx.EVT_MENU, self.app.csvFromPsydat, id=item.GetId())

        if self.appPrefs['debugMode']:
            item = menu.Append(wx.ID_ANY,
                               _translate("Unit &testing...\tCtrl-T"),
                               _translate("Show dialog to run unit tests"))
            self.Bind(wx.EVT_MENU, self.onUnitTests, id=item.GetId())

        # ---_demos---#000000#FFFFFF------------------------------------------
        self.demosMenu = wx.Menu()
        self.demos = {}
        menuBar.Append(self.demosMenu, _translate('&Demos'))
        # for demos we need a dict of {event ID: filename, ...}
        # add folders
        folders = glob.glob(os.path.join(self.paths['demos'], 'coder', '*'))
        for folder in folders:
            # if it isn't a folder then skip it
            if (not os.path.isdir(folder)):
                continue
            # otherwise create a submenu
            folderDisplayName = os.path.split(folder)[-1]
            if folderDisplayName.startswith('_'):
                continue  # don't include private folders
            if folderDisplayName in _localized:
                folderDisplayName = _localized[folderDisplayName]
            submenu = wx.Menu()
            self.demosMenu.AppendSubMenu(submenu, folderDisplayName)

            # find the files in the folder (search two levels deep)
            demoList = glob.glob(os.path.join(folder, '*.py'))
            demoList += glob.glob(os.path.join(folder, '*', '*.py'))
            demoList += glob.glob(os.path.join(folder, '*', '*', '*.py'))

            demoList.sort()

            for thisFile in demoList:
                shortname = thisFile.split(os.path.sep)[-1]
                if shortname == "run.py":
                    # file is just "run" so get shortname from directory name
                    # instead
                    shortname = thisFile.split(os.path.sep)[-2]
                elif shortname.startswith('_'):
                    continue  # remove any 'private' files
                item = submenu.Append(wx.ID_ANY, shortname)
                thisID = item.GetId()
                self.demos[thisID] = thisFile
                self.Bind(wx.EVT_MENU, self.loadDemo, id=thisID)
        # also add simple demos to root
        self.demosMenu.AppendSeparator()
        demos = glob.glob(os.path.join(self.paths['demos'], 'coder', '*.py'))
        for thisFile in demos:
            shortname = thisFile.split(os.path.sep)[-1]
            if shortname.startswith('_'):
                continue  # remove any 'private' files
            item = self.demosMenu.Append(wx.ID_ANY, shortname)
            thisID = item.GetId()
            self.demos[thisID] = thisFile
            self.Bind(wx.EVT_MENU, self.loadDemo, id=thisID)

        # ---_shell---#000000#FFFFFF--------------------------------------------
        # self.shellMenu = wx.Menu()
        # menu = self.shellMenu
        # menuBar.Append(menu, '&Shell')
        #
        # item = menu.Append(
        #     wx.ID_ANY,
        #     "Run selected line\tCtrl+Enter",
        #     "Pushes selected lines to the shell and executes them.")
        # self.Bind(wx.EVT_MENU, self.onPushLineToShell, id=item.GetId())

        # ---_projects---#000000#FFFFFF---------------------------------------
        self.pavloviaMenu = psychopy.app.pavlovia_ui.menu.PavloviaMenu(parent=self)
        menuBar.Append(self.pavloviaMenu, _translate("Pavlovia.org"))

        # ---_window---#000000#FFFFFF-----------------------------------------
        self.windowMenu = FrameSwitcher(self)
        menuBar.Append(self.windowMenu,
                    _translate("Window"))

        # ---_help---#000000#FFFFFF-------------------------------------------
        self.helpMenu = wx.Menu()
        menuBar.Append(self.helpMenu, _translate('&Help'))
        item = self.helpMenu.Append(wx.ID_ANY,
                                    _translate("&PsychoPy Homepage"),
                                    _translate("Go to the PsychoPy homepage"))
        self.Bind(wx.EVT_MENU, self.app.followLink, id=item.GetId())
        self.app.urls[item.GetId()] = self.app.urls['psychopyHome']
        item = self.helpMenu.Append(wx.ID_ANY,
                                    _translate("&PsychoPy Coder Tutorial"),
                                    _translate("Go to the online PsychoPy tutorial"))
        self.Bind(wx.EVT_MENU, self.app.followLink, id=item.GetId())
        self.app.urls[item.GetId()] = self.app.urls['coderTutorial']
        item = self.helpMenu.Append(wx.ID_ANY,
                                    _translate("&PsychoPy API (reference)"),
                                    _translate("Go to the online PsychoPy reference manual"))
        self.Bind(wx.EVT_MENU, self.app.followLink, id=item.GetId())
        self.app.urls[item.GetId()] = self.app.urls['psychopyReference']
        self.helpMenu.AppendSeparator()
        item = self.helpMenu.Append(wx.ID_ANY,
                                    _translate("&System Info..."),
                                    _translate("Get system information."))
        self.Bind(wx.EVT_MENU, self.app.showSystemInfo, id=item.GetId())
        self.helpMenu.AppendSeparator()
        # on mac this will move to the application menu
        self.helpMenu.Append(wx.ID_ABOUT,
                             _translate("&About..."),
                             _translate("About PsychoPy"))
        self.Bind(wx.EVT_MENU, self.app.showAbout, id=wx.ID_ABOUT)

        item = self.helpMenu.Append(wx.ID_ANY,
                                    _translate("&News..."),
                                    _translate("News"))
        self.Bind(wx.EVT_MENU, self.app.showNews, id=item.GetId())

        self.SetMenuBar(menuBar)

    def makeStatusBar(self):
        """Make the status bar for Coder."""
        self.statusBar = wx.StatusBar(self, wx.ID_ANY)
        self.statusBar.SetFieldsCount(4)
        self.statusBar.SetStatusWidths([-2, 160, 160, 160])

        self.SetStatusBar(self.statusBar)

    def onSetCWDFromEditor(self, event):
        """Set the current working directory to the location of the current file
        in the editor."""
        if self.currentDoc is None:
            dlg = wx.MessageDialog(
                self,
                "Cannot set working directory, no document open in editor.",
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            event.Skip()
            return

        if not os.path.isabs(self.currentDoc.filename):
            dlg = wx.MessageDialog(
                self,
                "Cannot change working directory to location of file `{}`. It"
                " needs to be saved first.".format(self.currentDoc.filename),
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            event.Skip()
            return

        # split the file off the path
        cwdpath, _ = os.path.split(self.currentDoc.filename)

        # set the working directory
        try:
            os.chdir(cwdpath)
        except OSError:
            dlg = wx.MessageDialog(
                self,
                "Cannot set `{}` as working directory.".format(cwdpath),
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            event.Skip()
            return

        if hasattr(self, 'fileBrowserWindow'):
            dlg = wx.MessageDialog(
                self,
                "Working directory changed, would you like to display it in "
                "the file browser pane?",
                'Question', style=wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)

            if dlg.ShowModal() == wx.ID_YES:
                self.fileBrowserWindow.gotoDir(cwdpath)

    def onSetCWDFromBrowserPane(self, event):
        """Set the current working directory by browsing for it."""

        if not hasattr(self, 'fileBrowserWindow'):
            dlg = wx.MessageDialog(
                self,
                "Cannot set working directory, file browser pane unavailable.",
                "Error",
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            event.Skip()

        cwdpath = self.fileBrowserWindow.currentPath
        try:
            os.chdir(cwdpath)
        except OSError:
            dlg = wx.MessageDialog(
                self,
                "Cannot set `{}` as working directory.".format(cwdpath),
                "Error",
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            event.Skip()
            return

    def onSetCWDFromBrowse(self, event):
        """Set the current working directory by browsing for it."""
        dlg = wx.DirDialog(self, "Choose directory ...", "",
                           wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)

        if dlg.ShowModal() == wx.ID_OK:
            cwdpath = dlg.GetPath()
            dlg.Destroy()
        else:
            dlg.Destroy()
            event.Skip()  # user canceled
            return

        try:
            os.chdir(cwdpath)
        except OSError:
            dlg = wx.MessageDialog(
                self,
                "Cannot set `{}` as working directory.".format(cwdpath),
                "Error",
                style=wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            event.Skip()
            return

        if hasattr(self, 'fileBrowserWindow'):
            dlg = wx.MessageDialog(
                self,
                "Working directory changed, would you like to display it in "
                "the file browser pane?",
                'Question', style=wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)

            if dlg.ShowModal() == wx.ID_YES:
                self.fileBrowserWindow.gotoDir(cwdpath)

    # mdc - potential feature for the future
    # def onPushLineToShell(self, event=None):
    #     """Run a line in the code editor in the shell."""
    #     if self.currentDoc is None:
    #         return
    #
    #     lineno = self.currentDoc.GetCurrentLine()
    #     cmdText = self.currentDoc.GetLineText(lineno)
    #
    #     if self._useShell == 'pyshell':
    #         self.shell.run(cmdText, prompt=False)
    #
    #     self.currentDoc.GotoLine(lineno + 1)

    def onIdle(self, event):
        # check the script outputs to see if anything has been written to
        # stdout
        if self.scriptProcess is not None:
            if self.scriptProcess.IsInputAvailable():
                stream = self.scriptProcess.GetInputStream()
                text = stream.read()
                self.outputWindow.write(text)
            if self.scriptProcess.IsErrorAvailable():
                stream = self.scriptProcess.GetErrorStream()
                text = stream.read()
                self.outputWindow.write(text)
        # check if we're in the same place as before
        if self.currentDoc is not None:
            if hasattr(self.currentDoc, 'GetCurrentPos'):
                pos = self.currentDoc.GetCurrentPos()
                if self._lastCaretPos != pos:
                    self.currentDoc.OnUpdateUI(evt=None)
                    self._lastCaretPos = pos
            last = self.fileStatusLastChecked
            interval = self.fileStatusCheckInterval
            if time.time() - last > interval and not self.showingReloadDialog:
                if not self.expectedModTime(self.currentDoc):
                    self.showingReloadDialog = True
                    filename = os.path.basename(self.currentDoc.filename)
                    msg = _translate("'%s' was modified outside of PsychoPy:\n\n"
                                     "Reload (without saving)?") % filename
                    dlg = dialogs.MessageDialog(self, message=msg, type='Warning')
                    if dlg.ShowModal() == wx.ID_YES:
                        self.statusBar.SetStatusText(_translate('Reloading file'))
                        self.fileReload(event,
                                        filename=self.currentDoc.filename,
                                        checkSave=False)
                    self.showingReloadDialog = False
                    self.statusBar.SetStatusText('')
                    dlg.Destroy()
                self.fileStatusLastChecked = time.time()

    def pageChanged(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        self.currentDoc = self.notebook.GetPage(new)
        self.app.updateWindowMenu()
        self.setFileModified(self.currentDoc.UNSAVED)
        self.SetLabel('%s - PsychoPy Coder' % self.currentDoc.filename)

        if hasattr(self, 'structureWindow'):
            self.currentDoc.analyseScript()

        self.statusBar.SetStatusText(self.currentDoc.getFileType(), 2)

        # todo: reduce redundancy w.r.t OnIdle()
        if not self.expectedModTime(self.currentDoc):
            filename = os.path.basename(self.currentDoc.filename)
            msg = _translate("'%s' was modified outside of PsychoPy:\n\n"
                             "Reload (without saving)?") % filename
            dlg = dialogs.MessageDialog(self, message=msg, type='Warning')
            if dlg.ShowModal() == wx.ID_YES:
                self.statusBar.SetStatusText(_translate('Reloading file'))
                self.fileReload(event,
                                filename=self.currentDoc.filename,
                                checkSave=False)
                self.setFileModified(False)
            self.statusBar.SetStatusText('')
            dlg.Destroy()

    def filesDropped(self, event):
        fileList = event.GetFiles()
        for filename in fileList:
            if os.path.isfile(filename):
                if filename.lower().endswith('.psyexp'):
                    self.app.newBuilderFrame(filename)
                else:
                    self.setCurrentDoc(filename)

    # def pluginManager(self, evt=None, value=True):
    #     """Show the plugin manger frame."""
    #     PluginManagerFrame(self).ShowModal()

    def OnFindOpen(self, event):
        # open the find dialog if not already open
        if self.findDlg is not None:
            return
        win = wx.Window.FindFocus()
        self.findDlg = wx.FindReplaceDialog(win, self.findData, "Find",
                                            wx.FR_NOWHOLEWORD)
        self.findDlg.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)
        self.findDlg.Show()

    def OnFindNext(self, event):
        # find the next occurence of text according to last find dialogue data
        if not self.findData.GetFindString():
            self.OnFindOpen(event)
            return
        self.currentDoc.DoFindNext(self.findData, self.findDlg)
        # if self.findDlg is not None:
        #     self.OnFindClose(None)

    def OnFindClose(self, event):
        self.findDlg = None

    def OnFileHistory(self, evt=None):
        # get the file based on the menu ID
        fileNum = evt.GetId() - wx.ID_FILE1
        path = self.fileHistory.GetHistoryFile(fileNum)
        self.setCurrentDoc(path)  # load the file
        # add it back to the history so it will be moved up the list
        self.fileHistory.AddFileToHistory(path)

    def gotoLine(self, filename=None, line=0):
        # goto a specific line in a specific file and select all text in it
        self.setCurrentDoc(filename)
        self.currentDoc.EnsureVisible(line)
        self.currentDoc.GotoLine(line)
        endPos = self.currentDoc.GetCurrentPos()

        self.currentDoc.GotoLine(line - 1)
        stPos = self.currentDoc.GetCurrentPos()

        self.currentDoc.SetSelection(stPos, endPos)

    def getOpenFilenames(self):
        """Return the full filename of each open tab"""
        names = []
        for ii in range(self.notebook.GetPageCount()):
            names.append(self.notebook.GetPage(ii).filename)
        return names

    def quit(self, event):
        self.app.quit()

    def checkSave(self):
        """Loop through all open files checking whether they need save
        """
        for ii in range(self.notebook.GetPageCount()):
            doc = self.notebook.GetPage(ii)
            filename = doc.filename
            if doc.UNSAVED:
                self.notebook.SetSelection(ii)  # fetch that page and show it
                # make sure frame is at front
                self.Show(True)
                self.Raise()
                self.app.SetTopWindow(self)
                # then bring up dialog
                msg = _translate('Save changes to %s before quitting?')
                dlg = dialogs.MessageDialog(self, message=msg % filename,
                                            type='Warning')
                resp = dlg.ShowModal()
                sys.stdout.flush()
                dlg.Destroy()
                if resp == wx.ID_CANCEL:
                    return 0  # return, don't quit
                elif resp == wx.ID_YES:
                    self.fileSave()  # save then quit
                elif resp == wx.ID_NO:
                    pass  # don't save just quit
        return 1

    def closeFrame(self, event=None, checkSave=True):
        """Close open windows, update prefs.appData (but don't save)
        and either close the frame or hide it
        """
        if (len(self.app.getAllFrames(frameType="builder")) == 0
                and len(self.app.getAllFrames(frameType="runner")) == 0
                and sys.platform != 'darwin'):
            if not self.app.quitting:
                # send the event so it can be vetoed if neded
                self.app.quit(event)
                return  # app.quit() will have closed the frame already

        # check all files before initiating close of any
        if checkSave and self.checkSave() == 0:
            return 0  # this signals user cancelled

        wasShown = self.IsShown()
        self.Hide()  # ugly to see it close all the files independently

        # store current appData
        self.appData['prevFiles'] = []
        currFiles = self.getOpenFilenames()
        for thisFileName in currFiles:
            self.appData['prevFiles'].append(thisFileName)
        # get size and window layout info
        if self.IsIconized():
            self.Iconize(False)  # will return to normal mode to get size info
            self.appData['state'] = 'normal'
        elif self.IsMaximized():
            # will briefly return to normal mode to get size info
            self.Maximize(False)
            self.appData['state'] = 'maxim'
        else:
            self.appData['state'] = 'normal'
        self.appData['auiPerspective'] = self.paneManager.SavePerspective()
        self.appData['winW'], self.appData['winH'] = self.GetSize()
        self.appData['winX'], self.appData['winY'] = self.GetPosition()
        if sys.platform == 'darwin':
            # for some reason mac wxpython <=2.8 gets this wrong (toolbar?)
            self.appData['winH'] -= 39
        self.appData['fileHistory'] = []
        for ii in range(self.fileHistory.GetCount()):
            self.appData['fileHistory'].append(
                self.fileHistory.GetHistoryFile(ii))

        # as of wx3.0 the AUI manager needs to be uninitialised explicitly
        self.paneManager.UnInit()

        self.app.forgetFrame(self)
        self.Destroy()
        self.app.coder = None
        self.app.updateWindowMenu()

    def filePrint(self, event=None):
        pr = Printer()
        docName = self.currentDoc.filename
        text = open(docName, 'r').read()
        pr.Print(text, docName)

    def fileNew(self, event=None, filepath=""):
        self.setCurrentDoc(filepath)

    def fileReload(self, event, filename=None, checkSave=False):
        if filename is None:
            return  # should raise an exception

        docId = self.findDocID(filename)
        if docId == -1:
            return
        doc = self.notebook.GetPage(docId)

        # is the file still there
        if os.path.isfile(filename):
            with io.open(filename, 'r', encoding='utf-8-sig') as f:
                doc.SetText(f.read())
            doc.fileModTime = os.path.getmtime(filename)
            doc.EmptyUndoBuffer()
            doc.Colourise(0, -1)
            doc.UNSAVED = False
        else:
            # file was removed after we found the changes, lets
            # give the user a chance to save his file.
            self.UNSAVED = True

        if doc == self.currentDoc and hasattr(self, 'cdrBtnSave'):
            self.cdrBtnSave.Enable(doc.UNSAVED)

        self.statusBar.SetStatusText(_translate('Analyzing code'))
        if hasattr(self, 'structureWindow'):
            self.currentDoc.analyseScript()
        self.statusBar.SetStatusText('')

    @property
    def filename(self):
        if self.currentDoc:
            return self.currentDoc.filename

    def findDocID(self, filename):
        # find the ID of the current doc
        for ii in range(self.notebook.GetPageCount()):
            if self.notebook.GetPage(ii).filename == filename:
                return ii
        return -1

    def setCurrentDoc(self, filename, keepHidden=False):
        # check if this file is already open
        docID = self.findDocID(filename)
        readOnlyPref = 'readonly' in self.app.prefs.coder
        readonly = readOnlyPref and self.app.prefs.coder['readonly']
        if docID >= 0:
            self.currentDoc = self.notebook.GetPage(docID)
            self.notebook.SetSelection(docID)
        else:  # create new page and load document
            # if there is only a placeholder document then close it
            if len(self.getOpenFilenames()) == 1:
                if (len(self.currentDoc.GetText()) == 0 and
                        self.currentDoc.filename.startswith('untitled')):
                    self.fileClose(self.currentDoc.filename)

            # load text from document
            if os.path.isfile(filename):
                try:
                    with io.open(filename, 'r', encoding='utf-8-sig') as f:
                        fileText = f.read()
                        newlines = f.newlines
                except UnicodeDecodeError:
                    dlg = dialogs.MessageDialog(self, message=_translate(
                        'Failed to open `{}`. Make sure that encoding of '
                        'the file is utf-8.').format(filename), type='Info')
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
            elif filename == '':
                pass  # user requested a new document
            else:
                dlg = dialogs.MessageDialog(
                    self,
                    message='Failed to open {}. Not a file.'.format(filename),
                    type='Info')
                dlg.ShowModal()
                dlg.Destroy()
                return  # do nothing

            # create an editor window to put the text in
            p = self.currentDoc = CodeEditor(self.notebook, -1, frame=self,
                                             readonly=readonly)

            # load text
            if filename != '':
                # put the text in editor
                self.currentDoc.SetText(fileText)
                self.currentDoc.newlines = newlines
                del fileText  # delete the buffer
                self.currentDoc.fileModTime = os.path.getmtime(filename)
                self.fileHistory.AddFileToHistory(filename)
            else:
                # set name for an untitled document
                filename = 'untitled.py'
                allFileNames = self.getOpenFilenames()
                n = 1
                while filename in allFileNames:
                    filename = 'untitled%i.py' % n
                    n += 1

                # create modification time for in memory document
                self.currentDoc.fileModTime = time.ctime()

            self.currentDoc.EmptyUndoBuffer()

            path, shortName = os.path.split(filename)
            self.notebook.AddPage(p, shortName)
            nbIndex = len(self.getOpenFilenames()) - 1
            if isinstance(self.notebook, wx.Notebook):
                self.notebook.ChangeSelection(nbIndex)
            elif isinstance(self.notebook, aui.AuiNotebook):
                self.notebook.SetSelection(nbIndex)
            self.currentDoc.filename = filename

            self.currentDoc.setLexerFromFileName()  # chose the best lexer

            self.setFileModified(False)
            self.currentDoc.SetFocus()
            self.statusBar.SetStatusText(self.currentDoc.getFileType(), 2)

        self.SetLabel('%s - PsychoPy Coder' % self.currentDoc.filename)
        #if len(self.getOpenFilenames()) > 0:
        if hasattr(self, 'structureWindow'):
            self.statusBar.SetStatusText(_translate('Analyzing code'))
            self.currentDoc.analyseScript()
            self.statusBar.SetStatusText('')
        if not keepHidden:
            self.Show()  # if the user had closed the frame it might be hidden
        if readonly:
            self.currentDoc.SetReadOnly(True)
        self.currentDoc._applyAppTheme()
        isExp = filename.endswith(".py") or filename.endswith(".psyexp")

        # if the toolbar is done then adjust buttons
        if hasattr(self, 'cdrBtnRunner'):
            self.toolbar.EnableTool(self.cdrBtnRunner.Id, isExp)
            self.toolbar.EnableTool(self.cdrBtnRun.Id, isExp)
        if 'pavloviaSync' in self.btnHandles:
            self.toolbar.EnableTool(self.btnHandles['pavloviaSync'].Id, bool(self.filename))
        # update menu items
        self.pavloviaMenu.syncBtn.Enable(bool(self.filename))
        self.pavloviaMenu.newBtn.Enable(bool(self.filename))
        self.app.updateWindowMenu()

    def fileOpen(self, event=None, filename=None):
        if not filename:
            # get path of current file (empty if current file is '')
            if hasattr(self.currentDoc, 'filename'):
                initPath = os.path.split(self.currentDoc.filename)[0]
            else:
                initPath = ''
            dlg = wx.FileDialog(
                self, message=_translate("Open file ..."),
                defaultDir=initPath, style=wx.FD_OPEN
            )

            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                self.statusBar.SetStatusText(_translate('Loading file'))
            else:
                return -1

        if filename and os.path.isfile(filename):
            if filename.lower().endswith('.psyexp'):
                self.app.newBuilderFrame(fileName=filename)
            else:
                self.setCurrentDoc(filename)
                self.setFileModified(False)
        self.statusBar.SetStatusText('')

        # don't do this, this will add unwanted files to the task list - mdc
        # self.app.runner.addTask(fileName=filename)

    def expectedModTime(self, doc):
        # check for possible external changes to the file, based on
        # mtime-stamps
        if doc is None:
            return True  # we have no file loaded
        # files that don't exist DO have the expected mod-time
        filename = doc.filename
        if not os.path.exists(filename):
            return True
        if not os.path.isabs(filename):
            return True
        actualModTime = os.path.getmtime(filename)
        expectedModTime = doc.fileModTime
        if actualModTime != expectedModTime:
            msg = 'File %s modified outside of the Coder (IDE).' % filename
            print(msg)
            return False
        return True

    def fileSave(self, event=None, filename=None, doc=None):
        """Save a ``doc`` with a particular ``filename``.
        If ``doc`` is ``None`` then the current active doc is used.
        If the ``filename`` is ``None`` then the ``doc``'s current filename
        is used or a dlg is presented to get a new filename.
        """
        if hasattr(self.currentDoc, 'AutoCompActive'):
            if self.currentDoc.AutoCompActive():
                self.currentDoc.AutoCompCancel()

        if doc is None:
            doc = self.currentDoc
        if filename is None:
            filename = doc.filename
        if filename.startswith('untitled'):
            self.fileSaveAs(filename)
            # self.setFileModified(False) # done in save-as if saved; don't
            # want here if not saved there
        else:
            # here detect odd conditions, and set failToSave = True to try
            # 'Save-as' rather than 'Save'
            failToSave = False
            if not self.expectedModTime(doc) and os.path.exists(filename):
                msg = _translate("File appears to have been modified outside "
                                 "of PsychoPy:\n   %s\nOK to overwrite?")
                basefile = os.path.basename(doc.filename)
                dlg = dialogs.MessageDialog(self, message=msg % basefile,
                                            type='Warning')
                if dlg.ShowModal() != wx.ID_YES:
                    failToSave = True
                dlg.Destroy()
            if os.path.exists(filename) and not os.access(filename, os.W_OK):
                msg = _translate("File '%s' lacks write-permission:\n"
                                 "Will try save-as instead.")
                basefile = os.path.basename(doc.filename)
                dlg = dialogs.MessageDialog(self, message=msg % basefile,
                                            type='Info')
                dlg.ShowModal()
                failToSave = True
                dlg.Destroy()
            try:
                if failToSave:
                    raise IOError
                self.statusBar.SetStatusText(_translate('Saving file'))
                newlines = '\n'  # system default, os.linesep
                with io.open(filename, 'w', encoding='utf-8', newline=newlines) as f:
                    f.write(doc.GetText())
                self.setFileModified(False)
                doc.fileModTime = os.path.getmtime(filename)  # JRG
            except Exception:
                print("Unable to save %s... trying save-as instead." %
                      os.path.basename(doc.filename))
                self.fileSaveAs(filename)

        if analyseAuto and len(self.getOpenFilenames()) > 0:
            self.statusBar.SetStatusText(_translate('Analyzing current source code'))
            self.currentDoc.analyseScript()
        # reset status text
        self.statusBar.SetStatusText('')
        self.fileHistory.AddFileToHistory(filename)

    def fileSaveAs(self, event, filename=None, doc=None):
        """Save a ``doc`` with a new ``filename``, after presenting a dlg
        to get a new filename.

        If ``doc`` is ``None`` then the current active doc is used.

        If the ``filename`` is not ``None`` then this will be the initial
        value for the filename in the dlg.
        """
        # cancel autocomplete if active
        if self.currentDoc.AutoCompActive():
            self.currentDoc.AutoCompCancel()

        if doc is None:
            doc = self.currentDoc
            docId = self.notebook.GetSelection()
        else:
            docId = self.findDocID(doc.filename)
        if filename is None:
            filename = doc.filename
        # if we have an absolute path then split it
        initPath, filename = os.path.split(filename)
        # set wildcards; need strings to appear inside _translate
        if sys.platform != 'darwin':
            wildcard = _translate("Python scripts (*.py)|*.py|Text file "
                                  "(*.txt)|*.txt|Any file (*.*)|*.*")
        else:
            wildcard = _translate("Python scripts (*.py)|*.py|Text file "
                                  "(*.txt)|*.txt|Any file (*.*)|*")

        dlg = wx.FileDialog(
            self, message=_translate("Save file as ..."), defaultDir=initPath,
            defaultFile=filename, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            wildcard=wildcard)

        if dlg.ShowModal() == wx.ID_OK:
            newPath = dlg.GetPath()
            doc.filename = newPath
            self.fileSave(event=None, filename=newPath, doc=doc)
            path, shortName = os.path.split(newPath)
            self.notebook.SetPageText(docId, shortName)
            self.setFileModified(False)
            # JRG: 'doc.filename' should = newPath = dlg.getPath()
            doc.fileModTime = os.path.getmtime(doc.filename)
            # update the lexer since the extension could have changed
            self.currentDoc.setLexerFromFileName()
            # re-analyse the document
            self.currentDoc.analyseScript()
            # Update status bar and title bar labels
            self.statusBar.SetStatusText(self.currentDoc.getFileType(), 2)
            self.SetLabel(f'{self.currentDoc.filename} - PsychoPy Coder')

        dlg.Destroy()

    def fileClose(self, event, filename=None, checkSave=True):
        if self.currentDoc is None:
            # so a coder window with no files responds like the builder window
            # to self.keys.close
            self.closeFrame()
            return
        if filename is None:
            filename = self.currentDoc.filename
        self.currentDoc = self.notebook.GetPage(self.notebook.GetSelection())
        if self.currentDoc.UNSAVED and checkSave:
            sys.stdout.flush()
            msg = _translate('Save changes to %s before quitting?') % filename
            dlg = dialogs.MessageDialog(self, message=msg, type='Warning')
            resp = dlg.ShowModal()
            sys.stdout.flush()
            dlg.Destroy()
            if resp == wx.ID_CANCEL:
                if isinstance(event, aui.AuiNotebookEvent):
                    event.Veto()
                return -1  # return, don't quit
            elif resp == wx.ID_YES:
                # save then quit
                self.fileSave(None)
            elif resp == wx.ID_NO:
                pass  # don't save just quit
        # remove the document and its record
        currId = self.notebook.GetSelection()
        # if this was called by AuiNotebookEvent, then page has closed already
        if not isinstance(event, aui.AuiNotebookEvent):
            self.notebook.DeletePage(currId)
            newPageID = self.notebook.GetSelection()
        else:
            newPageID = self.notebook.GetSelection() - 1
        # set new current doc
        if newPageID < 0:
            self.currentDoc = None
            self.statusBar.SetStatusText("", 1)  # clear line pos
            self.statusBar.SetStatusText("", 2)  # clear file type in status bar
            self.statusBar.SetStatusText("", 3)  # psyhcopy version
            # clear the source tree
            self.SetLabel("PsychoPy v%s (Coder)" % self.app.version)
            self.structureWindow.srcTree.DeleteAllItems()
        else:
            self.currentDoc = self.notebook.GetPage(newPageID)
            self.structureWindow.refresh()
            # set to current file status
            self.setFileModified(self.currentDoc.UNSAVED)
        # return 1

    def fileCloseAll(self, event, checkSave=True):
        """Close all files open in the editor."""
        if self.currentDoc is None:
            event.Skip()
            return

        for fname in self.getOpenFilenames():
            self.fileClose(event, fname, checkSave)

    def runFile(self, event=None):
        """Open Runner for running the script."""

        fullPath = self.currentDoc.filename
        filename = os.path.split(fullPath)[1]
        # does the file need saving before running?
        if self.currentDoc.UNSAVED:
            sys.stdout.flush()
            msg = _translate('Save changes to %s before running?') % filename
            dlg = dialogs.MessageDialog(self, message=msg, type='Warning')
            resp = dlg.ShowModal()
            sys.stdout.flush()
            dlg.Destroy()
            if resp == wx.ID_CANCEL:
                return -1  # return, don't run
            elif resp == wx.ID_YES:
                self.fileSave(None)  # save then run
            elif resp == wx.ID_NO:
                pass  # just run
        if self.app.runner == None:
            self.app.showRunner()
        self.app.runner.addTask(fileName=fullPath)
        self.app.runner.Raise()
        if event:
            if event.Id in [self.cdrBtnRun.Id, self.IDs.cdrRun]:
                self.app.runner.panel.runLocal(event)
                self.Raise()
            else:
                self.app.showRunner()

    def copy(self, event):
        foc = self.FindFocus()
        foc.Copy()
        if isinstance(foc, CodeEditor):
            self.currentDoc.Copy()  # let the text ctrl handle this
        # elif isinstance(foc, StdOutRich):

    def duplicateLine(self, event):
        self.currentDoc.LineDuplicate()

    def cut(self, event):
        self.currentDoc.Cut()  # let the text ctrl handle this

    def paste(self, event):
        foc = self.FindFocus()
        if hasattr(foc, 'Paste'):
            foc.Paste()

    def undo(self, event):
        if self.currentDoc:
            self.currentDoc.Undo()

    def redo(self, event):
        if self.currentDoc:
            self.currentDoc.Redo()

    def commentSelected(self, event):
        self.currentDoc.commentLines()

    def uncommentSelected(self, event):
        self.currentDoc.uncommentLines()

    def toggleComments(self, event):
        self.currentDoc.toggleCommentLines()

    def bigFont(self, event):
        self.currentDoc.increaseFontSize()

    def smallFont(self, event):
        self.currentDoc.decreaseFontSize()

    def resetFont(self, event):
        self.currentDoc.resetFontSize()

    def foldAll(self, event):
        self.currentDoc.FoldAll(wx.stc.STC_FOLDACTION_TOGGLE)

    # def unfoldAll(self, event):
    #   self.currentDoc.ToggleFoldAll(expand = False)

    def setOutputWindow(self, event=None, value=None):
        # show/hide the output window (from the view menu control)
        if value is None:
            value = self.outputChk.IsChecked()
        self.outputChk.Check(value)
        if value:
            # show the pane
            self.prefs['showOutput'] = True
            self.paneManager.GetPane('Shelf').Show()
        else:
            # hide the pane
            self.prefs['showOutput'] = False
            self.paneManager.GetPane('Shelf').Hide()
        self.app.prefs.saveUserPrefs()  # includes a validation
        self.paneManager.Update()

    def setShowIndentGuides(self, event):
        # show/hide the source assistant (from the view menu control)
        newVal = self.indentGuideChk.IsChecked()
        self.appData['showIndentGuides'] = newVal
        for ii in range(self.notebook.GetPageCount()):
            self.notebook.GetPage(ii).SetIndentationGuides(newVal)

    def setShowWhitespace(self, event):
        newVal = self.showWhitespaceChk.IsChecked()
        self.appData['showWhitespace'] = newVal
        for ii in range(self.notebook.GetPageCount()):
            self.notebook.GetPage(ii).SetViewWhiteSpace(newVal)

    def setShowEOLs(self, event):
        newVal = self.showEOLsChk.IsChecked()
        self.appData['showEOLs'] = newVal
        for ii in range(self.notebook.GetPageCount()):
            self.notebook.GetPage(ii).SetViewEOL(newVal)

    def onCloseSourceAsst(self, event):
        """Called when the source assisant is closed."""
        pass

    def setSourceAsst(self, event):
        # show/hide the source assistant (from the view menu control)
        if not self.sourceAsstChk.IsChecked():
            self.paneManager.GetPane("SourceAsst").Hide()
            self.prefs['showSourceAsst'] = False
        else:
            self.paneManager.GetPane("SourceAsst").Show()
            self.prefs['showSourceAsst'] = True
        self.paneManager.Update()

    # def setAutoComplete(self, event=None):
    #     # show/hide the source assistant (from the view menu control)
    #     self.prefs['autocomplete'] = self.useAutoComp = \
    #         self.chkShowAutoComp.IsChecked()

    # def setFileBrowser(self, event):
    #     # show/hide the source file browser
    #     if not self.fileBrowserChk.IsChecked():
    #         self.paneManager.GetPane("FileBrowser").Hide()
    #         self.prefs['showFileBrowser'] = False
    #     else:
    #         self.paneManager.GetPane("FileBrowser").Show()
    #         self.prefs['showFileBrowser'] = True
    #     self.paneManager.Update()

    def analyseCodeNow(self, event):
        self.statusBar.SetStatusText(_translate('Analyzing code'))
        if self.currentDoc is not None:
            self.currentDoc.analyseScript()
        else:
            # todo: add _translate()
            txt = 'Open a file from the File menu, or drag one onto this app, or open a demo from the Help menu'

        self.statusBar.SetStatusText(_translate('ready'))

    # def setAnalyseAuto(self, event):
    #     set autoanalysis (from the check control in the tools menu)
    #     if self.analyseAutoChk.IsChecked():
    #        self.prefs['analyseAuto']=True
    #     else:
    #        self.prefs['analyseAuto']=False

    def loadDemo(self, event):
        self.setCurrentDoc(self.demos[event.GetId()])

    def tabKeyPressed(self, event):
        # if several chars are selected then smartIndent
        # if we're at the start of the line then smartIndent
        if self.currentDoc.shouldTrySmartIndent():
            self.smartIndent(event=None)
        else:
            # self.currentDoc.CmdKeyExecute(wx.stc.STC_CMD_TAB)
            pos = self.currentDoc.GetCurrentPos()
            self.currentDoc.InsertText(pos, '\t')
            self.currentDoc.SetCurrentPos(pos + 1)
            self.currentDoc.SetSelection(pos + 1, pos + 1)

    def smartIndent(self, event):
        self.currentDoc.smartIndent()

    def indent(self, event):
        self.currentDoc.indentSelection(4)

    def dedent(self, event):
        self.currentDoc.indentSelection(-4)

    def setFileModified(self, isModified):
        # changes the document flag, updates save buttons
        self.currentDoc.UNSAVED = isModified
        # disabled when not modified
        if hasattr(self, 'cdrBtnSave'):
            self.cdrBtnSave.Enable(isModified)
        # self.fileMenu.Enable(self.fileMenu.FindItem('&Save\tCtrl+S"'),
        #     isModified)

    def onProcessEnded(self, event):
        # this is will check the stdout and stderr for any last messages
        self.onIdle(event=None)
        self.scriptProcess = None
        self.scriptProcessID = None
        self.toolbar.EnableTool(self.cdrBtnRun.Id, True)
        self.toolbar.EnableTool(self.cdrBtnRunner.Id, True)

    def onURL(self, evt):
        """decompose the URL of a file and line number"""
        # "C:\Program Files\wxPython2.8 Docs and Demos\samples\hangman\hangman.py"
        tmpFilename, tmpLineNumber = evt.GetString().rsplit('", line ', 1)
        filename = tmpFilename.split('File "', 1)[1]
        try:
            lineNumber = int(tmpLineNumber.split(',')[0])
        except ValueError:
            lineNumber = int(tmpLineNumber.split()[0])
        self.gotoLine(filename, lineNumber)

    def onUnitTests(self, evt=None):
        """Show the unit tests frame"""
        if self.unitTestFrame:
            self.unitTestFrame.Raise()
        else:
            self.unitTestFrame = UnitTestFrame(app=self.app)
        # UnitTestFrame.Show()

    def onPavloviaSync(self, evt=None):
        """Push changes to project repo, or create new proj if proj is None"""
        self.project = pavlovia.getProject(self.currentDoc.filename)
        self.fileSave(self.currentDoc.filename)  # Must save on sync else changes not pushed
        pavlovia_ui.syncProject(parent=self, project=self.project)

    def onPavloviaRun(self, evt=None):
        # TODO: Allow user to run project from coder
        pass

    def setPavloviaUser(self, user):
        # TODO: update user icon on button to user avatar
        pass

    def _applyAppTheme(self, target=None):
        """Overrides theme change from ThemeMixin.
        Don't call - this is called at the end of theme.setter"""
        ThemeMixin._applyAppTheme(self)  # handles most recursive setting
        ThemeMixin._applyAppTheme(self.toolbar)
        ThemeMixin._applyAppTheme(self.statusBar)
        # updating sourceAsst will incl fileBrowser and sourcetree
        ThemeMixin._applyAppTheme(self.sourceAsst)
        ThemeMixin._applyAppTheme(self.notebook)
        self.notebook.Refresh()
        if hasattr(self, 'shelf'):
            ThemeMixin._applyAppTheme(self.shelf)
        if sys.platform == 'win32':
            self.Update()  # kills mac. Not sure about linux
