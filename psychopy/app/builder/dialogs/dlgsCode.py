#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

"""Dialog classes for the Builder Code component
"""

from __future__ import absolute_import, division, print_function
from builtins import str

import keyword
import wx
from collections import OrderedDict

try:
    from wx.lib.agw import flatnotebook
except ImportError:  # was here wx<4.0:
    from wx.lib import flatnotebook

from psychopy.constants import PY3

if PY3:
    from importlib.util import find_spec as loader
else:
    from pkgutil import find_loader as loader
hasMetapensiero = loader("metapensiero") is not None

from .. import validators
from psychopy.localization import _translate
from psychopy.app.coder.codeEditorBase import BaseCodeEditor
from psychopy.experiment.py2js_transpiler import translatePythonToJavaScript


class DlgCodeComponentProperties(wx.Dialog):
    _style = (wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
              | wx.DIALOG_NO_PARENT)

    def __init__(self, frame, title, params, order,
                 helpUrl=None, suppressTitles=True, size=wx.DefaultSize,
                 style=_style, editing=False, depends=[],
                 timeout=None):

        # translate title
        localizedTitle = title.replace(' Properties',
                                       _translate(' Properties'))
        wx.Dialog.__init__(self, None, -1, localizedTitle,
                           size=size, style=style)
        self.frame = frame
        self.app = frame.app
        self.helpUrl = helpUrl
        self.params = params  # dict
        self.order = order
        self.title = title
        self.timeout = timeout
        self.warningsDict = {}  # to store warnings for all fields
        # keep localized title to update dialog's properties later.
        self.localizedTitle = localizedTitle
        self.codeBoxes = {}
        self.tabs = OrderedDict()

        if not editing and 'name' in self.params:
            # then we're adding a new component so ensure a valid name:
            makeValid = self.frame.exp.namespace.makeValid
            self.params['name'].val = makeValid(params['name'].val)

        agwStyle = flatnotebook.FNB_NO_X_BUTTON
        if hasattr(flatnotebook, "FNB_NAV_BUTTONS_WHEN_NEEDED"):
            # not available in wxPython 2.8
            agwStyle |= flatnotebook.FNB_NAV_BUTTONS_WHEN_NEEDED
        if hasattr(flatnotebook, "FNB_NO_TAB_FOCUS"):
            # not available in wxPython 2.8.10
            agwStyle |= flatnotebook.FNB_NO_TAB_FOCUS
        self.codeNotebook = flatnotebook.FlatNotebook(self, wx.ID_ANY,
                                                      style=agwStyle)

        openToPage = None
        tabN = -1
        for paramN, paramName in enumerate(self.order):
            param = self.params.get(paramName)
            if paramName == 'name':
                self.nameLabel = wx.StaticText(self, wx.ID_ANY,
                                               _translate(param.label))
                _style = wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB
                self.componentName = wx.TextCtrl(self, wx.ID_ANY,
                                                 str(param.val),
                                                 style=_style)
                self.componentName.SetToolTip(wx.ToolTip(
                        _translate(param.hint)))
                self.componentName.SetValidator(validators.NameValidator())
                self.nameOKlabel = wx.StaticText(self, -1, '',
                                                 style=wx.ALIGN_RIGHT)
                self.nameOKlabel.SetForegroundColour(wx.RED)
            elif paramName == 'Code Type':
                _codeTypes = self.params['Code Type'].allowedVals
                _selectedCodeType = self.params['Code Type'].val
                _selectedCodeTypeIndex = _codeTypes.index(_selectedCodeType)
                self.codeTypeMenu = wx.Choice(self, choices=_codeTypes)

                if not hasMetapensiero and _selectedCodeType.lower() == 'auto->js':
                    _selectedCodeTypeIndex -= 1

                self.codeTypeMenu.SetSelection(_selectedCodeTypeIndex)
                self.codeTypeMenu.Bind(wx.EVT_CHOICE, self.onCodeChoice)
                self.codeTypeName = wx.StaticText(self, wx.ID_ANY,
                                                  _translate(param.label))
            else:
                codeType = ["Py", "JS"]["JS" in paramName]  # Give CodeBox a code type
                tabName = paramName.replace("JS ", "")
                if tabName in self.tabs:
                    _panel = self.tabs[tabName]
                else:
                    _panel = wx.Panel(self.codeNotebook, wx.ID_ANY)
                    self.tabs[tabName] = _panel
                    tabN += 1

                self.codeBoxes[paramName] = CodeBox(_panel, wx.ID_ANY,
                                                    pos=wx.DefaultPosition,
                                                    style=0,
                                                    prefs=self.app.prefs,
                                                    params=params,
                                                    codeType=codeType)
                self.codeBoxes[paramName].AddText(param.val)
                self.codeBoxes[paramName].Bind(wx.EVT_KEY_UP, self.onKeyUp)  # For real time translation

                if len(param.val.strip()) and openToPage is None:
                    # index of first non-blank page
                    openToPage = tabN

        if self.helpUrl is not None:
            self.helpButton = wx.Button(self, wx.ID_HELP,
                                        _translate(" Help "))
            tip = _translate("Go to online help about this component")
            self.helpButton.SetToolTip(wx.ToolTip(tip))
        self.okButton = wx.Button(self, wx.ID_OK, _translate(" OK "))
        self.okButton.SetDefault()
        self.cancelButton = wx.Button(self, wx.ID_CANCEL,
                                      _translate(" Cancel "))
        self.__set_properties()
        self.__do_layout()
        if openToPage is None:
            openToPage = 0
        self.codeNotebook.SetSelection(openToPage)
        self.Update()
        self.Bind(wx.EVT_BUTTON, self.helpButtonHandler, self.helpButton)

        if self.timeout:
            timeout = wx.CallLater(self.timeout, self.onEnter)
            timeout.Start()
        # do show and process return
        ret = self.ShowModal()

        if ret == wx.ID_OK:
            self.checkName()
            self.OK = True
            self.params = self.getParams()  # get new vals from dlg
            self.Validate()
        else:
            self.OK = False

    def readOnlyCodeBox(self, val=False):
        """
        Sets ReadOnly for JS code boxes.

        Parameters
        ----------
        val : bool
            True/False for ReadOnly/ReadWrite
        """
        for box in self.codeBoxes:
            if 'JS' in box:
                self.codeBoxes[box].SetReadOnly(val)

    def onKeyUp(self, event):
        """
        Translates Python to JS on EVT_KEY_UP event, if Code Type is Auto->JS.
        """
        if self.codeChoice[1].val.lower() != 'auto->js':
            return

        pythonCodeBox = event.GetEventObject()
        keys = list(self.codeBoxes.keys())
        vals = list(self.codeBoxes.values())
        codeBox = keys[vals.index(pythonCodeBox)]
        if 'JS' not in codeBox:
            self.runTranslation(codeBox)

        if event:
            event.Skip()

    @property
    def codeChoice(self):
        """
        Set code to Python, JS, Both, or Auto->JS for translation.

        Returns
        -------
        tuple :
            (previousCodeType, code type param)
        """
        param = self.params['Code Type']  # Update param with menu selection
        prevCodeType = param.val
        param.val = param.allowedVals[self.codeTypeMenu.GetSelection()]
        return prevCodeType, param

    def undoCodeTypeChoice(self, prevCodeType):
        """
        Return code type to previous selection.

        Parameters
        ----------
        prevCodeType: str
            Code Type
        """
        prevCodeTypeIndex = self.params['Code Type'].allowedVals.index(prevCodeType)
        self.codeTypeMenu.SetSelection(prevCodeTypeIndex)
        self.params['Code Type'].val = prevCodeType

    def onCodeChoice(self, event):
        """
        Set code to Python, JS, Both, or Auto->JS for translation.
        Calls translation and updates to visible windows
        """
        prevCodeType, param = self.codeChoice

        if not hasMetapensiero and param.val.lower() == "auto->js" :
            msg = ("\nPy to JS auto-translation requires the metapensiero library.\n"
                   "Available for Python 3.5+.\n")
            dlg = CodeOverwriteDialog(self, -1, "Warning: requires the metapensiero library", msg)
            dlg.ShowModal()
            self.undoCodeTypeChoice(prevCodeType)
            return

        self.translateCode(event, prevCodeType, param.val)
        self.updateVisibleCode(event)

        if event:
            event.Skip()

    def translateCode(self, event, prevCodeType='', newCodeType=''):
        """
        For each code box, calls runTranslate to translate Python code to JavaScript.
        Overwrite warning given when previous code type (prevCodeType) is Py, JS, or Both,
        and when codeChangeDetected determines whether JS code has new additions

        Parameters
        ----------
        event : wx.Event
        prevCodeType : str
            Previous code type selected
        newCodeType : str
            New code type selected
        """
        if not newCodeType.lower() == "auto->js":
            return

        if prevCodeType.lower() != 'auto->js' and self.codeChangeDetected():
            msg = ("\nAuto-JS translation will overwrite your existing JavaScript code.\n"
                   "Press OK to continue, or Cancel.\n")
            dlg = CodeOverwriteDialog(self, -1, "Warning: Python to JavaScript Translation", msg)
            retVal = dlg.ShowModal()
            if not retVal == wx.ID_OK:
                self.undoCodeTypeChoice(prevCodeType)
                return

        for boxName in self.codeBoxes:
            if 'JS' not in boxName:
                self.runTranslation(boxName)

        if event:
            event.Skip()

    def runTranslation(self, codeBox, codeChangeTest=False):
        """
        Runs Python to JS translation for single code box.
        Only receives Python code boxes.

        Parameters
        ----------
        codeBox : Str
            The name of the code box e.g., Begin Experiment
        codeChangeTest: bool
            Whether the translation is part of the overwrite test:
            i.e., is it safe to overwrite users new JS code

        Returns
        -------
        Return values only given if codeChangeTest is True.
            Returns translated JS code as str, or False if translation fails
        """
        jsCode = ''
        jsBox = codeBox.replace(' ', ' JS ')
        pythonCode = self.codeBoxes[codeBox].GetValue()
        self.readOnlyCodeBox(False)

        try:
            if pythonCode:
                jsCode = translatePythonToJavaScript(pythonCode)

            if codeChangeTest:
                return jsCode

            self.codeBoxes[jsBox].SetValue(jsCode)
        except Exception:  # Errors can be caught using alerts syntax checks
            if codeChangeTest:
                return False
            self.codeBoxes[jsBox].SetValue("/* Syntax Error: Fix Python code */")
        finally:
            self.readOnlyCodeBox(self.codeChoice[1].val.lower() == 'auto->js')

    def codeChangeDetected(self):
        """
        Compares current JS code with newly translated code for each tab.

        Returns
        -------
        bool
            True if current code differs from translated code, else False
        """
        for boxName in self.codeBoxes:
            if 'JS' not in boxName:
                newJS = self.runTranslation(boxName, True)
                currentJS = self.codeBoxes[boxName.replace(' ', ' JS ')].GetValue()

                if newJS == False or currentJS != newJS:
                    return True

        return False

    def updateVisibleCode(self, event=None):
        """
        Receives keyboard events and code menu choice events.
        On choice events, the code is stored for python or JS parameters,
        and written to panel depending on choice of code. The duplicate panel
        is shown/hidden depending on code choice. When duplicate is shown, Python and JS
        code are shown in codeBox(left panel) and codeBoxDup (right panel), respectively.
        """
        codeType = self.codeChoice[1].val

        for boxName in self.codeBoxes:
            self.readOnlyCodeBox(codeType.lower() == 'auto->js')
            if codeType.lower() in ['both', 'auto->js']:
                self.codeBoxes[boxName].Show()
            elif codeType == 'JS':
                # user only wants JS code visible
                if 'JS' in boxName:
                    self.codeBoxes[boxName].Show()
                else:
                    self.codeBoxes[boxName].Hide()
            else:
                # user only wants Py code visible
                if 'JS' in boxName:
                    self.codeBoxes[boxName].Hide()
                else:
                    self.codeBoxes[boxName].Show()

        for thisTabname in self.tabs:
            self.tabs[thisTabname].Layout()

        if event:
            event.Skip()

    def onEnter(self, evt=None, retval=wx.ID_OK):
        self.EndModal(retval)

    def checkName(self, event=None):
        """
        Issue a form validation on name change.
        """
        self.Validate()

    def __set_properties(self):

        self.SetTitle(self.localizedTitle)  # use localized title
        self.SetSize((640, 480))

    def __do_layout(self, show=False):
        self.updateVisibleCode()
        for tabName in self.tabs:
            pyName = tabName
            jsName = pyName.replace(" ", " JS ")
            panel = self.tabs[tabName]
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            pyBox = self.codeBoxes[pyName]
            jsBox = self.codeBoxes[jsName]
            sizer.Add(pyBox, 1, wx.EXPAND, 2)
            sizer.Add(jsBox, 1, wx.EXPAND, 2)
            panel.SetSizer(sizer)
            tabLabel = _translate(tabName)
            # Add a visual indicator when tab contains code
            if (self.params.get(pyName).val or self.params.get(jsName).val):
                tabLabel += ' *'
            self.codeNotebook.AddPage(panel, tabLabel)

        nameSizer = wx.BoxSizer(wx.HORIZONTAL)
        nameSizer.Add(self.nameLabel, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        nameSizer.Add(self.componentName,
                      flag=wx.EXPAND | wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                      border=10, proportion=1)
        nameSizer.Add(self.nameOKlabel, 0, wx.ALL, 10)
        nameSizer.Add(self.codeTypeName,
                      flag=wx.TOP | wx.RIGHT, border=13, proportion=0)
        nameSizer.Add(self.codeTypeMenu, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer.Add(nameSizer)
        mainSizer.Add(self.codeNotebook, 1, wx.EXPAND | wx.ALL, 10)
        buttonSizer.Add(self.helpButton, 0, wx.RIGHT, 10)
        buttonSizer.Add(self.okButton, 0, wx.LEFT, 10)
        buttonSizer.Add(self.cancelButton, 0, 0, 0)
        mainSizer.Add(buttonSizer, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        self.SetSizer(mainSizer)
        self.Layout()
        self.Center()

    def getParams(self):
        """retrieves data from any fields in self.codeGuiElements
        (populated during the __init__ function)

        The new data from the dlg get inserted back into the original params
        used in __init__ and are also returned from this method.
        """
        # get data from input fields
        for fieldName in self.params:
            param = self.params[fieldName]
            if fieldName == 'name':
                param.val = self.componentName.GetValue()
            elif fieldName == 'Code Type':
                param.val = self.codeTypeMenu.GetStringSelection()
            elif fieldName == 'disabled':
                pass
            else:
                codeBox = self.codeBoxes[fieldName]
                param.val = codeBox.GetText()
        return self.params

    def helpButtonHandler(self, event):
        """Uses self.app.followLink() to self.helpUrl
        """
        self.app.followLink(url=self.helpUrl)


class CodeBox(BaseCodeEditor):
    # this comes mostly from the wxPython demo styledTextCtrl 2

    def __init__(self, parent, ID, prefs,
                 # set the viewer to be small, then it will increase with
                 # wx.aui control
                 pos=wx.DefaultPosition, size=wx.Size(100, 160),
                 style=0,
                 params=None,
                 codeType='Py'):

        BaseCodeEditor.__init__(self, parent, ID, pos, size, style)

        self.parent = parent
        self.prefs = prefs
        self.params = params
        self.codeType = codeType
        self.SetLexer(wx.stc.STC_LEX_PYTHON)
        self.SetKeyWords(0, " ".join(keyword.kwlist))

        self.SetProperty("fold", "1")
        # 4 means 'tabs are bad'; 1 means 'flag inconsistency'
        self.SetProperty("tab.timmy.whinge.level", "4")
        self.SetViewWhiteSpace(self.prefs.appData['coder']['showWhitespace'])
        self.SetViewEOL(self.prefs.appData['coder']['showEOLs'])

        self.Bind(wx.stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.SetIndentationGuides(False)

        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

        self.setupStyles()

    def OnKeyPressed(self, event):
        keyCode = event.GetKeyCode()
        _mods = event.GetModifiers()

        # Check combination keys
        if keyCode == ord('/') and wx.MOD_CONTROL == _mods:
            if self.params is not None:
                self.toggleCommentLines()
        elif keyCode == ord('V') and wx.MOD_CONTROL == _mods:
            self.Paste()
            return  # so that we don't reach the skip line at end

        if keyCode == wx.WXK_RETURN and not self.AutoCompActive():
            # process end of line and then do smart indentation
            event.Skip(False)
            self.CmdKeyExecute(wx.stc.STC_CMD_NEWLINE)
            if self.params is not None:
                self.smartIdentThisLine()
            return  # so that we don't reach the skip line at end

        event.Skip()

    def setupStyles(self):

        if wx.Platform == '__WXMSW__':
            faces = {'size': 10}
        elif wx.Platform == '__WXMAC__':
            faces = {'size': 14}
        else:
            faces = {'size': 12}
        if self.prefs.coder['codeFontSize']:
            faces['size'] = int(self.prefs.coder['codeFontSize'])
        faces['small'] = faces['size'] - 2
        # Global default styles for all languages
        # ,'Arial']  # use arial as backup
        faces['code'] = self.prefs.coder['codeFont']
        # ,'Arial']  # use arial as backup
        faces['comment'] = self.prefs.coder['commentFont']
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,
                          "face:%(code)s,size:%(size)d" % faces)
        self.StyleClearAll()  # Reset all to be like the default

        # Global default styles for all languages
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,
                          "face:%(code)s,size:%(size)d" % faces)
        self.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER,
                          "back:#C0C0C0,face:%(code)s,size:%(small)d" % faces)
        self.StyleSetSpec(wx.stc.STC_STYLE_CONTROLCHAR,
                          "face:%(comment)s" % faces)
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT,
                          "fore:#FFFFFF,back:#0000FF,bold")
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD,
                          "fore:#000000,back:#FF0000,bold")

        # Python styles
        # Default
        self.StyleSetSpec(wx.stc.STC_P_DEFAULT,
                          "fore:#000000,face:%(code)s,size:%(size)d" % faces)
        # Comments
        spec = "fore:#007F00,face:%(comment)s,size:%(size)d"
        self.StyleSetSpec(wx.stc.STC_P_COMMENTLINE, spec % faces)
        # Number
        self.StyleSetSpec(wx.stc.STC_P_NUMBER,
                          "fore:#007F7F,size:%(size)d" % faces)
        # String
        self.StyleSetSpec(wx.stc.STC_P_STRING,
                          "fore:#7F007F,face:%(code)s,size:%(size)d" % faces)
        # Single quoted string
        self.StyleSetSpec(wx.stc.STC_P_CHARACTER,
                          "fore:#7F007F,face:%(code)s,size:%(size)d" % faces)
        # Keyword
        self.StyleSetSpec(wx.stc.STC_P_WORD,
                          "fore:#00007F,bold,size:%(size)d" % faces)
        # Triple quotes
        self.StyleSetSpec(wx.stc.STC_P_TRIPLE,
                          "fore:#7F0000,size:%(size)d" % faces)
        # Triple double quotes
        self.StyleSetSpec(wx.stc.STC_P_TRIPLEDOUBLE,
                          "fore:#7F0000,size:%(size)d" % faces)
        # Class name definition
        self.StyleSetSpec(wx.stc.STC_P_CLASSNAME,
                          "fore:#0000FF,bold,underline,size:%(size)d" % faces)
        # Function or method name definition
        self.StyleSetSpec(wx.stc.STC_P_DEFNAME,
                          "fore:#007F7F,bold,size:%(size)d" % faces)
        # Operators
        self.StyleSetSpec(wx.stc.STC_P_OPERATOR, "bold,size:%(size)d" % faces)
        # Identifiers
        self.StyleSetSpec(wx.stc.STC_P_IDENTIFIER,
                          "fore:#000000,face:%(code)s,size:%(size)d" % faces)
        # Comment-blocks
        self.StyleSetSpec(wx.stc.STC_P_COMMENTBLOCK,
                          "fore:#7F7F7F,size:%(size)d" % faces)
        # End of line where string is not closed
        spec = "fore:#000000,face:%(code)s,back:#E0C0E0,eol,size:%(size)d"
        self.StyleSetSpec(wx.stc.STC_P_STRINGEOL, spec % faces)

        self.SetCaretForeground("BLUE")

    def setStatus(self, status):
        if status == 'error':
            color = (255, 210, 210, 255)
        elif status == 'changed':
            color = (220, 220, 220, 255)
        else:
            color = (255, 255, 255, 255)
        self.StyleSetBackground(wx.stc.STC_STYLE_DEFAULT, color)
        self.setupStyles()  # then reset fonts again on top of that color

    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            lineClicked = self.LineFromPosition(evt.GetPosition())

            _flag = wx.stc.STC_FOLDLEVELHEADERFLAG
            if self.GetFoldLevel(lineClicked) & _flag:
                if evt.GetShift():
                    self.SetFoldExpanded(lineClicked, True)
                    self.Expand(lineClicked, True, True, 1)
                elif evt.GetControl():
                    if self.GetFoldExpanded(lineClicked):
                        self.SetFoldExpanded(lineClicked, False)
                        self.Expand(lineClicked, False, True, 0)
                    else:
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 100)
                else:
                    self.ToggleFold(lineClicked)

class CodeOverwriteDialog(wx.Dialog):
    def __init__(self, parent, ID, title,
                 msg='',
                 size=wx.DefaultSize,
                 pos=wx.DefaultPosition,
                 style=wx.DEFAULT_DIALOG_STYLE):

        wx.Dialog.__init__(self, parent, ID, title,
                           size=size, pos=pos, style=style)

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Set warning Message
        msg = _translate(msg)

        warning = wx.StaticText(self, wx.ID_ANY, msg)
        warning.SetForegroundColour((200, 0, 0))
        sizer.Add(warning, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        # Set divider
        line = wx.StaticLine(self, wx.ID_ANY, size=(20, -1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.TOP, 5)

        # Set buttons
        btnsizer = wx.StdDialogButtonSizer()

        btn = wx.Button(self, wx.ID_OK)
        btn.SetHelpText("The OK button completes the dialog")
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btn.SetHelpText("The Cancel button cancels the dialog. (Crazy, huh?)")
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Center and size
        self.CenterOnScreen()
        self.SetSizerAndFit(sizer)
