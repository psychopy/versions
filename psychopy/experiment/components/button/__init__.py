#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2022 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

from os import path
from pathlib import Path

from psychopy.alerts import alerttools
from psychopy.experiment.components import BaseVisualComponent, Param, getInitVals, _translate
from psychopy.experiment.py2js_transpiler import translatePythonToJavaScript
from psychopy.localization import _localized as __localized
_localized = __localized.copy()

# only use _localized values for label values, nothing functional:
_localized.update({'callback': _translate("Callback Function"),
                   'forceEndRoutine': _translate('Force end of Routine'),
                   'text': _translate('Button text'),
                   'font': _translate('Font'),
                   'letterHeight': _translate('Letter height'),
                   'bold': _translate('Bold'),
                   'italic': _translate('Italic'),
                   'padding': _translate('Padding'),
                   'anchor': _translate('Anchor'),
                   'fillColor': _translate('Fill Colour'),
                   'borderColor': _translate('Border Colour'),
                   'borderWidth': _translate('Border Width'),
                   'oncePerClick': _translate('Run once per click'),
                   'save': _translate("Record clicks"),
                   'timeRelativeTo': _translate("Time relative to")
                   })


class ButtonComponent(BaseVisualComponent):
    """
    A component for presenting a clickable textbox with a programmable callback
    """
    categories = ['Responses']
    targets = ['PsychoPy', 'PsychoJS']
    iconFile = Path(__file__).parent / 'button.png'
    tooltip = _translate('Button: A clickable textbox')
    beta = True

    def __init__(self, exp, parentName, name="button",
                 startType='time (s)', startVal=0,
                 stopType='duration (s)', stopVal=1.0,
                 startEstim='', durationEstim='',
                 text=_translate("Click here"), font='Arvo',
                 pos=(0, 0), size="", padding="", anchor='center', units='from exp settings', ori=0,
                 color="white", fillColor="darkgrey", borderColor="None", borderWidth=0, colorSpace='rgb', opacity="",
                 letterHeight=0.05, bold=True, italic=False,
                 callback="", save='every click', timeRelativeTo='button onset', forceEndRoutine=True, oncePerClick=True):
        super(ButtonComponent, self).__init__(exp, parentName, name,
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
        self.type = 'Button'
        self.url = "https://www.psychopy.org/builder/components/button.html"
        self.order += [  # controls order of params within tabs
            "forceEndRoutine", "text", "callback", "oncePerClick", # Basic tab
            "borderWidth", "opacity",  # Appearance tab
            "font", "letterHeight", "lineSpacing", "bold", "italic",  # Formatting tab
        ]
        # params
        _allow3 = ['constant', 'set every repeat', 'set every frame']  # list
        self.params['color'].label = _translate("Text Color")

        self.params['forceEndRoutine'] = Param(
            forceEndRoutine, valType='bool', inputType="bool", categ='Basic',
            updates='constant', direct=False,
            hint=_translate("Should a response force the end of the Routine "
                            "(e.g end the trial)?"),
            label=_localized['forceEndRoutine'])

        # If force end routine, then once per click doesn't make sense
        self.depends += [
            {
                "dependsOn": "forceEndRoutine",
                "condition": "==True",
                "param": "oncePerClick",
                "true": "disable",  # what to do with param if condition is True
                "false": "enable",  # permitted: hide, show, enable, disable
            }
        ]

        self.params['oncePerClick'] = Param(
            oncePerClick, valType='bool', inputType="bool", allowedTypes=[], categ='Basic',
            updates='constant',
            hint=_translate("Should the callback run once per click (True), or each frame until click is released (False)"),
            label=_localized['oncePerClick']
        )
        self.params['callback'] = Param(
            callback, valType='extendedCode', inputType="multi", allowedTypes=[], categ='Basic',
            updates='constant',
            hint=_translate("Code to run when button is clicked"),
            label=_localized['callback'])
        self.params['text'] = Param(
            text, valType='str', inputType="single", allowedTypes=[], categ='Basic',
            updates='constant', allowedUpdates=_allow3[:],  # copy the list
            hint=_translate("The text to be displayed"),
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
            hint=_translate("Should text anchor to the top, center or bottom of the box?"),
            label=_localized['anchor'])
        self.params['borderWidth'] = Param(
            borderWidth, valType='num', inputType="single", allowedTypes=[], categ='Appearance',
            updates='constant', allowedUpdates=_allow3[:],
            hint=_translate("Textbox border width"),
            label=_localized['borderWidth'])
        self.params['save'] = Param(
            save, valType='str', inputType="choice", categ='Data',
            allowedVals=['first click', 'last click', 'every click', 'none'],
            hint=_translate(
                "What clicks on this button should be saved to the data output?"),
            direct=False,
            label=_localized['save'])
        self.params['timeRelativeTo'] = Param(
            timeRelativeTo, valType='str', inputType="choice", categ='Data',
            allowedVals=['button onset', 'experiment', 'routine'],
            updates='constant',
            direct=False,
            hint=_translate(
                "What should the values of mouse.time should be "
                "relative to?"),
            label=_localized['timeRelativeTo'])


    def writeInitCode(self, buff):
        # do we need units code?
        if self.params['units'].val == 'from exp settings':
            unitsStr = ""
        else:
            unitsStr = "units=%(units)s," % self.params
        # do writing of init
        inits = getInitVals(self.params, 'PsychoPy')
        code = (
                "%(name)s = visual.ButtonStim(win, \n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                    "text=%(text)s, font=%(font)s,\n"
                    "pos=%(pos)s," + unitsStr + "\n"
                    "letterHeight=%(letterHeight)s,\n"
                    "size=%(size)s, borderWidth=%(borderWidth)s,\n"
                    "fillColor=%(fillColor)s, borderColor=%(borderColor)s,\n"
                    "color=%(color)s, colorSpace=%(colorSpace)s,\n"
                    "opacity=%(opacity)s,\n"
                    "bold=%(bold)s, italic=%(italic)s,\n"
                    "padding=%(padding)s,\n"
                    "anchor=%(anchor)s,\n"
                    "name='%(name)s'\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
                ")\n"
                "%(name)s.buttonClock = core.Clock()"
        )
        buff.writeIndentedLines(code % inits)

    def writeInitCodeJS(self, buff):
        inits = getInitVals(self.params, 'PsychoJS')

        code = (
            "%(name)s = new visual.ButtonStim({\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                "win: psychoJS.window,\n"
                "name: '%(name)s',\n"
                "text: %(text)s,\n"
                "fillColor: %(fillColor)s,\n"
                "borderColor: %(borderColor)s,\n"
                "color: %(color)s,\n"
                "colorSpace: %(colorSpace)s,\n"
                "pos: %(pos)s,\n"
                "letterHeight: %(letterHeight)s,\n"
                "size: %(size)s\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
            "});\n"
            "%(name)s.clock = new util.Clock();\n\n"
        )
        buff.writeIndentedLines(code % inits)

    def writeFrameCode(self, buff):
        BaseVisualComponent.writeFrameCode(self, buff)
        # do writing of init
        inits = getInitVals(self.params, 'PsychoPy')
        # Get callback from params
        callback = inits['callback']
        if inits['callback']:
            callback = str(callback)
        else:
            callback = ""
        # String to get time
        if inits['timeRelativeTo'] == 'button onset':
            timing = "%(name)s.buttonClock.getTime()"
        elif inits['timeRelativeTo'] == 'experiment':
            timing = "globalClock.getTime()"
        elif inits['timeRelativeTo'] == 'routine':
            timing = "routineTimer.getTime()"
        else:
            timing = "globalClock.getTime()"
        # Assemble code
        code = (
            f"if %(name)s.status == STARTED:\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                f"# check whether %(name)s has been pressed\n"
                f"if %(name)s.isClicked:\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                    f"if not %(name)s.wasClicked:\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                        f"%(name)s.timesOn.append({timing}) # store time of first click\n"
                        f"%(name)s.timesOff.append({timing}) # store time clicked until\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
                    f"else:\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                        f"%(name)s.timesOff[-1] = {timing} # update time clicked until\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        if self.params['oncePerClick'].val or self.params['forceEndRoutine'].val:
            code = (
                f"if not %(name)s.wasClicked:\n"
            )
            buff.writeIndentedLines(code % inits)
            buff.setIndentLevel(1, relative=True)
            if self.params['forceEndRoutine'].val:
                code = (
                        f"continueRoutine = False  # end routine when %(name)s is clicked\n"
                )
                buff.writeIndentedLines(code % inits)
            if self.params['oncePerClick'].val:
                buff.writeIndentedLines(callback % inits)
                buff.setIndentLevel(-1, relative=True)
        if not self.params['oncePerClick'].val:
            buff.writeIndentedLines(callback % inits)
        code = (
                    f"%(name)s.wasClicked = True  # if %(name)s is still clicked next frame, it is not a new click\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
                f"else:\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                    f"%(name)s.wasClicked = False  # if %(name)s is clicked next frame, it is a new click\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-2, relative=True)
        code = (
            f"else:\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
            f"%(name)s.wasClicked = False  # if %(name)s is clicked next frame, it is a new click\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)

    def writeFrameCodeJS(self, buff):
        BaseVisualComponent.writeFrameCodeJS(self, buff)
        # do writing of init
        inits = getInitVals(self.params, 'PsychoJS')
        # Get callback from params
        callback = inits['callback']
        if inits['callback'].val not in [None, "None", "none", "undefined"]:
            callback = translatePythonToJavaScript(str(callback))
        else:
            callback = ""

        # Check for current and last button press
        code = (
            "if (%(name)s.status === PsychoJS.Status.STARTED) {\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                "// check whether %(name)s has been pressed\n"
                "if (%(name)s.isClicked) {\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                    "if (!%(name)s.wasClicked) {\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                        "// store time of first click\n"
                        "%(name)s.timesOn.push(%(name)s.clock.getTime());\n"
                        "%(name)s.numClicks += 1;\n"
                        "// store time clicked until\n"
                        "%(name)s.timesOff.push(%(name)s.clock.getTime());\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
                    "} else {\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                    "// update time clicked until;\n"
                    "%(name)s.timesOff[%(name)s.timesOff.length - 1] = %(name)s.clock.getTime();\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
                    "}\n"
        )
        buff.writeIndentedLines(code % inits)

        if self.params['oncePerClick'] or self.params['forceEndRoutine']:
            code = (
                    "if (!%(name)s.wasClicked) {\n"
            )
            buff.writeIndentedLines(code % inits)
            buff.setIndentLevel(1, relative=True)
            if self.params['forceEndRoutine']:
                code = (
                    "// end routine when %(name)s is clicked\n"
                    "continueRoutine = false;\n"
                )
                buff.writeIndentedLines(code % inits)
            if self.params['oncePerClick']:
                buff.writeIndentedLines(callback % inits)
            buff.setIndentLevel(-1, relative=True)
            code = (
                    "}\n"
            )
            buff.writeIndentedLines(code % inits)
        if not self.params['oncePerClick']:
            buff.writeIndentedLines(callback % inits)

        # Store current button press as last
        code = (
                    "// if %(name)s is still clicked next frame, it is not a new click\n"
                    "%(name)s.wasClicked = true;\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
                "} else {\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                    "// if %(name)s is clicked next frame, it is a new click\n"
                    "%(name)s.wasClicked = false;\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
                "}\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
            "} else {\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                "// keep clock at 0 if %(name)s hasn't started / has finished\n"
                "%(name)s.clock.reset();\n"
                "// if %(name)s is clicked next frame, it is a new click\n"
                "%(name)s.wasClicked = false;\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
            "}\n"
        )
        buff.writeIndentedLines(code % inits)

    def writeRoutineEndCode(self, buff):
        BaseVisualComponent.writeRoutineEndCode(self, buff)
        if len(self.exp.flow._loopList):
            currLoop = self.exp.flow._loopList[-1]  # last (outer-most) loop
        else:
            currLoop = self.exp._expHandler
        name = self.params['name']
        if self.params['save'] == 'first click':
            index = "[0]"
        elif self.params['save'] == 'last click':
            index = "[-1]"
        else:
            index = ""
        if self.params['save'] != 'none':
            code = (
                f"{currLoop.params['name']}.addData('{name}.numClicks', {name}.numClicks)\n"
                f"if {name}.numClicks:\n"
                f"   {currLoop.params['name']}.addData('{name}.timesOn', {name}.timesOn{index})\n"
                f"   {currLoop.params['name']}.addData('{name}.timesOff', {name}.timesOff{index})\n"
                f"else:\n"
                f"   {currLoop.params['name']}.addData('{name}.timesOn', \"\")\n"
                f"   {currLoop.params['name']}.addData('{name}.timesOff', \"\")\n"
            )
            buff.writeIndentedLines(code)

    def writeRoutineEndCodeJS(self, buff):
        # Save data
        code = (
            "psychoJS.experiment.addData('%(name)s.numClicks', %(name)s.numClicks);\n"
            "psychoJS.experiment.addData('%(name)s.timesOn', %(name)s.timesOn);\n"
            "psychoJS.experiment.addData('%(name)s.timesOff', %(name)s.timesOff);\n"
        )
        buff.writeIndentedLines(code % self.params)

    def integrityCheck(self):
        super().integrityCheck()  # run parent class checks first
        alerttools.testFont(self) # Test whether font is available locally