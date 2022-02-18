#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2022 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

from pathlib import Path
from psychopy.alerts import alerttools, alert
from psychopy.experiment.components import BaseVisualComponent, Param, getInitVals, _translate
from psychopy.localization import _localized as __localized
from ..keyboard import KeyboardComponent
_localized = __localized.copy()

# only use _localized values for label values, nothing functional:
_localized.update({'text': _translate('Text'),
                   'font': _translate('Font'),
                   'letterHeight': _translate('Letter height'),
                   'flipHorizontal': _translate('Flip horizontal'),
                   'flipVertical': _translate('Flip vertical'),
                   'languageStyle': _translate('Language style'),
                   'bold': _translate('Bold'),
                   'italic': _translate('Italic'),
                   'lineSpacing': _translate('Line Spacing'),
                   'padding': _translate('Padding'),
                   'anchor': _translate('Anchor'),
                   'fillColor': _translate('Fill Colour'),
                   'borderColor': _translate('Border Colour'),
                   'borderWidth': _translate('Border Width'),
                   'editable': _translate('Editable?'),
                   'autoLog': _translate('Auto Log')
                   })


class TextboxComponent(BaseVisualComponent):
    """An event class for presenting text-based stimuli
    """
    categories = ['Stimuli', 'Responses']
    targets = ['PsychoPy', 'PsychoJS']
    iconFile = Path(__file__).parent / 'textbox.png'
    tooltip = _translate('Textbox: present text stimuli but cooler')
    beta = True

    def __init__(self, exp, parentName, name='textbox',
                 # effectively just a display-value
                 text=_translate('Any text\n\nincluding line breaks'),
                 font='Open Sans', units='from exp settings', bold=False, italic=False,
                 color='white', colorSpace='rgb', opacity="",
                 pos=(0, 0), size=(None, None), letterHeight=0.05, ori=0,
                 anchor='center', alignment='center',
                 lineSpacing=1.0, padding=0,  # gap between box and text
                 startType='time (s)', startVal=0.0,
                 stopType='duration (s)', stopVal=1.0,
                 startEstim='', durationEstim='',
                 languageStyle='LTR', fillColor="None",
                 borderColor="None", borderWidth=2,
                 flipHoriz=False,
                 flipVert=False,
                 editable=False, autoLog=True):
        super(TextboxComponent, self).__init__(exp, parentName, name,
                                            units=units,
                                            color=color, fillColor=fillColor, borderColor=borderColor,
                                            colorSpace=colorSpace,
                                            pos=pos,
                                            ori=ori,
                                            size=size,
                                            startType=startType,
                                            startVal=startVal,
                                            stopType=stopType,
                                            stopVal=stopVal,
                                            startEstim=startEstim,
                                            durationEstim=durationEstim)
        self.type = 'Textbox'
        self.url = "https://www.psychopy.org/builder/components/textbox.html"
        self.order += [  # controls order of params within tabs
            "editable", "text",  # Basic tab
            "borderWidth", "opacity",  # Appearance tab
            "font", "letterHeight", "lineSpacing", "bold", "italic",  # Formatting tab
            ]
        self.order.insert(self.order.index("units"), "padding") # Add "padding" just before spatial units
        # params
        _allow3 = ['constant', 'set every repeat', 'set every frame']  # list
        self.params['color'].label = _translate("Text Color")

        self.params['text'] = Param(
            text, valType='str', inputType="multi", allowedTypes=[], categ='Basic',
            updates='constant', allowedUpdates=_allow3[:],  # copy the list
            hint=_translate("The text to be displayed"),
            canBePath=False,
            label=_localized['text'])
        self.params['font'] = Param(
            font, valType='str', inputType="single", allowedTypes=[], categ='Formatting',
            updates='constant', allowedUpdates=_allow3[:],  # copy the list
            hint=_translate("The font name (e.g. Comic Sans)"),
            label=_localized['font'])
        self.params['letterHeight'] = Param(
            letterHeight, valType='num', inputType="single", allowedTypes=[], categ='Formatting',
            updates='constant', allowedUpdates=_allow3[:],  # copy the list
            hint=_translate("Specifies the height of the letter (the width"
                            " is then determined by the font)"),
            label=_localized['letterHeight'])
        self.params['flipHoriz'] = Param(
            flipHoriz, valType='bool', inputType="bool", allowedTypes=[], categ='Layout',
            updates='constant',
            hint=_translate("horiz = left-right reversed; vert = up-down"
                            " reversed; $var = variable"),
            label=_localized['flipHorizontal'])
        self.params['flipVert'] = Param(
            flipVert, valType='bool', inputType="bool", allowedTypes=[], categ='Layout',
            updates='constant',
            hint=_translate("horiz = left-right reversed; vert = up-down"
                            " reversed; $var = variable"),
            label=_localized['flipVertical'])
        self.params['languageStyle'] = Param(
            languageStyle, valType='str', inputType="choice", categ='Formatting',
            allowedVals=['LTR', 'RTL', 'Arabic'],
            hint=_translate("Handle right-to-left (RTL) languages and Arabic reshaping"),
            label=_localized['languageStyle'])
        self.params['italic'] = Param(
            italic, valType='bool', inputType="bool", allowedTypes=[], categ='Formatting',
            updates='constant',
            hint=_translate("Should text be italic?"),
            label=_localized['italic'])
        self.params['bold'] = Param(
            bold, valType='bool', inputType="bool", allowedTypes=[], categ='Formatting',
            updates='constant',
            hint=_translate("Should text be bold?"),
            label=_localized['bold'])
        self.params['lineSpacing'] = Param(
            lineSpacing, valType='num', inputType="single", allowedTypes=[], categ='Formatting',
            updates='constant',
            hint=_translate("Defines the space between lines"),
            label=_localized['lineSpacing'])
        self.params['padding'] = Param(
            padding, valType='num', inputType="single", allowedTypes=[], categ='Layout',
            updates='constant', allowedUpdates=_allow3[:],
            hint=_translate("Defines the space between text and the textbox border"),
            label=_localized['padding'])
        self.params['anchor'] = Param(
            anchor, valType='str', inputType="choice", categ='Layout',
            allowedVals=['center',
                         'top-center',
                         'bottom-center',
                         'center-left',
                         'center-right',
                         'top-left',
                         'top-right',
                         'bottom-left',
                         'bottom-right',
                         ],
            updates='constant',
            hint=_translate("Which point on the stimulus should be anchored to its exact position?"),
            label=_translate('Anchor'))
        self.params['alignment'] = Param(
            alignment, valType='str', inputType="choice", categ='Formatting',
            allowedVals=['center',
                         'top-center',
                         'bottom-center',
                         'center-left',
                         'center-right',
                         'top-left',
                         'top-right',
                         'bottom-left',
                         'bottom-right',
                         ],
            updates='constant',
            hint=_translate("How should text be laid out within the box?"),
            label=_translate("Alignment"))
        self.params['borderWidth'] = Param(
            borderWidth, valType='num', inputType="single", allowedTypes=[], categ='Appearance',
            updates='constant', allowedUpdates=_allow3[:],
            hint=_translate("Textbox border width"),
            label=_localized['borderWidth'])
        self.params['editable'] = Param(
            editable, valType='bool', inputType="bool", allowedTypes=[], categ='Basic',
            updates='constant',
            hint=_translate("Should textbox be editable?"),
            label=_localized['editable'])
        self.params['autoLog'] = Param(
            autoLog, valType='bool', inputType="bool", allowedTypes=[], categ='Data',
            updates='constant',
            hint=_translate(
                    'Automatically record all changes to this in the log file'),
            label=_localized['autoLog'])

    def writeInitCode(self, buff):
        # do we need units code?
        if self.params['units'].val == 'from exp settings':
            unitsStr = ""
        else:
            unitsStr = "units=%(units)s," % self.params
        # do writing of init
        # replaces variable params with sensible defaults
        inits = getInitVals(self.params, 'PsychoPy')
        code = (
            "%(name)s = visual.TextBox2(\n"
            "     win, text=%(text)s, font=%(font)s,\n"
            "     pos=%(pos)s," + unitsStr +
            "     letterHeight=%(letterHeight)s,\n"
            "     size=%(size)s, borderWidth=%(borderWidth)s,\n"
            "     color=%(color)s, colorSpace=%(colorSpace)s,\n"
            "     opacity=%(opacity)s,\n"
            "     bold=%(bold)s, italic=%(italic)s,\n"
            "     lineSpacing=%(lineSpacing)s,\n"
            "     padding=%(padding)s, alignment=%(alignment)s,\n"
            "     anchor=%(anchor)s,\n"
            "     fillColor=%(fillColor)s, borderColor=%(borderColor)s,\n"
            "     flipHoriz=%(flipHoriz)s, flipVert=%(flipVert)s, languageStyle=%(languageStyle)s,\n"
            "     editable=%(editable)s,\n"
            "     name='%(name)s',\n"
            "     autoLog=%(autoLog)s,\n"
            ")\n"
        )
        buff.writeIndentedLines(code % inits)

    def writeInitCodeJS(self, buff):
        # do we need units code?
        if self.params['units'].val == 'from exp settings':
            unitsStr = "  units: undefined, \n"
        else:
            unitsStr = "  units: %(units)s, \n" % self.params
        # do writing of init
        # replaces variable params with sensible defaults
        inits = getInitVals(self.params, 'PsychoJS')

        # check for NoneTypes
        for param in inits:
            if inits[param] in [None, 'None', '']:
                inits[param].val = 'undefined'
                if param == 'text':
                    inits[param].val = ""

        code = ("%(name)s = new visual.TextBox({\n"
                "  win: psychoJS.window,\n"
                "  name: '%(name)s',\n"
                "  text: %(text)s,\n"
                "  font: %(font)s,\n" 
                "  pos: %(pos)s, letterHeight: %(letterHeight)s,\n"
                "  size: %(size)s," + unitsStr +
                "  color: %(color)s, colorSpace: %(colorSpace)s,\n"
                "  fillColor: %(fillColor)s, borderColor: %(borderColor)s,\n"
                "  bold: %(bold)s, italic: %(italic)s,\n"
                "  opacity: %(opacity)s,\n"
                "  padding: %(padding)s,\n"
                "  editable: %(editable)s,\n"
                "  multiline: true,\n"
                "  anchor: %(anchor)s,\n")
        buff.writeIndentedLines(code % inits)

        depth = -self.getPosInRoutine()
        code = ("  depth: %.1f \n"
                "});\n\n" % (depth))
        buff.writeIndentedLines(code)
        depth = -self.getPosInRoutine()

    def writeRoutineStartCode(self, buff):
        # Give alert if in the same routine as a Keyboard component
        if self.params['editable'].val:
            routine = self.exp.routines[self.parentName]
            for sibling in routine:
                if isinstance(sibling, KeyboardComponent):
                    alert(4405, strFields={'textbox': self.params['name'], 'keyboard': sibling.params['name']})

        code = (
            "%(name)s.reset()"
        )
        buff.writeIndentedLines(code % self.params)
        BaseVisualComponent.writeRoutineStartCode(self, buff)

    def writeRoutineStartCodeJS(self, buff):
        if self.params['editable']:
            # replaces variable params with sensible defaults
            inits = getInitVals(self.params, 'PsychoJS')
            # check for NoneTypes
            for param in inits:
                if inits[param] in [None, 'None', '']:
                    inits[param].val = 'undefined'
                    if param == 'text':
                        inits[param].val = ""

            code = (
                "%(name)s.setText(%(text)s);\n"
                "%(name)s.refresh();\n"
            )
            buff.writeIndentedLines(code % inits)
        BaseVisualComponent.writeRoutineStartCodeJS(self, buff)

    def writeRoutineEndCode(self, buff):
        name = self.params['name']
        if len(self.exp.flow._loopList):
            currLoop = self.exp.flow._loopList[-1]  # last (outer-most) loop
        else:
            currLoop = self.exp._expHandler
        if self.params['editable']:
            buff.writeIndentedLines(f"{currLoop.params['name']}.addData('{name}.text',{name}.text)\n")
        # get parent to write code too (e.g. store onset/offset times)
        super().writeRoutineEndCode(buff)

    def writeRoutineEndCodeJS(self, buff):
        name = self.params['name']
        if len(self.exp.flow._loopList):
            currLoop = self.exp.flow._loopList[-1]  # last (outer-most) loop
        else:
            currLoop = self.exp._expHandler
        if self.params['editable']:
            buff.writeIndentedLines(f"psychoJS.experiment.addData('{name}.text',{name}.text)\n")
        # get parent to write code too (e.g. store onset/offset times)
        super().writeRoutineEndCodeJS(buff)

    def integrityCheck(self):
        super().integrityCheck()  # run parent class checks first
        alerttools.testFont(self) # Test whether font is available locally
