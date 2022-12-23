#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2015 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

from pathlib import Path
from psychopy.experiment.components import BaseVisualComponent, Param, \
    getInitVals, _translate
from psychopy.visual import slider
from psychopy.experiment import py2js
from psychopy import logging
from psychopy.data import utils
from psychopy.localization import _localized as __localized
_localized = __localized.copy()
import copy

__author__ = 'Jon Peirce'

# only use _localized values for label values, nothing functional:
_localized.update({'categoryChoices': _translate('Category choices'),
                   'labels': _translate('Labels'),
                   'ticks': _translate('Ticks'),
                   'forceEndRoutine': _translate('Force end of Routine'),
                   'storeHistory': _translate('Store history'),
                   'storeRating': _translate('Store rating'),
                   'storeRatingTime': _translate('Store rating time'),
                   'readOnly': _translate('readOnly')})

knownStyles = slider.Slider.knownStyles
legacyStyles = slider.Slider.legacyStyles
knownStyleTweaks = slider.Slider.knownStyleTweaks
legacyStyleTweaks = slider.Slider.legacyStyleTweaks


# ticks = (1, 2, 3, 4, 5),
# labels = None,
# pos = None,
# size = None,
# units = None,
# flip = False,
# style = 'rating',
# granularity = 0,
# textSize = 1.0,
# readOnly = False,
# color = 'LightGray',
# textFont = 'Helvetica Bold',

class SliderComponent(BaseVisualComponent):
    """A class for presenting a rating scale as a builder component
    """

    categories = ['Responses']
    targets = ['PsychoPy', 'PsychoJS']
    iconFile = Path(__file__).parent / 'slider.png'
    tooltip = _translate('Slider: A simple, flexible object for getting ratings')

    def __init__(self, exp, parentName,
                 name='slider',
                 labels='',
                 ticks="(1, 2, 3, 4, 5)",
                 initVal="",
                 size='(1.0, 0.1)',
                 pos='(0, -0.4)',
                 flip=False,
                 style='rating', styleTweaks=[],
                 granularity=0,
                 color="LightGray",
                 fillColor='Red',
                 borderColor='White',
                 font="Open Sans",
                 letterHeight=0.05,
                 startType='time (s)', startVal='0.0',
                 stopType='condition', stopVal='',
                 startEstim='', durationEstim='',
                 forceEndRoutine=True,
                 storeRating=True, storeRatingTime=True, storeHistory=False, readOnly=False):
        super(SliderComponent, self).__init__(
                exp, parentName, name,
                pos=pos, size=size,
                color=color, fillColor=fillColor, borderColor=borderColor,
                startType=startType, startVal=startVal,
                stopType=stopType, stopVal=stopVal,
                startEstim=startEstim, durationEstim=durationEstim)
        self.type = 'Slider'
        self.url = "https://www.psychopy.org/builder/components/slider.html"
        self.exp.requirePsychopyLibs(['visual', 'event'])

        # params
        self.order += ['forceEndRoutine',  # Basic tab
                       'contrast', 'styles', 'styleTweaks', # Appearance tab
                       'font',  # Formatting tab
                       'flip',  # Layout tab
                       'ticks', 'labels',  'granularity', 'readOnly',  # Data tab
                      ]
        self.order.insert(self.order.index("colorSpace"), "style")
        self.order.insert(self.order.index("units"), "Item Padding")

        # normal params:
        # = the usual as inherited from BaseVisual plus:
        self.params['ticks'] = Param(
                ticks, valType='list', inputType="single", allowedTypes=[], categ='Basic',
                updates='constant',
                hint=_translate("Tick positions (numerical) on the scale, "
                                "separated by commas"),
                label=_localized['ticks'])
        self.params['labels'] = Param(
                labels, valType='list', inputType="single", allowedTypes=[], categ='Basic',
                updates='constant',
                hint=_translate("Labels for the tick marks on the scale, "
                                "separated by commas"),
                label=_localized['labels'])
        self.params['initVal'] = Param(
            initVal, valType='code', inputType="single", categ='Basic',
            hint=_translate("Value of the slider befre any response, leave blank to hide the marker until clicked on"),
            label=_translate("Starting Value")
        )
        self.params['granularity'] = Param(
                granularity, valType='num', inputType="single", allowedTypes=[], categ='Basic',
                updates='constant',
                hint=_translate("Specifies the minimum step size "
                                "(0 for a continuous scale, 1 for integer "
                                "rating scale)"),
                label=_translate('Granularity'))
        self.params['forceEndRoutine'] = Param(
                forceEndRoutine, valType='bool', inputType="bool", allowedTypes=[], categ='Basic',
                updates='constant', allowedUpdates=[],
                hint=_translate("Should setting a rating (releasing the mouse) "
                                "cause the end of the routine (e.g. trial)?"),
                label=_localized['forceEndRoutine'])
        self.params['readOnly'] = Param(
            readOnly, valType='bool', allowedTypes=[], categ='Data',
            updates='constant', allowedUpdates=[],
            hint=_translate("Should participant be able to change the rating on the Slider?"),
            label=_localized['readOnly'])

        # advanced params:
        self.params['flip'] = Param(
                flip, valType='bool', inputType="bool", categ='Layout',
                updates='constant', allowedUpdates=[],
                hint=_translate(
                        "By default the labels will be on the bottom or "
                        "left of the scale, but this can be flipped to the "
                        "other side."),
                label=_translate('Flip'))

        # Color changes
        self.params['color'].label = _translate("Label Color")
        self.params['color'].hint = _translate("Color of all labels on this slider (might be overridden by the style setting)")
        self.params['fillColor'].label = _translate("Marker Color")
        self.params['fillColor'].hint = _translate("Color of the marker on this slider (might be overridden by the style setting)")
        self.params['borderColor'].label = _translate("Line Color")
        self.params['borderColor'].hint = _translate("Color of all lines on this slider (might be overridden by the style setting)")

        self.params['font'] = Param(
                font, valType='str', inputType="single", categ='Formatting',
                updates='constant',
                allowedUpdates=['constant', 'set every repeat'],
                hint=_translate(
                        "Font for the labels"),
                label=_translate('Font'))

        self.params['letterHeight'] = Param(
                letterHeight, valType='num', inputType="single", categ='Formatting',
                updates='constant',
                allowedUpdates=['constant', 'set every repeat'],
                hint=_translate(
                        "Letter height for text in labels"),
                label=_translate('Letter height'))

        self.params['styles'] = Param(
                style, valType='str', inputType="choice", categ='Appearance',
                updates='constant', allowedVals=knownStyles,
                hint=_translate(
                        "Discrete styles to control the overall appearance of the slider."),
                label=_translate('Styles'))

        self.params['styleTweaks'] = Param(
                styleTweaks, valType='list', inputType="multiChoice", categ='Appearance',
                updates='constant', allowedVals=knownStyleTweaks,
                hint=_translate(
                        "Tweaks to change the appearance of the slider beyond its style."),
                label=_translate('Style Tweaks'))

        # data params
        self.params['storeRating'] = Param(
                storeRating, valType='bool', inputType="bool", allowedTypes=[], categ='Data',
                updates='constant', allowedUpdates=[],
                hint=_translate("store the rating"),
                label=_localized['storeRating'])
        self.params['storeRatingTime'] = Param(
                storeRatingTime, valType='bool', inputType="bool", allowedTypes=[], categ='Data',
                updates='constant', allowedUpdates=[],
                hint=_translate("Store the time taken to make the choice (in "
                                "seconds)"),
                label=_localized['storeRatingTime'])
        self.params['storeHistory'] = Param(
                storeHistory, valType='bool', inputType="bool", allowedTypes=[], categ='Data',
                updates='constant', allowedUpdates=[],
                hint=_translate("store the history of (selection, time)"),
                label=_localized['storeHistory'])

    def writeInitCode(self, buff):

        inits = getInitVals(self.params)
        # check units
        if inits['units'].val == 'from exp settings':
            inits['units'].val = None

        inits['depth'] = -self.getPosInRoutine()

        # Use None as a start value if none set
        inits['initVal'] = inits['initVal'] or None

        # build up an initialization string for Slider():
        initStr = ("{name} = visual.Slider(win=win, name='{name}',\n"
                   "    startValue={initVal}, size={size}, pos={pos}, units={units},\n"
                   "    labels={labels}, ticks={ticks}, granularity={granularity},\n"
                   "    style={styles}, styleTweaks={styleTweaks}, opacity={opacity},\n"
                   "    labelColor={color}, markerColor={fillColor}, lineColor={borderColor}, colorSpace={colorSpace},\n"
                   "    font={font}, labelHeight={letterHeight},\n"
                   "    flip={flip}, ori={ori}, depth={depth}, readOnly={readOnly})\n"
                   .format(**inits))
        buff.writeIndented(initStr)

    def writeInitCodeJS(self, buff):
        inits = getInitVals(self.params)
        for param in inits:
            if inits[param].val in ['', None, 'None', 'none']:
                inits[param].val = 'undefined'

        # Check for unsupported units
        if inits['units'].val == 'from exp settings':
            inits['units'] = copy.copy(self.exp.settings.params['Units'])
        if inits['units'].val in ['cm', 'deg', 'degFlatPos', 'degFlat']:
            msg = ("'{units}' units for your '{name}' Slider are not currently supported for PsychoJS: "
                  "switching units to 'height'. Note, this will affect the size and positioning of '{name}'.")
            logging.warning(msg.format(units=inits['units'].val, name=inits['name'].val))
            inits['units'].val = "height"

        boolConverter = {False: 'false', True: 'true'}
        sliderStyles = {'slider': 'SLIDER',
                        'scrollbar': 'SLIDER',
                        '()': 'RATING',
                        'rating': 'RATING',
                        'radio': 'RADIO',
                        'labels45': 'LABELS_45',
                        'whiteOnBlack': 'WHITE_ON_BLACK',
                        'triangleMarker': 'TRIANGLE_MARKER'}

        # If no style given, set default 'rating' as list
        if len(inits['styles'].val) == 0:
            inits['styles'].val = 'rating'

        # reformat styles for JS
        # concatenate styles and tweaks
        tweaksList = utils.listFromString(self.params['styleTweaks'].val)
        if type(inits['styles'].val) == list:  # from an experiment <2021.1
            stylesList = inits['styles'].val + tweaksList
        else:
            stylesList = [inits['styles'].val] + tweaksList
        stylesListJS = [sliderStyles[this] for this in stylesList]
        # if not isinstance(inits['styleTweaks'].val, (tuple, list)):
        #     inits['styleTweaks'].val = [inits['styleTweaks'].val]
        # inits['styleTweaks'].val = ', '.join(["visual.Slider.StyleTweaks.{}".format(adj)
        #                                       for adj in inits['styleTweaks'].val])

        # convert that to string and JS-ify
        inits['styles'].val = py2js.expression2js(str(stylesListJS))
        inits['styles'].valType = 'code'

        inits['depth'] = -self.getPosInRoutine()

        # build up an initialization string for Slider():
        initStr = ("{name} = new visual.Slider({{\n"
                   "  win: psychoJS.window, name: '{name}',\n"
                   "  startValue: {initVal},\n"
                   "  size: {size}, pos: {pos}, ori: {ori}, units: {units},\n"
                   "  labels: {labels}, fontSize: {letterHeight}, ticks: {ticks},\n"
                   "  granularity: {granularity}, style: {styles},\n"
                   "  color: new util.Color({color}), markerColor: new util.Color({fillColor}), lineColor: new util.Color({borderColor}), \n"
                   "  opacity: {opacity}, fontFamily: {font}, bold: true, italic: false, depth: {depth}, \n"
                   ).format(**inits)
        initStr += ("  flip: {flip},\n"
                    "}});\n\n").format(flip=boolConverter[inits['flip'].val])
        buff.writeIndentedLines(initStr)

    def writeRoutineStartCode(self, buff):
        buff.writeIndented("%(name)s.reset()\n" % (self.params))

    def writeRoutineStartCodeJS(self, buff):
        buff.writeIndented("%(name)s.reset()\n" % (self.params))

    def writeFrameCode(self, buff):
        super(SliderComponent, self).writeFrameCode(buff)  # Write basevisual frame code
        forceEnd = self.params['forceEndRoutine'].val
        if forceEnd:
            code = ("\n# Check %(name)s for response to end routine\n"
                    "if %(name)s.getRating() is not None and %(name)s.status == STARTED:\n"
                    "    continueRoutine = False")
            buff.writeIndentedLines(code % (self.params))

    def writeFrameCodeJS(self, buff):
        super(SliderComponent, self).writeFrameCodeJS(buff)  # Write basevisual frame code
        forceEnd = self.params['forceEndRoutine'].val
        if forceEnd:
            code = ("\n// Check %(name)s for response to end routine\n"
                    "if (%(name)s.getRating() !== undefined && %(name)s.status === PsychoJS.Status.STARTED) {\n"
                    "  continueRoutine = false; }\n")
            buff.writeIndentedLines(code % (self.params))

    def writeRoutineEndCode(self, buff):
        name = self.params['name']
        if len(self.exp.flow._loopList):
            currLoop = self.exp.flow._loopList[-1]  # last (outer-most) loop
        else:
            currLoop = self.exp._expHandler

        # write the actual code
        storeTime = self.params['storeRatingTime'].val
        if self.params['storeRating'].val or storeTime:
            if currLoop.type in ['StairHandler', 'QuestHandler']:
                msg = ("# NB PsychoPy doesn't handle a 'correct answer' "
                       "for Slider events so doesn't know what to "
                       "tell a StairHandler (or QuestHandler)\n")
                buff.writeIndented(msg)
            elif currLoop.type in ['TrialHandler', 'ExperimentHandler']:
                loopName = currLoop.params['name']
            else:
                loopName = 'thisExp'

            if self.params['storeRating'].val == True:
                code = "%s.addData('%s.response', %s.getRating())\n"
                buff.writeIndented(code % (loopName, name, name))
            if self.params['storeRatingTime'].val == True:
                code = "%s.addData('%s.rt', %s.getRT())\n"
                buff.writeIndented(code % (loopName, name, name))
            if self.params['storeHistory'].val == True:
                code = "%s.addData('%s.history', %s.getHistory())\n"
                buff.writeIndented(code % (loopName, name, name))

            # get parent to write code too (e.g. store onset/offset times)
            super().writeRoutineEndCode(buff)

    def writeRoutineEndCodeJS(self, buff):
        name = self.params['name']
        if len(self.exp.flow._loopList):
            currLoop = self.exp.flow._loopList[-1]  # last (outer-most) loop
        else:
            currLoop = self.exp._expHandler

        # write the actual code
        storeTime = self.params['storeRatingTime'].val
        if self.params['storeRating'].val or storeTime:
            if currLoop.type in ['StairHandler', 'QuestHandler']:
                msg = ("/* NB PsychoPy doesn't handle a 'correct answer' "
                       "for Slider events so doesn't know what to "
                       "tell a StairHandler (or QuestHandler)*/\n")
                buff.writeIndented(msg)

            if self.params['storeRating'].val == True:
                code = "psychoJS.experiment.addData('%s.response', %s.getRating());\n"
                buff.writeIndented(code % (name, name))
            if self.params['storeRatingTime'].val == True:
                code = "psychoJS.experiment.addData('%s.rt', %s.getRT());\n"
                buff.writeIndented(code % (name, name))
            if self.params['storeHistory'].val == True:
                code = "psychoJS.experiment.addData('%s.history', %s.getHistory());\n"
                buff.writeIndented(code % (name, name))
