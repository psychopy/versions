#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2022 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

from pathlib import Path
from psychopy.experiment.components import Param, getInitVals, _translate, BaseVisualComponent
from psychopy.visual import form
from psychopy.localization import _localized as __localized
_localized = __localized.copy()

__author__ = 'Jon Peirce, David Bridges, Anthony Haffey'

# only use _localized values for label values, nothing functional:
_localized.update({'Items': _translate('Items'),
                   'Text Height': _translate('Text Height'),
                   'Style': _translate('Styles'),
                   'Item Padding': _translate('Item Padding'),
                   'Data Format': _translate('Data Format'),
                   'Randomize': _translate('Randomize')
                   })
knownStyles = list(form.Form.knownStyles)


class FormComponent(BaseVisualComponent):
    """A class for presenting a survey as a Builder component"""

    categories = ['Responses']
    targets = ['PsychoPy', 'PsychoJS']
    iconFile = Path(__file__).parent / 'form.png'
    tooltip = _translate('Form: a Psychopy survey tool')
    beta = True

    def __init__(self, exp, parentName,
                 name='form',
                 items='.csv',
                 textHeight=0.03,
                 font="Open Sans",
                 randomize=False,
                 fillColor='',
                 borderColor='',
                 itemColor='white',
                 responseColor='white',
                 markerColor='red',
                 size=(1, .7),
                 pos=(0, 0),
                 style='dark',
                 itemPadding=0.05,
                 startType='time (s)', startVal='0.0',
                 stopType='duration (s)', stopVal='',
                 startEstim='', durationEstim='',
                 # legacy
                 color='white'):

        super(FormComponent, self).__init__(
            exp, parentName, name=name,
            pos=pos, size=size,
            color=color, fillColor=fillColor, borderColor=borderColor,
            startType=startType, startVal=startVal,
            stopType=stopType, stopVal=stopVal,
            startEstim=startEstim, durationEstim=durationEstim)

        # these are defined by the BaseVisual but we don't want them
        del self.params['ori']
        del self.params['units']  # we only support height units right now
        del self.params['color']

        self.type = 'Form'
        self.url = "https://www.psychopy.org/builder/components/form.html"
        self.exp.requirePsychopyLibs(['visual', 'event', 'logging'])

        # params
        self.order += ['Items', 'Randomize',  # Basic tab
                       'Data Format',  # Data tab
                      ]
        self.order.insert(self.order.index("units"), "Item Padding")

        # normal params:
        # = the usual as inherited from BaseComponent plus:

        self.params['Items'] = Param(
            items, valType='file', inputType="table", allowedTypes=[], categ='Basic',
            updates='constant',
            hint=_translate("The csv filename containing the items for your survey."),
            label=_localized['Items'])

        self.params['Text Height'] = Param(
            textHeight, valType='num', inputType="single", allowedTypes=[], categ='Formatting',
            updates='constant',
            hint=_translate("The size of the item text for Form"),
            label=_localized['Text Height'])

        self.params['Font'] = Param(
            font, valType='str', inputType="single", allowedTypes=[], categ='Formatting',
            updates='constant', allowedUpdates=["constant"],
            hint=_translate("The font name (e.g. Comic Sans)"),
            label=_translate('Font'))

        self.params['Randomize'] = Param(
            randomize, valType='bool', inputType="bool", allowedTypes=[], categ='Basic',
            updates='constant',
            hint=_translate("Do you want to randomize the order of your questions?"),
            label=_localized['Randomize'])

        self.params['Item Padding'] = Param(
            itemPadding, valType='num', inputType="single", allowedTypes=[], categ='Layout',
            updates='constant',
            hint=_translate("The padding or space between items."),
            label=_localized['Item Padding'])

        self.params['Data Format'] = Param(
            'rows', valType='str', inputType="choice", allowedTypes=[], categ='Basic',
            allowedVals=['columns', 'rows'],
            updates='constant',
            hint=_translate("Store item data by columns, or rows"),
            label=_localized['Data Format'])

        # Appearance
        for param in ['fillColor', 'borderColor', 'itemColor', 'responseColor', 'markerColor', 'Style']:
            if param in self.order:
                self.order.remove(param)
            self.order.insert(
                self.order.index("colorSpace"),
                param
            )

        self.params['Style'] = Param(
            style, valType='str', inputType="choice", categ="Appearance",
            updates='constant', allowedVals=knownStyles + ["custom..."],
            hint=_translate(
                    "Styles determine the appearance of the form"),
            label=_localized['Style'])

        for param in ['fillColor', 'borderColor', 'itemColor', 'responseColor', 'markerColor']:
            self.depends += [{
                "dependsOn": "Style",  # must be param name
                "condition": "=='custom...'",  # val to check for
                "param": param,  # param property to alter
                "true": "enable",  # what to do with param if condition is True
                "false": "disable",  # permitted: hide, show, enable, disable
            }]

        self.params['fillColor'].hint = _translate("Color of the form's background")

        self.params['borderColor'].hint = _translate("Color of the outline around the form")

        self.params['itemColor'] = Param(itemColor,
            valType='color', inputType="color", categ='Appearance',
            updates='constant',
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=_translate("Base text color for questions"),
            label=_translate("Item Color"))

        self.params['responseColor'] = Param(responseColor,
            valType='color', inputType="color", categ='Appearance',
            updates='constant',
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=_translate("Base text color for responses, also sets color of lines in sliders and borders of textboxes"),
            label=_translate("Response Color"))

        self.params['markerColor'] = Param(markerColor,
            valType='color', inputType="color", categ='Appearance',
            updates='constant',
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=_translate("Color of markers and the scrollbar"),
            label=_translate("Marker Color"))

        self.params['pos'].allowedUpdates = []
        self.params['size'].allowedUpdates = []

    def writeInitCode(self, buff):
        inits = getInitVals(self.params)
        # build up an initialization string for Form():
        code = (
            "win.allowStencil = True\n"
            "%(name)s = visual.Form(win=win, name='%(name)s',\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
            "items=%(Items)s,\n"
            "textHeight=%(Text Height)s,\n"
            "font=%(Font)s,\n"
            "randomize=%(Randomize)s,\n"
            "style=%(Style)s,\n"
            "fillColor=%(fillColor)s, borderColor=%(borderColor)s, itemColor=%(itemColor)s, \n"
            "responseColor=%(responseColor)s, markerColor=%(markerColor)s, colorSpace=%(colorSpace)s, \n"
            "size=%(size)s,\n"
            "pos=%(pos)s,\n"
            "itemPadding=%(Item Padding)s"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
            ")\n"
        )
        buff.writeIndentedLines(code % inits)

    def writeInitCodeJS(self, buff):
        inits = getInitVals(self.params)
        # build up an initialization string for Form():
        initStr = ("{name} = new visual.Form({{\n"
                   "  win : psychoJS.window, name:'{name}',\n"
                   "  items : {Items},\n"
                   "  textHeight : {Text Height},\n"
                   "  font : {Font},\n"
                   "  randomize : {Randomize},\n"
                   "  size : {size},\n"
                   "  pos : {pos},\n"
                   "  style : {Style},\n"
                   "  itemPadding : {Item Padding}\n"
                   "}});\n".format(**inits))
        buff.writeIndentedLines(initStr)

    def writeRoutineEndCode(self, buff):
        # save data, according to row/col format
        buff.writeIndented("{name}.addDataToExp(thisExp, {Data Format})\n"
                           .format(**self.params))
        buff.writeIndented("{name}.autodraw = False\n"
                           .format(**self.params))

    def writeRoutineEndCodeJS(self, buff):
        # save data, according to row/col format
        buff.writeIndented("{name}.addDataToExp(psychoJS.experiment, {Data Format});\n"
                           .format(**self.params))
